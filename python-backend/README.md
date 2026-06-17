# 小智ESP32服务端 - Python版 (FastAPI骨架)

> 用于迁移Java后端接口的FastAPI骨架，与现有Java后端并行共存

---

## 一、目录结构

```
python-backend/
├── app/
│   ├── __init__.py      # 包初始化
│   ├── main.py          # FastAPI入口，CORS，中间件
│   ├── config.py        # 配置管理（pydantic-settings）
│   ├── database.py      # SQLAlchemy数据库连接
│   └── routers/
│       ├── __init__.py  # 路由包初始化
│       └── health.py    # 健康检查接口 GET /health
├── .env.example         # 配置模板（不含真实密码）
├── requirements.txt     # Python依赖
└── README.md            # 本文件
```

---

## 二、环境准备

### 2.1 Python版本

要求：**Python 3.10+**

### 2.2 安装依赖

```bash
cd python-backend
pip install -r requirements.txt
```

### 2.3 配置环境变量

1. 复制配置模板：
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写真实配置：
```env
# 数据库配置 - 对应Java application-dev.yml
DATABASE_URL=mysql+pymysql://root:你的真实密码@127.0.0.1:3306/xiaozhi_esp32_server

# 认证配置 - 对应Java TokenGenerator
SECRET_KEY=你的真实密钥至少32位
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=720
```

---

## 三、启动服务

### 3.1 开发模式启动

```bash
cd python-backend
uvicorn app.main:app --reload --port 8001
```

**注意**：默认端口8000与现有Python WebSocket服务冲突，建议使用8001或其他端口。

### 3.2 生产模式启动

```bash
cd python-backend
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

---

## 四、访问接口

启动成功后，可访问：

| 地址 | 说明 |
|------|------|
| http://localhost:8001/ | 根路径欢迎页 |
| http://localhost:8001/health | 健康检查，返回 `{"ok": true}` |
| http://localhost:8001/docs | Swagger API文档 |
| http://localhost:8001/redoc | ReDoc API文档 |

---

## 五、与Java后端对比

| 项目 | Java后端 | Python后端 |
|------|---------|-----------|
| 框架 | Spring Boot 3.4.3 | FastAPI |
| 端口 | 8002 | 8001（可配置） |
| Context-Path | /xiaozhi | 无（后续可加） |
| ORM | MyBatis Plus | SQLAlchemy |
| 数据库 | MySQL | MySQL（同一库） |
| 文档 | Knife4j/Swagger | FastAPI Swagger |
| 认证 | Shiro + Token | 待实现 |

---

## 六、后续迁移计划

1. **P0核心接口**：登录认证、设备绑定、智能体管理
2. **P1重要接口**：聊天记录、知识库、音色克隆
3. **P2管理接口**：用户管理、参数管理、字典管理

---

## 七、注意事项

1. **CORS配置**：当前 `allow_origins=["*"]` 仅用于开发，后续需收紧为具体前端地址
2. **数据库连接**：使用同一数据库 `xiaozhi_esp32_server`，与Java后端共享数据
3. **认证兼容**：后续需实现与Java Token认证兼容的逻辑

---

> 创建时间: 2026-06-16