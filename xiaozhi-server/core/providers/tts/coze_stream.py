import os
import uuid
import json
import base64
import queue
import asyncio
import traceback
import time

from typing import TYPE_CHECKING, Callable, Optional, Any, Coroutine
from asyncio import Task
import websockets

from config.logger import setup_logging
from core.utils.util import check_model_key  # type: ignore[import]
from core.utils.tts import MarkdownCleaner, convert_percentage_to_range  # type: ignore[import]
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType

if TYPE_CHECKING:
    pass

TAG = __name__
logger = setup_logging()


class CozeStreamManager:
    """Coze 双向流式语音合成 WebSocket 连接管理器（纯TTS模式）

    使用 Coze 官方「双向流式语音合成」协议，非对话模式。
    协议文档: https://docs.coze.cn/developer_guides/tts_event

    延迟优化：
      - 支持 Opus 直出模式（codec=opus），消除 PCM→本地 Opus 转码管线，
        可减少 60~120ms 的缓冲+编码延迟。
      - PCM 模式保留作为降级方案。
    """

    def __init__(self, config: dict[str, Any]):
        # 保存原始配置供后续扩展参数读取
        self._config: dict[str, Any] = config
        # 基础配置
        self.access_token: str = config.get("access_token", "")
        self.bot_id: str = config.get("bot_id", "")  # 纯TTS模式下不使用，保留兼容
        self.user_id: str = config.get("user_id", uuid.uuid4().hex)
        self.voice_id: Optional[str] = config.get("voice_id")
        self.language: str = config.get("language", "中文")
        self.private_voice_id: Optional[str] = config.get("private_voice")
        self.output_dir: str = config.get("output_dir", "tmp/")

        # 输出编码格式：默认 PCM（已验证可工作，对齐 realtime_voice.py）
        # 可设为 "opus" 启用 Opus 直出（实验性，需确保 Coze Opus 参数与 ESP32 解码器兼容）
        self.codec: str = config.get("tts_codec", "pcm")

        # WebSocket 连接
        self.ws: Optional[Any] = None
        self.monitor_task: Optional[Task[Any]] = None
        self.is_connected: bool = False
        self.current_session_id: Optional[str] = None
        self.last_active_time: Optional[float] = None

        # 消息序列号
        self._event_seq: int = 0

        # 回调函数
        self.on_audio_data_callback: Optional[Callable[[bytes], None]] = None
        self.on_tts_completed_callback: Optional[Callable[[], Coroutine[Any, Any, None]]] = None

    # 空闲超时（秒）：超过此时间无活动则自动关闭，释放资源
    _IDLE_TIMEOUT: float = 120.0

    async def connect(self, session_id: str) -> None:
        """建立纯 TTS WebSocket 连接

        注意：/v1/audio/speech 是单次合成端点，每个 WS 连接对应一次合成会话。
              speech.audio.completed 后会话即结束，不可复用连接进行下一轮合成。
              因此每次 connect() 都创建新连接（不复用）。
        """
        # 关闭上一轮的残留连接
        if self.ws:
            logger.bind(tag=TAG).debug("关闭上一轮 TTS 连接")
            await self.close()

        # 纯 TTS 端点（与对话端点 v1/chat 不同）
        ws_url = "wss://ws.coze.cn/v1/audio/speech"

        try:
            self.ws = await websockets.connect(
                ws_url,
                additional_headers={"Authorization": f"Bearer {self.access_token}"},  # type: ignore[arg-type]
                ping_interval=15,
                ping_timeout=10,
                close_timeout=5,
            )  # type: ignore[assignment]
            self.is_connected = True
            self.current_session_id = session_id
            self.last_active_time = time.time()
            logger.bind(tag=TAG).info(f"Coze TTS WebSocket 连接成功, session_id={session_id}")

            # 发送 speech.update 配置事件（纯 TTS 协议）
            await self._send_speech_update()

            # 启动响应监听任务
            if self.monitor_task is None or self.monitor_task.done():
                self.monitor_task = asyncio.create_task(self._monitor_response())
                logger.bind(tag=TAG).debug("启动 TTS 响应监听任务")
        except Exception as e:
            self.is_connected = False
            self.ws = None
            logger.bind(tag=TAG).error(f"Coze TTS WebSocket 连接失败: {e}")
            raise

    def _is_connection_healthy(self) -> bool:
        """检查现有连接是否健康可复用"""
        if not self.ws or not self.is_connected:
            return False
        # 检查空闲超时
        if self.last_active_time and (time.time() - self.last_active_time) > self._IDLE_TIMEOUT:
            return False
        return True

    def _next_id(self) -> str:
        """生成唯一消息 ID"""
        self._event_seq += 1
        return f"tts_{int(time.time()*1000)}_{self._event_seq:04d}"

    async def _send(self, event: dict[str, Any]) -> None:
        """发送 JSON 事件到 WebSocket"""
        if self.ws and self.is_connected:
            await self.ws.send(json.dumps(event, ensure_ascii=False))
            self.last_active_time = time.time()

    async def _send_speech_update(self) -> None:
        """发送 speech.update 配置事件（纯 TTS 协议）

        协议参考: https://docs.coze.cn/developer_guides/tts_event#6166c24c

        延迟优化：
          - Opus 模式：Coze 直接输出 Opus 帧，跳过 PCM 本地转码，首包延迟降低 60~120ms。
          - frame_size_ms=20：比默认 60ms 更快产出首帧。
        """
        if self.codec == "opus":
            # Opus 直出模式：消除服务端 PCM → 客户端 Opus 编码管线
            data: dict[str, Any] = {
                "output_audio": {
                    "codec": "opus",
                    "opus_config": {
                        "bitrate": self._config.get("opus_bitrate", 24000),
                        "frame_size_ms": self._config.get("opus_frame_size_ms", 20),
                        "use_cbr": True,
                    },
                },
            }
        else:
            # PCM 模式（降级方案）：从配置读取采样率，默认 24000
            pcm_sr: int = self._config.get("sample_rate", 24000)
            data = {
                "output_audio": {
                    "codec": "pcm",
                    "pcm_config": {"sample_rate": pcm_sr},
                },
            }

        if self.voice_id:
            data["output_audio"]["voice_id"] = self.voice_id

        # 可选参数：语速 [-50, 100]，默认 0；音量 [-50, 100]，默认 0
        speech_rate: Optional[int] = self._config.get("speech_rate")  # type: ignore[assignment]
        if speech_rate is not None:
            data["output_audio"]["speech_rate"] = max(-50, min(100, int(speech_rate)))
        loudness_rate: Optional[int] = self._config.get("loudness_rate")  # type: ignore[assignment]
        if loudness_rate is not None:
            data["output_audio"]["loudness_rate"] = max(-50, min(100, int(loudness_rate)))

        event: dict[str, Any] = {
            "id": self._next_id(),
            "event_type": "speech.update",
            "data": data,
        }
        await self._send(event)
        voice_info = f", voice={self.voice_id}" if self.voice_id else ""
        rate_info = f", rate={speech_rate}" if speech_rate else ""
        logger.bind(tag=TAG).info(f"已发送 speech.update 配置 [codec={self.codec}]{voice_info}{rate_info}")

    async def send_text(self, text: str) -> None:
        """发送文本片段到 Coze（仅 append，不触发合成）

        流式模式：每个 LLM 文本片段到达时立即 append，
        等 LAST 时再调用 complete_text() 触发合成。
        """
        if not self.ws or not self.is_connected:
            logger.bind(tag=TAG).warning("WebSocket 未连接，无法发送文本")
            return

        event: dict[str, Any] = {
            "id": self._next_id(),
            "event_type": "input_text_buffer.append",
            "data": {"delta": text},
        }
        try:
            await self._send(event)
            logger.bind(tag=TAG).debug(f"TTS append({len(text)}字): {text[:30]}...")
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS send_text 发送失败: {e}")

    async def complete_text(self) -> None:
        """提交文本，触发 Coze 开始语音合成"""
        if not self.ws or not self.is_connected:
            logger.bind(tag=TAG).warning("WebSocket 未连接，无法提交文本")
            return

        event: dict[str, Any] = {
            "id": self._next_id(),
            "event_type": "input_text_buffer.complete",
        }
        try:
            await self._send(event)
            logger.bind(tag=TAG).info("TTS 文本已提交，等待语音合成")
        except Exception as e:
            logger.bind(tag=TAG).error(f"TTS complete_text 发送失败: {e}")

    async def interrupt(self) -> None:
        """打断当前 TTS 合成：关闭连接

        立即标记 is_connected=False 防止竞态窗口内继续发送数据。
        """
        self.is_connected = False
        logger.bind(tag=TAG).info("TTS 打断：关闭当前连接")
        await self.close()

    async def _monitor_response(self) -> None:
        """长期运行任务：监听 Coze TTS 服务端返回的消息并分发处理"""
        try:
            while self.is_connected:
                try:
                    # 设置 30s 超时防止服务端无响应时永久阻塞
                    msg = await asyncio.wait_for(
                        self.ws.recv(),  # type: ignore[union-attr]
                        timeout=30,
                    )
                    self.last_active_time = time.time()

                    if isinstance(msg, str):
                        await self._handle_tts_event(msg)
                    elif isinstance(msg, (bytes, bytearray)):
                        logger.bind(tag=TAG).debug("收到二进制消息，长度=%d", len(msg))

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("Coze TTS WebSocket 连接已关闭")
                    break
                except asyncio.TimeoutError:
                    # recv 超时但连接仍有效，继续等待（用于检测僵死连接）
                    logger.bind(tag=TAG).debug("TTS recv 超时，继续监听")
                    continue
                except Exception as e:
                    logger.bind(tag=TAG).error(
                        f"处理响应消息失败: {e}\n{traceback.format_exc()}"
                    )
                    break
        except asyncio.CancelledError:
            logger.bind(tag=TAG).debug("TTS 监听任务被取消")
        finally:
            self.is_connected = False
            self.monitor_task = None

    async def _handle_tts_event(self, msg: str) -> None:
        """解析并分发纯 TTS 协议事件

        协议参考: https://docs.coze.cn/developer_guides/tts_event
        """
        try:
            data: dict[str, Any] = json.loads(msg)  # type: ignore[assignment]
            event_type: str = data.get("event_type", "")  # type: ignore[assignment]

            if event_type == "speech.created":
                # TTS 连接建立确认
                logid: str = data.get("detail", {}).get("logid", "")  # type: ignore[assignment]
                logger.bind(tag=TAG).info(f"TTS 会话已建立, logid={logid}")

            elif event_type == "speech.updated":
                # 配置更新确认
                logger.bind(tag=TAG).info("TTS speech.update 配置已确认")

            elif event_type == "input_text_buffer.completed":
                # 文本提交确认，服务端开始合成
                logid: str = data.get("detail", {}).get("logid", "")  # type: ignore[assignment]
                logger.bind(tag=TAG).info(f"TTS 文本已提交，开始语音合成, logid={logid}")

            elif event_type == "speech.audio.update":
                # 合成增量音频数据
                # 协议: data.delta 为 base64 编码的 PCM 音频片段（必选字段）
                # 参考: https://docs.coze.cn/developer_guides/tts_event#98163c71
                audio_payload: dict[str, Any] = data.get("data", {})  # type: ignore[assignment]
                raw_delta: str = audio_payload.get("delta", "")  # type: ignore[assignment]
                if raw_delta:
                    try:
                        audio_bytes: bytes = base64.b64decode(raw_delta)  # type: ignore[assignment]
                        logger.bind(tag=TAG).debug(f"收到 TTS 音频: {len(audio_bytes)} bytes")
                        if self.on_audio_data_callback:
                            self.on_audio_data_callback(audio_bytes)
                    except Exception as e:
                        logger.bind(tag=TAG).warning(f"TTS 音频 base64 解码失败: {e}")
                else:
                    logid: str = data.get("detail", {}).get("logid", "")  # type: ignore[assignment]
                    logger.bind(tag=TAG).warning(
                        f"TTS 音频事件但 delta 为空, logid={logid}, 原始data={str(data)[:300]}"
                    )

            elif event_type == "speech.audio.completed":
                # 语音合成完成
                logid: str = data.get("detail", {}).get("logid", "")  # type: ignore[assignment]
                logger.bind(tag=TAG).info(f"TTS 语音合成完成, logid={logid}")
                if self.on_tts_completed_callback:
                    await self.on_tts_completed_callback()

            elif event_type in (
                "conversation.audio.sentence_start",
                "conversation.audio.delta",
                "conversation.audio.completed",
            ):
                pass  # TTS 音频事件（句子边界/音频块/完成），下游已通过 on_audio_data_callback 处理

            elif event_type == "error":
                error_code: Any = data.get("data", {}).get("code")  # type: ignore[assignment]
                error_msg: str = data.get("data", {}).get("msg", str(data))  # type: ignore[assignment]
                logid: str = data.get("detail", {}).get("logid", "")  # type: ignore[assignment]
                logger.bind(tag=TAG).error(
                    f"Coze TTS 错误: code={error_code}, msg={error_msg}, logid={logid}"
                )

            else:
                # 记录所有未处理的事件（INFO 级别便于调试）
                logger.bind(tag=TAG).debug(f"TTS 未处理事件: {event_type}, 数据={str(data)[:200]}")

        except json.JSONDecodeError:
            logger.bind(tag=TAG).warning(f"无法解析 JSON 消息: {msg[:200]}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理 TTS 事件异常: {e}")

    async def close(self) -> None:
        """关闭连接并清理资源"""
        if self.monitor_task and not self.monitor_task.done():
            self.monitor_task.cancel()
            try:
                await self.monitor_task
            except (asyncio.CancelledError, Exception):
                pass
            self.monitor_task = None

        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None

        self.is_connected = False
        logger.bind(tag=TAG).info("Coze TTS 资源已清理")


class TTSProvider(TTSProviderBase):
    """Coze 双向流式语音合成 TTS Provider（纯 TTS 模式）

    延迟优化：
      - Opus 直出模式（默认）：Coze 输出 Opus 帧 → 直接入队，
        消除 PCM 缓冲(60ms) + 本地 Opus 编码(~10ms/帧) 的双重延迟。
      - PCM 降级模式：保留原有管线不变。
    """

    TTS_PARAM_CONFIG: list[Any] = []

    def __init__(self, config: dict[str, Any], delete_audio_file: bool) -> None:
        super().__init__(config, delete_audio_file)

        self.interface_type = InterfaceType.DUAL_STREAM
        self.report_on_last = True

        # 基础配置
        self.access_token: str = config.get("access_token", "")
        self.voice_id: Optional[str] = config.get("voice_id")
        self.private_voice_id: Optional[str] = config.get("private_voice")

        # 默认 audio_params 配置（对齐 huoshan 配置合并模式）
        default_audio_params: dict[str, Any] = {
            "speech_rate": 0,
            "loudness_rate": 0,
        }
        # 合并用户配置
        self.audio_params: dict[str, Any] = {**default_audio_params, **config.get("audio_params", {})}

        # 应用百分比参数调整（对齐 huoshan 模式）
        if "ttsVolume" in config:
            self.audio_params["loudness_rate"] = int(convert_percentage_to_range(
                config["ttsVolume"], min_val=-50, max_val=100, base_val=0
            ))
        if "ttsRate" in config:
            self.audio_params["speech_rate"] = int(convert_percentage_to_range(
                config["ttsRate"], min_val=-50, max_val=100, base_val=0
            ))

        # API Key 校验（对齐 huoshan）
        model_key_msg = check_model_key("TTS", self.access_token)
        if model_key_msg:
            logger.bind(tag=TAG).error(model_key_msg)

        # 连接对象（TYPE_CHECKING 外部无法解析 ConnectionHandler 类型）
        self.conn: Any = None  # type: ignore[assignment]

        # 创建共享的流管理器（传入含 speech_rate/loudness_rate 的完整配置）
        self.stream_manager: CozeStreamManager = CozeStreamManager({
            **config,
            "speech_rate": self.audio_params.get("speech_rate", 0),
            "loudness_rate": self.audio_params.get("loudness_rate", 0),
        })

        # 延迟优化：根据编码格式决定是否需要本地 Opus 编码器
        self._use_opus_direct: bool = self.stream_manager.codec == "opus"

        if self._use_opus_direct:
            # Opus 直出模式：不需要本地 Opus 编码器，Coze 直接输出 Opus 帧
            # 注意：base.open_audio_channels() 会检测到 opus_encoder 为 None 并尝试创建，
            # 所以这里显式设为 None 阻止 base 类创建（Opus 模式下不需要）
            self.opus_encoder: Any = None
            logger.bind(tag=TAG).info("TTS 启用 Opus 直出模式（实验性，零本地转码延迟）")
        else:
            # PCM 模式：不在此处预创建 opus_encoder
            # 由 base.open_audio_channels() 在连接建立后用 conn.sample_rate 动态创建，
            # 确保编码器采样率与设备实际配置一致（对齐 huoshan_double_stream 行为）
            self.opus_encoder: Any = None  # type: ignore[assignment]
            logger.bind(tag=TAG).info("TTS 使用 PCM 模式（Coze 输出 PCM → 本地 Opus 编码）")

        # PCM 数据缓冲区（仅 PCM 模式使用）
        self.pcm_buffer: bytearray = bytearray()

        # 滑动窗口匹配前缀缓冲（对齐 huoshan 显式初始化）
        self._pending_prefix: str = ""
        # 待播放文件列表（对齐 huoshan 显式初始化）
        self.before_stop_play_files: list[Any] = []

    async def open_audio_channels(self, conn: Any) -> None:
        """打开音频通道，设置回调（对齐 huoshan 错误处理模式）"""
        try:
            await super().open_audio_channels(conn)  # type: ignore[arg-type]
            # 更新 audio_params 中的采样率为实际的 conn.sample_rate
            self.audio_params["sample_rate"] = conn.sample_rate  # type: ignore[assignment]
        except Exception as e:
            logger.bind(tag=TAG).error(f"Failed to open audio channels: {str(e)}")
            raise

        # 设置流管理器的回调
        self.stream_manager.on_audio_data_callback = self._on_coze_audio
        self.stream_manager.on_tts_completed_callback = self._on_tts_completed

    def _on_coze_audio(self, audio_data: bytes) -> None:
        """处理从 Coze 接收到的音频数据

        延迟优化：
          - Opus 直出模式：base64 解码后直接推入 Opus 队列，零缓冲零编码。
          - PCM 模式：缓冲满帧后本地编码为 Opus（对齐 huoshan_double_stream）。
        """
        if self._use_opus_direct:
            # Opus 直出模式：Coze 输出的已是完整 Opus 帧，直接入队
            self.handle_opus(audio_data)
        else:
            # PCM 模式：使用编码器实际采样率计算帧大小（兼容设备配置的 16k/24k）
            sr: int = getattr(self.opus_encoder, 'sample_rate', 24000)  # type: ignore[union-attr]
            frame_size = int(sr * 1 * 0.06 / 1000 * 2)  # 单声道 16bit, 60ms帧

            self.pcm_buffer.extend(audio_data)

            while len(self.pcm_buffer) >= frame_size:
                frame = bytes(self.pcm_buffer[:frame_size])
                del self.pcm_buffer[:frame_size]
                self.opus_encoder.encode_pcm_to_opus_stream(
                    frame, end_of_stream=False, callback=self.handle_opus
                )

    async def _on_tts_completed(self) -> None:
        """TTS 合成完成回调：处理剩余数据、待播放文件并发送 LAST 标记

        延迟优化：
          - Opus 直出模式：无残留数据需 flush，直接发送 LAST。
          - PCM 模式：flush 缓冲区剩余 PCM 数据。
        """
        if not self._use_opus_direct and self.opus_encoder is not None:
            # PCM 模式：flush 剩余 PCM 数据
            if len(self.pcm_buffer) > 0:
                remaining = bytes(self.pcm_buffer)
                self.pcm_buffer.clear()
                self.opus_encoder.encode_pcm_to_opus_stream(
                    remaining, end_of_stream=True, callback=self.handle_opus
                )
            else:
                self.opus_encoder.encode_pcm_to_opus_stream(
                    b"", end_of_stream=True, callback=self.handle_opus
                )
            self.pcm_buffer.clear()
        # Opus 直出模式：Coze 已在 speech.audio.completed 前发完所有帧，无需 flush

        # 处理待播放文件（对齐 huoshan 在 SessionFinished 时调用）
        self._process_before_stop_play_files()

        # 发送 LAST 标记
        self.tts_audio_queue.put((
            SentenceType.LAST, [], None,
            getattr(self, "current_sentence_id", None)
        ))
        logger.bind(tag=TAG).debug("TTS completed: 已处理剩余数据、待播放文件并发送 LAST")

    def tts_text_priority_thread(self) -> None:
        """重写父类方法：处理双流式 TTS 文本队列（对齐 huoshan 日志风格）"""
        while not self.conn.stop_event.is_set():
            try:
                message: Any = self.tts_text_queue.get(timeout=1)  # type: ignore[assignment]

                if message.sentence_id != self.conn.sentence_id:  # type: ignore[union-attr]
                    continue

                # 处理客户端打断
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息，终止TTS文本处理线程")
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.interrupt(),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=5)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"发送打断事件失败: {e}")
                    continue

                logger.bind(tag=TAG).debug(
                    f"收到TTS任务｜{message.sentence_type.name} ｜ {message.content_type.name} | 会话ID: {message.sentence_id}"  # type: ignore[union-attr]
                )

                if message.sentence_type == SentenceType.FIRST:  # type: ignore[union-attr]
                    # 重置流式处理状态
                    self.reset_stream_state()
                    self.current_sentence_id: str = message.sentence_id  # type: ignore[assignment]
                    self.pcm_buffer.clear()

                    session_id: str = message.sentence_id  # type: ignore[assignment]
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.connect(session_id),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=self.tts_timeout)
                        self.before_stop_play_files.clear()
                        logger.bind(tag=TAG).debug(f"Coze TTS 会话已启动, session_id={session_id}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"启动 Coze TTS 会话失败: {e}")
                        continue

                    self.tts_audio_queue.put((SentenceType.FIRST, [], None, message.sentence_id))

                elif ContentType.FILE == message.content_type:  # type: ignore[union-attr]
                    tts_file: Any = message.content_file  # type: ignore[assignment, union-attr]
                    logger.bind(tag=TAG).info(
                        f"添加音频文件到待播放列表: {tts_file}"
                    )
                    if tts_file and os.path.exists(str(tts_file)):  # type: ignore[arg-type]
                        self._process_audio_file_stream(tts_file, callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail))  # type: ignore[arg-type]

                elif ContentType.TEXT == message.content_type:  # type: ignore[union-attr]
                    content_detail: Any = message.content_detail  # type: ignore[assignment, union-attr]
                    if content_detail:
                        try:
                            # 过滤 Markdown（对齐 huoshan text_to_speak 流程）
                            filtered_text = MarkdownCleaner.clean_markdown(content_detail)
                            if filtered_text:
                                # 使用滑动窗口匹配处理跨分片的替换词（对齐 huoshan）
                                _match_result: tuple[list[str], str] = self._match_stream_text(filtered_text)  # type: ignore[assignment]
                                confirmed_texts: list[str] = _match_result[0]
                                self._pending_prefix: str = _match_result[1]

                                # 发送每个确定的文本片段到 Coze
                                # 延迟优化：send_text 使用 fire-and-forget，不阻塞等待 WS 发送完成。
                                # LLM 流式输出有大量小分片，每个都 future.result() 会产生 N 次串行网络延迟。
                                # WebSocket send 只是写入 socket buffer（~微秒级），无需逐次确认。
                                for txt in confirmed_texts:  # type: ignore[union-attr]
                                    txt_str: str = txt  # type: ignore[assignment]
                                    if txt_str:
                                        asyncio.run_coroutine_threadsafe(
                                            self.stream_manager.send_text(txt_str),  # type: ignore[arg-type]
                                            loop=self.conn.loop,
                                        )
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"TTS append 失败: {e}")

                elif message.sentence_type == SentenceType.LAST:  # type: ignore[union-attr]
                    # LAST 时提交文本，触发 Coze 语音合成
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.complete_text(),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=10)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"TTS complete 失败: {e}")

            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理TTS文本失败: {str(e)}, 类型: {type(e).__name__}, "
                    f"堆栈: {traceback.format_exc()}"
                )
                continue

    async def text_to_speak(self, text: str, output_file: Optional[str] = None) -> None:  # type: ignore[override]
        """发送文本到 Coze TTS 服务（对齐 huoshan 双流式发送模式）

        DUAL_STREAM 模式下通过 tts_text_priority_thread → stream_manager 完成流式 TTS，
        此方法保留用于非双流式场景或直接调用。
        """
        try:
            if self.stream_manager.ws is None or not self.stream_manager.is_connected:
                logger.bind(tag=TAG).warning("WebSocket 未连接，终止发送文本")
                return

            # 过滤 Markdown（对齐 huoshan）
            filtered_text = MarkdownCleaner.clean_markdown(text)

            if filtered_text:
                # 使用滑动窗口匹配处理跨分片的替换词（对齐 huoshan）
                _match_result: tuple[list[str], str] = self._match_stream_text(filtered_text)  # type: ignore[assignment]
                confirmed_texts: list[str] = _match_result[0]
                self._pending_prefix: str = _match_result[1]

                # 发送每个确定的文本片段到 Coze
                for txt in confirmed_texts:  # type: ignore[union-attr]
                    txt_str: str = txt  # type: ignore[assignment]
                    if txt_str and self.stream_manager.ws:
                        await self.stream_manager.send_text(txt_str)  # type: ignore[arg-type]
            return
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送TTS文本失败: {str(e)}")
            if self.stream_manager.ws:
                try:
                    await self.stream_manager.close()
                except Exception:
                    pass
            raise

    async def close(self) -> None:
        """清理所有资源（对齐 huoshan 清理模式）"""
        await super().close()
        await self.stream_manager.close()
        if hasattr(self, "opus_encoder") and self.opus_encoder is not None:
            self.opus_encoder.close()
        logger.bind(tag=TAG).info("TTSProvider 资源已全部清理")

    def audio_to_opus_data_stream(
        self, audio_file_path: str, callback: Callable[[Any], Any] = None  # type: ignore[assignment]
    ) -> None:
        """重写父类方法：使用独立的临时编码器处理音频文件，避免与TTS流式编码器并发冲突。

        双流式TTS中，monitor任务在event loop线程接收TTS音频并使用self.opus_encoder编码，
        同时tts_text_priority_thread处理音乐文件也使用self.opus_encoder，
        共享的encoder.buffer非线程安全，并发访问会导致SILK resampler断言失败。
        （对齐 huoshan_double_stream.py 线程安全模式）
        """
        from core.utils.util import audio_to_data_stream  # type: ignore[import]
        return audio_to_data_stream(  # type: ignore[return-value]
            audio_file_path, is_opus=True, callback=callback,
            sample_rate=self.conn.sample_rate, opus_encoder=None  # type: ignore[arg-type]
        )
