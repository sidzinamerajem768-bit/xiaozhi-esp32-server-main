# Auth模块实现计划 - 保持与Java兼容

> 创建时间: 2026-06-16
> 认证方式: MD5 Token + 数据库存储（与Java完全兼容）

---

## 一、任务概述

在 `python-backend/app/` 下实现Auth模块，对齐Java登录接口行为，使用与Java相同的认证方式（MD5 Token + 数据库存储）。

### 关键决策

- **认证方式**: 保持与Java兼容，使用UUID+MD5生成32位token，存储在sys_user_token表
- **密码验证**: 使用passlib的bcrypt，兼容Java的BCryptPasswordEncoder
- **接口路径**: 对齐Java的 `/user/login`（完整路径 `/api/user/login`，因为Java的context-path是/xiaozhi）

---

## 二、Java认证流程分析

### 2.1 登录接口

**Java接口**: `POST /xiaozhi/user/login`

**请求体** (LoginDTO):
```json
{
  "username": "手机号",
  "password": "密码（SM2加密）",
  "captchaId": "验证码UUID",
  "mobileCaptcha": "短信验证码（可选）"
}
```

**返回** (Result<TokenDTO>):
```json
{
  "code": 0,
  "msg": "success",
  "data": {
    "token": "32位MD5字符串",
    "expire": 43200,  // 12小时（秒）
    "clientHash": "客户端指纹"
  }
}
```

**错误**:
- 用户不存在: `ErrorCode.ACCOUNT_PASSWORD_ERROR` → 401
- 密码错误: `ErrorCode.ACCOUNT_PASSWORD_ERROR` → 401

### 2.2 Token生成逻辑

**Java代码**: [TokenGenerator.java](file:///c:/Users/zxjciallo/Desktop/1/xiaozhi-esp32-server-main/manager-api/src/main/java/xiaozhi/modules/security/oauth2/TokenGenerator.java)

```java
// 生成UUID
UUID.randomUUID().toString()
// 计算MD5
MessageDigest.getInstance("MD5").digest(uuid.getBytes())
// 返回32位十六进制字符串
```

### 2.3 Token存储

**表名**: `sys_user_token`

**字段** (推测，需验证):
- id (主键)
- user_id (用户ID)
- token (32位MD5字符串)
- update_date (更新时间)
- expire_date (过期时间)

### 2.4 用户表结构

**表名**: `sys_user`

**字段**:
- id (Long, 主键)
- username (String, 用户名/手机号)
- password (String, BCrypt加密)
- super_admin (Integer, 0/1)
- status (Integer, 0停用/1正常)
- creator (Long)
- create_date (DateTime)
- updater (Long)
- update_date (DateTime)

---

## 三、文件创建清单

### 目录结构

```
python-backend/app/
├── models/
│   ├── __init__.py
│   └── user.py           # User ORM model（映射sys_user表）
│   └── user_token.py     # UserToken ORM model（映射sys_user_token表）
├── schemas/
│   ├── __init__.py
│   └── user.py           # Pydantic请求/响应schema
├── deps.py               # get_current_user依赖
├── routers/
│   ├── auth.py           # 登录路由（新增）
│   └── health.py         # 健康检查（已存在）
└── main.py               # 注册auth router（修改）
```

---

## 四、文件内容设计

### 4.1 app/models/__init__.py

空文件，标记为Python包。

### 4.2 app/models/user.py

**User ORM Model** - 映射sys_user表

```python
class User(Base):
    __tablename__ = "sys_user"
    
    id = Column(BigInteger, primary_key=True)
    username = Column(String(50))  # 用户名/手机号
    password = Column(String(100))  # BCrypt加密
    super_admin = Column(Integer, default=0)
    status = Column(Integer, default=1)
    creator = Column(BigInteger)
    create_date = Column(DateTime)
    updater = Column(BigInteger)
    update_date = Column(DateTime)
```

### 4.3 app/models/user_token.py

**UserToken ORM Model** - 映射sys_user_token表

```python
class UserToken(Base):
    __tablename__ = "sys_user_token"
    
    id = Column(BigInteger, primary_key=True)
    user_id = Column(BigInteger)
    token = Column(String(32))  # 32位MD5
    update_date = Column(DateTime)
    expire_date = Column(DateTime)
```

### 4.4 app/schemas/__init__.py

空文件。

### 4.5 app/schemas/user.py

**Pydantic Schema**

```python
# 登录请求
class LoginRequest(BaseModel):
    username: str
    password: str
    captchaId: Optional[str] = None  # 暂不实现验证码
    mobileCaptcha: Optional[str] = None

# Token响应
class TokenResponse(BaseModel):
    token: str
    expire: int  # 秒
    clientHash: Optional[str] = None

# 用户信息响应
class UserInfoResponse(BaseModel):
    id: int
    username: str
    superAdmin: int
    status: int
```

### 4.6 app/deps.py

**get_current_user依赖**

```python
def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    # 从Authorization头提取token
    # 查询sys_user_token表验证
    # 返回User对象
```

### 4.7 app/routers/auth.py

**登录路由**

```python
@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    # 1. 查询用户
    # 2. 验证密码（bcrypt）
    # 3. 生成token（UUID + MD5）
    # 4. 存储token到sys_user_token
    # 5. 返回TokenResponse

@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    # 返回当前用户信息
```

### 4.8 app/main.py（修改）

注册auth router：
```python
from app.routers import health, auth
app.include_router(auth.router, prefix="/api/user")
```

---

## 五、依赖更新

### requirements.txt（新增）

```txt
# 密码加密 - 对应Java的BCryptPasswordEncoder
passlib[bcrypt]>=1.7.4

# Token生成 - UUID + hashlib（Python内置，无需额外安装）
```

---

## 六、实施步骤

### Step 1: 更新requirements.txt

添加 `passlib[bcrypt]` 依赖。

### Step 2: 创建models目录和文件

- `app/models/__init__.py`
- `app/models/user.py` - User ORM
- `app/models/user_token.py` - UserToken ORM

### Step 3: 创建schemas目录和文件

- `app/schemas/__init__.py`
- `app/schemas/user.py` - Pydantic schema

### Step 4: 创建deps.py

实现 `get_current_user` 依赖函数。

### Step 5: 创建auth.py路由

实现 `/login` 和 `/me` 接口。

### Step 6: 修改main.py

注册auth router。

---

## 七、验收标准

### 7.1 登录测试

```bash
# 正确密码
curl -X POST http://localhost:8001/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username": "手机号", "password": "密码"}'
# 期望: 200 + {"token": "...", "expire": 43200}

# 错误密码
curl -X POST http://localhost:8001/api/user/login \
  -H "Content-Type: application/json" \
  -d '{"username": "手机号", "password": "错误密码"}'
# 期望: 401 + {"message": "用户名或密码错误"}
```

### 7.2 Token验证测试

```bash
# 使用token访问受保护接口
curl -X GET http://localhost:8001/api/user/me \
  -H "Authorization: Bearer {token}"
# 期望: 200 + {"id": ..., "username": ...}

# 无token访问
curl -X GET http://localhost:8001/api/user/me
# 期望: 401
```

### 7.3 与Java兼容性测试

1. Python生成的token，Java后端能否验证？
2. Java生成的token，Python后端能否验证？

---

## 八、注意事项

### 8.1 密码处理

Java前端使用SM2加密密码传输，Python后端暂不实现SM2解密，直接接收明文密码（开发环境）。

**后续需添加**: SM2解密逻辑，对齐Java的 `Sm2DecryptUtil.decryptAndValidateCaptcha`。

### 8.2 验证码

Java登录需要图形验证码（captchaId），Python后端暂不实现验证码验证。

**后续需添加**: 验证码生成和验证逻辑。

### 8.3 Token表结构

需先查询数据库确认 `sys_user_token` 表的实际字段名。

---

## 九、数据库表结构验证

在实施前，需要查询数据库确认：

1. `sys_user_token` 表是否存在
2. 表字段名是否与推测一致

**查询SQL**:
```sql
DESCRIBE sys_user_token;
SELECT * FROM sys_user_token LIMIT 1;
```

---

> 计划完成，共需创建7个新文件，修改2个现有文件。