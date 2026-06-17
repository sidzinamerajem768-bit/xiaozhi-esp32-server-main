"""
智能体管理路由模块
对应Java的AgentController.java

提供智能体CRUD接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid

from app.database import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.device import Device
from app.schemas.agent import (
    AgentDTO, AgentCreateDTO, AgentUpdateDTO, AgentInfoVO,
    AgentListResult, AgentInfoResult, AgentCreateResult,
    AgentTagDTO
)
from app.deps import get_current_user


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/agent",
    tags=["智能体管理"],
)


# ========================================
# 获取用户智能体列表
# Migrated from Java: AgentController.getUserAgents @ GET /agent/list
# ========================================
@router.get("/list")
async def get_user_agents(
    keyword: Optional[str] = Query(None, description="搜索关键词"),
    searchType: str = Query("name", description="搜索类型"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取用户智能体列表
    对应Java的AgentController.java:
        @GetMapping("/list")
        public Result<List<AgentDTO>> getUserAgents(...)
    
    Args:
        keyword: 搜索关键词
        searchType: 搜索类型（name/code）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        AgentListResult: 智能体列表
    """
    # 查询用户的智能体
    query = db.query(Agent).filter(Agent.user_id == current_user.id)
    
    # 搜索过滤
    if keyword:
        if searchType == "name":
            query = query.filter(Agent.agent_name.like(f"%{keyword}%"))
        elif searchType == "code":
            query = query.filter(Agent.agent_code.like(f"%{keyword}%"))
    
    # 排序
    query = query.order_by(Agent.sort.asc(), Agent.created_at.desc())
    
    agents = query.all()
    
    # 构建响应数据
    agent_list = []
    for agent in agents:
        # 查询设备数量
        device_count = db.query(Device).filter(Device.agent_id == agent.id).count()
        
        agent_dto = AgentDTO(
            id=agent.id,
            agentName=agent.agent_name,
            systemPrompt=agent.system_prompt,
            summaryMemory=agent.summary_memory,
            lastConnectedAt=None,  # 需要从设备表获取最后连接时间
            deviceCount=device_count,
            tags=None,  # 标签功能暂不实现
        )
        agent_list.append(agent_dto)
    
    return AgentListResult(
        code=0,
        msg="success",
        data=agent_list
    )


# ========================================
# 获取智能体详情
# Migrated from Java: AgentController.getAgentById @ GET /agent/{id}
# ========================================
@router.get("/{id}")
async def get_agent_by_id(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取智能体详情
    对应Java的AgentController.java:
        @GetMapping("/{id}")
        public Result<AgentInfoVO> getAgentById(@PathVariable("id") String id)
    
    Args:
        id: 智能体ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        AgentInfoResult: 智能体详情
    """
    # 查询智能体
    agent = db.query(Agent).filter(Agent.id == id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )
    
    # 检查权限（用户只能查看自己的智能体）
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限查看该智能体"
        )
    
    # 构建响应数据
    agent_info = AgentInfoVO(
        id=agent.id,
        agentName=agent.agent_name,
        userId=agent.user_id,
        systemPrompt=agent.system_prompt,
        summaryMemory=agent.summary_memory,
        asrModelId=agent.asr_model_id,
        llmModelId=agent.llm_model_id,
        ttsModelId=agent.tts_model_id,
        ttsVoiceId=agent.tts_voice_id,
    )
    
    return AgentInfoResult(
        code=0,
        msg="success",
        data=agent_info
    )


# ========================================
# 创建智能体
# Migrated from Java: AgentController.save @ POST /agent
# ========================================
@router.post("")
async def create_agent(
    dto: AgentCreateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    创建智能体
    对应Java的AgentController.java:
        @PostMapping
        public Result<String> save(@RequestBody @Valid AgentCreateDTO dto)
    
    Args:
        dto: 创建请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        AgentCreateResult: 创建结果（返回智能体ID）
    """
    # 生成智能体ID
    agent_id = str(uuid.uuid4())
    
    # 生成智能体编码（简化版）
    agent_code = f"AGT_{agent_id[:8]}"
    
    # 创建智能体实体
    agent = Agent(
        id=agent_id,
        user_id=current_user.id,
        agent_code=agent_code,
        agent_name=dto.agentName,
        creator=current_user.id,
        created_at=datetime.now(),
        sort=0,
    )
    
    # 保存到数据库
    db.add(agent)
    db.commit()
    
    return AgentCreateResult(
        code=0,
        msg="success",
        data=agent_id
    )


# ========================================
# 更新智能体
# Migrated from Java: AgentController.update @ PUT /agent/{id}
# ========================================
@router.put("/{id}")
async def update_agent(
    id: str,
    dto: AgentUpdateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    更新智能体
    对应Java的AgentController.java:
        @PutMapping("/{id}")
        public Result<Void> update(@PathVariable String id, @RequestBody @Valid AgentUpdateDTO dto)
    
    Args:
        id: 智能体ID
        dto: 更新请求
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Result: 更新结果
    """
    # 查询智能体
    agent = db.query(Agent).filter(Agent.id == id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )
    
    # 检查权限
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限修改该智能体"
        )
    
    # 更新字段
    if dto.agentName is not None:
        agent.agent_name = dto.agentName
    if dto.systemPrompt is not None:
        agent.system_prompt = dto.systemPrompt
    if dto.summaryMemory is not None:
        agent.summary_memory = dto.summaryMemory
    if dto.asrModelId is not None:
        agent.asr_model_id = dto.asrModelId
    if dto.llmModelId is not None:
        agent.llm_model_id = dto.llmModelId
    if dto.ttsModelId is not None:
        agent.tts_model_id = dto.ttsModelId
    if dto.ttsVoiceId is not None:
        agent.tts_voice_id = dto.ttsVoiceId
    
    agent.updater = current_user.id
    agent.updated_at = datetime.now()
    
    # 保存更新
    db.commit()
    
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 删除智能体
# Migrated from Java: AgentController.delete @ DELETE /agent/{id}
# ========================================
@router.delete("/{id}")
async def delete_agent(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    删除智能体
    对应Java的AgentController.java:
        @DeleteMapping("/{id}")
        public Result<Void> delete(@PathVariable String id)
    
    Args:
        id: 智能体ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Result: 删除结果
    """
    # 查询智能体
    agent = db.query(Agent).filter(Agent.id == id).first()
    
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )
    
    # 检查权限
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限删除该智能体"
        )
    
    # 删除关联的设备（对应Java的deviceService.deleteByAgentId(id))
    db.query(Device).filter(Device.agent_id == id).delete()
    
    # 删除智能体
    db.delete(agent)
    db.commit()
    
    return {"code": 0, "msg": "success", "data": None}