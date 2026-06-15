import json
import asyncio
import time
import base64
import websockets
import opuslib_next  # type: ignore[import]
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from typing import TYPE_CHECKING, Optional, Any, Tuple

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """Coze 流式语音识别 ASR Provider

    协议对齐官方文档 coze_asr_docs.md：
      - 配置：transcriptions.update / transcriptions.updated
      - 文本：transcriptions.message.update(data.content) 全量渐进文本
      - 完成：transcriptions.message.completed

    延迟优化：
      - 音频帧批量发送（减少 WebSocket 消息开销，从 ~50msg/s 降至 ~10msg/s）
      - Opus 直传模式（跳过 Opus→PCM 解码，直接 base64 上传 Opus 数据）
    """

    # 批量发送参数：每批累积帧数（每帧 20ms，5 帧 = 100ms 一批）
    _BATCH_FRAME_COUNT: int = 5
    # 最大批量间隔（毫秒），超时后即使未攒够帧数也发送
    _BATCH_MAX_INTERVAL_MS: int = 80
    # 空闲超时（秒）：超过此时间无活动则视为连接过期，下一轮重建
    _IDLE_TIMEOUT: float = 120.0

    def __init__(self, config: dict[str, Any], delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config: dict[str, Any] = config
        self.text: str = ""
        self.output_dir: str = config.get("output_dir", "tmp/")
        self.delete_audio_file: bool = delete_audio_file

        # Coze 配置
        self.access_token: str = config.get("access_token", "")
        self.bot_id: str = config.get("bot_id", "")

        # Opus 直传模式标志（默认关闭：需要 OGG 容器封装，裸 Opus 包会导致服务端 717995003 错误）
        # 参考 realtime_voice.py 使用 PCM 模式验证通过
        self._use_opus_input: bool = config.get("asr_opus_input", False)

        if self._use_opus_input:
            # Opus 直传模式：不需要 PCM 解码器，直接上传 Opus 数据
            self.decoder: Any = None
        else:
            # PCM 模式：需要 Opus 解码器将 ESP32 的 Opus 帧解码为 PCM
            self.decoder: Any = opuslib_next.Decoder(16000, 1)  # type: ignore[assignment]

        # WebSocket 连接
        self.ws: Optional[Any] = None
        self.result_task: Optional[asyncio.Task[Any]] = None
        self.is_processing: bool = False  # 处理状态标志
        self._is_stopping: bool = False  # 停止标志，防止竞态条件
        self._ws_connected_time: float = 0.0  # 连接建立时间，用于空闲超时判断

        # 会话就绪事件（每轮复用，不重新创建）
        self._ready_event: Optional[asyncio.Event] = None

        # 轮次 ID（每轮递增，用于隔离）
        self._round_id: int = 0
        self._current_round: int = 0

        # 音频帧计数
        self._audio_frame_count: int = 0

        # 消息序列号
        self._event_seq: int = 0

        # === 批量发送缓冲区 ===
        self._batch_buffer: bytearray = bytearray()
        self._batch_frame_count: int = 0
        self._batch_last_send_time: float = 0.0

    def _next_id(self) -> str:
        """生成唯一消息 ID"""
        self._event_seq += 1
        return f"asr_{int(time.time()*1000)}_{self._event_seq:04d}"

    async def _send(self, event: dict[str, Any]) -> None:
        """发送 JSON 事件到 WebSocket"""
        if self.ws:
            raw = json.dumps(event, ensure_ascii=False)
            etype = event.get("event_type", "?")
            logger.bind(tag=TAG).debug(f"[ASR SEND] {etype} → {raw[:200]}")
            await self.ws.send(raw)

    async def open_audio_channels(self, conn: "ConnectionHandler") -> None:
        await super().open_audio_channels(conn)

    async def _flush_batch(self) -> None:
        """将批量缓冲区的音频数据一次性发送到 Coze ASR 服务"""
        if not self._batch_buffer or not self.ws:
            return

        b64_data = base64.b64encode(bytes(self._batch_buffer)).decode("utf-8")
        self._batch_buffer.clear()
        self._batch_frame_count = 0
        self._batch_last_send_time = time.monotonic()

        try:
            await self._send({
                "id": self._next_id(),
                "event_type": "input_audio_buffer.append",
                "data": {"delta": b64_data},
            })
        except Exception as e:
            logger.bind(tag=TAG).debug(f"批量发送音频数据异常: {e}")

    async def receive_audio(self, conn: "ConnectionHandler", audio: bytes, audio_have_voice: bool) -> None:
        # 先调用父类方法处理基础逻辑
        await super().receive_audio(conn, audio, audio_have_voice)  # type: ignore[arg-type]

        current_round = self._current_round

        # 首帧到达时：新建连接 或 复用已有连接开启新轮次
        if not self.is_processing:
            if self._is_ws_healthy():
                # === 跨轮次复用：WS 已存在且健康，仅重置轮次状态 ===
                await self._start_new_round()
                logger.bind(tag=TAG).info(
                    f"=== ASR 第 {self._round_id} 轮开始 [复用连接, opus_input={self._use_opus_input}] ==="
                )
            else:
                # === 需要新建连接（对齐参考实现：并发收发，不阻塞等响应）===
                try:
                    await self._cleanup_ws()  # 仅清理 WS，不重置轮次计数

                    # 新一轮：递增 round_id + 创建 Event
                    self._round_id += 1
                    self._current_round = self._round_id
                    if self._ready_event is None:
                        self._ready_event = asyncio.Event()
                    else:
                        self._ready_event.clear()

                    self.is_processing = True
                    self._is_stopping = False
                    self.text = ""
                    self._audio_frame_count = 0
                    self._event_seq = 0
                    self._batch_buffer.clear()
                    self._batch_frame_count = 0
                    self._batch_last_send_time = time.monotonic()

                    logger.bind(tag=TAG).info(
                        f"=== ASR 第 {self._round_id} 轮开始 [新建连接, opus_input={self._use_opus_input}] ==="
                    )

                    ws_url = f"wss://ws.coze.cn/v1/chat?bot_id={self.bot_id}"
                    logger.bind(tag=TAG).info(f"[ASR] 正在连接 {ws_url}")

                    self.ws = await websockets.connect(
                        ws_url,
                        additional_headers={"Authorization": f"Bearer {self.access_token}"},  # type: ignore[arg-type]
                        ping_interval=15,
                        ping_timeout=10,
                        close_timeout=5,
                    )
                    self._ws_connected_time = time.monotonic()

                    # 发送初始化配置请求
                    await self._send_chat_update()
                    logger.bind(tag=TAG).info("已发送 chat.update 配置")

                    # ★ 关键改动：不等待 chat.updated 响应就立即标记可发音频
                    #   对齐参考实现 realtime_voice.py 的并发收发模型：
                    #   configure_call() 后立即启动 mic 线程和 recv 线程并发运行
                    self._ready_event.set()
                    logger.bind(tag=TAG).info("ASR 会话已就绪（并发模式，不阻塞等确认）")

                    # 启动接收ASR结果的异步任务（长生命周期，跨轮次复用）
                    if self.result_task is None or self.result_task.done():
                        self.result_task = asyncio.create_task(
                            self._forward_asr_results(conn)
                        )

                except Exception as e:
                    logger.bind(tag=TAG).error(f"建立 Coze ASR 连接失败: {str(e)}")
                    await self._cleanup()
                    return

        # 发送当前音频数据（仅会话就绪后 + 当前轮次匹配）
        if (
            self.ws
            and self.is_processing
            and not self._is_stopping
            and self._ready_event is not None
            and self._ready_event.is_set()
            and self._current_round == current_round
        ):
            try:
                if self._use_opus_input:
                    raw_audio: bytes = audio
                else:
                    pcm_frame: Any = self.decoder.decode(audio, 960)  # type: ignore[assignment]
                    if not pcm_frame or len(pcm_frame) == 0:
                        return
                    raw_audio = pcm_frame  # type: ignore[assignment]

                # 累积到批量缓冲区
                self._batch_buffer.extend(raw_audio)
                self._batch_frame_count += 1
                self._audio_frame_count += 1

                # 判断是否需要发送（达到批量大小时 或 超过时间间隔）
                now = time.monotonic()
                should_flush: bool = (
                    self._batch_frame_count >= self._BATCH_FRAME_COUNT
                    or (now - self._batch_last_send_time) * 1000 >= self._BATCH_MAX_INTERVAL_MS
                )
                if should_flush:
                    await self._flush_batch()

            except Exception as e:
                logger.bind(tag=TAG).debug(f"处理音频数据异常: {e}")

    def _is_ws_healthy(self) -> bool:
        """检查现有 ASR WebSocket 连接是否健康可复用"""
        if not self.ws or not self.result_task or self.result_task.done():
            return False
        # 检查空闲超时
        if self._ws_connected_time > 0 and (time.monotonic() - self._ws_connected_time) > self._IDLE_TIMEOUT:
            return False
        return True

    async def _start_new_round(self) -> None:
        """在已有健康连接上开启新一轮 ASR（不重建 WebSocket）

        跨轮次复用核心：仅重置轮次状态 + 重发 chat.update 配置，
        WebSocket 和监听任务保持不变。
        """
        # 递增轮次 ID
        self._round_id += 1
        self._current_round = self._round_id

        # 复用 ready_event（clear 后重新等待确认）
        if self._ready_event is None:
            self._ready_event = asyncio.Event()
        else:
            self._ready_event.clear()

        # 重置轮次状态
        self.is_processing = True
        self._is_stopping = False
        self.text = ""
        self._audio_frame_count = 0
        self._event_seq = 0
        self._batch_buffer.clear()
        self._batch_frame_count = 0
        self._batch_last_send_time = time.monotonic()

        # 重新发送配置（每轮必须重新配置）
        await self._send_chat_update()

        # 并发模式：立即标记可发音频，不等待服务端确认
        self._ready_event.set()

    async def _send_chat_update(self) -> None:
        """发送 chat.update 配置事件（对齐 /v1/chat 端点协议）

        参考实现: realtime_voice.py — configure_call()
        注意: /v1/chat 是统一对话端点，使用 chat.* 事件族（非 transcriptions.*）。
              transcriptions.* 是独立 ASR 端点的协议，在此端点上会返回 4000 错误。

        必须包含 chat_config / output_audio / turn_detection 等完整配置，
        否则服务端不会返回 chat.created / chat.updated 确认事件。
        """
        if self._use_opus_input:
            # Opus 直传模式：告诉 Coze 输入为 Opus 编码
            input_audio: dict[str, Any] = {
                "format": "ogg",
                "codec": "opus",
                "sample_rate": 16000,
                "channel": 1,
            }
        else:
            # PCM 模式
            input_audio = {
                "format": "pcm",
                "codec": "pcm",
                "sample_rate": 16000,
                "channel": 1,
                "bit_depth": 16,
            }

        await self._send({
            "id": self._next_id(),
            "event_type": "chat.update",
            "data": {
                # 对齐 realtime_voice.py configure_call() 精确结构
                "chat_config": {
                    "user_id": "xiaozhi_asr_user",
                    "auto_save_history": True,
                    "meta_data": {"source": "xiaozhi_esp32"},
                },
                "input_audio": input_audio,
                "output_audio": {
                    "codec": "pcm",
                    "pcm_config": {"sample_rate": 16000},
                    "speech_rate": 0,
                    "loudness_rate": 0,
                },
                "turn_detection": {
                    "type": "server_vad",
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 600,
                },
                "asr_config": {
                    "stream_mode": "bidirectional_stream",
                    "enable_punc": True,
                    "enable_itn": True,
                    "enable_ddc": True,
                },
            },
        })
        logger.bind(tag=TAG).info("[ASR] chat.update 已发送 (对齐 realtime_voice.py)")

    async def _forward_asr_results(self, conn: "ConnectionHandler") -> None:
        """长期运行任务：监听 Coze ASR 服务端消息，跨轮次复用同一 WS

        对齐 realtime_voice.py 参考实现的对话结束检测逻辑：
          - 服务端 VAD（turn_detection.server_vad）检测用户说话结束
          - 主信号：conversation.message.completed (role=user)
          - 备选信号：conversation.audio_transcript.completed
          - 生命周期：chat.created → chat.in_progress → chat.completed

        不使用客户端静默超时，完全由服务端 VAD 判定说话结束。
        """
        try:
            while self.ws and not conn.stop_event.is_set():
                active_round = self._current_round

                # 获取当前连接的音频数据
                audio_data: list[bytes] = conn.asr_audio  # type: ignore[assignment]

                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).info("Coze ASR 连接已关闭")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"Coze ASR recv 异常: {e}")
                    if hasattr(e, "__cause__") and e.__cause__:
                        logger.bind(tag=TAG).warning(f"错误原因: {str(e.__cause__)}")
                    break

                if isinstance(msg, bytes):
                    continue

                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("event_type", "")

                # 全量事件日志：排查服务端响应问题（无论是否处理都记录）
                logger.bind(tag=TAG).debug(
                    f"[ASR RECV] event_type={event_type}, "
                    f"round={active_round}, processing={self.is_processing}"
                )

                # ============================================================
                # 连接事件（/v1/chat 端点协议）
                # ============================================================
                if event_type == "chat.created":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(f"[连接] 已接通 (第{active_round}轮), logid={logid}")
                    # fallback: chat.created 也标记就绪，避免 chat.updated 延迟时卡住
                    if self._ready_event and not self._ready_event.is_set():
                        self._ready_event.set()
                        logger.bind(tag=TAG).info("[连接] ★ chat.created 触发就绪 (fallback)")

                elif event_type == "chat.updated":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(
                        f"[配置] chat.updated 已确认 (第{active_round}轮), logid={logid}"
                    )
                    if self._ready_event:
                        self._ready_event.set()

                # ============================================================
                # ★ VAD：服务端检测到用户开始说话（不等 ASR 结果）
                #    对齐 realtime_voice.py L428-430
                # ============================================================
                elif event_type == "input_audio_buffer.speech_started":
                    logger.bind(tag=TAG).debug(
                        f"[VAD] speech_started — 用户开始说话 (第{active_round}轮)"
                    )

                # ============================================================
                # ★ ASR 流式文本（主来源：对齐 realtime_voice.py L435-448）
                # ============================================================
                elif event_type == "conversation.message.delta":
                    payload = data.get("data", {})
                    role: str = payload.get("role", "")
                    content: str = payload.get("content", "")
                    if role == "user" and content:
                        self.text = content
                        logger.bind(tag=TAG).info(f"[ASR] 转写: {content}")

                # ============================================================
                # ★ ASR 文本更新（备选来源：audio_transcript）
                # ============================================================
                elif event_type == "conversation.audio_transcript.update":
                    payload = data.get("data", {})
                    transcript: str = (
                        payload.get("content", "")
                        or payload.get("text", "")
                        or payload.get("delta", "")
                    )
                    if transcript:
                        self.text = transcript
                        logger.bind(tag=TAG).info(f"[ASR] 转写(transcript): {transcript}")

                # ============================================================
                # ★ 用户说话结束 — 服务端 VAD 判定（主信号）
                #    对齐 realtime_voice.py L457-463
                # ============================================================
                elif event_type == "conversation.message.completed":
                    payload = data.get("data", {})
                    role = payload.get("role", "")
                    if role == "user":
                        logid = data.get("detail", {}).get("logid", "")
                        logger.bind(tag=TAG).info(
                            f"[VAD] 用户说完 (第{active_round}轮), "
                            f"转写结果: '{self.text}', logid={logid}"
                        )
                        if self.text.strip() and len(audio_data) > 15:
                            await self.handle_voice_stop(conn, audio_data.copy())
                        self.is_processing = False

                # ============================================================
                # ★ 转写完成（备选信号）
                # ============================================================
                elif event_type == "conversation.audio_transcript.completed":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(
                        f"[ASR] audio_transcript.completed (第{active_round}轮), "
                        f"最终结果: '{self.text}', logid={logid}"
                    )
                    # 仅在 message.completed 未触发时才处理（避免重复）
                    if self.is_processing and self.text.strip() and len(audio_data) > 15:
                        await self.handle_voice_stop(conn, audio_data.copy())
                    self.is_processing = False

                # ============================================================
                # 对话生命周期（对齐 realtime_voice.py L470-513）
                # ============================================================

                elif event_type == "conversation.chat.created":
                    # 服务端开始处理用户输入 → 进入思考状态
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(
                        f"[生命周期] chat.created — 服务端开始处理 (第{active_round}轮), "
                        f"logid={logid}"
                    )

                elif event_type == "conversation.chat.in_progress":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).debug(
                        f"[生命周期] chat.in_progress (第{active_round}轮), logid={logid}"
                    )

                elif event_type == "conversation.chat.completed":
                    # 整轮对话完成（ASR + LLM + TTS 全部结束）
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(
                        f"[生命周期] chat.completed — 本轮结束 (第{active_round}轮), "
                        f"logid={logid}"
                    )
                    self.is_processing = False
                    # 不 break —— 允许下一轮复用此连接

                elif event_type == "conversation.chat.failed":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).error(
                        f"[生命周期] chat.failed (第{active_round}轮), logid={logid}"
                    )
                    self.is_processing = False

                # ============================================================
                # 音频缓冲区事件
                # ============================================================
                elif event_type == "input_audio_buffer.completed":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).debug(f"ASR: input_audio_buffer.completed, logid={logid}")

                elif event_type == "input_audio_buffer.cleared":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).debug(f"ASR: input_audio_buffer.cleared, logid={logid}")

                # ============================================================
                # 错误
                # ============================================================
                elif event_type == "error":
                    error_code = data.get("data", {}).get("code")
                    error_msg = data.get("data", {}).get("msg", str(data))
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).error(
                        f"Coze ASR 错误 (第{active_round}轮): "
                        f"code={error_code}, msg={error_msg}, logid={logid}"
                    )
                    self.is_processing = False

                else:
                    logger.bind(tag=TAG).info(f"ASR 未处理事件: {event_type}")

            logger.bind(tag=TAG).info(
                f"ASR 监听循环退出, text='{self.text}', frames={self._audio_frame_count}"
            )

        except asyncio.CancelledError:
            logger.bind(tag=TAG).info("ASR 监听任务被取消")
        except Exception as e:
            logger.bind(tag=TAG).error(f"Coze ASR 结果处理异常: {e}")
            if hasattr(e, "__cause__") and e.__cause__:
                logger.bind(tag=TAG).error(f"异常根因: {str(e.__cause__)}")
        finally:
            # 循环退出后清理（WS 已断开或严重错误）
            await self._cleanup()
            conn.reset_audio_states()

    async def _send_stop_request(self) -> None:
        """发送停止信号通知服务端结束当前语音输入

        延迟优化：发送前先 flush 残留的批量缓冲区数据，确保所有音频都已上传。
        """
        self._is_stopping = True  # 先标记为停止状态，阻止后续音频发送
        # 先 flush 残留的批量数据
        await self._flush_batch()
        if self.ws:
            try:
                await self._send({
                    "id": self._next_id(),
                    "event_type": "input_audio_buffer.complete",
                    "data": {},
                })
                logger.bind(tag=TAG).debug("已发送 input_audio_buffer.complete")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"发送停止信号时出错: {e}")

    async def _send_clear_buffer(self) -> None:
        """发送清除缓冲区请求（对齐官方文档 input_audio_buffer.clear）"""
        if self.ws:
            try:
                await self._send({
                    "id": self._next_id(),
                    "event_type": "input_audio_buffer.clear",
                })
                logger.bind(tag=TAG).debug("已发送 input_audio_buffer.clear")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"发送清除缓冲区时出错: {e}")

    def stop_ws_connection(self) -> None:
        """停止 ASR 连接"""
        if self.ws:
            asyncio.create_task(self.ws.close())
            self.ws = None
        self.is_processing = False
        self._is_stopping = False

    async def speech_to_text(
        self,
        opus_data: list[Any],
        session_id: str,
        audio_format: str = "opus",
        artifacts: Optional[Any] = None,
    ) -> Tuple[Optional[str], Optional[str]]:
        result = self.text
        self.text = ""  # 清空text
        return result, None

    async def close(self) -> None:
        """资源清理方法（完整清理，关闭 WS 和所有状态）"""
        await self._cleanup()
        # 重置所有状态
        self.text = ""  # 清空text
        self._audio_frame_count = 0
        self._event_seq = 0
        self._round_id = 0
        self._current_round = 0
        self._batch_buffer.clear()
        self._batch_frame_count = 0
        # 显式释放 decoder 资源（仅 PCM 模式下存在）
        if hasattr(self, "decoder") and self.decoder is not None:
            try:
                del self.decoder
                self.decoder = None
                logger.bind(tag=TAG).debug("Coze decoder resources released")
            except Exception as e:
                logger.bind(tag=TAG).debug(f"释放 decoder 资源时出错: {e}")
    async def _cleanup_ws(self) -> None:
        """仅清理 WebSocket 连接，保留轮次计数等状态（用于重建连接前）"""
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        self._ws_connected_time = 0.0

    async def _cleanup(self) -> None:
        """完整清理：WebSocket + 所有状态（监听循环退出后调用）"""
        if self.result_task and not self.result_task.done():
            self.result_task.cancel()
            try:
                await self.result_task
            except (asyncio.CancelledError, Exception):
                pass
            self.result_task = None

        await self._cleanup_ws()

        self.is_processing = False
        self._is_stopping = False
        if self._ready_event:
            self._ready_event.clear()
