"""
配置路由模块
对应Java的ConfigController.java

提供服务端配置获取接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, List

from app.database import get_db
from app.models.agent import Agent
from app.models.device import Device


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/config",
    tags=["配置管理"],
)


# ========================================
# 获取服务端配置
# Migrated from Java: ConfigController.getConfig @ POST /config/server-base
# ========================================
@router.post("/server-base")
async def get_server_config(
    db: Session = Depends(get_db)
):
    """
    获取服务端配置
    对应Java的ConfigController.java:
        @PostMapping("server-base")
        public Result<Object> getConfig()
    
    Args:
        db: 数据库会话
        
    Returns:
        Result: 服务端配置
    """
    # 简化版：返回基本配置
    # 实际需要从sys_params表读取配置
    config = {
        "mqttGateway": None,  # MQTT网关地址
        "websocket": None,  # WebSocket地址
        "ota": None,  # OTA地址
        "version": "1.0.0",  # 服务版本
    }
    
    return {"code": 0, "msg": "success", "data": config}


# ========================================
# 获取智能体模型
# Migrated from Java: ConfigController.getAgentModels @ POST /config/agent-models
# ========================================
@router.post("/agent-models")
async def get_agent_models(
    macAddress: str,
    selectedModule: Optional[List[str]] = None,
    db: Session = Depends(get_db)
):
    """
    获取智能体模型
    对应Java的ConfigController.java:
        @PostMapping("agent-models")
        public Result<Object> getAgentModels(@Valid @RequestBody AgentModelsDTO dto)
    
    Args:
        macAddress: 设备MAC地址
        selectedModule: 选中的模块列表
        db: 数据库会话
        
    Returns:
        Result: 智能体模型配置
    """
    # 查询设备
    device = db.query(Device).filter(Device.mac_address == macAddress).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在"
        )
    
    # 查询智能体
    agent = db.query(Agent).filter(Agent.id == device.agent_id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )
    
    # 构建响应
    models = {
        "asrModelId": agent.asr_model_id,
        "llmModelId": agent.llm_model_id,
        "ttsModelId": agent.tts_model_id,
        "ttsVoiceId": agent.tts_voice_id,
        "systemPrompt": agent.system_prompt,
        "summaryMemory": agent.summary_memory,
    }
    
    return {"code": 0, "msg": "success", "data": models}


# ========================================
# 获取替换词
# Migrated from Java: ConfigController.getCorrectWords @ POST /config/correct-words
# ========================================
@router.post("/correct-words")
async def get_correct_words(
    macAddress: str,
    db: Session = Depends(get_db)
):
    """
    获取替换词
    对应Java的ConfigController.java:
        @PostMapping("correct-words")
        public Result<Object> getCorrectWords(@Valid @RequestBody CorrectWordsDTO dto)
    
    Args:
        macAddress: 设备MAC地址
        db: 数据库会话
        
    Returns:
        Result: 替换词列表
    """
    # 简化版：返回空列表
    # 实际需要从correct_word表读取配置
    correct_words = []
    
    return {"code": 0, "msg": "success", "data": correct_words}