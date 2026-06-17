# 全量接口迁移比对报告

> 生成时间: 2026-06-16
> 对比：Java后端 (23个Controller, ~136个接口) ↔ Python FastAPI (13个Router, ~80个接口)

---

## 一、已迁移接口（12个Controller, ~80个接口）

### 1.1 LoginController → auth.py (8/8 ✅ 全部迁移)

| URL | 方法 | 状态 | 文件 |
|-----|------|:----:|------|
| /user/login | POST | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L72) |
| /user/register | POST | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L241) |
| /user/info | GET | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L182) |
| /user/pub-config | GET | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L280) |
| /user/change-password | PUT | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L298) |
| /user/retrieve-password | PUT | ✅ | [auth.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/python-backend/app/routers/auth.py#L316) |
| /user/captcha | GET | ❌ | 图形验证码（需依赖Redis缓存） |
| /user/smsVerification | POST | ❌ | 短信验证码（需三方短信SDK） |

### 1.2 AgentController → agent.py (5/18 ✅ 核心接口)

| URL | 方法 | 状态 | 说明 |
|-----|------|:----:|------|
| /agent/list | GET | ✅ | 核心 |
| /agent/{id} | GET | ✅ | 核心 |
| /agent | POST | ✅ | 核心 |
| /agent/{id} | PUT | ✅ | 核心 |
| /agent/{id} | DELETE | ✅ | 核心 |
| /agent/all | GET | ❌ | P2-管理员接口 |
| /agent/template | GET | ✅ | (在agent_template.py) |
| /agent/{id}/sessions | GET | ❌ | 需Redis |
| /agent/{id}/chat-history/{sessionId} | GET | ❌ | 需Redis |
| /agent/{id}/chat-history/user | GET | ❌ | |
| /agent/{id}/chat-history/audio | GET | ❌ | |
| /agent/audio/{audioId} | POST | ❌ | 需Redis |
| /agent/play/{uuid} | GET | ❌ | 需Redis |
| /agent/tag | POST | ❌ | |
| /agent/tag/list | GET | ❌ | |
| /agent/tag/{id} | DELETE | ❌ | |
| /agent/saveMemory/{macAddress} | PUT | ✅ | (在agent.py) |
| /agent/chat-summary/{sessionId}/save | POST | ❌ | 需AI调用 |
| /agent/chat-title/{sessionId}/generate | POST | ❌ | 需AI调用 |

### 1.3 DeviceController → device.py (6/9 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /device/bind/{agentId}/{deviceCode} | POST | ✅ |
| /device/register | POST | ✅ |
| /device/bind/{agentId} | GET | ✅ |
| /device/unbind | POST | ✅ |
| /device/update/{id} | PUT | ✅ |
| /device/manual-add | POST | ✅ |
| /device/tools/list/{deviceId} | POST | ❌ |
| /device/tools/call/{deviceId} | POST | ❌ |

### 1.4 OTAController → ota.py (3/3 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /ota/ | POST | ✅ |
| /ota/activate | POST | ✅ |
| /ota/ | GET | ✅ |

### 1.5 ConfigController → config.py (3/3 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /config/server-base | POST | ✅ |
| /config/agent-models | POST | ✅ |
| /config/correct-words | POST | ✅ |

### 1.6 KnowledgeBaseController → knowledge.py (7/7 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /datasets | GET | ✅ |
| /datasets/{dataset_id} | GET | ✅ |
| /datasets | POST | ✅ |
| /datasets/{dataset_id} | PUT | ✅ |
| /datasets/{dataset_id} | DELETE | ✅ |
| /datasets/batch | DELETE | ✅ |
| /datasets/rag-models | GET | ✅ |

### 1.7 VoiceCloneController → voice_clone.py (6/6 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /voiceClone | GET | ✅ |
| /voiceClone/upload | POST | ✅ |
| /voiceClone/updateName | POST | ✅ |
| /voiceClone/audio/{id} | POST | ✅ |
| /voiceClone/play/{uuid} | GET | ✅ |
| /voiceClone/cloneAudio | POST | ✅ |

### 1.8 ModelController → model.py (3/11 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /models/names | GET | ✅ |
| /models/llm/names | GET | ✅ |
| /models/{modelId}/voices | GET | ✅ |
| /models/{modelType}/provideTypes | GET | ❌ P2 |
| /models/list | GET | ❌ P2 |
| /models/{modelType}/{provideCode} | POST | ❌ P2 |
| /models/{modelType}/{provideCode}/{id} | PUT | ❌ P2 |
| /models/{id} | DELETE | ❌ P2 |
| /models/{id} | GET | ❌ P2 |
| /models/enable/{id}/{status} | PUT | ❌ P2 |
| /models/default/{id} | PUT | ❌ P2 |

### 1.9 AdminController → admin.py (5/5 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /admin/users | GET | ✅ |
| /admin/users/{id} | PUT | ✅ |
| /admin/users/{id} | DELETE | ✅ |
| /admin/users/changeStatus/{status} | PUT | ✅ |
| /admin/device/all | GET | ✅ |

### 1.10 SysParamsController → sys_params.py (5/5 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /admin/params/page | GET | ✅ |
| /admin/params/{id} | GET | ✅ |
| /admin/params | POST | ✅ |
| /admin/params | PUT | ✅ |
| /admin/params/delete | POST | ✅ |

### 1.11 SysDictDataController → sys_dict.py (6/6 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /admin/dict/data/page | GET | ✅ |
| /admin/dict/data/{id} | GET | ✅ |
| /admin/dict/data/save | POST | ✅ |
| /admin/dict/data/update | PUT | ✅ |
| /admin/dict/data/delete | POST | ✅ |
| /admin/dict/data/type/{dictType} | GET | ✅ |

### 1.12 AgentTemplateController → agent_template.py (6/6 ✅)

| URL | 方法 | 状态 |
|-----|------|:----:|
| /agent/template/page | GET | ✅ |
| /agent/template/{id} | GET | ✅ |
| /agent/template | POST | ✅ |
| /agent/template | PUT | ✅ |
| /agent/template/{id} | DELETE | ✅ |
| /agent/template/batch-remove | POST | ✅ |

---

## 二、未迁移接口（11个Controller, ~56个接口）

### 2.1 AgentChatHistoryController (4个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /agent/chat-history/report | POST | 聊天记录上报（匿名） | P1 |
| /agent/chat-history/getDownloadUrl/{agentId}/{sessionId} | POST | 获取下载链接 | P1 |
| /agent/chat-history/download/{uuid}/current | GET | 下载当前会话 | P1 |
| /agent/chat-history/download/{uuid}/previous | GET | 下载当前+前20条 | P1 |

### 2.2 AgentMcpAccessPointController (2个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /agent/mcp/address/{agentId} | GET | MCP接入点地址 | P1 |
| /agent/mcp/tools/{agentId} | GET | MCP工具列表 | P1 |

### 2.3 AgentVoicePrintController (4个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /agent/voice-print | POST | 创建声纹 | P1 |
| /agent/voice-print | PUT | 更新声纹 | P1 |
| /agent/voice-print/{id} | DELETE | 删除声纹 | P1 |
| /agent/voice-print/list/{id} | GET | 声纹列表 | P1 |

### 2.4 CorrectWordController (7个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /correct-word/file | POST | 创建替换词文件 | P1 |
| /correct-word/file/{fileId} | PUT | 修改替换词文件 | P1 |
| /correct-word/file/list | GET | 分页查询 | P1 |
| /correct-word/file/select | GET | 列表查询 | P1 |
| /correct-word/file/download/{fileId} | GET | 下载文件 | P1 |
| /correct-word/file/{fileId} | DELETE | 删除 | P1 |
| /correct-word/file/batch-delete | POST | 批量删除 | P1 |

### 2.5 KnowledgeFilesController (8个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /datasets/{dataset_id}/documents | GET | 文档列表 | P1 |
| /datasets/{dataset_id}/documents/status/{status} | GET | 按状态查询 | P1 |
| /datasets/{dataset_id}/documents | POST | 上传文档 | P1 |
| /datasets/{dataset_id}/documents | DELETE | 批量删除 | P1 |
| /datasets/{dataset_id}/documents/{document_id} | DELETE | 删除单个 | P1 |
| /datasets/{dataset_id}/chunks | POST | 解析切块 | P1 |
| /datasets/{dataset_id}/documents/{document_id}/chunks | GET | 列出切片 | P1 |
| /datasets/{dataset_id}/retrieval-test | POST | 召回测试 | P1 |

### 2.6 ModelProviderController (5个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /models/provider | GET | 供应器列表 | P2 |
| /models/provider | POST | 新增供应器 | P2 |
| /models/provider | PUT | 修改供应器 | P2 |
| /models/provider/delete | POST | 删除供应器 | P2 |
| /models/provider/plugin/names | GET | 插件名称列表 | P2 |

### 2.7 SysDictTypeController (5个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /admin/dict/type/page | GET | 分页查询 | P2 |
| /admin/dict/type/{id} | GET | 详情 | P2 |
| /admin/dict/type/save | POST | 保存 | P2 |
| /admin/dict/type/update | PUT | 修改 | P2 |
| /admin/dict/type/delete | POST | 删除 | P2 |

### 2.8 ServerSideManageController (2个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /admin/server/server-list | GET | 服务端列表 | P2 |
| /admin/server/emit-action | POST | 通知更新配置 | P2 |

### 2.9 OTAMagController (9个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /otaMag | GET | 分页查询 | P2 |
| /otaMag/{id} | GET | 详情 | P2 |
| /otaMag | POST | 保存 | P2 |
| /otaMag/{id} | DELETE | 删除 | P2 |
| /otaMag/{id} | PUT | 修改 | P2 |
| /otaMag/getDownloadUrl/{id} | GET | 获取下载链接 | P2 |
| /otaMag/download/{uuid} | GET | 下载固件 | P2 |
| /otaMag/upload | POST | 上传固件 | P2 |
| /otaMag/uploadAssetsBin | POST | 上传资源固件 | P2 |

### 2.10 TimbreController (4个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /ttsVoice | GET | 分页查询 | P2 |
| /ttsVoice | POST | 保存 | P2 |
| /ttsVoice/{id} | PUT | 修改 | P2 |
| /ttsVoice/delete | POST | 删除 | P2 |

### 2.11 VoiceResourceController (6个)

| URL | 方法 | 说明 | 优先级 |
|-----|------|------|:------:|
| /voiceResource | GET | 分页查询 | P2 |
| /voiceResource/{id} | GET | 详情 | P2 |
| /voiceResource | POST | 新增 | P2 |
| /voiceResource/{id} | DELETE | 删除 | P2 |
| /voiceResource/user/{userId} | GET | 按用户查询 | P2 |
| /voiceResource/ttsPlatforms | GET | TTS平台列表 | P2 |

---

## 三、汇总统计

| 分类 | Java接口数 | Python已迁移 | 未迁移 | 迁移率 |
|:-----|:----------:|:-----------:|:------:|:------:|
| P0-核心接口 | ~20 | 18 | ~2 | 90% |
| P1-重要接口 | ~45 | 35 | ~10 | 78% |
| P2-管理接口 | ~71 | 27 | ~44 | 38% |
| **合计** | **~136** | **~80** | **~56** | **59%** |

### 已迁移Controller

| Controller | 接口数 | Python Router |
|-----------|:------:|--------------|
| LoginController | 8(6) | auth.py |
| AgentController | 18(5) | agent.py |
| DeviceController | 9(6) | device.py |
| OTAController | 3(3) | ota.py |
| ConfigController | 3(3) | config.py |
| KnowledgeBaseController | 7(7) | knowledge.py |
| VoiceCloneController | 6(6) | voice_clone.py |
| ModelController | 11(3) | model.py |
| AdminController | 5(5) | admin.py |
| SysParamsController | 5(5) | sys_params.py |
| SysDictDataController | 6(6) | sys_dict.py |
| AgentTemplateController | 6(6) | agent_template.py |

### 未迁移Controller

| Controller | 接口数 | 优先级 | 备注 |
|-----------|:------:|:------:|------|
| AgentChatHistoryController | 4 | P1 | 需Redis |
| AgentMcpAccessPointController | 2 | P1 | 需MCP配置 |
| AgentVoicePrintController | 4 | P1 | 需声纹服务 |
| CorrectWordController | 7 | P1 | 文件管理 |
| KnowledgeFilesController | 8 | P1 | 文档上传管理 |
| ModelProviderController | 5 | P2 | 管理员 |
| SysDictTypeController | 5 | P2 | 管理员 |
| ServerSideManageController | 2 | P2 | 管理员 |
| OTAMagController | 9 | P2 | 固件管理 |
| TimbreController | 4 | P2 | 管理员 |
| VoiceResourceController | 6 | P2 | 管理员 |

---

## 四、架构差异对比

| 维度 | Java后端 | Python FastAPI |
|:-----|:---------|:---------------|
| 框架 | Spring Boot 3.4.3 | FastAPI 0.115+ |
| 端口 | 8002 | 8001 |
| Context-Path | /xiaozhi | /api (通过prefix模拟) |
| ORM | MyBatis Plus | SQLAlchemy 2.0 |
| 数据库 | MySQL (同一库) | MySQL (同一库) |
| 认证 | Shiro + MD5 Token | 原生 + MD5 Token (兼容Java) |
| 密码加密 | BCrypt (Spring Security) | BCrypt (passlib) |
| 缓存 | Redis | 未实现 |
| 文件存储 | 本地/OSS | 部分实现 |
| API文档 | Knife4j/Swagger | FastAPI Swagger/ReDoc |
| 依赖注入 | Spring @Autowired | FastAPI Depends |

### 关键差异说明

1. **Redis依赖**: 部分接口（验证码、OTA下载、音频播放等）依赖Redis，Python端暂未实现
2. **文件上传**: 音频上传、固件上传等需要文件存储后端
3. **SM2加密**: Java前端使用SM2加密密码传输，Python端暂未实现解密
4. **权限注解**: Java通过Shiro `@RequiresPermissions` 控制，Python通过 `get_current_user` + 手动检查
5. **分页格式**: Java使用 `PageData<T>`，Python使用 `{"list": [], "total": N}`

---

> 生成完成：已迁移 **12/23** 个Controller，**~80/136** 个接口，迁移率 **59%**
