"""
智能体ORM模型
对应Java的AgentEntity.java

映射ai_agent表，用于存储智能体信息
"""

from sqlalchemy import Column, String, BigInteger, Integer, DateTime
from sqlalchemy.orm import declarative_base

from app.models.user import Base


class Agent(Base):
    """
    智能体表
    对应Java的AgentEntity.java
    表名: ai_agent
    """
    __tablename__ = "ai_agent"
    
    # 主键ID - 对应Java的@TableId(type = IdType.ASSIGN_UUID)
    id = Column(String(36), primary_key=True, comment="智能体唯一标识")
    
    # 所属用户ID - 对应Java的userId字段
    user_id = Column(BigInteger, nullable=False, index=True, comment="所属用户ID")
    
    # 智能体编码 - 对应Java的agentCode字段
    agent_code = Column(String(50), comment="智能体编码")
    
    # 智能体名称 - 对应Java的agentName字段
    agent_name = Column(String(100), nullable=False, comment="智能体名称")
    
    # 语音识别模型标识 - 对应Java的asrModelId字段
    asr_model_id = Column(String(36), comment="语音识别模型标识")
    
    # 语音活动检测标识 - 对应Java的vadModelId字段
    vad_model_id = Column(String(36), comment="语音活动检测标识")
    
    # 大语言模型标识 - 对应Java的llmModelId字段
    llm_model_id = Column(String(36), comment="大语言模型标识")
    
    # 小模型标识 - 对应Java的slmModelId字段
    slm_model_id = Column(String(36), comment="小模型标识")
    
    # VLLM模型标识 - 对应Java的vllmModelId字段
    vllm_model_id = Column(String(36), comment="VLLM模型标识")
    
    # 语音合成模型标识 - 对应Java的ttsModelId字段
    tts_model_id = Column(String(36), comment="语音合成模型标识")
    
    # 音色标识 - 对应Java的ttsVoiceId字段
    tts_voice_id = Column(String(36), comment="音色标识")
    
    # 音色语言 - 对应Java的ttsLanguage字段
    tts_language = Column(String(20), comment="音色语言")
    
    # TTS音量 - 对应Java的ttsVolume字段
    tts_volume = Column(Integer, comment="TTS音量")
    
    # TTS语速 - 对应Java的ttsRate字段
    tts_rate = Column(Integer, comment="TTS语速")
    
    # TTS音调 - 对应Java的ttsPitch字段
    tts_pitch = Column(Integer, comment="TTS音调")
    
    # 记忆模型标识 - 对应Java的memModelId字段
    mem_model_id = Column(String(36), comment="记忆模型标识")
    
    # 意图模型标识 - 对应Java的intentModelId字段
    intent_model_id = Column(String(36), comment="意图模型标识")
    
    # 聊天记录配置 - 对应Java的chatHistoryConf字段
    chat_history_conf = Column(Integer, default=0, comment="聊天记录配置（0不记录 1仅记录文本 2记录文本和语音）")
    
    # 角色设定参数 - 对应Java的systemPrompt字段
    system_prompt = Column(String(2000), comment="角色设定参数")
    
    # 总结记忆 - 对应Java的summaryMemory字段
    summary_memory = Column(String(2000), comment="总结记忆")
    
    # 语言编码 - 对应Java的langCode字段
    lang_code = Column(String(10), comment="语言编码")
    
    # 交互语种 - 对应Java的language字段
    language = Column(String(20), comment="交互语种")
    
    # 排序 - 对应Java的sort字段
    sort = Column(Integer, default=0, comment="排序")
    
    # 创建者 - 对应Java的creator字段
    creator = Column(BigInteger, comment="创建者")
    
    # 创建时间 - 对应Java的createdAt字段
    created_at = Column(DateTime, comment="创建时间")
    
    # 更新者 - 对应Java的updater字段
    updater = Column(BigInteger, comment="更新者")
    
    # 更新时间 - 对应Java的updatedAt字段
    updated_at = Column(DateTime, comment="更新时间")