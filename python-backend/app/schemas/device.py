"""
设备相关Pydantic Schema
对应Java的DeviceEntity.java和DeviceRegisterDTO.java

用于请求参数验证和响应数据序列化
"""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ========================================
# 设备响应Schema
# 对应Java的DeviceEntity.java
# ========================================
class DeviceDTO(BaseModel):
    """
    设备数据传输对象
    对应Java的DeviceEntity.java
    
    注意：字段名使用驼峰命名，与Java保持一致
    """
    id: Optional[str] = Field(None, description="ID")
    userId: Optional[int] = Field(None, description="关联用户ID")
    macAddress: Optional[str] = Field(None, description="MAC地址")
    lastConnectedAt: Optional[datetime] = Field(None, description="最后连接时间")
    autoUpdate: Optional[int] = Field(None, description="自动更新开关(0关闭/1开启)")
    board: Optional[str] = Field(None, description="设备硬件型号")
    alias: Optional[str] = Field(None, description="设备别名")
    agentId: Optional[str] = Field(None, description="智能体ID")
    appVersion: Optional[str] = Field(None, description="固件版本号")
    sort: Optional[int] = Field(None, description="排序")


# ========================================
# 设备注册请求Schema
# 对应Java的DeviceRegisterDTO.java
# ========================================
class DeviceRegisterDTO(BaseModel):
    """
    设备注册对象
    对应Java的DeviceRegisterDTO.java
    """
    macAddress: str = Field(..., description="MAC地址")


# ========================================
# 设备解绑请求Schema
# 对应Java的DeviceUnBindDTO.java
# ========================================
class DeviceUnBindDTO(BaseModel):
    """
    设备解绑对象
    对应Java的DeviceUnBindDTO.java
    """
    deviceId: str = Field(..., description="设备ID")


# ========================================
# 设备更新请求Schema
# 对应Java的DeviceUpdateDTO.java
# ========================================
class DeviceUpdateDTO(BaseModel):
    """
    设备更新对象
    对应Java的DeviceUpdateDTO.java
    """
    alias: Optional[str] = Field(None, description="设备别名")
    autoUpdate: Optional[int] = Field(None, description="自动更新开关")


# ========================================
# OTA请求Schema
# 对应Java的DeviceReportReqDTO.java
# ========================================
class DeviceReportReqDTO(BaseModel):
    """
    设备上报请求对象
    对应Java的DeviceReportReqDTO.java
    """
    application: Optional[str] = Field(None, description="应用名称")
    board: Optional[str] = Field(None, description="设备型号")
    version: Optional[str] = Field(None, description="固件版本")


# ========================================
# 统一响应格式
# ========================================
class DeviceListResult(BaseModel):
    """
    设备列表响应
    """
    code: int = Field(0, description="响应码")
    msg: str = Field("success", description="响应消息")
    data: Optional[List[DeviceDTO]] = Field(None, description="设备列表")


class DeviceRegisterResult(BaseModel):
    """
    设备注册响应
    """
    code: int = Field(0, description="响应码")
    msg: str = Field("success", description="响应消息")
    data: Optional[str] = Field(None, description="验证码")