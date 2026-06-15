# 双向流式语音合成事件
## 上行事件
### 更新语音合成配置

* **事件类型**：`speech.update`
* **事件说明**：更新流式语音合成配置。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `speech.update`。 |
   | data | Object | 可选 | 事件数据，包含语音合成配置的详细信息。 |
   | data.output_audio | Object | 可选 | 输出音频格式。 |
   | data.output_audio.codec | String | 可选 | 输出音频编码，支持 `pcm`、`opus`。默认是 `pcm`。 |
   | data.output_audio.pcm_config | Object | 可选 | 当 `codec` 设置为 `opus` 时，不需要设置此字段。 <br> 当 `codec` 设置为 `pcm` 时，返回的 PCM 数据将固定为单声道，采样深度为 16 位。 <br>  |
   | data.output_audio.pcm_config.sample_rate | Integer | 可选 | 输出 `pcm` 音频的采样率，默认 24000。 |
   | data.output_audio.pcm_config.frame_size_ms | Float | 可选 | 输出每个 pcm 包的时长，单位 ms，默认不限制。 |
   | data.output_audio.pcm_config. limit_config | Object | 可选 | 输出音频限流配置，默认不限制。 |
   | data.output_audio.pcm_config. limit_config.period | Integer | 可选 | 周期的时长，单位为秒。例如设置为 10 秒，则以 10 秒作为一个周期。 |
   | data.output_audio.pcm_config. limit_config.max_frame_num | Integer | 可选 | 周期内，最大返回 pcm 包数量。 |
   | data.output_audio.opus_config | Object | 可选 | 当 `codec` 设置为 `pcm` 时，不需要设置此字段。 |
   | data.output_audio.opus_config.bitrate | Integer | 可选 | 输出 `opus` 的码率，默认 48000。 |
   | data.output_audio.opus_config.use_cbr | Boolean | 可选 | 输出 `opus` 是否使用 CBR 编码，默认为 `false`。 |
   | data.output_audio.opus_config.frame_size_ms | Float | 可选 | 输出 `opus` 的帧长，默认是 10。可选值： <br> 2.5、5、10、20、40、60 |
   | data.output_audio.opus_config.limit_config | Object | 可选 | 输出音频限流配置，默认不限速。 |
   | data.output_audio.opus_config.limit_config.period | Integer | 可选 | 周期的时长，单位为秒。例如设置为 10 秒，则以 10 秒作为一个周期。 |
   | data.output_audio.opus_config.limit_config.max_frame_num | Integer | 可选 | 周期内最大返回的 Opus 帧数量。 |
   | data.output_audio.speech_rate | Integer | 可选 | 输出音频的语速，取值范围 [-50, 100]，默认为 0。-50 表示 0.5 倍速，100 表示 2 倍速。 |
   | data.output_audio.loudness_rate | Integer | 可选 | 输出音频的音量，取值范围 [-50, 100]，默认为 0。-50 表示 0.5 倍音量，100 表示 2 倍音量。不支持复刻音色。 |
   | data.output_audio.voice_id | String | 可选 | 输出音频的音色 ID。默认音色为"柔美女友"。你可以调用[查看音色列表](https://docs.coze.cn/api/open/docs/developer_guides/list_voices) API 查看当前可用的所有音色 ID。 |
   | data.output_audio.context_texts | String | 可选 | 语音合成的辅助信息，用于控制合成语音的整体情绪（如悲伤、生气）、方言（如四川话、北京话）、语气（如撒娇、暧昧、吵架、夹子音）、语速（快慢）及音调（高低）等。默认为空。 <br> 示例：用低沉沙哑的语气、带着沧桑与绝望地说。 <br> * 仅当 `voice_id` 为豆包语音合成大模型 2.0 音色时才支持该参数，具体音色列表请参见[系统音色列表](https://docs.coze.cn/api/open/docs/dev_how_to_guides/sys_voice)。 <br> * 更多关于豆包语音合成 2.0 的 `context_texts` 示例和效果可参考[语音指令-示例库](https://www.volcengine.com/docs/6561/1871062?lang=zh#_1-2-%F0%9F%92%A1%E8%AF%AD%E9%9F%B3%E6%8C%87%E4%BB%A4-%E7%A4%BA%E4%BE%8B%E5%BA%93)。 <br>  |
   | data.output_audio.emotion_config | Object | 可选 | 设置多情感音色的情感类型和情感值，仅当 `voice_id` 为多情感音色时才需要设置。 |
   | data.output_audio.emotion_config.emotion | String | 可选 | 设置多情感音色的情感类型。不同音色支持的情感范围不同，可以通过[系统音色列表](https://www.coze.cn/open/docs/dev_how_to_guides/sys_voice)查看各音色支持的情感。默认为空。枚举值如下： <br>  <br> * happy-开心 <br> * sad-悲伤 <br> * angry-生气 <br> * surprised-惊讶 <br> * fear-恐惧 <br> * hate-厌恶 <br> * excited-激动 <br> * coldness-冷漠 <br> * neutral-中性 |
   | data.output_audio.emotion_config.emotion_scale | Float | 可选 | 情感值用于量化情感的强度。数值越高，情感表达越强烈，例如： “开心” 的情感值 5 比 1 更显兴奋。 <br> 取值范围：1.0~5.0，默认值：4.0。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "speech.update",
     "data": {
         "output_audio": {
             "codec": "pcm",
             "pcm_config": {
                 "sample_rate": 24000
             },
             "speech_rate": 50,
             "voice_id": "音色id"
         }
     }
   }
   ```


### 流式输入文字

* **事件类型**：`input_text_buffer.append`
* **事件说明**：流式向服务端提交文字的片段。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `input_text_buffer.append`。 |
   | data | Object | 必选 | 事件数据，包含文字片段。 |
   | data.delta | String | 必选 | 需要合成语音的文字片段。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "input_text_buffer.append",
     "data": {
         "delta": "text"
     }
   }
   ```


### 提交文字

* **事件类型**：`input_text_buffer.complete`
* **事件说明**：提交 `append` 的文本，发送后将收到 `input_text_buffer.completed` 的下行事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `input_text_buffer.complete`。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "input_text_buffer.complete"
   }
   ```


## 下行事件
### 连接成功

* **事件类型**：`speech.created`
* **事件说明**：语音合成连接成功后，返回此事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 服务端生成的唯一 ID。 |
   | event_type | String | 必选 | 固定为 `speech.created`。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
     "id": "7446668538246561xxxx",
     "event_type": "speech.created",
     "detail": {
         "logid": "20241210152726467C48D89D6DB2F3***"
     }
   }
   ```


### 配置更新完成

* **事件类型**：`speech.updated`
* **事件说明**：配置更新成功后，会返回最新的配置。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `speech.updated`。 |
   | data | Object | 必选 | 事件数据，包含语音合成配置的详细信息。 |
   | data.output_audio | Object | 必选 | 输出音频格式。 |
   | data.output_audio.codec | String | 必选 | 输出音频编码，支持 `pcm`、`opus`。默认是 `pcm`。 |
   | data.output_audio.pcm_config | Object | 可选 | 当 `codec` 设置为 `opus` 时，不需要设置此字段。 |
   | data.output_audio.pcm_config.sample_rate | Integer | 可选 | 输出 `pcm` 音频的采样率，默认 24000。 |
   | data.output_audio.opus_config | Object | 可选 | 当 `codec` 设置为 `pcm` 时，不需要设置此字段。 |
   | data.output_audio.opus_config.bitrate | Integer | 可选 | 输出 `opus` 的码率，默认 48000。 |
   | data.output_audio.opus_config.use_cbr | Boolean | 可选 | 输出 `opus` 是否使用 CBR 编码，默认为 `false`。 |
   | data.output_audio.opus_config.frame_size_ms | Float | 可选 | 输出 `opus` 的帧长，默认是 10。 |
   | data.output_audio.speech_rate | Integer | 必选 | 输出音频的语速，取值范围 [-50, 100]，默认为 0。-50 表示 0.5 倍速，100 表示 2 倍速。 |
   | data.output_audio.voice_id | String | 必选 | 输出音频的音色 ID。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "speech.updated",
     "data": {
         "output_audio": {
             "codec": "pcm",
             "pcm_config": {
                 "sample_rate": 24000
             },
             "speech_rate": 50,
             "voice_id": "音色id"
         }
     },
     "detail": {
         "logid": "20241210152726467C48D89D6DB2F3***"  }
   }
   ```


### `input_text_buffer` 提交完成

* **事件类型**：`input_text_buffer.completed`
* **事件说明**：流式提交的文字完成后，返回此事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `input_text_buffer.completed`。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "input_text_buffer.completed",
     "detail": {
         "logid": "20241210152726467C48D89D6DB2F3***"
     }
   }
   ```


### 合成增量语音

* **事件类型**：`speech.audio.update`
* **事件说明**：语音合成产生增量语音时，返回此事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `speech.audio.update`。 |
   | data | Object | 必选 | 事件数据，包含音频片段信息。 |
   | data.delta | String | 必选 | base64 编码后的音频片段。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "speech.audio.update",
     "data": {
         "delta": "base64EncodedAudioDelta"
     },
     "detail": {
         "logid": "20241210152726467C48D89D6DB2F3***"  }
   }
   ```


### 合成完成 

* **事件类型**：`speech.audio.completed`
* **事件说明**：语音合成完成后，返回此事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 客户端自行生成的事件 ID，方便定位问题。 |
   | event_type | String | 必选 | 固定为 `speech.audio.completed`。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
     "id": "event_id",
     "event_type": "speech.audio.completed",
     "detail": {
         "logid": "20241210152726467C48D89D6DB2F3***"
     }
   }
   ```


### 发生错误

* **事件类型**：`error`
* **事件说明**：对话过程中的错误事件。
* **事件结构**：
   | **参数** | **类型** | **是否必选** | **说明** |
   | --- | --- | --- | --- |
   | id | String | 必选 | 服务端生成的唯一 ID。 |
   | event_type | String | 必选 | 固定为 `error`。 |
   | data | Object | 必选 | 事件数据，包含错误信息。 |
   | data.code | Integer | 必选 | 错误码。 |
   | data.msg | String | 必选 | 错误信息。 |
   | detail | Object | 必选 | 事件详情。 |
   | detail.logid | String | 必选 | 本次请求的日志 ID。如果遇到异常报错场景，且反复重试仍然报错，可以根据此 logid 及错误码联系扣子团队获取帮助。详细说明可参考获取帮助和技术支持。 |
* **事件示例**：
   ```JSON
   {
       "id": "event_1",
       "event_type": "error"
       "data": {
           "code": 1,
           "msg": "发生异常"
       },
       "detail": {
           "logid": "20241210152726467C48D89D6DB2F3***"
       }
   }
   ```
