"""
OTA路由模块
对应Java的OTAController.java

提供OTA版本检查和设备激活检查接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header, Response
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
import json

from app.database import get_db
from app.models.device import Device
from app.schemas.device import DeviceReportReqDTO


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/ota",
    tags=["OTA管理"],
)


# ========================================
# OTA版本检查
# Migrated from Java: OTAController.checkOTAVersion @ POST /ota/
# ========================================
@router.post("/")
async def check_ota_version(
    dto: DeviceReportReqDTO,
    device_id: str = Header(..., alias="Device-Id", description="设备唯一标识"),
    client_id: Optional[str] = Header(None, alias="Client-Id", description="客户端标识"),
    db: Session = Depends(get_db)
):
    """
    OTA版本检查
    对应Java的OTAController.java:
        @PostMapping
        public ResponseEntity<String> checkOTAVersion(...)
    
    Args:
        dto: 设备上报请求
        device_id: 设备ID（MAC地址）
        client_id: 客户端标识
        db: 数据库会话
        
    Returns:
        Response: OTA响应（JSON格式）
    """
    if not device_id:
        return Response(
            content=json.dumps({"error": "Device ID is required"}),
            media_type="application/json",
            status_code=400
        )
    
    # 验证MAC地址格式
    # 对应Java的isMacAddressValid方法
    import re
    mac_pattern = r"^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$"
    if not re.match(mac_pattern, device_id):
        return Response(
            content=json.dumps({"error": "Invalid device ID"}),
            media_type="application/json",
            status_code=400
        )
    
    # 查询设备
    device = db.query(Device).filter(Device.mac_address == device_id).first()
    
    # 构建响应
    # 对应Java的DeviceReportRespDTO
    response_data = {
        "activation": device is not None,  # 设备是否已激活
        "firmwareUrl": None,  # 固件下载地址（暂不实现）
        "firmwareVersion": None,  # 固件版本（暂不实现）
    }
    
    return Response(
        content=json.dumps(response_data),
        media_type="application/json"
    )


# ========================================
# 设备激活状态检查
# Migrated from Java: OTAController.activateDevice @ POST /ota/activate
# ========================================
@router.post("/activate")
async def activate_device(
    device_id: str = Header(..., alias="Device-Id", description="设备唯一标识"),
    client_id: Optional[str] = Header(None, alias="Client-Id", description="客户端标识"),
    db: Session = Depends(get_db)
):
    """
    设备激活状态检查
    对应Java的OTAController.java:
        @PostMapping("activate")
        public ResponseEntity<String> activateDevice(...)
    
    Args:
        device_id: 设备ID（MAC地址）
        client_id: 客户端标识
        db: 数据库会话
        
    Returns:
        Response: 激活状态响应
    """
    if not device_id:
        return Response(status_code=202)
    
    # 查询设备
    device = db.query(Device).filter(Device.mac_address == device_id).first()
    
    if not device:
        return Response(status_code=202)
    
    return Response(content="success", status_code=200)


# ========================================
# OTA接口健康检查
# Migrated from Java: OTAController.getOTA @ GET /ota/
# ========================================
@router.get("/")
async def get_ota_health():
    """
    OTA接口健康检查
    对应Java的OTAController.java:
        @GetMapping
        public ResponseEntity<String> getOTA()
    
    Returns:
        str: 健康检查结果
    """
    return "OTA接口运行正常"