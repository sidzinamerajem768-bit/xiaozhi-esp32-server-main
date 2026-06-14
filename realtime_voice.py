"""
扣子双向流式对话 — 电话式实时语音对话

## 电话式体验特性

  - 全双工: 麦克风和扬声器同时工作，像真打电话一样
  - 随时打断: 对方说话时你可以直接插话，对方会立即停下来听
  - 状态提示: 清晰显示「聆听中」「对方正在说」「思考中」
  - 流畅过渡: 没有尴尬的空白，回合切换自然

## 交互示意

  📞 已接通，开始通话...
  ┌─────────────────────────────────────────────┐
  │ 🔊 聆听中...                                 │
  │                                             │
  │ 🗣️  你: 今天天气怎么样？                      │
  │                                             │
  │ 💭 思考中...                                 │
  │ 🔊 对方正在说...                             │
  │ 🤖 小先锋: 今天天气不错呀，适合出去走走~        │
  │                                             │
  │  ← 你可以随时打断，直接说话即可 →              │
  │                                             │
  │ 🔊 聆听中...                                 │
  │ 🗣️  你: 那帮我推荐个地方                      │
  │ ...                                         │
  └─────────────────────────────────────────────┘

快捷键: 按 Ctrl+C 挂断

依赖: pip install pyaudio websockets python-dotenv
"""

import os
import sys
import json
import time
import base64
import threading
from enum import Enum, auto
from dotenv import load_dotenv
import pyaudio
import websockets.sync.client as ws_sync

load_dotenv()

# ============================================================
# 配置
# ============================================================

ACCESS_TOKEN = os.getenv("COZE_ACCESS_TOKEN")
BOT_ID = os.getenv("COZE_BOT_ID")
WS_URL = f"wss://ws.coze.cn/v1/chat?bot_id={BOT_ID}"

SAMPLE_RATE = 16000
CHANNELS = 1
BIT_DEPTH = 16
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 3200  # 200ms @ 16kHz

# ============================================================
# 通话状态
# ============================================================

class CallState(Enum):
    IDLE = auto()        # 空闲，等待用户说话
    LISTENING = auto()   # 聆听中（用户正在说话）
    THINKING = auto()    # 思考中（服务端处理）
    SPEAKING = auto()    # 对方正在说（播放 Bot 语音）
    INTERRUPTED = auto() # 被用户打断，正在切换

STATE_LABELS = {
    CallState.IDLE:         "📱 等待中...",
    CallState.LISTENING:    "🎤 聆听中...",
    CallState.THINKING:     "💭 思考中...",
    CallState.SPEAKING:     "🔊 对方正在说...",
    CallState.INTERRUPTED:  "⚡ 打断切换中...",
}


# ============================================================
# 音频播放器（支持即时打断）
# ============================================================

class AudioPlayer:
    """电话式音频播放器：支持随时被打断并立即静音"""

    def __init__(self):
        self.pya = pyaudio.PyAudio()
        self.stream: pyaudio.Stream | None = None
        self._lock = threading.Lock()
        self._active = False

    def start(self):
        """打开扬声器"""
        with self._lock:
            if self._active:
                return
            self.stream = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                output=True,
                frames_per_buffer=CHUNK_SIZE,
            )
            self._active = True

    def write(self, pcm_data: bytes) -> bool:
        """
        写入 PCM 数据并播放。
        返回 True 表示正常播放，False 表示播放被中断。
        """
        with self._lock:
            if not self._active or not self.stream:
                return False
            try:
                self.stream.write(pcm_data, exception_on_underflow=False)
                return True
            except Exception:
                return False

    def mute(self):
        """立即静音（打断时调用）"""
        with self._lock:
            if self.stream and self._active:
                try:
                    self.stream.stop_stream()
                    self.stream.close()
                except Exception:
                    pass
                self.stream = None
                self._active = False

    def unmute(self):
        """取消静音，恢复播放"""
        self.start()

    def close(self):
        self.mute()
        self.pya.terminate()


# ============================================================
# 音频播放队列（线程安全）
# ============================================================

class AudioPlaybackQueue:
    """音频播放队列 + 播放线程，支持即时清空（打断时用）"""

    def __init__(self, player: AudioPlayer):
        self.player = player
        self._queue: list[bytes] = []
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._playback_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        self.player.mute()
        if self._thread:
            self._thread.join(timeout=1)

    def enqueue(self, pcm_data: bytes):
        with self._lock:
            self._queue.append(pcm_data)

    def clear(self):
        """清空播放队列（打断时调用）"""
        with self._lock:
            self._queue.clear()
        self.player.mute()

    def _playback_loop(self):
        while self._running:
            data = None
            with self._lock:
                if self._queue:
                    data = self._queue.pop(0)

            if data:
                # 确保播放器是活跃的
                self.player.unmute()
                self.player.write(data)
            else:
                time.sleep(0.01)

    def is_empty(self) -> bool:
        with self._lock:
            return len(self._queue) == 0


# ============================================================
# 电话式语音对话
# ============================================================

class PhoneCall:
    """电话式实时语音对话"""

    def __init__(self):
        self.ws: ws_sync.ClientConnection | None = None

        # 音频
        self.pya = pyaudio.PyAudio()
        self.player = AudioPlayer()
        self.playback = AudioPlaybackQueue(self.player)

        # 线程
        self._running = False
        self._mic_thread: threading.Thread | None = None
        self._recv_thread: threading.Thread | None = None

        # 打电话状态
        self._state_lock = threading.Lock()
        self._state = CallState.IDLE
        self._event_seq = 0

        # 统计
        self._audio_chunks = 0
        self._total_rounds = 0

    # ================================================================
    # 通话状态管理
    # ================================================================

    @property
    def state(self) -> CallState:
        with self._state_lock:
            return self._state

    @state.setter
    def state(self, new_state: CallState):
        with self._state_lock:
            old = self._state
            if old != new_state:
                self._state = new_state
                self._print_state(old, new_state)

    def _print_state(self, old: CallState, new: CallState):
        """打印状态切换"""
        label = STATE_LABELS.get(new, str(new))

        # 用不同前缀区分状态切换类型
        if new == CallState.LISTENING:
            print(f"\n  {label}")
        elif new == CallState.THINKING:
            print(f"  {label}")
        elif new == CallState.SPEAKING:
            print(f"  {label}")
        elif new == CallState.INTERRUPTED:
            print(f"\n  {label}")
        elif new == CallState.IDLE:
            print(f"\n  {label}")

    # ================================================================
    # WebSocket
    # ================================================================

    def _next_id(self) -> str:
        self._event_seq += 1
        return f"call_{int(time.time()*1000)}_{self._event_seq:04d}"

    def _send(self, event: dict):
        if self.ws:
            self.ws.send(json.dumps(event, ensure_ascii=False))

    def connect(self) -> bool:
        try:
            self.ws = ws_sync.connect(
                WS_URL,
                additional_headers={"Authorization": f"Bearer {ACCESS_TOKEN}"},
                open_timeout=10,
            )
            return True
        except Exception as e:
            print(f"\n[错误] 连接失败: {e}")
            return False

    def configure_call(self):
        """配置电话式对话参数"""
        event = {
            "id": self._next_id(),
            "event_type": "chat.update",
            "data": {
                "chat_config": {
                    "user_id": "phone_call_user",
                    "auto_save_history": True,
                    "meta_data": {"source": "phone_call_demo"},
                },
                "input_audio": {
                    "format": "pcm",
                    "codec": "pcm",
                    "sample_rate": SAMPLE_RATE,
                    "channel": CHANNELS,
                    "bit_depth": BIT_DEPTH,
                },
                "output_audio": {
                    "codec": "pcm",
                    "pcm_config": {"sample_rate": SAMPLE_RATE},
                    "speech_rate": 0,
                    "loudness_rate": 0,
                },
                # 服务端 VAD：自动判断说话/停止
                "turn_detection": {
                    "type": "server_vad",
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 600,
                    # 默认「发声即打断」— 用户一开口就打断 Bot
                },
                "asr_config": {
                    "stream_mode": "bidirectional_stream",
                    "enable_punc": True,
                    "enable_itn": True,
                    "enable_ddc": True,
                },
            },
        }
        self._send(event)

    # ================================================================
    # 麦克风采集线程
    # ================================================================

    def _mic_loop(self):
        """持续采集麦克风音频，发送到服务端"""
        try:
            mic = self.pya.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=SAMPLE_RATE,
                input=True,
                frames_per_buffer=CHUNK_SIZE,
            )
        except Exception as e:
            print(f"\n[错误] 无法打开麦克风: {e}")
            self._running = False
            return

        while self._running:
            try:
                pcm = mic.read(CHUNK_SIZE, exception_on_overflow=False)
                b64 = base64.b64encode(pcm).decode("utf-8")
                self._send({
                    "id": self._next_id(),
                    "event_type": "input_audio_buffer.append",
                    "data": {"delta": b64},
                })
            except Exception:
                if self._running:
                    break

        mic.stop_stream()
        mic.close()

    # ================================================================
    # 打断处理
    # ================================================================

    def _interrupt_bot(self):
        """用户插话，立即打断 Bot"""
        # 1. 清空播放队列，立即静音
        self.playback.clear()

        # 2. 清除服务端音频缓冲
        self._send({
            "id": self._next_id(),
            "event_type": "input_audio_buffer.clear",
        })

        # 3. 通知服务端取消当前推理
        self._send({
            "id": self._next_id(),
            "event_type": "conversation.chat.cancel",
        })

        self.state = CallState.INTERRUPTED
        # 短暂显示打断状态后切换到聆听
        time.sleep(0.1)
        self.state = CallState.LISTENING

    # ================================================================
    # WebSocket 接收线程
    # ================================================================

    def _recv_loop(self):
        """接收下行事件，根据事件驱动状态切换和打断逻辑"""

        while self._running and self.ws:
            try:
                raw = self.ws.recv(timeout=0.5)
            except TimeoutError:
                continue
            except Exception as e:
                if self._running:
                    print(f"\n[错误] 连接中断: {e}")
                self._running = False
                break

            try:
                evt = json.loads(raw)
            except json.JSONDecodeError:
                continue

            etype = evt.get("event_type", "")

            # ----- 连接事件 -----
            if etype == "chat.created":
                logid = evt.get("detail", {}).get("logid", "")
                print(f"  [连接] 已接通 | logid: {logid}")

            # ----- 配置确认 → 开始通话 -----
            elif etype == "chat.updated":
                # 启动播放队列
                self.playback.start()
                # 启动麦克风采集
                self._mic_thread = threading.Thread(target=self._mic_loop, daemon=True)
                self._mic_thread.start()
                self.state = CallState.IDLE

            # ========================================================
            # VAD 检测到用户开始说话 → 即时打断（不等 ASR）
            # ========================================================
            elif etype == "input_audio_buffer.speech_started":
                if self.state == CallState.SPEAKING:
                    self._interrupt_bot()

            # ========================================================
            # 用户侧事件（ASR 识别到用户说话）
            # ========================================================
            elif etype == "conversation.message.delta":
                data = evt.get("data", {})
                role = data.get("role", "")
                content = data.get("content", "")
                msg_type = data.get("type", "")

                if role == "user" and content:
                    # 用户正在说话 → 如果 Bot 在说，打断它
                    if self.state == CallState.SPEAKING:
                        self._interrupt_bot()
                    else:
                        self.state = CallState.LISTENING
                    sys.stdout.write(f"\r  🗣️  你: {content}")
                    sys.stdout.flush()

                elif role == "assistant" and content:
                    # Bot 回复文本（字幕）
                    self.state = CallState.SPEAKING
                    sys.stdout.write(f"\r  🤖 小先锋: {content}")
                    sys.stdout.flush()

            # ----- 消息完成 -----
            elif etype == "conversation.message.completed":
                data = evt.get("data", {})
                role = data.get("role", "")
                if role == "user":
                    print()  # 用户说完换行
                elif role == "assistant":
                    print()  # Bot 说完换行

            # ========================================================
            # 对话生命周期
            # ========================================================

            # 对话创建 → 用户说完，服务端开始处理
            elif etype == "conversation.chat.created":
                self.state = CallState.THINKING

            # 对话处理中
            elif etype == "conversation.chat.in_progress":
                self.state = CallState.THINKING

            # ========================================================
            # 音频事件
            # ========================================================

            # 音频字幕
            elif etype == "conversation.audio.sentence_start":
                text = evt.get("data", {}).get("content", "")
                if text:
                    print(f"\r  🤖 小先锋: {text}")
                    sys.stdout.flush()

            # 音频数据 → 入队播放
            elif etype == "conversation.audio.delta":
                b64 = evt.get("data", {}).get("content", "")
                if b64:
                    try:
                        pcm = base64.b64decode(b64)
                        # 如果当前不是 SPEAKING 或 LISTENING 状态（没有被响应占用），
                        # 说明是新的一轮回复开始了
                        if self.state not in (CallState.SPEAKING,):
                            self.state = CallState.SPEAKING
                        self.playback.enqueue(pcm)
                        self._audio_chunks += 1
                    except Exception:
                        pass

            # ========================================================
            # 对话结束
            # ========================================================

            elif etype == "conversation.chat.completed":
                self._total_rounds += 1
                # 等待播放队列清空
                while not self.playback.is_empty():
                    time.sleep(0.05)
                self._audio_chunks = 0
                self.state = CallState.IDLE

            elif etype == "conversation.chat.failed":
                print(f"\n  [挂断] 对话失败")
                self._running = False

            elif etype == "error":
                code = evt.get("data", {}).get("code", 0)
                msg = evt.get("data", {}).get("msg", "")
                print(f"\n  [错误] {code}: {msg}")
                if code in (4100, 4101):
                    self._running = False

    # ================================================================
    # 运行
    # ================================================================

    def run(self):
        """开始通话"""
        print()
        print("╔══════════════════════════════════════════╗")
        print("║       📞 扣子电话助手 — 语音通话         ║")
        print("║       直接说话即可，随时可以打断对方       ║")
        print("║       按 Ctrl+C 挂断电话                 ║")
        print("╚══════════════════════════════════════════╝")
        print()

        if not self.connect():
            return

        self._running = True
        self.configure_call()

        # 启动接收线程
        self._recv_thread = threading.Thread(target=self._recv_loop, daemon=True)
        self._recv_thread.start()

        try:
            while self._running:
                time.sleep(0.1)
        except KeyboardInterrupt:
            print("\n\n  📴 挂断中...")
        finally:
            self._hangup()

    def _hangup(self):
        """挂断电话"""
        self._running = False

        # 发送清空事件
        try:
            self._send({
                "id": self._next_id(),
                "event_type": "input_audio_buffer.clear",
            })
        except Exception:
            pass

        # 等待线程结束
        for t in [self._mic_thread, self._recv_thread]:
            if t and t.is_alive():
                t.join(timeout=2)

        # 关闭音频
        self.playback.stop()
        self.player.close()
        self.pya.terminate()

        # 关闭连接
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass

        print(f"  📴 已挂断 | 共通话 {self._total_rounds} 轮")
        print()


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    if not ACCESS_TOKEN or ACCESS_TOKEN == "your_pat_token_here":
        print("错误: 请先在 .env 中设置 COZE_ACCESS_TOKEN 和 COZE_BOT_ID")
        sys.exit(1)

    call = PhoneCall()
    call.run()
