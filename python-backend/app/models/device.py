"""
设备ORM模型
对应Java的DeviceEntity.java

映射ai_device表，用于存储设备信息
"""

from sqlalchemy import Column, String, BigInteger, Integer, DateTime
from sqlalchemy.orm import declarative_base

from app.models.user import Base


class Device(Base):
    """
    设备表
    对应Java的DeviceEntity.java
    表名: ai_device
    """
    __tablename__ = "ai_device"
    
    # 主键ID - 对应Java的@TableId(type = IdType.ASSIGN_UUID)
    id = Column(String(36), primary_key=True, comment="ID")
    
    # 关联用户ID - 对应Java的userId字段
    user_id = Column(BigInteger, index=True, comment="关联用户ID")
    
    # MAC地址 - 对应Java的macAddress字段
    mac_address = Column(String(20), unique=True, comment="MAC地址")
    
    # 最后连接时间 - 对应Java的lastConnectedAt字段
    last_connected_at = Column(DateTime, comment="最后连接时间")
    
    # 自动更新开关 - 对应Java的autoUpdate字段
    auto_update = Column(Integer, default=1, comment="自动更新开关(0关闭/1开启)")
    
    # 设备硬件型号 - 对应Java的board字段
    board = Column(String(50), comment="设备硬件型号")
    
    # 设备别名 - 对应Java的alias字段
    alias = Column(String(100), comment="设备别名")
    
    # 智能体ID - 对应Java的agentId字段
    agent_id = Column(String(36), index=True, comment="智能体ID")
    
    # 固件版本号 - 对应Java的appVersion字段
    app_version = Column(String(20), comment="固件版本号")
    
    # 排序 - 对应Java的sort字段
    sort = Column(Integer, default=0, comment="排序")
    
    # 更新者 - 对应Java的updater字段
    updater = Column(BigInteger, comment="更新者")
    
    # 更新时间 - 对应Java的updateDate字段
    update_date = Column(DateTime, comment="更新时间")
    
    # 创建者 - 对应Java的creator字段
    creator = Column(BigInteger, comment="创建者")
    
    # 创建时间 - 对应Java的createDate字段
    create_date = Column(DateTime, comment="创建时间")