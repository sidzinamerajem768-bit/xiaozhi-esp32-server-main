# 全量接口迁移计划

> 创建时间: 2026-06-16
> 目标: 将Java后端所有接口迁移到Python FastAPI

---

## 一、任务概述

将Java后端约80个接口迁移到Python FastAPI，按优先级分阶段执行。

### 约束条件
- ❌ 不修改任何Vue代码
- ❌ 不修改任何Java代码（先共存）
- ✅ URL路径保持一致
- ✅ HTTP方法保持一致
- ✅ 入参/返回字段名一致（大小写也一致）
- ✅ 每迁完一个接口写注释标注来源

---

## 二、迁移阶段划分

### 阶段1: P0核心接口（必须迁移）

| 模块 | 接口数量 | 说明 |
|------|---------|------|
| 登录认证 | 4 | login, register, info, pub-config |
| 设备管理 | 3 | bind, register, unbind |
| 智能体管理 | 5 | list, get, create, update, delete |
| OTA | 2 | 版本检查, 激活检查 |
| 配置 | 2 | server-base, agent-models |

**总计**: 16个接口

### 阶段2: P1重要接口（优先迁移）

| 模块 | 接口数量 | 说明 |
|------|---------|------|
| 登录认证 | 2 | change-password, retrieve-password |
| 智能体管理 | 7 | template, sessions, chat-history等 |
| 设备管理 | 4 | update, manual-add, tools等 |
| 模型配置 | 2 | names, voices |
| 知识库 | 7 | 全部CRUD |
| 音色克隆 | 6 | 全部接口 |

**总计**: 30个接口

### 阶段3: P2管理接口（可延后）

| 模块 | 接口数量 | 说明 |
|------|---------|------|
| 管理员 | 5 | 用户管理 |
| 参数管理 | 5 | 参数CRUD |
| 字典管理 | 6 | 字典CRUD |
| 模型配置 | 8 | 管理员接口 |
| 智能体模板 | 6 | 管理员接口 |

**总计**: 34个接口

---

## 三、阶段1详细计划（本次执行）

### 3.1 登录认证模块

**已完成**: `/user/login`, `/user/info`

**待迁移**:
- `/user/register` - 用户注册
- `/user/pub-config` - 公共配置

### 3.2 设备管理模块

**Controller**: [DeviceController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/device/controller/DeviceController.java)

**待迁移**:
- `POST /device/bind/{agentId}/{deviceCode}` - 绑定设备
- `POST /device/register` - 注册设备
- `GET /device/bind/{agentId}` - 获取已绑定设备
- `POST /device/unbind` - 解绑设备

### 3.3 智能体管理模块

**Controller**: [AgentController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/agent/controller/AgentController.java)

**待迁移**:
- `GET /agent/list` - 获取用户智能体列表
- `GET /agent/{id}` - 获取智能体详情
- `POST /agent` - 创建智能体
- `PUT /agent/{id}` - 更新智能体
- `DELETE /agent/{id}` - 删除智能体

### 3.4 OTA模块

**Controller**: [OTAController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/device/controller/OTAController.java)

**待迁移**:
- `POST /ota/` - OTA版本检查
- `POST /ota/activate` - 设备激活检查

### 3.5 配置模块

**Controller**: [ConfigController.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/config/controller/ConfigController.java)

**待迁移**:
- `POST /config/server-base` - 获取服务端配置
- `POST /config/agent-models` - 获取智能体模型

---

## 四、文件创建计划

### 4.1 新增ORM模型

| 文件 | 说明 |
|------|------|
| `app/models/agent.py` | Agent ORM（映射agent表） |
| `app/models/device.py` | Device ORM（映射device表） |
| `app/models/agent_device.py` | AgentDevice ORM（映射agent_device绑定表） |

### 4.2 新增Schema

| 文件 | 说明 |
|------|------|
| `app/schemas/agent.py` | Agent请求/响应schema |
| `app/schemas/device.py` | Device请求/响应schema |

### 4.3 新增路由

| 文件 | 说明 |
|------|------|
| `app/routers/agent.py` | 智能体管理路由 |
| `app/routers/device.py` | 设备管理路由 |
| `app/routers/ota.py` | OTA路由 |
| `app/routers/config.py` | 配置路由 |

---

## 五、实施步骤

### Step 1: 读取Java Controller源码

读取以下Controller文件，了解接口实现逻辑：
- AgentController.java
- DeviceController.java
- OTAController.java
- ConfigController.java

### Step 2: 创建ORM模型

根据Java Entity类创建对应的SQLAlchemy ORM模型。

### Step 3: 创建Pydantic Schema

根据Java DTO类创建对应的Pydantic Schema。

### Step 4: 创建路由文件

实现每个接口，标注来源注释。

### Step 5: 注册路由

在main.py中注册新路由。

### Step 6: 测试验证

使用curl/Python测试每个接口。

---

## 六、验收标准

每个接口迁移完成后需验证：
1. URL路径一致
2. HTTP方法一致
3. 入参字段名一致（大小写一致）
4. 返回字段名一致（大小写一致）
5. 注释标注来源

---

## 七、注意事项

### 7.1 字段命名规范

Java使用驼峰命名（如`superAdmin`），Python需保持一致：
- JSON返回字段：`superAdmin`（不是`super_admin`）
- ORM字段：`super_admin`（数据库字段名）

### 7.2 统一响应格式

Java返回格式：
```json
{
  "code": 0,
  "msg": "success",
  "data": {...}
}
```

Python需保持一致。

### 7.3 权限控制

- 普通用户接口：使用`get_current_user`依赖
- 管理员接口：检查`superAdmin == 1`
- 无需认证接口：不使用依赖

---

> 阶段1计划完成，共需迁移16个核心接口。