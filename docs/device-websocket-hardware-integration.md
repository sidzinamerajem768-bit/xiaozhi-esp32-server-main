# 设备 WebSocket API 接口文档
host: 8.156.35.144
## 1. WebSocket 连接

```text
ws://{host}:8084/ws/v1/dev/{productKey}/{deviceId}?authMode={authMode}&token={token}&timestamp={timestamp}&nonce={nonce}&sign={sign}
```

路径参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `productKey` | 是 | 产品标识。 |
| `deviceId` | 是 | 设备唯一 ID。 |

Query 参数：

| 参数 | 必填 | 说明 |
| --- | --- | --- |
| `authMode` | 是 | `init` 或 `device`。 |
| `token` | 是 | `init` 使用初始化 token；`device` 使用注册返回的 `deviceToken`。 |
| `timestamp` | 是 | 毫秒时间戳。 |
| `nonce` | 是 | 每次握手唯一随机字符串。 |
| `sign` | 是 | HMAC-SHA256 签名，十六进制小写。 |

## 2. 握手签名

签名原文固定为：

```text
GET
/ws/v1/dev/{productKey}/{deviceId}
{productKey}
{deviceId}
{authMode}
{timestamp}
{nonce}
{token}
```

签名算法：

```text
sign = hex_lowercase(HMAC_SHA256(secret, canonical))
```

密钥选择：

| authMode | token | secret |
| --- | --- | --- |
| `init` | 初始化 token | 产品级 `productSecret` |
| `device` | 注册返回的 `deviceToken` | 注册返回的 `deviceSecret` |

## 3. 通用请求帧

```json
{
  "header": {
    "requestId": "req-001",
    "method": "POST",
    "uri": "/heartbeat",
    "timestamp": 1779454918489,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "query": {},
  "body": {}
}
```

## 4. 通用响应帧

```json
{
  "requestId": "req-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779454919000,
  "data": {}
}
```

## 5. `/register` 设备注册

连接模式：`authMode=init`

请求：

```json
{
  "header": {
    "requestId": "reg-001",
    "method": "POST",
    "uri": "/register",
    "timestamp": 1779454918489,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "sn": "SN202605220001",
    "mac": "AA:BB:CC:DD:EE:FF",
    "model": "robot-v1",
    "fwVersion": "1.0.0",
    "hwVersion": "1.0"
  }
}
```

响应：

```json
{
  "requestId": "reg-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779454919000,
  "data": {
    "deviceToken": "dev_token_xxx",
    "deviceSecret": "dev_secret_xxx",
    "activateStatus": "activated"
  }
}
```

## 6. `online_ack` 上线确认

连接模式：`authMode=device`

设备正式连接成功后，服务端主动下发：

```json
{
  "header": {
    "method": "POST",
    "uri": "/cmd/downlink",
    "timestamp": 1779454920000,
    "protocolVersion": "1.0"
  },
  "body": {
    "cmdType": "online_ack",
    "params": {
      "serverTime": 1779454920000,
      "nextIntervalSec": 60
    }
  }
}
```

## 7. `/heartbeat` 心跳

请求：

```json
{
  "header": {
    "requestId": "hb-001",
    "method": "POST",
    "uri": "/heartbeat",
    "timestamp": 1779454980000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "battery": 86,
    "rssi": -55,
    "ip": "192.168.1.20"
  }
}
```

响应：

```json
{
  "requestId": "hb-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779454980100,
  "data": {
    "nextIntervalSec": 60,
    "serverTime": 1779454980100
  }
}
```

## 8. `/state/report` 状态上报

请求：

```json
{
  "header": {
    "requestId": "state-001",
    "method": "POST",
    "uri": "/state/report",
    "timestamp": 1779454990000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "workMode": "normal",
    "micStatus": "on",
    "speakerVolume": 70,
    "ledStatus": "on",
    "networkType": "wifi"
  }
}
```

响应：

```json
{
  "requestId": "state-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779454990100,
  "data": {
    "needSyncConfig": false
  }
}
```

## 9. `/event/alarm` 告警上报

请求：

```json
{
  "header": {
    "requestId": "alarm-001",
    "method": "POST",
    "uri": "/event/alarm",
    "timestamp": 1779455000000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "alarmType": "sos_button",
    "level": "high",
    "eventTime": 1779455000000
  }
}
```

响应：

```json
{
  "requestId": "alarm-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455000100,
  "data": {
    "accepted": true,
    "dispatchId": "ALM123456789"
  }
}
```

## 10. `/ota/check` OTA 检查

请求：

```json
{
  "header": {
    "requestId": "ota-check-001",
    "method": "GET",
    "uri": "/ota/check",
    "timestamp": 1779455010000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "query": {
    "fwVersion": "1.0.0",
    "channel": "stable"
  },
  "body": {}
}
```

无升级响应：

```json
{
  "requestId": "ota-check-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455010100,
  "data": {
    "hasUpdate": false
  }
}
```

有升级响应：

```json
{
  "requestId": "ota-check-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455010100,
  "data": {
    "hasUpdate": true,
    "targetVersion": "1.1.0",
    "packageUrl": "https://example.com/firmware.bin",
    "checksum": "sha256-hex",
    "checksumType": "sha256",
    "force": false,
    "releaseTime": "2026-06-08T10:00:00"
  }
}
```

## 11. `/ota/progress` OTA 进度

请求：

```json
{
  "header": {
    "requestId": "ota-progress-001",
    "method": "POST",
    "uri": "/ota/progress",
    "timestamp": 1779455020000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "targetVersion": "1.1.0",
    "stage": "downloading",
    "progress": 35,
    "errorCode": null,
    "errorMessage": null,
    "reportTime": 1779455020000
  }
}
```

响应：

```json
{
  "requestId": "ota-progress-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455020100
}
```

## 12. `/cmd/downlink` 服务端下行命令

服务端主动下发：

```json
{
  "header": {
    "requestId": "srv-123456789",
    "method": "POST",
    "uri": "/cmd/downlink",
    "timestamp": 1779455030000,
    "fwVersion": "server",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "cmdId": "CMD123456789",
    "cmdType": "volume_set",
    "params": {
      "volume": 60
    },
    "timeoutSec": 5
  }
}
```

设备收到后立即响应：

```json
{
  "requestId": "srv-123456789",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455030100,
  "data": {
    "cmdId": "CMD123456789",
    "execStatus": "received"
  }
}
```

## 13. `/cmd/ack` 指令执行回执

请求：

```json
{
  "header": {
    "requestId": "cmd-ack-001",
    "method": "POST",
    "uri": "/cmd/ack",
    "timestamp": 1779455040000,
    "fwVersion": "1.0.0",
    "protocolVersion": "1.0"
  },
  "path": {
    "productKey": "pioneer_ai_robot",
    "deviceId": "RBT202605220001"
  },
  "body": {
    "cmdId": "CMD123456789",
    "execStatus": "success",
    "resultCode": 0,
    "resultMessage": "done",
    "eventTime": 1779455040000
  }
}
```

响应：

```json
{
  "requestId": "cmd-ack-001",
  "code": 0,
  "message": "OK",
  "timestamp": 1779455040100
}
```

## 14. 错误码

| code | message |
| --- | --- |
| `0` | `OK` |
| `1001` | 参数缺失或格式错误 |
| `1002` | token 无效或过期 |
| `1003` | 设备未激活 |
| `1004` | 设备不存在 |
| `1005` | 请求过于频繁 |
| `1006` | 请求处理中 |
| `1007` | 签名错误 |
| `1008` | 时间戳过期 |
| `1009` | 连接数超限 |
| `1010` | 未知 uri |
| `2001` | 指令不支持 |
| `2002` | 指令执行失败 |
| `3001` | OTA 包不存在 |
| `3002` | OTA 校验失败 |
| `5000` | 服务器内部错误 |

## 15. WebSocket 关闭码

| closeCode | 说明 |
| --- | --- |
| `4001` | 鉴权失败 |
| `4002` | 设备未激活 |
| `4008` | 心跳超时 |
| `4009` | 设备在别处上线 |
| `4010` | 服务端限流或主动断开 |

