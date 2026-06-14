# Coze 流式 ASR+LLM+TTS 统一接口设计文档

> 日期: 2026-06-12
> 状态: 已批准

## 1. 背景

xiaozhi-esp32-server 项目需要接入 Coze 的**双向流式语音对话 WebSocket OpenAPI**，通过一次 WebSocket 连接同时完成 ASR（语音识别）、LLM（大模型对话）、TTS（语音合成）全链路，实现低延迟的实时语音交互。

## 2. 目标

- 新增 `coze_stream` 类型的 ASR Provider 和 TTS Provider
- 复用现有的 Provider 基类接口、线程模型和队列机制
- 与现有架构（豆包双流等）保持一致的代码风格
- 支持 VAD 语音活动检测、打断、重连

## 3. API 规范

### 3.1 连接信息

| 项目 | 值 |
|------|-----|
| URL | `wss://ws.coze.cn/v1/chat?bot_id=xxx&authorization=Bearer xxx` |
| 鉴权 | Bearer Token（Header 或 URL 参数） |
| 心跳 | 服务端每 15 秒 ping，需自动 pong |

### 3.2 上行事件（客户端 → 服务端）

| 事件类型 | 说明 |
|----------|------|
| `input_audio_buffer_append` | 发送音频帧（PCM/OPUS） |
| `input_audio_buffer_complete` | 结束音频输入，触发 ASR+LLM+TTS |
| `conversation.message.create` | 发送文本消息（可选） |
| `conversation.interrupt` | 打断当前对话 |

### 3.3 下行事件（服务端 → 客户端）

| 事件类型 | 说明 |
|----------|------|
| `conversation.chat.created` | ASR 完成，包含识别文本和 logid |
| `conversation.message.delta` | LLM 流式文本输出 |
| `conversation.audio.delta` | TTS 流式音频输出（PCM 24000Hz） |
| `conversation.chat.completed` | 对话正常结束 |
| `conversation.chat.canceled` | 对话被取消 |
| `error` | 错误事件 |

### 3.4 音频格式

| 方向 | 格式 | 采样率 |
|------|------|--------|
| 上行 | PCM / OPUS | 16000Hz（设备原生） |
| 下行 | PCM | **24000Hz**（Coze 固定） |

## 4. 架构设计

### 4.1 整体架构图

```
┌─────────────────────────────────────────────────────┐
│                  ConnectionHandler                   │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐   │
│  │ ASR Queue │───▶│CozeStream│◀───│ TTS Text Queue│   │
│  └──────────┘    │ Manager  │    └──────────────┘   │
│                  (共享WS连接)                       │
│                  └─────┬─────┘                       │
│                        │                             │
│              ┌────────▼────────┐                    │
│              │ TTS Audio Queue │                    │
│              └────────┬────────┘                    │
│                       ▼                             │
│              播放 Opus 音频帧                         │
└─────────────────────────────────────────────────────┘
                        │ WebSocket
                        ▼
              wss://ws.coze.cn/v1/chat
```

### 4.2 文件结构

```
core/providers/
├── asr/
│   └── coze_stream.py      # ASR Provider
├── tts/
│   └── coze_stream.py      # TTS Provider + CozeStreamManager
```

### 4.3 核心类职责

#### CozeStreamManager（定义在 tts/coze_stream.py 中）

WebSocket 连接管理器，被 ASR 和 TTS Provider 共享：

- 管理 WS 连接生命周期（建立/维护/关闭）
- 封装上行事件发送（音频帧、结束信号、打断）
- 运行下行事件监听循环，分发事件到对应回调
- 维护会话状态（idle/listening/speaking）

#### ASRProvider（asr/coze_stream.py）

继承 `ASRProviderBase`：

- 重写 `receive_audio()`：Opus 解码 → PCM → 通过 Manager 发送
- 重写 `speech_to_text()`：从 Manager 获取 ASR 识别结果
- VAD 检测到语音结束时调用 `send_audio_complete()`
- 持有 `stream_manager` 引用（由 TTS Provider 注入）

#### TTSProvider（tts/coze_stream.py）

继承 `TTSProviderBase`：

- 创建并持有 `CozeStreamManager` 实例
- 重写 `open_audio_channels()`：将 Manager 注入到 ASR Provider
- 重写 `tts_text_priority_thread()`：处理会话生命周期和打断
- 从 Manager 接收 PCM 音频数据，Opus 编码后推入播放队列
- LLM 在 Coze 服务端完成，本地不需要单独的 LLM Provider

## 5. 数据流详解

### 5.1 用户说话流程

```
ESP32 Opus音频
    ↓
ASRProvider.receive_audio()
    ↓
opuslib_next.Decoder 解码为 PCM (16kHz)
    ↓
CozeStreamManager.send_audio(pcm_data)   ← WebSocket 上行
    ↓
VAD 检测到静音
    ↓
CozeStreamManager.send_audio_complete() ← 触发服务端 ASR+LLM+TTS
    ↓
收到 conversation.chat.created          ← WebSocket 下行
    ↓
提取 ASR 文本 → handle_voice_stop()     ← 进入回复阶段
```

### 5.2 AI 回复流程

```
Coze 服务端: ASR文本 → LLM推理 → TTS合成
    ↓
conversation.audio.delta (PCM 24000Hz)  ← WebSocket 下行
    ↓
OpusEncoder 编码 (24kHz → Opus)
    ↓
tts_audio_queue.put((MIDDLE, opus_data))
    ↓
sendAudioMessage() → ESP32 播放
    ↓
conversation.chat.completed             ← 对话结束
```

### 5.3 打断流程

```
用户打断检测 (client_abort=True)
    ↓
TTSProvider.tts_text_priority_thread() 检测到中断标志
    ↓
CozeStreamManager.interrupt()           ← WebSocket 上行 interrupt 事件
    ↓
清空音频缓冲区, 重置状态
```

## 6. 配置项

### config.yaml

```yaml
ASR:
  CozeStreamASR:
    type: coze_stream
    access_token: 你的coze个人令牌
    bot_id: "你的bot_id"
    output_dir: tmp/

TTS:
  CozeStreamTTS:
    type: coze_stream
    access_token: 你的coze个人令牌
    bot_id: "你的bot_id"
    voice_id: "7426720361733046281"   # 可选，指定TTS音色
    sample_rate: 24000                 # Coze固定输出采样率
    output_dir: tmp/
```

使用时设置：
```yaml
selected_module:
  ASR: CozeStreamASR
  TTS: CozeStreamTTS
  # LLM 不需要配置，由 Coze 内部完成
```

## 7. 关键技术点

### 7.1 采样率转换

Coze 下行 PCM 固定 24000Hz，而 xiaozhi 设备通常使用 16000Hz。
方案：TTS Provider 的 OpusEncoder 使用 24000Hz 初始化编码，解码端（ESP32）按实际采样率处理。

### 7.2 Provider 间状态同步

ASR 和 TTS 通过共享 `CozeStreamManager` 实例通信：
- TTS Provider 在 `open_audio_channels()` 中创建 Manager 并注入 ASR
- ASR 识别完成后通过 Manager 的回调通知机制触发后续流程

### 7.3 连接生命周期

- 首次说话时建立 WS 连接
- 对话结束后保持连接复用（类似 alibl_stream 的 60 秒复用策略）
- 连接异常时自动重连
- 会话切换时正确清理旧连接

### 7.4 错误处理

- 网络异常：捕获 WebSocket 异常，记录日志，标记连接不可用
- 认证失败（error 事件 code 4027/4028）：记录日志，提示检查 token
- 超时：配置合理的超时时间，超时后关闭连接并重试

## 8. 设计决策记录

| 决策 | 理由 |
|------|------|
| 选择方案 A（统一 Provider 模式） | 兼容现有注册机制，与豆包双流风格一致 |
| CozeStreamManager 放在 TTS 文件中 | TTS 是更复杂的 Provider，自然拥有连接管理职责 |
| 不使用 cozepy SDK | 减少依赖，更好地控制事件分发逻辑 |
| LLM 由 Coze 内部完成 | 统一接口的核心价值就是避免本地三次调用的延迟 |
