# Python后端FastAPI骨架创建计划

> 创建时间: 2026-06-16
> 目标: 创建独立的FastAPI骨架，与现有Java后端并行共存

---

## 一、任务概述

在项目根目录新建 `python-backend/` 目录，搭建可独立运行的FastAPI骨架，用于后续迁移Java后端接口。

### 约束条件
- ❌ 不修改任何Java代码
- ❌ 不修改任何Vue代码
- ❌ 不安装不必要的包
- ✅ 注释使用中文
- ✅ 关键配置处注明"对应原来Java的哪个配置"

---

## 二、当前状态分析

### 现有后端架构

| 后端 | 框架 | 端口 | 数据库 |
|------|------|------|--------|
| Java后端 | Spring Boot 3.4.3 + Shiro | 8002 | MySQL (xiaozhi_esp32_server) |
| Python后端 | aiohttp | HTTP:8003, WS:8000 | - |

### Java后端关键配置参考

**数据库配置** (对应 application-dev.yml):
```yaml
driver-class-name: com.mysql.cj.jdbc.Driver
url: jdbc:mysql://127.0.0.1:3306/xiaozhi_esp32_server
username: root
password: Kjie2007
```

**认证配置** (对应 TokenGenerator.java):
- Token生成: UUID + MD5
- Token有效期: 12小时 (43200分钟)
- 密码加密: BCrypt

---

## 三、创建文件清单

### 目录结构

```
python-backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI入口，CORS，中间件
│   ├── config.py        # 从.env读配置（pydantic-settings）
│   ├── database.py      # SQLAlchemy engine + SessionLocal + get_db
│   └── routers/
│       ├── __init__.py
│       └── health.py    # GET /health 健康检查
├── .env.example         # 配置模板（不含真实密码）
├── requirements.txt     # 依赖清单
└── README.md            # 启动说明
```

---

## 四、文件内容设计

### 4.1 requirements.txt

```txt
# Python 3.10+ 要求
fastapi[standard]>=0.115.0
uvicorn[standard]>=0.30.0
sqlalchemy>=2.0.0
pymysql>=1.1.0           # MySQL驱动（对应Java的mysql-connector-j）
python-dotenv>=1.0.0
pydantic-settings>=2.0.0
```

### 4.2 .env.example

```env
# 数据库配置 - 对应Java application-dev.yml的spring.datasource.druid
DATABASE_URL=mysql+pymysql://root:你的密码@127.0.0.1:3306/xiaozhi_esp32_server

# 认证配置 - 对应Java TokenGenerator.java和SysUserTokenServiceImpl.java
SECRET_KEY=你的密钥至少32位
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=43200  # 12小时，对应Java的EXPIRE=3600*12
```

### 4.3 app/config.py

使用 `pydantic-settings` 的 `BaseSettings` 从 `.env` 读取配置。

关键点：
- `DATABASE_URL`: 对应Java的 `spring.datasource.druid.url`
- `SECRET_KEY`: 用于JWT签名（后续迁移认证时使用）
- `ACCESS_TOKEN_EXPIRE_MINUTES`: 对应Java的12小时有效期

### 4.4 app/database.py

使用 SQLAlchemy 2.0 语法：
- `create_engine` 创建数据库引擎
- `SessionLocal` 创建会话工厂
- `get_db` 依赖注入函数

### 4.5 app/main.py

关键配置：
1. **CORS中间件** - `allow_origins=["*"]` 占位（后续收紧）
2. **路由注册** - 包含 `routers.health`
3. **Swagger文档** - FastAPI自动生成，访问 `/docs`

### 4.6 app/routers/health.py

健康检查接口：
- `GET /health` 返回 `{"ok": true}`

---

## 五、实施步骤

### Step 1: 创建目录结构

```bash
mkdir python-backend
mkdir python-backend/app
mkdir python-backend/app/routers
```

### Step 2: 创建 requirements.txt

写入依赖清单，包含：
- fastapi[standard]
- uvicorn[standard]
- sqlalchemy
- pymysql
- python-dotenv
- pydantic-settings

### Step 3: 创建 .env.example

写入配置模板，注明对应Java配置位置。

### Step 4: 创建 app/__init__.py

空文件，标记为Python包。

### Step 5: 创建 app/config.py

使用 pydantic-settings 读取环境变量。

### Step 6: 创建 app/database.py

配置 SQLAlchemy 连接MySQL。

### Step 7: 创建 app/routers/__init__.py

空文件。

### Step 8: 创建 app/routers/health.py

实现 `GET /health` 接口。

### Step 9: 创建 app/main.py

FastAPI入口，配置CORS和路由。

### Step 10: 创建 README.md

写入启动说明。

---

## 六、验收标准

1. **启动测试**:
   ```bash
   cd python-backend
   uvicorn app.main:app --reload --port 8000
   ```
   服务能正常启动

2. **健康检查**:
   访问 `http://localhost:8000/health` 返回 `{"ok": true}`

3. **Swagger文档**:
   访问 `http://localhost:8000/docs` 能看到API文档

---

## 七、注意事项

1. **端口冲突**: 默认端口8000与现有Python WebSocket服务冲突，实际运行时可改用其他端口（如8001），或README中注明端口可配置

2. **数据库连接**: `.env.example` 不含真实密码，用户需复制为 `.env` 并填写真实配置

3. **CORS配置**: 当前 `allow_origins=["*"]` 仅用于开发，后续需收紧为具体前端地址

4. **Python版本**: 要求Python 3.10+，因使用现代语法（如类型注解）

---

## 八、文件创建顺序

按依赖关系从底层到顶层创建：

1. `requirements.txt` - 依赖定义
2. `.env.example` - 配置模板
3. `app/__init__.py` - 包标记
4. `app/config.py` - 配置读取
5. `app/database.py` - 数据库连接
6. `app/routers/__init__.py` - 路由包标记
7. `app/routers/health.py` - 健康检查接口
8. `app/main.py` - FastAPI入口
9. `README.md` - 使用说明

---

> 计划完成，共需创建9个文件，预计10分钟完成。