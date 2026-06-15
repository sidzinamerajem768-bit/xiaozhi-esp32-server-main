# 小智 ESP32 服务端系统架构与协议文档

> 版本: 1.0 | 更新: 2025-06-15

---

## 一、系统架构总览

### 1.1 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                     ESP32 设备端                          │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │ 音频采集  │  │ VAD 检测  │  │ MCP 工具服务         │   │
│  │ (OPUS)   │→│ (Silero) │  │ (设备端功能)          │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
│         │                                               │
│         ▼ WebSocket (wss://)                            │
├─────────────────────────────────────────────────────────┤
│                    服务端                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐   │
│  │  路由层   │→│  消息分发  │→│  ConnectionHandler   │   │
│  └──────────┘  └──────────┘  └──────────────────────┘   │
│         │                        │                      │
│         ▼                        ▼                      │
│  ┌──────────┐           ┌──────────────────┐            │
│  │  ASR 模块 │           │  意图识别模块     │            │
│  │(Coze全链路)│          │(function_call模式) │            │
│  └──────────┘           └──────────────────┘            │
│         │                        │                      │
│         ▼                        ▼                      │
│  ┌──────────────────┐  ┌──────────────────┐            │
│  │  Coze WebSocket   │  │  MCP 工具执行器   │            │
│  │ (ASR+Bot+TTS)     │  │                 │            │
│  └──────────────────┘  └──────────────────┘            │
│         │                        │                      │
│         ▼                        ▼                      │
│  ┌─────────────────────────────────────────────────┐   │
│  │  外部服务: Coze API / 物联网平台 / 第三方API     │   │
│  └─────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────┤
```

### 1.2 核心模块

| 模块 | 职责 | 当前实现 |
|---|---|---|
| **WebSocket 服务器** | 管理设备连接、消息路由、心跳 | `websocket_server.py` |
| **ConnectionHandler** | 连接生命周期管理、会话状态、组件编排 | `connection.py` |
| **ASR Provider** | 语音识别、全链路语音对话 | `coze_stream.py` (ASR) |
| **TTS Provider** | 文本转语音 | `coze_stream.py` (TTS) |
| **Intent Provider** | 用户意图识别、工具调用触发 | `function_call.py` |
| **Tool Handler** | 工具注册、执行、结果处理 | `unified_tool_handler.py` |
| **MCP Handler** | 设备端 MCP 协议通信 | `mcp_handler.py` |
| **Memory Provider** | 对话记忆管理 | `mem_report_only.py` |

### 1.3 数据流（CozeStreamASR 全链路模式）

```
用户说话
  → Opus 音频帧 → WebSocket → 服务端
  → CozeStreamASR WebSocket → Coze 云端
  → ASR(转文字) → Bot(对话) → TTS(语音合成)
  → 音频帧 → WebSocket → ESP32 播放

  同步（文本到达）：
  → startToChat() → handle_user_intent()
    ├─ 工具调用 → 执行 MCP 工具 → speak_txt(结果播报)
    └─ 纯对话   → conn.llm is None → 跳过 chat()，Coze WebSocket 已回复
```

### 1.4 配置模型

系统通过管理后台 API 拉取差异化配置，覆盖 `config.yaml` 默认值：

```json
{
  "selected_module": {
    "ASR": "ASR_CozeStreamASR",
    "TTS": "TTS_CozeStreamTTS",
    "Intent": "Intent_function_call",
    "Memory": "Memory_mem_report_only"
  },
  "ASR": { "ASR_CozeStreamASR": { "type": "CozeStreamASR", ... } },
  "TTS": { "TTS_CozeStreamTTS": { "type": "CozeStreamTTS", ... } },
  "Intent": { "Intent_function_call": { "type": "function_call" } }
}
```

---

## 二、WebSocket 协议

### 2.1 连接建立

设备端发起 WebSocket 连接（ws/wss），携带认证信息：

```
GET /ws
Headers:
  Authorization: Bearer <token>
  Device-ID: <mac-address>
  Protocol-Version: 1
```

### 2.2 消息格式

所有消息使用 JSON 编码，顶层包含 `type` 字段：

```json
{
  "type": "<message_type>",
  ...其他字段...
}
```

### 2.3 消息类型

#### 2.3.1 `hello` — 握手

设备端发起，协商能力与参数：

```json
{
  "type": "hello",
  "version": 1,
  "transport": "websocket",
  "features": { "mcp": true },
  "audio_params": {
    "format": "opus",
    "sample_rate": 16000,
    "channels": 1,
    "frame_duration": 60
  }
}
```

| 字段 | 含义 |
|---|---|
| `version` | 协议版本 |
| `transport` | 传输方式，固定 `websocket` |
| `features.mcp` | 是否支持 MCP 工具协议 |
| `audio_params` | 音频编码参数 |

#### 2.3.2 `listen` — 监听状态

服务端 → 设备端，控制麦克风状态：

```json
{
  "type": "listen",
  "state": "start" | "stop" | "detect",
  "mode": "auto" | "manual",
  "text": "可选，detect 时可携带唤醒文本"
}
```

| 状态 | 含义 |
|---|---|
| `detect` | 进入唤醒检测模式 |
| `start` | 开始监听（麦克风打开） |
| `stop` | 停止监听（麦克风关闭） |

#### 2.3.3 `abort` — 打断

任意方向，中止当前语音播放或识别：

```json
{
  "type": "abort",
  "reason": "wakeup" | "manual" | "new_session"
}
```

#### 2.3.4 `sentence_start` — 开始播报

服务端 → 设备端，通知开始播放 TTS 音频：

```json
{
  "type": "tts",
  "text": "待播报文本（可选）"
}
```

#### 2.3.5 `sentence_end` — 停止播报

服务端 → 设备端，通知停止播放：

```json
{
  "type": "tts",
  "state": "stop"
}
```

#### 2.3.6 `stt` — 语音识别结果

服务端 → 设备端（可选），显示用户语音识别文本：

```json
{
  "type": "stt",
  "text": "识别文本"
}
```

#### 2.3.7 `audio` — 音频数据

双向传输，二进制帧（非 JSON），包含 Opus 编码的音频数据。设备端 → 服务端为麦克风采集，服务端 → 设备端为 TTS 合成音频。

#### 2.3.8 `mcp` — MCP 工具调用

双向，JSON-RPC 2.0 格式，详见第四节。

#### 2.3.9 `ping` / `pong` — 心跳

```json
{ "type": "ping" }
{ "type": "pong" }
```

### 2.4 会话生命周期

```
设备连接 → HELLO(能力协商)
         → listen(detect) [等待唤醒]
         → 唤醒词命中 → listen(start)
         → 音频帧流式上传
         → [VAD 检测语音结束] → ASR 识别
         → 意图分析
           ├─ 工具调用 → MCP 请求/响应 → TTS 播报
           └─ 纯对话   → Coze 全链路回复
         → sentence_start + 音频帧(播报)
         → sentence_end
         → listen(start) [下一轮]
```

---

## 三、音频流协议

### 3.1 编码参数

| 参数 | 值 | 说明 |
|---|---|---|
| 编码格式 | Opus | Audio Opus，帧级编码 |
| 采样率 | 16000 Hz（设备输入）| 设备麦克风 |
| 采样率 | 24000 Hz（TTS 输出）| 服务端 TTS 合成 |
| 声道数 | 1 (Mono) | 单声道 |
| 帧时长 | 60ms | 每帧 Opus 包时长 |
| 比特率 | 自适应 | Opus 默认 |

### 3.2 VAD 参数

| 参数 | 默认值 | 说明 |
|---|---|---|
| 说话阈值 | 0.5 | Silero VAD 语音概率阈值 |
| 静音超时 | 1000ms | 语音结束后等待时间触发识别 |
| 最小语音时长 | 100ms | 有效语音最小长度 |

### 3.3 TTS 流式输出

服务端 TTS 音频以 Opus 帧流式推送到设备端，播放时序：

```
sentence_start(JSON) → Opus帧1 → Opus帧2 → ... → Opus帧N → stop(JSON)
```

---

## 四、MCP 工具协议

### 4.1 概述

MCP (Model Context Protocol) 用于服务端与设备端之间的工具调用通信。基于 JSON-RPC 2.0，通过 WebSocket 传输。

### 4.2 初始化

设备端在 HELLO 中声明 `features.mcp: true` 后，服务端发送初始化请求：

**请求（服务端 → 设备端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
      "protocolVersion": "2024-11-05",
      "capabilities": { "tools": {} },
      "clientInfo": {
        "name": "XiaozhiClient",
        "version": "1.0.0"
      }
    }
  }
}
```

**响应（设备端 → 服务端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 1,
    "result": {
      "protocolVersion": "2024-11-05",
      "capabilities": { "tools": {} },
      "serverInfo": {
        "name": "esp32-device",
        "version": "2.2.6"
      }
    }
  }
}
```

### 4.3 工具列表获取

**请求（服务端 → 设备端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/list"
  }
}
```

**响应（设备端 → 服务端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 2,
    "result": {
      "tools": [
        {
          "name": "self.audio_speaker.set_volume",
          "description": "Set the volume of the audio speaker.",
          "inputSchema": {
            "type": "object",
            "properties": {
              "volume": { "type": "integer", "minimum": 0, "maximum": 100 }
            },
            "required": ["volume"]
          }
        },
        {
          "name": "self.lamp.set_power",
          "description": "Control the desk lamp. Turns on or off.",
          "inputSchema": {
            "type": "object",
            "properties": {
              "on": { "type": "boolean" }
            },
            "required": ["on"]
          }
        }
      ]
    }
  }
}
```

工具定义格式：

| 字段 | 类型 | 说明 |
|---|---|---|
| `name` | string | 工具名，格式 `self.<domain>.<action>` |
| `description` | string | 工具描述，供 LLM 理解用途 |
| `inputSchema.type` | string | 固定 `object` |
| `inputSchema.properties` | object | 参数定义（JSON Schema） |
| `inputSchema.required` | string[] | 必填参数列表 |

### 4.4 工具调用

**请求（服务端 → 设备端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 3,
    "method": "tools/call",
    "params": {
      "name": "self.lamp.set_power",
      "arguments": { "on": true }
    }
  }
}
```

**成功响应（设备端 → 服务端）：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 3,
    "result": {
      "content": [{ "type": "text", "text": "true" }],
      "isError": false
    }
  }
}
```

**错误响应：**

```json
{
  "type": "mcp",
  "payload": {
    "jsonrpc": "2.0",
    "id": 3,
    "error": {
      "code": -32603,
      "message": "Missing valid argument: volume"
    }
  }
}
```

### 4.5 工具调用流程（Coze 全链路模式）

```
用户: "把灯打开"

CozeStreamASR WebSocket 内部:
  → ASR → Bot 生成 "好的~<tool_call>self_lamp_set_power({on:true})</tool_call>" + 音频
  → 音频直接回设备播放 ✅
  → 文本同步到达服务端

服务端:
  → intent(function_call) 模式
  ├─ tool_call 检测
  │  → extract_json_from_string → 解析工具名+参数
  │  → MCP tools/call → 设备端执行
  │  → 结果静默记录(不播报TTS)
  └─ 纯对话 → conn.llm is None → skip
```

---

## 五、模块接口说明

### 5.1 ASR Provider

```python
class ASRProviderBase(ABC):
    """语音识别基类"""

    interface_type: InterfaceType  # STREAM | NON_STREAM | LOCAL

    async def open_audio_channels(self, conn):
        """打开音频通道，初始化 ASR 连接"""

    async def close_audio_channels(self):
        """关闭音频通道"""

    async def receive_audio(self, conn, audio_data, have_voice):
        """接收并处理音频数据"""

    async def save_audio(self, conn, audio_data):
        """保存临时音频数据（非流式模式使用）"""
```

**CozeStreamASR** 实现全双工语音对话（ASR + Bot + TTS 合一），通过 WebSocket 连接 Coze 云端，直接在连接内完成语音识别、对话生成、语音合成。

### 5.2 TTS Provider

```python
class TTSProviderBase(ABC):
    """文本转语音基类"""

    async def open_audio_channels(self, conn):
        """打开音频通道"""

    async def text_to_speak(self, text, output_file=None):
        """将文本转为语音（异步）"""

    def to_tts_stream(self, text, opus_handler=None):
        """流式 TTS 处理"""

    def tts_one_sentence(self, conn, content_type, content_detail=None):
        """单句 TTS 合成并放入队列"""
```

**CozeStreamTTS** 通过流管理器（CozeStreamManager）实现 WebSocket 流式 TTS，音频通过回调直接推入播放队列。`to_tts_stream` 为空实现（音频已由 `stream_manager` 回调处理）。

### 5.3 LLM Provider

```python
class LLMProviderBase(ABC):
    """大语言模型基类"""

    def response(self, session_id, dialogue, **kwargs):
        """流式响应生成"""

    def response_no_stream(self, system_prompt, user_prompt, **kwargs):
        """非流式响应生成（用于意图识别）"""

    def response_with_functions(self, session_id, dialogue, functions=None):
        """带函数调用的流式响应生成"""
```

> 注：CozeStreamASR 全链路模式下，LLM 模块不启用（`conn.llm is None`）。Bot 对话由 CozeStreamASR WebSocket 内部处理。

### 5.4 Intent Provider

```python
class IntentProviderBase(ABC):
    """意图识别基类"""

    async def detect_intent(self, conn, dialogue_history, text):
        """识别用户意图，返回 JSON 字符串"""
```

**function_call 模式**返回值：

```json
// 继续对话
{"function_call": {"name": "continue_chat"}}

// 工具调用
{"function_call": {"name": "handle_exit_intent", "arguments": {"say_goodbye": "再见"}}}

// 需要上下文
{"function_call": {"name": "result_for_context"}}
```

### 5.5 Tool Handler

#### 5.5.1 Action 类型

| 类型 | 含义 | 后续处理 |
|---|---|---|
| `RESPONSE` | 工具成功返回文本 | TTS 播报响应文本 |
| `REQLLM` | 需要 LLM 处理结果 | 非 Coze 模式：调用 LLM② 生成回复 |
| `NOTFOUND` | 工具不存在 | 播报错误信息 |
| `ERROR` | 工具执行出错 | 播报错误信息 |
| `RECORD` | 仅记录到对话历史 | 记录 tool_calls + tool 消息 |

#### 5.5.2 Coze 模式工具处理

Coze 模式下，工具的初始回复文本已在 `<tool_call>` 之前由流式 LLM 输出到 TTS，工具执行结果**不触发第二轮 LLM**，也**不额外播报**：

| Action | Coze 模式处理 |
|---|---|
| `RESPONSE` | 静默，仅写对话历史 |
| `NOTFOUND` | 静默 |
| `ERROR` | 静默 |
| `REQLLM` | 跳过，不调 LLM |
| `RECORD` | 正常记录 |

---

## 六、核心交互时序

### 6.1 工具调用（如"开灯"）

```
ESP32                     Server                        Coze Cloud
  │                         │                              │
  │──audio(Opus帧)─────────►│                              │
  │                         │──CozeStream ASR WebSocket──► │
  │                         │                              │
  │                         │◄──转写文本────────────────── │
  │                         │                              │
  │                         │───intent(function_call)──────│
  │                         │   <tool_call> 解析成功       │
  │                         │                              │
  │◄────MCP tools/call──────│                              │
  │────MCP result──────────►│                              │
  │                         │  工具结果：静默记录           │
  │                         │                              │
  │◄──sentence_start ───────│                              │
  │◄──audio(Opus帧)─────────│◄──Coze TTS 音频───────────── │
  │◄──sentence_end ─────────│                              │
  │                         │                              │
```

### 6.2 纯对话（如"还行"）

```
ESP32                     Server                        Coze Cloud
  │                         │                              │
  │──audio(Opus帧)─────────►│                              │
  │                         │──CozeStream ASR WebSocket──► │
  │                         │                              │
  │                         │◄──转写文本────────────────── │
  │                         │                              │
  │                         │───intent(function_call)──────│
  │                         │   continue_chat → skip       │
  │                         │   conn.llm is None → return  │
  │                         │                              │
  │◄──sentence_start ───────│                              │
  │◄──audio(Opus帧)─────────│◄──Coze Bot + TTS 音频─────── │
  │◄──sentence_end ─────────│                              │
  │                         │                              │
```

---

## 七、关键代码路径

| 功能 | 入口文件 | 关键方法 |
|---|---|---|
| 消息分发 | `textMessageProcessor.py` | `handleTextMessage()` |
| 握手 | `helloMessageHandler.py` | `handle()` |
| 监听控制 | `listenMessageHandler.py` | `handle()` |
| 音频接收 | `receiveAudioHandle.py` | `receive_audio()` → `startToChat()` |
| 打断处理 | `abortHandle.py` | `handleAbortMessage()` |
| 意图识别 | `intentHandler.py` | `handle_user_intent()` |
| 对话 chat | `connection.py` | `chat()` |
| 工具调用 | `unified_tool_manager.py` | `handle_llm_function_call()` |
| MCP 通信 | `mcp_handler.py` | `handle_mcp_message()` |
| 音频发送 | `sendAudioHandle.py` | `sendAudioMessage()` |
| TTS 队列 | `base.py` | `tts_text_priority_thread()` |
| Coze ASR | `coze_stream.py` | `receive_audio()` → Coze WS |
| Coze TTS | `coze_stream.py` | `text_to_speak()` + stream_manager |

---

## 八、延迟指标

| 阶段 | 说明 | 典型值 |
|---|---|---|
| **ASR** | 语音 → 文本 | Coze 云端处理，约 0.3-0.8s |
| **意图识别** | 文本 → 意图分类 | function_call 模式：0s（LLM 内嵌） |
| **LLM 首 token** | 请求 → 首字输出 | 由 Coze Bot 处理 |
| **TTS 排队** | 文本入队 → 发送到 Coze | 0.1-0.2s |
| **TTS 网络** | 发送 Coze → 首帧返回 | 0.3-0.6s |
| **TTS 总耗时** | 请求 → 合成完成 | 0.5-1.0s |
| **端到端** | 说话结束 → 首字播放 | ~1.0-2.0s（Coze 全链路） |
