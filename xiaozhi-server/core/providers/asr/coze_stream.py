import json
import gzip
import uuid
import asyncio
import websockets
import opuslib_next
from core.providers.asr.base import ASRProviderBase
from config.logger import setup_logging
from core.providers.asr.dto.dto import InterfaceType
from typing import TYPE_CHECKING, Optional, Any, Tuple
import time
import base64

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
    
TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """Coze 流式语音识别 ASR Provider（独立 WebSocket 连接）

    协议完全对齐 realtime_voice.py 的双向流式对话模式：
      - ASR 文本通过 conversation.message.delta(role=user) 返回
      - ASR 完成通过 conversation.message.completed(role=user) / conversation.chat.created 触发
      - 不手动发送 input_audio_buffer.complete，由 Coze server_vad 自动检测语音结束
    """

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file

        # Coze 配置
        self.access_token: str = config.get("access_token", "")
        self.bot_id: str = config.get("bot_id", "")

        # Opus 解码器（16kHz, 单声道）
        self.decoder = opuslib_next.Decoder(16000, 1)

        # WebSocket 连接
        self.ws: Optional[Any] = None
        self.result_task: Optional[asyncio.Task] = None
        self.is_processing: bool = False
        self._is_stopping: bool = False

        # 会话就绪事件（每轮创建新的）
        self._ready_event: Optional[asyncio.Event] = None

        # 轮次 ID（每轮递增，用于隔离）
        self._round_id: int = 0
        self._current_round: int = 0

        # ASR 结果
        self.text: str = ""

        # 音频帧计数
        self._audio_frame_count: int = 0

        # 消息序列号
        self._event_seq: int = 0

        # 最小音频帧数门槛（防止客户端 VAD 过早停止发送音频）
        self._MIN_FRAMES: int = 50

    def _next_id(self) -> str:
        """生成唯一消息 ID"""
        self._event_seq += 1
        return f"asr_{int(time.time()*1000)}_{self._event_seq:04d}"

    async def _send(self, event: dict) -> None:
        """发送 JSON 事件到 WebSocket"""
        if self.ws:
            await self.ws.send(json.dumps(event, ensure_ascii=False))

    async def open_audio_channels(self, conn: "ConnectionHandler") -> None:
        """打开音频通道"""
        await super().open_audio_channels(conn)

    async def receive_audio(
        self, conn: "ConnectionHandler", audio: bytes, audio_have_voice: bool
    ) -> None:
        """接收音频数据并发送到 Coze ASR 服务端

        协议流程（对齐 realtime_voice.py）：
          1. 检测到语音 → 连接 + 发 chat.update → 等待 chat.updated 确认
          2. 确认后持续发送 input_audio_buffer.append（不手动发 complete）
          3. Coze server_vad 自动检测语音结束 → 返回 message.delta/completed
          4. 收到 completed/chat.created → 触发 handle_voice_stop
        """
        await super().receive_audio(conn, audio, audio_have_voice)

        current_round = self._current_round

        # ★ 预连接：在 listen 状态的首帧音频到达时就建立连接
        # （不等待 audio_have_voice，避免用户说完才连上的问题）
        if not self.is_processing:
            try:
                await self._cleanup()

                # 新一轮：递增 round_id + 创建全新 Event
                self._round_id += 1
                self._current_round = self._round_id
                self._ready_event = asyncio.Event()

                self.is_processing = True
                self._is_stopping = False
                self.text = ""
                self._audio_frame_count = 0
                self._event_seq = 0

                logger.bind(tag=TAG).info(
                    f"=== ASR 第 {self._round_id} 轮开始 ==="
                )

                ws_url = f"wss://ws.coze.cn/v1/chat?bot_id={self.bot_id}"
                logger.bind(tag=TAG).info(f"正在连接 Coze ASR 服务")

                self.ws = await websockets.connect(
                    ws_url,
                    additional_headers={"Authorization": f"Bearer {self.access_token}"},
                    ping_interval=15,
                    ping_timeout=10,
                    close_timeout=5,
                )

                await self._send_chat_update()
                logger.bind(tag=TAG).info("已发送 ASR chat.update 配置，等待确认...")

                self.result_task = asyncio.create_task(
                    self._forward_asr_results(conn, self._round_id)
                )
                logger.bind(tag=TAG).info("Coze ASR 已连接，等待会话就绪...")

                try:
                    await asyncio.wait_for(self._ready_event.wait(), timeout=10.0)
                    logger.bind(tag=TAG).info(
                        f"ASR 会话已就绪 (第{self._round_id}轮), 开始接收音频"
                    )
                except asyncio.TimeoutError:
                    logger.bind(tag=TAG).error("ASR 等待 chat.updated 确认超时 (10s)")
                    await self._cleanup()
                    return

            except Exception as e:
                logger.bind(tag=TAG).error(f"建立 Coze ASR 连接失败: {e}")
                await self._cleanup()
                return

        # 发送当前音频数据（仅会话就绪后 + 当前轮次匹配）
        # ★ 关键：不检查 client_voice_stop，持续发送直到收到服务端完成信号
        # （与 realtime_voice.py 的 _mic_loop 一致：持续发送，不手动 complete）
        if (
            self.ws
            and self.is_processing
            and not self._is_stopping
            and self._ready_event is not None
            and self._ready_event.is_set()
            and self._current_round == current_round
        ):
            try:
                pcm_frame = self.decoder.decode(audio, 960)
                if pcm_frame and len(pcm_frame) > 0:
                    b64_data = base64.b64encode(pcm_frame).decode("utf-8")
                    await self._send({
                        "id": self._next_id(),
                        "event_type": "input_audio_buffer.append",
                        "data": {"delta": b64_data},
                    })
                    self._audio_frame_count += 1
            except Exception as e:
                logger.bind(tag=TAG).debug(f"发送音频数据异常: {e}")

    async def _send_chat_update(self) -> None:
        """发送 chat.update 配置事件（与 realtime_voice.py configure_call 一致）

        注意：包含 output_audio 配置（即使我们不用 TTS 功能，
        Coze 协议要求配置完整的对话参数）
        """
        self._connect_start = time.time()
        await self._send({
            "id": self._next_id(),
            "event_type": "chat.update",
            "data": {
                "chat_config": {
                    "user_id": f"asr_{uuid.uuid4().hex[:12]}",
                    "auto_save_history": True,
                },
                "input_audio": {
                    "format": "pcm",
                    "codec": "pcm",
                    "sample_rate": 16000,
                    "channel": 1,
                    "bit_depth": 16,
                },
                "output_audio": {
                    "codec": "pcm",
                    "pcm_config": {"sample_rate": 24000},
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

    async def _forward_asr_results(
        self, conn: "ConnectionHandler", round_id: int
    ) -> None:
        """监听 Coze 返回的事件，提取 ASR 识别结果

        事件协议（对齐 realtime_voice.py _recv_loop）：
          - conversation.message.delta(role=user) → ASR 流式文本
          - conversation.message.completed(role=user) → 用户消息完成
          - conversation.chat.created → 服务端开始处理（用户说完的确认）
          - 不再使用 audio_transcript 系列（那是错误的 API）
        """
        try:
            while self.ws and not conn.stop_event.is_set():
                if self._current_round != round_id:
                    logger.bind(tag=TAG).info(
                        f"ASR 监听任务轮次过期 ({round_id} != {self._current_round}), 退出"
                    )
                    break

                try:
                    msg = await asyncio.wait_for(self.ws.recv(), timeout=0.5)
                except asyncio.TimeoutError:
                    continue
                except Exception as e:
                    logger.bind(tag=TAG).warning(f"Coze ASR recv 异常: {e}")
                    break

                if isinstance(msg, bytes):
                    continue

                try:
                    data = json.loads(msg)
                except json.JSONDecodeError:
                    continue

                event_type = data.get("event_type", "")

                # ====== 连接事件 ======
                if event_type == "chat.created":
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).info(
                        f"ASR chat.created (第{round_id}轮), logid={logid}"
                    )

                elif event_type == "chat.updated":
                    logger.bind(tag=TAG).info(
                        f"ASR chat.updated 配置已确认 (第{round_id}轮)"
                    )
                    if self._ready_event:
                        self._ready_event.set()

                # ====== ASR 文本（两种事件都支持）======
                # 优先: audio_transcript（Coze ASR 模式实际返回的）
                # 备选: message.delta(role=user)（对话模式）
                elif event_type == "conversation.audio_transcript.update":
                    payload = data.get("data", {})
                    text = (
                        payload.get("text")
                        or payload.get("content")
                        or payload.get("delta")
                        or ""
                    )
                    if text:
                        self.text = text  # 完整渐进文本（每次替换）
                        logger.bind(tag=TAG).info(f"[Coze ASR] 转写: {text}")

                elif event_type == "conversation.message.delta":
                    payload = data.get("data", {})
                    role = payload.get("role", "")
                    content = payload.get("content", "")

                    if role == "user" and content:
                        # 对话模式下的 ASR 文本（备选路径）
                        self.text = content
                        logger.bind(tag=TAG).info(f"[Coze ASR] 转写(message): {content}")

                    elif role == "assistant" and content:
                        logger.bind(tag=TAG).debug(f"[Coze ASR] Bot 回复: {content}")

                # ====== ASR 完成信号 ======
                # 优先: audio_transcript.completed（ASR 模式的主要完成信号）
                elif event_type == "conversation.audio_transcript.completed":
                    logger.bind(tag=TAG).info(
                        f"[Coze ASR] 转写完成 (第{round_id}轮), 最终结果: {self.text}"
                    )
                    if self.text.strip() and len(conn.asr_audio) > 15:
                        await self.handle_voice_stop(conn, conn.asr_audio.copy())
                    break

                # 备选: message.completed(role=user)（对话模式的完成信号）
                elif event_type == "conversation.message.completed":
                    payload = data.get("data", {})
                    role = payload.get("role", "")

                    if role == "user":
                        logger.bind(tag=TAG).info(
                            f"[Coze ASR] 用户消息完成 (第{round_id}轮), "
                            f"最终结果: {self.text}"
                        )
                        if self.text.strip() and len(conn.asr_audio) > 15:
                            await self.handle_voice_stop(conn, conn.asr_audio.copy())
                        break

                    elif role == "assistant":
                        logger.bind(tag=TAG).debug(
                            f"Bot 消息完成 (第{round_id}轮)"
                        )

                # ====== 对话生命周期（对齐 realtime_voice.py:470-475）======
                elif event_type == "conversation.chat.created":
                    # 服务端开始处理 → 确认用户已说完
                    # 兜底：如果之前没被 message.completed 触发，在这里触发
                    logger.bind(tag=TAG).info(
                        f"ASR conversation.chat.created (第{round_id}轮)"
                    )
                    if self.text.strip() and len(conn.asr_audio) > 15:
                        logger.bind(tag=TAG).info(
                            f"[Coze ASR] 基于 chat.created 触发 (第{round_id}轮): {self.text}"
                        )
                        await self.handle_voice_stop(conn, conn.asr_audio.copy())
                    break

                elif event_type == "conversation.chat.in_progress":
                    logger.bind(tag=TAG).debug("ASR: conversation.chat.in_progress")

                elif event_type == "conversation.chat.completed":
                    logger.bind(tag=TAG).debug("ASR: conversation.chat.completed")
                    break

                elif event_type == "conversation.chat.failed":
                    logger.bind(tag=TAG).error("ASR: conversation.chat.failed")
                    break

                # ====== VAD 事件 ======
                elif event_type == "input_audio_buffer.speech_started":
                    logger.bind(tag=TAG).info("ASR: 服务端 VAD 检测到语音")

                elif event_type == "input_audio_buffer.speech_stopped":
                    logger.bind(tag=TAG).info("ASR: 服务端 VAD 检测到静音")

                # ====== 音频事件（Bot 侧，忽略）======
                elif event_type == "conversation.audio.delta":
                    logger.bind(tag=TAG).debug("ASR: 收到 Bot 音频 delta (忽略)")

                elif event_type == "conversation.audio.sentence_start":
                    logger.bind(tag=TAG).debug("ASR: Bot 音频句子开始 (忽略)")

                elif event_type == "conversation.audio.completed":
                    logger.bind(tag=TAG).debug("ASR: Bot 音频完成 (忽略)")

                # ====== 错误 ======
                elif event_type == "error":
                    error_code = data.get("data", {}).get("code")
                    error_msg = data.get("data", {}).get("msg", str(data))
                    logid = data.get("detail", {}).get("logid", "")
                    logger.bind(tag=TAG).error(
                        f"Coze ASR 错误 (第{round_id}轮): "
                        f"code={error_code}, msg={error_msg}, logid={logid}"
                    )
                    break

                else:
                    logger.bind(tag=TAG).info(f"ASR 未处理事件: {event_type}")

            logger.bind(tag=TAG).info(
                f"ASR 监听循环结束 (第{round_id}轮), text='{self.text}', "
                f"frames={self._audio_frame_count}"
            )

        except asyncio.CancelledError:
            logger.bind(tag=TAG).info(f"ASR 监听任务被取消 (第{round_id}轮)")
        except Exception as e:
            logger.bind(tag=TAG).error(
                f"Coze ASR 结果处理异常 (第{round_id}轮): {e}"
            )
        finally:
            if self._current_round == round_id:
                await self._cleanup()

    async def _cleanup(self) -> None:
        """清理连接和状态"""
        if self.result_task and not self.result_task.done():
            self.result_task.cancel()
            try:
                await self.result_task
            except (asyncio.CancelledError, Exception):
                pass
            self.result_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

        self.is_processing = False
        self._is_stopping = False
        if self._ready_event:
            self._ready_event.clear()

    def stop_ws_connection(self) -> None:
        """停止 ASR 连接"""
        if self.ws or self.is_processing:
            asyncio.ensure_future(self._cleanup())

    async def speech_to_text(
        self,
        opus_data,
        session_id: str,
        audio_format: str = "opus",
        artifacts=None,
    ) -> Tuple[Optional[str], Optional[str]]:
        """返回 ASR 识别结果文本"""
        result = self.text
        self.text = ""
        return result, None

    async def close(self) -> None:
        """资源清理"""
        await self._cleanup()
        if hasattr(self, "decoder") and self.decoder:
            try:
                del self.decoder
                self.decoder = None
            except Exception as e:
                logger.bind(tag=TAG).debug(f"释放 dec