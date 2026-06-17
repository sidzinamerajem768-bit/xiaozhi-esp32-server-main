"""
FastAPI应用入口
对应Java的AdminApplication.java启动类

配置CORS、路由、中间件等
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import health, auth, agent, device, ota, config, knowledge, voice_clone, model, admin, sys_params, sys_dict, agent_template, knowledge_files, correct_word, agent_mcp, agent_voice_print, agent_chat


# 创建FastAPI应用实例
# 对应Java的@SpringBootApplication
app = FastAPI(
    title="小智ESP32服务端 - Python版",
    description="FastAPI骨架，用于迁移Java后端接口",
    version="0.1.0",
    docs_url="/docs",        # Swagger文档路径
    redoc_url="/redoc",      # ReDoc文档路径
)

# ========================================
# CORS配置
# 对应Java的WebMvcConfigurer跨域配置
# ========================================
# 注意：当前allow_origins=["*"]仅用于开发，后续需收紧为具体前端地址
# 对应Java的Access-Control-Allow-Origin配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],            # 允许所有来源，后续需收紧
    allow_credentials=True,         # 允许携带Cookie
    allow_methods=["*"],            # 允许所有HTTP方法
    allow_headers=["*"],            # 允许所有请求头
)

# ========================================
# 注册路由
# 对应Java的@RestController扫描注册
# ========================================
app.include_router(health.router)

# 认证路由 - 对应Java的LoginController
# prefix="/api" 对应Java的context-path: /xiaozhi
app.include_router(auth.router, prefix="/api")

# 智能体路由 - 对应Java的AgentController
app.include_router(agent.router, prefix="/api")

# 设备路由 - 对应Java的DeviceController
app.include_router(device.router, prefix="/api")

# OTA路由 - 对应Java的OTAController
app.include_router(ota.router, prefix="/api")

# 配置路由 - 对应Java的ConfigController
app.include_router(config.router, prefix="/api")

# 知识库路由 - 对应Java的KnowledgeBaseController
app.include_router(knowledge.router, prefix="/api")

# 音色克隆路由 - 对应Java的VoiceCloneController
app.include_router(voice_clone.router, prefix="/api")

# 模型配置路由 - 对应Java的ModelController
app.include_router(model.router, prefix="/api")

# 管理员路由 - 对应Java的AdminController
app.include_router(admin.router, prefix="/api")

# 参数管理路由 - 对应Java的SysParamsController
app.include_router(sys_params.router, prefix="/api")

# 字典数据管理路由 - 对应Java的SysDictDataController
app.include_router(sys_dict.router, prefix="/api")

# 智能体模板管理路由 - 对应Java的AgentTemplateController
app.include_router(agent_template.router, prefix="/api")

# 知识库文档管理路由 - 对应Java的KnowledgeFilesController
app.include_router(knowledge_files.router, prefix="/api")

# 替换词管理路由 - 对应Java的CorrectWordController
app.include_router(correct_word.router, prefix="/api")

# MCP接入点管理路由 - 对应Java的AgentMcpAccessPointController
app.include_router(agent_mcp.router, prefix="/api")

# 声纹管理路由 - 对应Java的AgentVoicePrintController
app.include_router(agent_voice_print.router, prefix="/api")

# 聊天记录管理路由 - 对应Java的AgentChatHistoryController
app.include_router(agent_chat.router, prefix="/api")


# ========================================
# 应用生命周期事件
# 对应Java的@PostConstruct和@PreDestroy
# ========================================
@app.on_event("startup")
async def startup_event():
    """
    应用启动事件
    对应Java的ApplicationRunner或CommandLineRunner
    """
    print("=" * 50)
    print("小智ESP32服务端 - Python版启动成功")
    print("Swagger文档: http://localhost:8000/docs")
    print("ReDoc文档: http://localhost:8000/redoc")
    print("健康检查: http://localhost:8000/health")
    print("登录接口: http://localhost:8000/api/user/login")
    print("智能体接口: http://localhost:8000/api/agent/list")
    print("设备接口: http://localhost:8000/api/device/register")
    print("配置接口: http://localhost:8000/api/config/server-base")
    print("知识库接口: http://localhost:8000/api/datasets")
    print("音色克隆接口: http://localhost:8000/api/voiceClone")
    print("模型配置接口: http://localhost:8000/api/models/names")
    print("=" * 50)


@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭事件
    对应Java的DisposableBean.destroy()
    """
    print("小智ESP32服务端 - Python版关闭")


# ========================================
# 根路径
# 对应Java的index页面
# ========================================
@app.get("/")
async def root():
    """
    根路径欢迎页
    """
    return {
        "message": "小智ESP32服务端 - Python版",
        "docs": "/docs",
        "health": "/health",
    }