"""
智能体相关Pydantic Schema
对应Java的AgentDTO.java和AgentCreateDTO.java

用于请求参数验证和响应数据序列化
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========================================
# 智能体标签Schema
# 对应Java的AgentTagDTO.java
# ========================================
class AgentTagDTO(BaseModel):
    """
    智能体标签
    对应Java的AgentTagDTO.java
    """
    id: Optional[str] = Field(None, description="标签ID")
    tagName: Optional[str] = Field(None, description="标签名称")


# ========================================
# 智能体响应Schema
# 对应Java的AgentDTO.java
# ========================================
class AgentDTO(BaseModel):
    """
    智能体数据传输对象
    对应Java的AgentDTO.java
    
    注意：字段名使用驼峰命名，与Java保持一致
    """
    id: Optional[str] = Field(None, description="智能体编码")
    agentName: Optional[str] = Field(None, description="智能体名称")
    ttsModelName: Optional[str] = Field(None, description="语音合成模型名称")
    ttsVoiceName: Optional[str] = Field(None, description="音色名称")
    llmModelName: Optional[str] = Field(None, description="大语言模型名称")
    vllmModelName: Optional[str] = Field(None, description="视觉模型名称")
    memModelId: Optional[str] = Field(None, description="记忆模型ID")
    systemPrompt: Optional[str] = Field(None, description="角色设定参数")
    summaryMemory: Optional[str] = Field(None, description="总结记忆")
    lastConnectedAt: Optional[datetime] = Field(None, description="最后连接时间")
    deviceCount: Optional[int] = Field(None, description="设备数量")
    tags: Optional[List[AgentTagDTO]] = Field(None, description="标签列表")


# ========================================
# 智能体创建请求Schema
# 对应Java的AgentCreateDTO.java
# ========================================
class AgentCreateDTO(BaseModel):
    """
    智能体创建对象
    对应Java的AgentCreateDTO.java
    """
    agentName: str = Field(..., description="智能体名称")


# ========================================
# 智能体更新请求Schema
# 对应Java的AgentUpdateDTO.java
# ========================================
class AgentUpdateDTO(BaseModel):
    """
    智能体更新对象
    对应Java的AgentUpdateDTO.java（简化版）
    """
    agentName: Optional[str] = Field(None, description="智能体名称")
    systemPrompt: Optional[str] = Field(None, description="角色设定参数")
    summaryMemory: Optional[str] = Field(None, description="总结记忆")
    asrModelId: Optional[str] = Field(None, description="语音识别模型标识")
    vadModelId: Optional[str] = Field(None, description="语音活动检测标识")
    llmModelId: Optional[str] = Field(None, description="大语言模型标识")
    ttsModelId: Optional[str] = Field(None, description="语音合成模型标识")
    ttsVoiceId: Optional[str] = Field(None, description="音色标识")
    ttsLanguage: Optional[str] = Field(None, description="音色语言")
    ttsVolume: Optional[int] = Field(None, description="TTS音量")
    ttsRate: Optional[int] = Field(None, description="TTS语速")
    ttsPitch: Optional[int] = Field(None, description="TTS音调")


# ========================================
# 智能体详情响应Schema
# 对应Java的AgentInfoVO.java
# ========================================
class AgentInfoVO(BaseModel):
    """
    智能体详情
    对应Java的AgentInfoVO.java（简化版）
    """
    id: Optional[str] = Field(None, description="智能体ID")
    agentName: Optional[str] = Field(None, description="智能体名称")
    userId: Optional[int] = Field(None, description="所属用户ID")
    systemPrompt: Optional[str] = Field(None, description="角色设定参数")
    summaryMemory: Optional[str] = Field(None, description="总结记忆")
    asrModelId: Optional[str] = Field(None, description="语音识别模型标识")
    llmModelId: Optional[str] = Field(None, description="大语言模型标识")
    ttsModelId: Optional[str] = Field(None, description="语音合成模型标识")
    ttsVoiceId: Optional[str] = Field(None, description="音色标识")


# ========================================
# 统一响应格式
# ========================================
class AgentListResult(BaseModel):
    """
    智能体列表响应
    """
    code: int = Field(0, description="响应码")
    msg: str = Field("success", description="响应消息")
    data: Optional[List[AgentDTO]] = Field(None, description="智能体列表")


class AgentInfoResult(BaseModel):
    """
    智能体详情响应
    """
    code: int = Field(0, description="响应码")
    msg: str = Field("success", description="响应消息")
    data: Optional[AgentInfoVO] = Field(None, description="智能体详情")


class AgentCreateResult(BaseModel):
    """
    智能体创建响应
    """
    code: int = Field(0, description="响应码")
    msg: str = Field("success", description="响应消息")
    data: Optional[str] = Field(None, description="智能体ID")