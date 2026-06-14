import os
import uuid
import json
import base64
import queue
import asyncio
import threading
import traceback
import time

from typing import TYPE_CHECKING, Callable, Optional, Any
from asyncio import Task
import websockets

from config.logger import setup_logging
from core.utils import opus_encoder_utils
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
    """

    def __init__(self, config: dict):
        # 基础配置
        self.access_token: str = config.get("access_token", "")
        self.bot_id: str = config.get("bot_id", "")  # 纯TTS模式下不使用，保留兼容
        self.user_id: str = config.get("user_id", uuid.uuid4().hex)
        self.voice_id: Optional[str] = config.get("voice_id")
        self.language: str = config.get("language", "中文")
        self.private_voice_id: Optional[str] = config.get("private_voice")
        self.output_dir: str = config.get("output_dir", "tmp/")

        # WebSocket 连接
        self.ws: Optional[Any] = None
        self.monitor_task: Optional[Task] = None
        self.is_connected: bool = False
        self.current_session_id: Optional[str] = None
        self.last_active_time: Optional[float] = None

        # 消息序列号
        self._event_seq: int = 0

        # 回调函数
        self.on_audio_data_callback: Optional[Callable[[bytes], None]] = None
        self.on_tts_completed_callback: Optional[Callable[[], None]] = None

    async def connect(self, session_id: str) -> None:
        """建立纯 TTS WebSocket 连接并启动响应监听任务

        每轮对话强制重新连接，避免复用旧连接导致状态异常。
        """
        # 强制关闭旧连接，确保每轮都是全新会话
        if self.is_connected or self.ws:
            logger.bind(tag=TAG).debug("关闭旧 TTS 连接，重新建立")
            await self.close()

        # 纯 TTS 端点（与对话端点 v1/chat 不同）
        ws_url = "wss://ws.coze.cn/v1/audio/speech"

        try:
            self.ws = await websockets.connect(
                ws_url,
                additional_headers={"Authorization": f"Bearer {self.access_token}"},
                ping_interval=15,
                ping_timeout=10,
                close_timeout=5,
            )
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

    def _next_id(self) -> str:
        """生成唯一消息 ID"""
        self._event_seq += 1
        return f"tts_{int(time.time()*1000)}_{self._event_seq:04d}"

    async def _send(self, event: dict) -> None:
        """发送 JSON 事件到 WebSocket"""
        if self.ws and self.is_connected:
            await self.ws.send(json.dumps(event, ensure_ascii=False))
            self.last_active_time = time.time()

    async def _send_speech_update(self) -> None:
        """发送 speech.update 配置事件（纯 TTS 协议）

        协议参考: https://docs.coze.cn/developer_guides/tts_event#6166c24c
        """
        data = {
            "output_audio": {
                "codec": "pcm",
                "pcm_config": {"sample_rate": 24000},
            },
        }
        if self.voice_id:
            data["output_audio"]["voice_id"] = self.voice_id

        event = {
            "id": self._next_id(),
            "event_type": "speech.update",
            "data": data,
        }
        await self._send(event)
        voice_info = f", voice={self.voice_id}" if self.voice_id else ""
        logger.bind(tag=TAG).info(f"已发送 speech.update 配置{voice_info}")

    async def send_text(self, text: str) -> None:
        """发送文本片段到 Coze（仅 append，不触发合成）

        流式模式：每个 LLM 文本片段到达时立即 append，
        等 LAST 时再调用 complete_text() 触发合成。
        """
        if not self.ws or not self.is_connected:
            logger.bind(tag=TAG).warning("WebSocket 未连接，无法发送文本")
            return

        event = {
            "id": self._next_id(),
            "event_type": "input_text_buffer.append",
            "data": {"delta": text},
        }
        await self._send(event)
        logger.bind(tag=TAG).debug(f"TTS append({len(text)}字): {text[:30]}...")

    async def complete_text(self) -> None:
        """提交文本，触发 Coze 开始语音合成"""
        if not self.ws or not self.is_connected:
            return

        event = {
            "id": self._next_id(),
            "event_type": "input_text_buffer.complete",
        }
        await self._send(event)
        logger.bind(tag=TAG).info("TTS 文本已提交，等待语音合成")

    async def interrupt(self) -> None:
        """打断当前 TTS 合成：关闭连接重新建立"""
        logger.bind(tag=TAG).info("TTS 打断：关闭当前连接")
        await self.close()

    async def _monitor_response(self) -> None:
        """长期运行任务：监听 Coze TTS 服务端返回的消息并分发处理"""
        try:
            while True:
                try:
                    msg = await self.ws.recv()
                    self.last_active_time = time.time()

                    if isinstance(msg, str):
                        await self._handle_tts_event(msg)
                    elif isinstance(msg, (bytes, bytearray)):
                        logger.bind(tag=TAG).debug("收到二进制消息，长度=%d", len(msg))

                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("Coze TTS WebSocket 连接已关闭")
                    break
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
            data = json.loads(msg)
            event_type = data.get("event_type", "")

            if event_type == "speech.created":
                # TTS 连接建立确认
                logid = data.get("detail", {}).get("logid", "")
                logger.bind(tag=TAG).info(f"TTS 会话已建立, logid={logid}")

            elif event_type == "speech.updated":
                # 配置更新确认
                logger.bind(tag=TAG).info("TTS speech.update 配置已确认")

            elif event_type == "input_text_buffer.completed":
                # 文本提交确认，服务端开始合成
                logid = data.get("detail", {}).get("logid", "")
                logger.bind(tag=TAG).info(f"TTS 文本已提交，开始语音合成, logid={logid}")

            elif event_type == "speech.audio.update":
                # 合成增量音频数据（base64 编码的 PCM 片段）
                audio_payload = data.get("data", {})
                # 记录原始数据结构以便调试
                raw = audio_payload.get("delta", "") or audio_payload.get("content", "") or ""
                logger.bind(tag=TAG).info(
                    f"TTS 音频事件: delta长度={len(raw)}, "
                    f"data.keys={list(audio_payload.keys()) if isinstance(audio_payload, dict) else type(audio_payload)}"
                )
                audio_bytes = self._extract_audio_data(data)
                if audio_bytes:
                    logger.bind(tag=TAG).info(f"收到 TTS 音频: {len(audio_bytes)} bytes")
                    if self.on_audio_data_callback:
                        self.on_audio_data_callback(audio_bytes)
                else:
                    logger.bind(tag=TAG).warning(
                        f"TTS 音频事件但无法提取数据, 原始data={str(data)[:300]}"
                    )

            elif event_type == "speech.audio.completed":
                # 语音合成完成
                logger.bind(tag=TAG).info("TTS 语音合成完成")
                if self.on_tts_completed_callback:
                    await self.on_tts_completed_callback()

            elif event_type == "error":
                error_code = data.get("data", {}).get("code")
                error_msg = data.get("data", {}).get("msg", str(data))
                logid = data.get("detail", {}).get("logid", "")
                logger.bind(tag=TAG).error(
                    f"Coze TTS 错误: code={error_code}, msg={error_msg}, logid={logid}"
                )

            else:
                # 记录所有未处理的事件（INFO 级别便于调试）
                logger.bind(tag=TAG).info(f"TTS 未处理事件: {event_type}, 数据={str(data)[:200]}")

        except json.JSONDecodeError:
            logger.bind(tag=TAG).warning(f"无法解析 JSON 消息: {msg[:200]}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"处理 TTS 事件异常: {e}")

    @staticmethod
    def _extract_audio_data(data: dict) -> Optional[bytes]:
        """从 speech.audio.update 事件中提取 base64 音频数据

        协议: data.delta 为 base64 编码的 PCM 音频片段
        参考: https://docs.coze.cn/developer_guides/tts_event#98163c71
        """
        audio_payload = data.get("data", {})
        if not isinstance(audio_payload, dict):
            return None

        raw_data = audio_payload.get("delta", "")
        if not raw_data:
            return None

        try:
            return base64.b64decode(raw_data)
        except Exception as e:
            logger.bind(tag=TAG).warning(f"TTS 音频 base64 解码失败: {e}")
            return None

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
    """Coze 双向流式语音合成 TTS Provider（纯 TTS 模式）"""

    TTS_PARAM_CONFIG: list = []

    def __init__(self, config: dict, delete_audio_file: bool):
        super().__init__(config, delete_audio_file)

        self.interface_type = InterfaceType.DUAL_STREAM
        self.report_on_last = True

        # 创建共享的流管理器
        self.stream_manager = CozeStreamManager(config)

        # Opus 编码器（固定参数：24kHz, 单声道, 60ms 帧）
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=24000, channels=1, frame_size_ms=60
        )

        # PCM 数据缓冲区
        self.pcm_buffer = bytearray()

    async def open_audio_channels(self, conn: Any) -> None:
        """打开音频通道，设置回调"""
        await super().open_audio_channels(conn)

        # 设置流管理器的回调
        self.stream_manager.on_audio_data_callback = self._on_coze_audio
        self.stream_manager.on_tts_completed_callback = self._on_tts_completed

    def _on_coze_audio(self, pcm_data: bytes) -> None:
        """处理从 Coze 接收到的 PCM 音频数据，缓冲满帧后编码为 Opus 并推送"""
        frame_size = int(24000 * 1 * 0.06 / 1000 * 2)  # 2880 bytes/frame

        self.pcm_buffer.extend(pcm_data)

        while len(self.pcm_buffer) >= frame_size:
            frame = bytes(self.pcm_buffer[:frame_size])
            del self.pcm_buffer[:frame_size]
            self.opus_encoder.encode_pcm_to_opus_stream(
                frame, end_of_stream=False, callback=self.handle_opus
            )

    async def _on_tts_completed(self) -> None:
        """TTS 合成完成回调：flush 缓冲区剩余数据并发送 LAST 标记"""
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

        self.tts_audio_queue.put((
            SentenceType.LAST, [], None,
            getattr(self, "current_sentence_id", None)
        ))
        logger.bind(tag=TAG).debug("TTS completed: 已 flush 剩余 PCM 并发送 LAST")

    def tts_text_priority_thread(self) -> None:
        """重写父类方法：处理双流式 TTS 文本队列"""
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)

                if message.sentence_id != self.conn.sentence_id:
                    continue

                # 处理客户端打断
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息，调用 stream_manager.interrupt()")
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.interrupt(),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=5)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"发送打断事件失败: {e}")
                    continue

                if message.sentence_type == SentenceType.FIRST:
                    self.reset_stream_state()
                    self.current_sentence_id = message.sentence_id
                    self.pcm_buffer.clear()

                    session_id = message.sentence_id
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.connect(session_id),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=self.tts_timeout)
                        logger.bind(tag=TAG).debug(f"Coze TTS 会话已启动, session_id={session_id}")
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"启动 Coze TTS 会话失败: {e}")
                        continue

                    self.tts_audio_queue.put((SentenceType.FIRST, [], None, message.sentence_id))

                elif ContentType.FILE == message.content_type:
                    tts_file = message.content_file
                    if tts_file and os.path.exists(tts_file):
                        self._process_audio_file_stream(tts_file, callback=self.handle_opus)

                elif ContentType.TEXT == message.content_type:
                    # 流式模式：每个文本片段立即 append 到 Coze
                    text = message.content_detail
                    if text:
                        try:
                            future = asyncio.run_coroutine_threadsafe(
                                self.stream_manager.send_text(text),
                                loop=self.conn.loop,
                            )
                            future.result(timeout=5)
                        except Exception as e:
                            logger.bind(tag=TAG).error(f"TTS append 失败: {e}")

                elif message.sentence_type == SentenceType.LAST:
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

    async def text_to_speak(self, text: str, output_file: Optional[str]) -> Optional[bytes]:
        """兼容保留方法，双流式模式下仅记录日志"""
        logger.bind(tag=TAG).info(
            f"text_to_speak 被调用（兼容保留）: text={text[:50]}, output_file={output_file}"
        )
        return None

    async def close(self) -> None:
        """清理所有资源"""
        await super().close()
        await self.stream_manager.close()
        if hasattr(self, "opus_encoder") and self.opus_encoder:
            self.opus_encoder.close()
        logger.bind(tag=TAG).info("TTSProvider 资源已全部清理")
