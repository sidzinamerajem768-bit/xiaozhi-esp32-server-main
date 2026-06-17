# 项目迁移审计报告

> 生成时间: 2026-06-16
> 项目: xiaozhi-esp32-server (小智ESP32语音助手服务端)

---

## 一、Java后端架构分析

### 1.1 框架与版本

| 项目 | 版本/配置 |
|------|----------|
| Spring Boot | 3.4.3 |
| Java | 21 |
| Shiro | 2.0.2 (jakarta) |
| MyBatis Plus | 3.5.5 |
| Druid | 1.2.20 |
| Knife4j/Swagger | 4.6.0 |

### 1.2 服务配置

| 配置项 | 值 |
|--------|-----|
| 服务端口 | `8002` |
| Context-Path | `/xiaozhi` |
| 完整访问地址 | `http://localhost:8002/xiaozhi` |

**配置文件位置**: 
- [application.yml](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/resources/application.yml)
- [application-dev.yml](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/resources/application-dev.yml)

### 1.3 数据库配置

| 项目 | 值 |
|------|-----|
| 数据库类型 | MySQL |
| 数据库名 | `xiaozhi_esp32_server` |
| 连接地址 | `jdbc:mysql://127.0.0.1:3306/xiaozhi_esp32_server` |
| 用户名 | `root` |
| Redis | `127.0.0.1:6379` (database: 0) |

### 1.4 认证方式分析

**认证方式**: **无状态Token认证**（非JWT）

#### 认证流程详解

1. **Token生成**: 
   - 使用 `TokenGenerator.generateValue()` 生成32位MD5哈希token
   - Token存储在数据库表 `sys_user_token` 中
   - Token有效期: 12小时 (`EXPIRE = 3600 * 12`)
   
2. **Token验证**:
   - `Oauth2Filter` 从请求头 `Authorization: Bearer xxx` 提取token
   - `Oauth2Realm` 验证token是否有效（查询数据库 + 检查过期时间）
   
3. **关键代码位置**:
   - [Oauth2Filter.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/Oauth2Filter.java) - Token提取与401拦截
   - [Oauth2Realm.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/Oauth2Realm.java) - Token验证与用户信息获取
   - [SysUserTokenServiceImpl.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/service/impl/SysUserTokenServiceImpl.java) - Token生成与管理
   - [TokenGenerator.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/TokenGenerator.java) - Token生成算法(MD5)

#### 密码加密方式

**加密算法**: **BCrypt**

- 代码位置: [PasswordUtils.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/password/PasswordUtils.java)
- 使用 `BCryptPasswordEncoder` 进行加密和验证

#### Shiro权限配置

| 权限标识 | 说明 |
|---------|------|
| `sys:role:superAdmin` | 超级管理员权限 |
| `sys:role:normal` | 普通用户权限 |

**无需认证的接口** (ShiroConfig配置):
```
/ota/**                    - OTA相关（anon）
/user/captcha              - 验证码（anon）
/user/login                - 登录（anon）
/user/register             - 注册（anon）
/user/pub-config           - 公共配置（anon）
/user/retrieve-password    - 找回密码（anon）
/config/**                 - 服务端配置（server密钥认证）
/agent/chat-history/report - 聊天记录上报（server密钥认证）
```

### 1.5 用户表结构

**表名**: `sys_user`

**实体类**: [SysUserEntity.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/sys/entity/SysUserEntity.java)

| 字段名 | 类型 | 说明 |
|--------|------|------|
| id | Long | 主键ID |
| username | String | 用户名（手机号） |
| password | String | 密码（BCrypt加密） |
| superAdmin | Integer | 超级管理员标识（0/1） |
| status | Integer | 状态（0停用/1正常） |
| creator | Long | 创建者 |
| createDate | Date | 创建时间 |
| updater | Long | 更新者 |
| updateDate | Date | 更新时间 |

---

## 二、Java后端接口清单

### 2.1 登录认证模块 (LoginController)

**Controller**: [LoginController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/controller/LoginController.java)
**Base Path**: `/user`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/user/captcha` | GET | 获取图形验证码 | ❌ | uuid | 图片流 | P0-核心 |
| `/user/smsVerification` | POST | 发送短信验证码 | ❌ | SmsVerificationDTO | Result<Void> | P1 |
| `/user/login` | POST | 用户登录 | ❌ | LoginDTO | Result<TokenDTO> | P0-核心 |
| `/user/register` | POST | 用户注册 | ❌ | LoginDTO | Result<Void> | P0-核心 |
| `/user/info` | GET | 获取用户信息 | ✅ | - | Result<UserDetail> | P0-核心 |
| `/user/change-password` | PUT | 修改密码 | ✅ | PasswordDTO | Result<?> | P1 |
| `/user/retrieve-password` | PUT | 找回密码 | ❌ | RetrievePasswordDTO | Result<?> | P1 |
| `/user/pub-config` | GET | 获取公共配置 | ❌ | - | Result<Map> | P0-核心 |

**TokenDTO结构**:
```json
{
  "token": "32位MD5字符串",
  "expire": 43200,  // 12小时（秒）
  "clientHash": "客户端标识"
}
```

### 2.2 智能体管理模块 (AgentController)

**Controller**: [AgentController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/agent/controller/AgentController.java)
**Base Path**: `/agent`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/agent/list` | GET | 获取用户智能体列表 | ✅ | keyword, searchType | Result<List<AgentDTO>> | P0-核心 |
| `/agent/all` | GET | 智能体列表(管理员) | ✅(superAdmin) | page, limit | Result<PageData> | P2 |
| `/agent/{id}` | GET | 获取智能体详情 | ✅ | id | Result<AgentInfoVO> | P0-核心 |
| `/agent` | POST | 创建智能体 | ✅ | AgentCreateDTO | Result<String> | P0-核心 |
| `/agent/{id}` | PUT | 更新智能体 | ✅ | id, AgentUpdateDTO | Result<Void> | P0-核心 |
| `/agent/{id}` | DELETE | 删除智能体 | ✅ | id | Result<Void> | P0-核心 |
| `/agent/template` | GET | 智能体模板列表 | ✅ | - | Result<List> | P1 |
| `/agent/{id}/sessions` | GET | 获取会话列表 | ✅ | id, page, limit | Result<PageData> | P1 |
| `/agent/{id}/chat-history/{sessionId}` | GET | 获取聊天记录 | ✅ | id, sessionId | Result<List> | P1 |
| `/agent/{id}/chat-history/user` | GET | 获取最近50条记录 | ✅ | id | Result<List> | P1 |
| `/agent/{id}/chat-history/audio` | GET | 获取音频内容 | ✅ | id | Result<String> | P1 |
| `/agent/audio/{audioId}` | POST | 获取音频下载ID | ✅ | audioId | Result<String> | P1 |
| `/agent/play/{uuid}` | GET | 播放音频 | ❌ | uuid | ResponseEntity<byte[]> | P1 |
| `/agent/tag` | POST | 创建标签 | ✅ | tagName | Result<AgentTagEntity> | P2 |
| `/agent/tag/list` | GET | 获取标签列表 | ✅ | - | Result<List> | P2 |
| `/agent/tag/{id}` | DELETE | 删除标签 | ✅ | id | Result<Void> | P2 |
| `/agent/{id}/tags` | GET | 获取智能体标签 | ✅ | id | Result<List> | P2 |
| `/agent/{id}/tags` | PUT | 保存智能体标签 | ✅ | id, tagIds | Result<Void> | P2 |
| `/agent/saveMemory/{macAddress}` | PUT | 根据设备更新智能体 | ❌(server) | macAddress, AgentMemoryDTO | Result<Void> | P1 |
| `/agent/chat-summary/{sessionId}/save` | POST | 生成聊天总结 | ❌(server) | sessionId | Result<Void> | P1 |
| `/agent/chat-title/{sessionId}/generate` | POST | 生成聊天标题 | ❌(server) | sessionId | Result<Void> | P1 |

### 2.3 设备管理模块 (DeviceController)

**Controller**: [DeviceController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/device/controller/DeviceController.java)
**Base Path**: `/device`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/device/bind/{agentId}/{deviceCode}` | POST | 绑定设备 | ✅ | agentId, deviceCode | Result<Void> | P0-核心 |
| `/device/register` | POST | 注册设备 | ❌ | DeviceRegisterDTO | Result<String> | P0-核心 |
| `/device/bind/{agentId}` | GET | 获取已绑定设备 | ✅ | agentId | Result<List> | P0-核心 |
| `/device/bind/{agentId}` | POST | 设备在线接口 | ✅ | agentId | Result<String> | P1 |
| `/device/unbind` | POST | 解绑设备 | ✅ | DeviceUnBindDTO | Result<Void> | P0-核心 |
| `/device/update/{id}` | PUT | 更新设备信息 | ✅ | id, DeviceUpdateDTO | Result<Void> | P1 |
| `/device/manual-add` | POST | 手动添加设备 | ✅ | DeviceManualAddDTO | Result<Void> | P1 |
| `/device/tools/list/{deviceId}` | POST | 获取设备工具列表 | ✅ | deviceId | Result<Object> | P1 |
| `/device/tools/call/{deviceId}` | POST | 调用设备工具 | ✅ | deviceId, DeviceToolsCallReqDTO | Result<Object> | P1 |

### 2.4 OTA模块 (OTAController)

**Controller**: [OTAController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/device/controller/OTAController.java)
**Base Path**: `/ota/`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/ota/` | POST | OTA版本检查 | ❌ | DeviceReportReqDTO, Device-Id header | ResponseEntity<String> | P0-核心 |
| `/ota/activate` | POST | 设备激活状态检查 | ❌ | Device-Id header | ResponseEntity<String> | P0-核心 |
| `/ota/` | GET | OTA接口健康检查 | ❌ | - | ResponseEntity<String> | P1 |

### 2.5 模型配置模块 (ModelController)

**Controller**: [ModelController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/model/controller/ModelController.java)
**Base Path**: `/models`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/models/names` | GET | 获取模型名称列表 | ✅ | modelType, modelName | Result<List> | P1 |
| `/models/llm/names` | GET | 获取LLM模型信息 | ✅ | modelName | Result<List> | P1 |
| `/models/{modelType}/provideTypes` | GET | 获取供应器列表 | ✅(superAdmin) | modelType | Result<List> | P2 |
| `/models/list` | GET | 获取模型配置列表 | ✅(superAdmin) | modelType, page, limit | Result<PageData> | P2 |
| `/models/{modelType}/{provideCode}` | POST | 新增模型配置 | ✅(superAdmin) | modelType, provideCode, ModelConfigBodyDTO | Result<ModelConfigDTO> | P2 |
| `/models/{modelType}/{provideCode}/{id}` | PUT | 编辑模型配置 | ✅(superAdmin) | modelType, provideCode, id | Result<ModelConfigDTO> | P2 |
| `/models/{id}` | DELETE | 删除模型配置 | ✅(superAdmin) | id | Result<Void> | P2 |
| `/models/{id}` | GET | 获取模型配置详情 | ✅(superAdmin) | id | Result<ModelConfigDTO> | P2 |
| `/models/enable/{id}/{status}` | PUT | 启用/关闭模型 | ✅(superAdmin) | id, status | Result<Void> | P2 |
| `/models/default/{id}` | PUT | 设置默认模型 | ✅(superAdmin) | id | Result<Void> | P2 |
| `/models/{modelId}/voices` | GET | 获取模型音色 | ✅ | modelId, voiceName | Result<List> | P1 |

### 2.6 知识库管理模块 (KnowledgeBaseController)

**Controller**: [KnowledgeBaseController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/knowledge/controller/KnowledgeBaseController.java)
**Base Path**: `/datasets`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/datasets` | GET | 分页查询知识库 | ✅ | name, page, page_size | Result<PageData> | P1 |
| `/datasets/{dataset_id}` | GET | 获取知识库详情 | ✅ | dataset_id | Result<KnowledgeBaseDTO> | P1 |
| `/datasets` | POST | 创建知识库 | ✅ | KnowledgeBaseDTO | Result<KnowledgeBaseDTO> | P1 |
| `/datasets/{dataset_id}` | PUT | 更新知识库 | ✅ | dataset_id, KnowledgeBaseDTO | Result<KnowledgeBaseDTO> | P1 |
| `/datasets/{dataset_id}` | DELETE | 删除知识库 | ✅ | dataset_id | Result<Void> | P1 |
| `/datasets/batch` | DELETE | 批量删除知识库 | ✅ | ids | Result<Void> | P1 |
| `/datasets/rag-models` | GET | 获取RAG模型列表 | ✅ | - | Result<List> | P1 |

### 2.7 音色克隆模块 (VoiceCloneController)

**Controller**: [VoiceCloneController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/voiceclone/controller/VoiceCloneController.java)
**Base Path**: `/voiceClone`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/voiceClone` | GET | 分页查询音色资源 | ✅ | page, limit | Result<PageData> | P1 |
| `/voiceClone/upload` | POST | 上传音频克隆 | ✅ | id, voiceFile | Result<String> | P1 |
| `/voiceClone/updateName` | POST | 更新克隆名称 | ✅ | id, name | Result<String> | P1 |
| `/voiceClone/audio/{id}` | POST | 获取音频下载ID | ✅ | id | Result<String> | P1 |
| `/voiceClone/play/{uuid}` | GET | 播放音频 | ❌ | uuid | audio/wav | P1 |
| `/voiceClone/cloneAudio` | POST | 复刻音频 | ✅ | cloneId | Result<String> | P1 |

### 2.8 配置管理模块 (ConfigController)

**Controller**: [ConfigController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/config/controller/ConfigController.java)
**Base Path**: `/config`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/config/server-base` | POST | 获取服务端配置 | ❌(server密钥) | - | Result<Object> | P0-核心 |
| `/config/agent-models` | POST | 获取智能体模型 | ❌(server密钥) | AgentModelsDTO | Result<Object> | P0-核心 |
| `/config/correct-words` | POST | 获取替换词 | ❌(server密钥) | CorrectWordsDTO | Result<Object> | P1 |

### 2.9 管理员模块 (AdminController)

**Controller**: [AdminController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/sys/controller/AdminController.java)
**Base Path**: `/admin`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/admin/users` | GET | 分页查找用户 | ✅(superAdmin) | mobile, page, limit | Result<PageData> | P2 |
| `/admin/users/{id}` | PUT | 重置密码 | ✅(superAdmin) | id | Result<String> | P2 |
| `/admin/users/{id}` | DELETE | 删除用户 | ✅(superAdmin) | id | Result<Void> | P2 |
| `/admin/users/changeStatus/{status}` | PUT | 批量修改用户状态 | ✅(superAdmin) | status, userIds | Result<Void> | P2 |
| `/admin/device/all` | GET | 分页查找设备 | ✅(superAdmin) | keywords, page, limit | Result<PageData> | P2 |

### 2.10 参数管理模块 (SysParamsController)

**Controller**: [SysParamsController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/sys/controller/SysParamsController.java)
**Base Path**: `/admin/params`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/admin/params/page` | GET | 分页查询参数 | ✅(superAdmin) | page, limit, paramCode | Result<PageData> | P2 |
| `/admin/params/{id}` | GET | 获取参数详情 | ✅(superAdmin) | id | Result<SysParamsDTO> | P2 |
| `/admin/params` | POST | 保存参数 | ✅(superAdmin) | SysParamsDTO | Result<Void> | P2 |
| `/admin/params` | PUT | 修改参数 | ✅(superAdmin) | SysParamsDTO | Result<Void> | P2 |
| `/admin/params/delete` | POST | 删除参数 | ✅(superAdmin) | ids[] | Result<Void> | P2 |

### 2.11 字典管理模块 (SysDictDataController)

**Controller**: [SysDictDataController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/sys/controller/SysDictDataController.java)
**Base Path**: `/admin/dict/data`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/admin/dict/data/page` | GET | 分页查询字典数据 | ✅(superAdmin) | dictTypeId, page, limit | Result<PageData> | P2 |
| `/admin/dict/data/{id}` | GET | 获取字典数据详情 | ✅(superAdmin) | id | Result<SysDictDataVO> | P2 |
| `/admin/dict/data/save` | POST | 新增字典数据 | ✅(superAdmin) | SysDictDataDTO | Result<Void> | P2 |
| `/admin/dict/data/update` | PUT | 修改字典数据 | ✅(superAdmin) | SysDictDataDTO | Result<Void> | P2 |
| `/admin/dict/data/delete` | POST | 删除字典数据 | ✅(superAdmin) | ids[] | Result<Void> | P2 |
| `/admin/dict/data/type/{dictType}` | GET | 获取字典数据列表 | ✅ | dictType | Result<List> | P1 |

### 2.12 智能体模板模块 (AgentTemplateController)

**Controller**: [AgentTemplateController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/agent/controller/AgentTemplateController.java)
**Base Path**: `/agent/template`

| URL | HTTP方法 | 功能 | 需鉴权 | 入参 | 出参 | 迁移优先级 |
|-----|---------|------|--------|------|------|-----------|
| `/agent/template/page` | GET | 获取模板分页列表 | ✅(superAdmin) | page, limit, agentName | Result<PageData> | P2 |
| `/agent/template/{id}` | GET | 获取模板详情 | ✅(superAdmin) | id | Result<AgentTemplateVO> | P2 |
| `/agent/template` | POST | 创建模板 | ✅(superAdmin) | AgentTemplateEntity | Result<AgentTemplateEntity> | P2 |
| `/agent/template` | PUT | 更新模板 | ✅(superAdmin) | AgentTemplateEntity | Result<AgentTemplateEntity> | P2 |
| `/agent/template/{id}` | DELETE | 删除模板 | ✅(superAdmin) | id | Result<String> | P2 |
| `/agent/template/batch-remove` | POST | 批量删除模板 | ✅(superAdmin) | ids[] | Result<String> | P2 |

---

## 三、Python后端架构分析

### 3.1 框架与入口

| 项目 | 配置 |
|------|------|
| 框架 | aiohttp (异步HTTP/WebSocket) |
| 入口文件 | [xiaozhi-server/app.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/app.py) |
| HTTP端口 | `8003` |
| WebSocket端口 | `8000` |

### 3.2 HTTP接口

**HTTP服务器**: [xiaozhi-server/core/http_server.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/core/http_server.py)

| URL | HTTP方法 | 功能 | 需鉴权 | 迁移优先级 |
|-----|---------|------|--------|-----------|
| `/xiaozhi/ota/` | GET/POST | OTA配置下发 | JWT认证 | P0-核心 |
| `/xiaozhi/ota/download/{filename}` | GET | OTA文件下载 | - | P0-核心 |
| `/mcp/vision/explain` | GET/POST | 视觉分析接口 | JWT认证 | P1 |

### 3.3 WebSocket服务

**WebSocket服务器**: [xiaozhi-server/core/websocket_server.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/core/websocket_server.py)

| 地址 | 功能 | 迁移优先级 |
|------|------|-----------|
| `ws://{ip}:8000/xiaozhi/v1/` | ESP32设备语音交互WebSocket | P0-核心 |

---

## 四、前端Vue架构分析

### 4.1 API配置

**配置文件**: [manager-web/.env.production](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/.env.production)

| 配置项 | 值 |
|--------|-----|
| baseURL | `/xiaozhi` (相对路径，同源部署) |
| publicPath | `/` |

### 4.2 HTTP客户端

**主要HTTP客户端**: 
- [httpClient.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/apis/httpClient.js) - Promise风格（推荐）
- [httpRequest.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/apis/httpRequest.js) - 回调风格

**请求拦截器配置**:
```javascript
// Token添加
config.headers['Authorization'] = 'Bearer ' + JSON.parse(token).token
```

**响应拦截器配置**:
```javascript
// 401处理
if (data.code === 401) {
  store.commit('clearAuth')
  goToPage(Constant.PAGE.LOGIN, true)
  return Promise.reject(new Error('Unauthorized'))
}
```

### 4.3 Token存储

**存储位置**: `localStorage`

**Vuex Store**: [manager-web/src/store/index.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/store/index.js)

```javascript
// 存储Token
localStorage.setItem('token', token)

// 存储用户信息
localStorage.setItem('userInfo', JSON.stringify(userInfo))

// 清除认证信息
localStorage.removeItem('token')
localStorage.removeItem('userInfo')
```

### 4.4 路由守卫

**路由配置**: [manager-web/src/router/index.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/router/index.js)

```javascript
router.beforeEach((to, from, next) => {
  if (to.meta && to.meta.requiresAuth) {
    const token = localStorage.getItem('token')
    if (!token) {
      return next({ name: 'login', query: { redirect: to.fullPath } })
    }
    // 普通用户重定向到用户端
    const userInfo = JSON.parse(localStorage.getItem('userInfo') || '{}')
    if (!userInfo.superAdmin) {
      window.location.href = '/user-portal/'
      return
    }
  }
  next()
})
```

---

## 五、迁移策略建议

### 5.1 认证方式结论

**认证方式**: **无状态Token认证**（非JWT，非Session+Cookie）

#### 特点分析

| 特性 | 当前实现 |
|------|---------|
| Token格式 | 32位MD5哈希字符串 |
| Token存储 | 数据库表 `sys_user_token` |
| Token有效期 | 12小时 |
| Token验证 | 每次请求查询数据库 |
| 密码加密 | BCrypt |
| 请求头格式 | `Authorization: Bearer xxx` |

#### 与JWT的区别

| 项目 | 当前实现 | JWT |
|------|---------|-----|
| Token生成 | UUID + MD5 | Header.Payload.Signature |
| Token验证 | 查询数据库 | 解析签名验证 |
| Token存储 | 需要数据库存储 | 无需存储（自包含） |
| 用户信息 | 查询数据库获取 | Token中包含 |

### 5.2 迁移优先级分类

#### P0-核心接口（必须迁移）

| 模块 | 接口 |
|------|------|
| 登录认证 | `/user/login`, `/user/register`, `/user/info`, `/user/pub-config` |
| 设备管理 | `/device/bind`, `/device/register`, `/device/unbind` |
| 智能体管理 | `/agent/list`, `/agent/{id}`, `/agent` (POST), `/agent/{id}` (PUT/DELETE) |
| OTA | `/ota/` (POST), `/ota/activate` |
| 配置 | `/config/server-base`, `/config/agent-models` |
| WebSocket | `ws://*:8000/xiaozhi/v1/` |

#### P1-重要接口（优先迁移）

| 模块 | 接口 |
|------|------|
| 登录认证 | `/user/change-password`, `/user/retrieve-password` |
| 智能体管理 | `/agent/template`, `/agent/{id}/sessions`, `/agent/{id}/chat-history/*` |
| 设备管理 | `/device/update/{id}`, `/device/manual-add` |
| 模型配置 | `/models/names`, `/models/{modelId}/voices` |
| 知识库 | `/datasets` (全部) |
| 音色克隆 | `/voiceClone` (全部) |
| Python HTTP | `/mcp/vision/explain` |

#### P2-管理接口（可延后）

| 模块 | 接口 |
|------|------|
| 管理员 | `/admin/*` (全部) |
| 参数管理 | `/admin/params/*` (全部) |
| 字典管理 | `/admin/dict/*` (全部) |
| 模型配置 | `/models/list`, `/models/{modelType}/provideTypes` (管理员接口) |
| 智能体模板 | `/agent/template/*` (管理员接口) |

### 5.3 迁移注意事项

1. **认证系统迁移**:
   - 当前Token存储在数据库，迁移时需要考虑Token兼容性
   - 如果迁移到JWT，需要前端同步修改Token解析逻辑
   - BCrypt密码加密可以直接复用

2. **前端适配**:
   - baseURL配置为相对路径 `/xiaozhi`，迁移时需确保API路径一致
   - Token存储在localStorage，迁移后需确保Token格式兼容
   - 401拦截逻辑已在httpClient中实现，迁移时需保持一致

3. **数据库迁移**:
   - 用户表 `sys_user` 结构简单，可直接迁移
   - Token表 `sys_user_token` 如果改用JWT可以废弃

4. **WebSocket服务**:
   - Python WebSocket服务是核心功能，必须保留
   - 端口8000，路径 `/xiaozhi/v1/`

---

## 六、附录：关键代码位置索引

### Java后端

| 功能 | 文件路径 |
|------|---------|
| 应用入口 | [AdminApplication.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/AdminApplication.java) |
| Shiro配置 | [ShiroConfig.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/config/ShiroConfig.java) |
| Token验证 | [Oauth2Filter.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/Oauth2Filter.java) |
| Token生成 | [TokenGenerator.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/TokenGenerator.java) |
| 密码加密 | [PasswordUtils.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/password/PasswordUtils.java) |
| 用户实体 | [SysUserEntity.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/sys/entity/SysUserEntity.java) |

### Python后端

| 功能 | 文件路径 |
|------|---------|
| 应用入口 | [xiaozhi-server/app.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/app.py) |
| HTTP服务器 | [xiaozhi-server/core/http_server.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/core/http_server.py) |
| WebSocket服务器 | [xiaozhi-server/core/websocket_server.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/core/websocket_server.py) |
| 配置加载 | [xiaozhi-server/config/settings.py](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/xiaozhi-server/config/settings.py) |

### 前端Vue

| 功能 | 文件路径 |
|------|---------|
| 应用入口 | [manager-web/src/main.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/main.js) |
| HTTP客户端 | [manager-web/src/apis/httpClient.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/apis/httpClient.js) |
| 路由配置 | [manager-web/src/router/index.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/router/index.js) |
| Vuex Store | [manager-web/src/store/index.js](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/src/store/index.js) |
| 环境配置 | [manager-web/.env.production](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-web/.env.production) |

---

## 七、总结

### 认证方式结论

**当前系统使用的是无状态Token认证（非JWT，非Session+Cookie）**

- Token由UUID+MD5生成，存储在数据库中
- 每次请求通过查询数据库验证Token有效性
- Token有效期12小时，存储在 `sys_user_token` 表
- 密码使用BCrypt加密
- 前端通过 `Authorization: Bearer xxx` 请求头传递Token

### 迁移策略建议

1. **如果保持现有认证方式**:
   - 直接复用Token生成和验证逻辑
   - 保持数据库Token表结构
   - 前端无需修改

2. **如果迁移到JWT**:
   - 需要修改Token生成逻辑
   - 需要修改前端Token解析逻辑
   - 可以废弃数据库Token表
   - 需要处理Token刷新机制

3. **如果迁移到Session+Cookie**:
   - 需要修改为有状态认证
   - 需要考虑分布式Session存储
   - 前端需要修改Token传递方式
   - 不推荐（当前架构更适合无状态）

---

> 文档生成完成，共扫描23个Controller文件，整理出约80个API接口。