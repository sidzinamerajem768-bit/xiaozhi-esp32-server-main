# Coze 流式 ASR+LLM+TTS 统一接口实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 新增 Coze 双向流式语音对话 WebSocket 接口的 ASR 和 TTS Provider，通过一次 WS 连接完成 ASR→LLM→TTS 全链路

**Architecture:** 采用统一 Provider 模式，新建 `asr/coze_stream.py` 和 `tts/coze_stream.py` 两个文件。TTS Provider 创建并持有 `CozeStreamManager`（WebSocket 连接管理器），ASR Provider 通过共享的 Manager 实例发送音频和获取识别结果。复用现有基类的线程模型、队列机制和 Opus 编码基础设施。

**Tech Stack:** Python asyncio + websockets + opuslib_next + 现有 xiaozhi Provider 基类体系

**Design Doc:** [2026-06-12-coze-stream-design.md](../specs/2026-06-12-coze-stream-design.md)

---

## 文件结构

| 文件 | 操作 | 职责 |
|------|------|------|
| `core/providers/tts/coze_stream.py` | **新建** | TTSProvider + CozeStreamManager（WS 连接管理） |
| `core/providers/asr/coze_stream.py` | **新建** | ASRProvider（音频采集→发送到 Coze WS） |
| `config.yaml` | **修改** | 添加 CozeStreamASR / CozeStreamTTS 配置段 |

---

### Task 1: 创建 CozeStreamManager 和 TTS Provider 骨架

**Files:**
- Create: `core/providers/tts/coze_stream.py`

**参考文件:**
- [alibl_stream.py](../../../core/providers/tts/alibl_stream.py) — 双流式 TTS 模式参考
- [cozecn.py](../../../core/providers/tts/cozecn.py) — 已有 Coze TTS 配置模式参考
- [base.py](../../../core/providers/tts/base.py) — TTS 基类

- [ ] **Step 1: 创建 tts/coze_stream.py 文件，实现 CozeStreamManager 类**

```python
"""
Coze 双向流式语音对话 TTS Provider
通过 WebSocket 一次连接完成 ASR + LLM + TTS 全链路
"""
import json
import uuid
import time
import queue
import asyncio
import traceback
import websockets
import opuslib_next
from typing import Callable, Optional, Any

from config.logger import setup_logging
from core.utils.tts import MarkdownCleaner
from core.providers.tts.base import TTSProviderBase
from core.providers.tts.dto.dto import SentenceType, ContentType, InterfaceType
from core.utils import opus_encoder_utils


TAG = __name__
logger = setup_logging()


class CozeStreamManager:
    """Coze WebSocket 流式语音对话连接管理器
    
    被 ASR Provider 和 TTS Provider 共享，
    管理 WebSocket 连接生命周期和事件分发。
    """
    
    def __init__(self, config: dict):
        # 基础配置
        self.access_token = config.get("access_token")
        self.bot_id = str(config.get("bot_id"))
        self.user_id = config.get("user_id", str(uuid.uuid4()))
        self.voice_id = config.get("voice_id")
        self.output_dir = config.get("output_dir", "tmp/")
        
        # WebSocket 配置
        self.ws_url = f"wss://ws.coze.cn/v1/chat?bot_id={self.bot_id}&authorization=Bearer {self.access_token}"
        self.ws: Optional[Any] = None
        self._monitor_task = None
        self._connect_lock = asyncio.Lock()
        
        # 连接状态
        self.is_connected = False
        self.is_listening = False  # 是否正在接收用户语音
        self.last_active_time: Optional[float] = None
        
        # 回调函数（由 ASR/TTS Provider 设置）
        self.on_asr_text_callback: Optional[Callable] = None  # ASR 识别结果回调
        self.on_audio_data_callback: Optional[Callable] = None  # TTS 音频数据回调
        self.on_chat_completed_callback: Optional[Callable] = None  # 对话结束回调
        
        # 当前会话信息
        self.current_session_id: Optional[str] = None
        
        # ASR 结果缓存（用于 speech_to_text 返回）
        self._asr_result_text = ""
        
        # Opus 解码器（用于下行音频处理时的备用场景）
        self.decoder = None
    
    async def connect(self, session_id: str) -> bool:
        """建立 WebSocket 连接"""
        try:
            async with self._connect_lock:
                if self.ws and self.is_connected:
                    # 检查连接是否仍然有效
                    return True
                
                logger.bind(tag=TAG).info(f"正在连接 Coze WebSocket: bot_id={self.bot_id}")
                
                self.ws = await websockets.connect(
                    self.ws_url,
                    ping_interval=15,
                    ping_timeout=10,
                    close_timeout=5,
                )
                self.is_connected = True
                self.current_session_id = session_id
                self.last_active_time = time.time()
                
                # 启动监听任务
                if self._monitor_task is None or self._monitor_task.done():
                    self._monitor_task = asyncio.create_task(self._monitor_response())
                
                logger.bind(tag=TAG).info("Coze WebSocket 连接成功")
                return True
                
        except Exception as e:
            logger.bind(tag=TAG).error(f"Coze WebSocket 连接失败: {e}")
            self.is_connected = False
            self.ws = None
            return False
    
    async def send_audio(self, pcm_data: bytes):
        """发送音频帧到 Coze（上行）
        
        Args:
            pcm_data: PCM 音频数据（16kHz, 16bit, mono）
        """
        if not self.ws or not self.is_connected:
            return
        
        try:
            event = {
                "id": str(uuid.uuid4()),
                "event_type": "input_audio_buffer_append",
                "data": {
                    "delta": pcm_data.hex()  # 发送 hex 编码的 PCM 数据
                }
            }
            await self.ws.send(json.dumps(event))
            self.last_active_time = time.time()
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送音频帧失败: {e}")
    
    async def send_audio_complete(self):
        """发送音频输入结束信号，触发服务端 ASR+LLM+TTS"""
        if not self.ws or not self.is_connected:
            return
        
        try:
            event = {
                "id": str(uuid.uuid4()),
                "event_type": "input_audio_buffer_complete",
                "data": {}
            }
            await self.ws.send(json.dumps(event))
            self.is_listening = False
            self.last_active_time = time.time()
            logger.bind(tag=TAG).info("已发送音频输入结束信号")
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送结束信号失败: {e}")
    
    async def interrupt(self):
        """打断当前对话"""
        if not self.ws or not self.is_connected:
            return
        
        try:
            event = {
                "id": str(uuid.uuid4()),
                "event_type": "conversation.interrupt",
                "data": {}
            }
            await self.ws.send(json.dumps(event))
            self.is_listening = False
            self.last_active_time = time.time()
            logger.bind(tag=TAG).info("已发送打断信号")
        except Exception as e:
            logger.bind(tag=TAG).error(f"发送打断信号失败: {e}")
    
    async def _monitor_response(self):
        """监听 WebSocket 下行事件（长期运行任务）"""
        try:
            while self.ws and self.is_connected:
                try:
                    msg = await self.ws.recv()
                    self.last_active_time = time.time()
                    
                    if isinstance(msg, str):
                        await self._handle_text_event(msg)
                    elif isinstance(msg, (bytes, bytearray)):
                        # 二进制数据暂不处理（Coze 使用 JSON 文本事件）
                        pass
                        
                except websockets.ConnectionClosed:
                    logger.bind(tag=TAG).warning("Coze WebSocket 连接已关闭")
                    break
                except Exception as e:
                    logger.bind(tag=TAG).error(f"处理响应时出错: {e}\n{traceback.format_exc()}")
                    continue
        except asyncio.CancelledError:
            pass
        finally:
            self.is_connected = False
            self._monitor_task = None
    
    async def _handle_text_event(self, msg: str):
        """处理文本类型的事件消息"""
        try:
            data = json.loads(msg)
            event_type = data.get("event_type", "")
            event_data = data.get("data", {})
            
            if event_type == "conversation.chat.created":
                # ASR 完成
                logid = event_data.get("logid", "")
                logger.bind(tag=TAG).info(f"[Coze] ASR 完成, logid={logid}")
                
                # 从 chat created 事件中提取 ASR 文本
                # 注意：实际字段名需根据 API 文档确认
                asr_text = event_data.get("content", "") or event_data.get("text", "")
                self._asr_result_text = asr_text
                
                if self.on_asr_text_callback:
                    await self.on_asr_text_callback(asr_text)
                    
            elif event_type == "conversation.message.delta":
                # LLM 流式文本输出（可用于字幕显示）
                content = event_data.get("content", "")
                if content:
                    logger.bind(tag=TAG).debug(f"[Coze] LLM delta: {content}")
                    
            elif event_type == "conversation.audio.delta":
                # TTS 流式音频输出
                audio_delta = event_data.get("delta")
                audio_data = event_data.get("data")
                
                # 获取音频数据（可能是 base64 或 hex 编码）
                raw_audio = audio_delta or audio_data
                if raw_audio:
                    if isinstance(raw_audio, str):
                        # 尝试解码 hex 或 base64
                        try:
                            audio_bytes = bytes.fromhex(raw_audio)
                        except ValueError:
                            import base64
                            audio_bytes = base64.b64decode(raw_audio)
                    else:
                        audio_bytes = raw_audio
                    
                    if self.on_audio_data_callback:
                        self.on_audio_data_callback(audio_bytes)
                        
            elif event_type == "conversation.chat.completed":
                # 对话正常结束
                logger.bind(tag=TAG).info("[Coze] 对话完成")
                self.is_listening = False
                if self.on_chat_completed_callback:
                    await self.on_chat_completed_callback()
                    
            elif event_type == "conversation.chat.canceled":
                # 对话被取消
                logger.bind(tag=TAG).info("[Coze] 对话被取消")
                self.is_listening = False
                
            elif event_type == "error":
                # 错误事件
                code = event_data.get("code", "unknown")
                msg = event_data.get("message", event_data.get("msg", "未知错误"))
                logger.bind(tag=TAG).error(f"[Coze] 错误: code={code}, msg={msg}")
                
            else:
                logger.bind(tag=TAG).debug(f"[Coze] 未处理事件: {event_type}")
                
        except json.JSONDecodeError:
            logger.bind(tag=TAG).warning(f"[Coze] JSON 解析失败: {msg[:200]}")
        except Exception as e:
            logger.bind(tag=TAG).error(f"[Coze] 处理事件异常: {e}")
    
    def get_asr_result(self) -> str:
        """获取最近的 ASR 识别结果"""
        result = self._asr_result_text
        self._asr_result_text = ""
        return result
    
    async def close(self):
        """关闭 WebSocket 连接并清理资源"""
        self.is_connected = False
        self.is_listening = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
            self._monitor_task = None
        
        if self.ws:
            try:
                await self.ws.close()
            except Exception:
                pass
            self.ws = None
        
        if self.decoder:
            del self.decoder
            self.decoder = None
```

- [ ] **Step 2: 在同一文件中实现 TTSProvider 类**

```python
class TTSProvider(TTSProviderBase):
    """Coze 流式 TTS Provider
    
    通过 CozeStreamManager 管理 WebSocket 连接，
    从 Coze 接收流式 PCM 音频数据并编码为 Opus 推送到播放队列。
    LLM 推理由 Coze 服务端完成，本地不需要单独的 LLM Provider。
    """
    
    TTS_PARAM_CONFIG = [
        ("speed", "speed", 0.5, 2, 1, lambda v: round(float(v), 1)),
    ]
    
    def __init__(self, config, delete_audio_file):
        super().__init__(config, delete_audio_file)
        self.interface_type = InterfaceType.DUAL_STREAM
        self.report_on_last = True
        
        # 创建 CozeStreamManager（ASR Provider 将共享此实例）
        self.stream_manager = CozeStreamManager(config)
        
        # Opus 编码器：Coze 输出 24000Hz PCM
        self.opus_encoder = opus_encoder_utils.OpusEncoderUtils(
            sample_rate=24000, channels=1, frame_size_ms=60
        )
        
        # PCM 缓冲区（用于处理非整数帧的数据）
        self.pcm_buffer = bytearray()
    
    async def open_audio_channels(self, conn):
        await super().open_audio_channels(conn)
        
        # 设置回调
        self.stream_manager.on_audio_data_callback = self._on_coze_audio
        self.stream_manager.on_chat_completed_callback = self._on_chat_completed
        
        # 将 stream_manager 引用注入到 ASR Provider
        # （ASR 在 TTS 之后初始化，此时可能还未创建）
        # 在 ASR 的 open_audio_channels 中再次注入
    
    def _on_coze_audio(self, pcm_data: bytes):
        """处理 Coze 下发的 TTS PCM 音频数据
        
        Args:
            pcm_data: 24000Hz PCM 音频数据
        """
        # 计算每帧字节数: sample_rate * channels * (frame_size_ms/1000) * bytes_per_sample
        # 24000 * 1 * 0.06 * 2 = 2880 bytes per frame
        frame_bytes = int(
            self.opus_encoder.sample_rate
            * self.opus_encoder.channels
            * self.opus_encoder.frame_size_ms
            / 1000
            * 2  # 16-bit = 2 bytes
        )
        
        self.pcm_buffer.extend(pcm_data)
        
        while len(self.pcm_buffer) >= frame_bytes:
            frame = bytes(self.pcm_buffer[:frame_bytes])
            del self.pcm_buffer[:frame_bytes]
            
            self.opus_encoder.encode_pcm_to_opus_stream(
                frame,
                end_of_stream=False,
                callback=self.handle_opus
            )
    
    async def _on_chat_completed(self):
        """对话完成回调"""
        # flush 剩余 PCM 数据
        if self.pcm_buffer:
            self.opus_encoder.encode_pcm_to_opus_stream(
                bytes(self.pcm_buffer),
                end_of_stream=True,
                callback=self.handle_opus
            )
            self.pcm_buffer.clear()
        
        # 发送 LAST 标记
        self.tts_audio_queue.put((SentenceType.LAST, [], None, getattr(self, 'current_sentence_id', None)))
    
    def tts_text_priority_thread(self):
        """重写 TTS 文本处理线程
        
        Coze 统一接口中 LLM 在服务端完成，
        此线程主要处理会话生命周期管理和打断逻辑。
        """
        while not self.conn.stop_event.is_set():
            try:
                message = self.tts_text_queue.get(timeout=1)
                
                if message.sentence_id != self.conn.sentence_id:
                    continue
                
                if self.conn.client_abort:
                    logger.bind(tag=TAG).info("收到打断信息")
                    try:
                        asyncio.run_coroutine_threadsafe(
                            self.stream_manager.interrupt(),
                            loop=self.conn.loop,
                        ).result(timeout=5)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"打断处理失败: {e}")
                    continue
                
                if message.sentence_type == SentenceType.FIRST:
                    # 开始新的对话轮次
                    self.reset_stream_state()
                    self.current_sentence_id = message.sentence_id
                    self.pcm_buffer.clear()
                    self.stream_manager.is_listening = True
                    
                    # 建立 WebSocket 连接
                    try:
                        future = asyncio.run_coroutine_threadsafe(
                            self.stream_manager.connect(message.sentence_id),
                            loop=self.conn.loop,
                        )
                        future.result(timeout=self.tts_timeout)
                    except Exception as e:
                        logger.bind(tag=TAG).error(f"建立 Coze 连接失败: {e}")
                        continue
                    
                    # 发送 FIRST 标记
                    self.tts_audio_queue.put((SentenceType.FIRST, [], None, message.sentence_id))
                
                elif ContentType.FILE == message.content_type:
                    # 处理音频文件
                    if message.content_file and __import__('os').path.exists(message.content_file):
                        self._process_audio_file_stream(
                            message.content_file,
                            callback=lambda audio_data: self.handle_audio_file(audio_data, message.content_detail)
                        )
                
                if message.sentence_type == SentenceType.LAST:
                    # 结束当前对话轮次
                    pass  # 由 on_chat_completed 回调处理 LAST 标记
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.bind(tag=TAG).error(
                    f"处理 TTS 文本失败: {str(e)}, 类型: {type(e).__name__}, "
                    f"堆栈: {traceback.format_exc()}"
                )
                continue
    
    async def text_to_speak(self, text, output_file):
        """Coze 统一接口中 TTS 由服务端驱动，此方法仅做兼容保留"""
        logger.bind(tag=TAG).debug(f"text_to_speak 被调用（Coze 模式下通常不直接调用）: {text}")
    
    async def close(self):
        """资源清理"""
        await super().close()
        await self.stream_manager.close()
        if hasattr(self, 'opus_encoder') and self.opus_encoder:
            self.opus_encoder.close()
```

---

### Task 2: 创建 ASR Provider

**Files:**
- Create: `core/providers/asr/coze_stream.py`

**参考文件:**
- [doubao_stream.py](../../../core/providers/asr/doubao_stream.py) — 流式 ASR 参考实现
- [base.py](../../../core/providers/asr/base.py) — ASR 基类

- [ ] **Step 1: 创建 asr/coze_stream.py 文件**

```python
"""
Coze 双向流式语音对话 ASR Provider
将设备端 Opus 音频解码为 PCM 后通过 CozeStreamManager 发送到 Coze WebSocket
"""
import uuid
import asyncio
import opuslib_next
from core.providers.asr.base import ASRProviderBase
from core.providers.asr.dto.dto import InterfaceType
from config.logger import setup_logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
    from core.providers.tts.coze_stream import CozeStreamManager


TAG = __name__
logger = setup_logging()


class ASRProvider(ASRProviderBase):
    """Coze 流式 ASR Provider
    
    通过共享的 CozeStreamManager 发送音频数据到 Coze WebSocket，
    并从 Manager 的回调中获取 ASR 识别结果。
    """
    
    def __init__(self, config, delete_audio_file):
        super().__init__()
        self.interface_type = InterfaceType.STREAM
        self.config = config
        self.output_dir = config.get("output_dir", "tmp/")
        self.delete_audio_file = delete_audio_file
        
        # 共享的 StreamManager（由 TTS Provider 注入）
        self.stream_manager: "CozeStreamManager" = None
        
        # Opus 解码器
        self.decoder = opuslib_next.Decoder(16000, 1)
        
        # 状态标志
        self.is_processing = False
        self._is_stopping = False
    
    async def open_audio_channels(self, conn: "ConnectionHandler"):
        await super().open_audio_channels(conn)
        
        # 从 TTS Provider 获取 stream_manager 引用
        if hasattr(conn, 'tts') and hasattr(conn.tts, 'stream_manager'):
            self.stream_manager = conn.tts.stream_manager
            logger.bind(tag=TAG).info("已从 TTS Provider 获取 CozeStreamManager 引用")
            
            # 设置 ASR 结果回调
            self.stream_manager.on_asr_text_callback = self._on_asr_result
    
    async def receive_audio(self, conn: "ConnectionHandler", audio, audio_have_voice):
        """接收音频数据并发送到 Coze
        
        重写父类方法：
        1. 先执行父类的基础逻辑（缓存音频、VAD 判断）
        2. 如果有声音且 WS 连接可用，开始发送音频帧
        3. VAD 检测到语音结束时，发送结束信号
        """
        # 先调用父类方法处理基础逻辑
        await super().receive_audio(conn, audio, audio_have_voice)
        
        # 如果没有 stream_manager 或未连接，跳过
        if not self.stream_manager or not self.stream_manager.is_connected:
            return
        
        # 如果本次有声音，且之前没有在处理
        if audio_have_voice and not self.is_processing:
            self.is_processing = True
            self._is_stopping = False
            self.stream_manager.is_listening = True
            logger.bind(tag=TAG).info("开始发送音频到 Coze")
        
        # 发送当前音频数据
        if self.stream_manager.is_connected and self.is_processing and not self._is_stopping:
            try:
                # Opus → PCM 解码
                pcm_frame = self.decoder.decode(audio, 960)
                if pcm_frame and len(pcm_frame) > 0:
                    # 通过 stream_manager 发送到 Coze
                    future = asyncio.run_coroutine_threadsafe(
                        self.stream_manager.send_audio(pcm_frame),
                        conn.loop,
                    )
                    # 不等待结果，避免阻塞
            except Exception as e:
                logger.bind(tag=TAG).error(f"发送音频数据失败: {e}")
        
        # 自动模式下 VAD 检测到语音结束时触发识别
        if (conn.asr.interface_type != InterfaceType.STREAM 
            and conn.client_voice_stop 
            and self.is_processing 
            and not self._is_stopping):
            
            # 发送音频结束信号
            self._is_stopping = True
            future = asyncio.run_coroutine_threadsafe(
                self.stream_manager.send_audio_complete(),
                conn.loop,
            )
    
    async def _on_asr_result(self, asr_text: str):
        """ASR 识别结果回调
        
        当 Coze 返回 conversation.chat.created 事件时触发，
        触发后续的 handle_voice_stop 流程。
        """
        if not asr_text:
            return
        
        logger.bind(tag=TAG).info(f"[Coze ASR] 识别结果: {asr_text}")
        self.is_processing = False
        self._is_stopping = False
        
        # 获取当前连接的音频数据快照
        conn = self.conn
        if conn and len(conn.asr_audio) > 15:
            await self.handle_voice_stop(conn, conn.asr_audio.copy())
    
    async def speech_to_text(self, opus_data, session_id, audio_format="opus", artifacts=None):
        """返回 ASR 识别结果文本
        
        从 CozeStreamManager 获取缓存的识别结果。
        """
        if self.stream_manager:
            result = self.stream_manager.get_asr_result()
            return result, None
        return "", None
    
    def stop_ws_connection(self):
        """停止 WebSocket 连接"""
        self.is_processing = False
        self._is_stopping = False
        if self.stream_manager and self.stream_manager.is_connected:
            asyncio.ensure_future(self.stream_manager.interrupt())
    
    async def close(self):
        """资源清理"""
        # 注意：不关闭 stream_manager，它由 TTS Provider 管理
        self.is_processing = False
        self._is_stopping = False
        if hasattr(self, 'decoder') and self.decoder:
            try:
                del self.decoder
                self.decoder = None
            except Exception as e:
                logger.bind(tag=TAG).debug(f"释放 decoder 时出错: {e}")
```

---

### Task 3: 更新配置文件

**Files:**
- Modify: `config.yaml`

- [ ] **Step 1: 在 ASR 配置段添加 CozeStreamASR**

在 `config.yaml` 的 `ASR:` 配置段中添加：

```yaml
  CozeStreamASR:
    # Coze 双向流式语音对话 - ASR 部分
    # 与 CozeStreamTTS 配合使用，共享同一个 WebSocket 连接
    type: coze_stream
    # 个人访问令牌 https://www.coze.cn/open/oauth/pats
    access_token: 你的coze个人令牌
    # 智能体 ID
    bot_id: "你的bot_id"
    # 用户 ID（可选，默认自动生成）
    user_id: "你的user_id"
    output_dir: tmp/
```

- [ ] **Step 2: 在 TTS 配置段添加 CozeStreamTTS**

在 `config.yaml` 的 `TTS:` 配置段中添加：

```yaml
  CozeStreamTTS:
    # Coze 双向流式语音对话 - TTS 部分
    # 通过 WebSocket 一次连接完成 ASR + LLM + TTS 全链路
    type: coze_stream
    # 个人访问令牌（应与 CozeStreamASR 保持一致）
    access_token: 你的coze个人令牌
    # 智能体 ID（应与 CozeStreamASR 保持一致）
    bot_id: "你的bot_id"
    # TTS 音色 ID（可选，不填则使用智能体默认音色）
    voice_id: "7426720361733046281"
    output_dir: tmp/
```

- [ ] **Step 3: 添加使用说明注释**

在配置文件中 `selected_module:` 段附近添加注释说明：

```yaml
# ===== Coze 流式语音对话模式 =====
# 使用 CozeStreamASR + CozeStreamTTS 时：
#   ASR: CozeStreamASR
#   TTS: CozeStreamTTS
#   LLM: 不需要配置（由 Coze 服务端内部完成 ASR+LLM+TTS）
# ==================================
```

---

### Task 4: Pylance 类型检查修复

**Files:**
- Verify: `core/providers/tts/coze_stream.py`
- Verify: `core/providers/asr/coze_stream.py`

- [ ] **Step 1: 运行 Pylance 检查两个新文件**

确保在严格模式下无类型错误。重点检查：
- `TYPE_CHECKING` 导入是否正确
- Optional 类型注解是否完整
- 方法签名与基类一致
- 异步方法是否有正确的 `async` 声明

Run: 在 IDE 中打开文件查看 Pylance 披错面板

Expected: 无 error 级别的诊断信息

- [ ] **Step 2: 修复发现的类型问题**

常见需要关注的问题：
- `CozeStreamManager` 的回调函数类型签名
- `asyncio.run_coroutine_threadsafe` 的返回值处理
- `opus_encoder_utils` 的属性访问

---

### Task 5: 集成验证

- [ ] **Step 1: 验证模块加载机制**

确认 `create_instance` 工厂函数能正确加载新模块：
- ASR: `asr.create_instance("coze_stream", config, delete_audio_file)` → `ASRProvider`
- TTS: `tts.create_instance("coze_stream", config, delete_audio_file)` → `TTSProvider`

- [ ] **Step 2: 验证初始化顺序**

确认 TTS 先于 ASR 初始化，使 `stream_manager` 注入时机正确：
1. `_initialize_tts()` → `TTSProvider.__init__()` 创建 `CozeStreamManager`
2. `tts.open_audio_channels(conn)` → 设置回调
3. `_initialize_asr()` → `ASRProvider.__init__()`
4. `asr.open_audio_channels(conn)` → 从 `conn.tts.stream_manager` 获取引用

- [ ] **Step 3: 端到端流程走查**

手动走查完整数据流：
1. ESP32 发送 Opus 音频 → `ASRProvider.receive_audio()` → PCM 解码 → `CozeStreamManager.send_audio()`
2. VAD 检测静音 → `send_audio_complete()`
3. Coze 返回 `conversation.chat.created` → `_on_asr_result()` → `handle_voice_stop()`
4. Coze 返回 `conversation.audio.delta` → `_on_coze_audio()` → Opus 编码 → 播放队列
5. Coze 返回 `conversation.chat.completed` → `_on_chat_completed()` → LAST 标记
