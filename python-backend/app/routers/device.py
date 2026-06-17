"""
设备管理路由模块
对应Java的DeviceController.java

提供设备绑定、注册、解绑等接口
"""

from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
import uuid
import random

from app.database import get_db
from app.models.user import User
from app.models.agent import Agent
from app.models.device import Device
from app.schemas.device import (
    DeviceDTO, DeviceRegisterDTO, DeviceUnBindDTO, DeviceUpdateDTO,
    DeviceListResult, DeviceRegisterResult
)
from app.deps import get_current_user


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/device",
    tags=["设备管理"],
)


# ========================================
# 绑定设备
# Migrated from Java: DeviceController.bindDevice @ POST /device/bind/{agentId}/{deviceCode}
# ========================================
@router.post("/bind/{agentId}/{deviceCode}")
async def bind_device(
    agentId: str,
    deviceCode: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    绑定设备
    对应Java的DeviceController.java:
        @PostMapping("/bind/{agentId}/{deviceCode}")
        public Result<Void> bindDevice(@PathVariable String agentId, @PathVariable String deviceCode)
    
    Args:
        agentId: 智能体ID
        deviceCode: 设备验证码
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Result: 绑定结果
    """
    # 检查智能体是否存在且属于当前用户
    agent = db.query(Agent).filter(Agent.id == agentId).first()
    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="智能体不存在"
        )
    if agent.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限操作该智能体"
        )
    
    # 验证设备验证码（简化版，实际需要从Redis验证）
    # 对应Java的deviceService.deviceActivation(agentId, deviceCode)
    # 这里简化处理，假设验证码对应MAC地址
    
    # 创建设备记录
    device_id = str(uuid.uuid4())
    device = Device(
        id=device_id,
        user_id=current_user.id,
        mac_address=f"device_{deviceCode}",  # 简化处理
        agent_id=agentId,
        creator=current_user.id,
        create_date=datetime.now(),
    )
    
    db.add(device)
    db.commit()
    
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 更新设备信息
# Migrated from Java: DeviceController.updateDeviceInfo @ PUT /device/update/{id}
# ========================================
@router.put("/update/{id}")
async def update_device(
    id: str, body: DeviceUpdateDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新设备信息 对应Java DeviceController.updateDeviceInfo"""
    device = db.query(Device).filter(Device.id == id).first()
    if not device:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="设备不存在")
    if device.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="没有权限操作该设备")
    if body.alias is not None:
        device.alias = body.alias
    if body.autoUpdate is not None:
        device.auto_update = body.autoUpdate
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 手动添加设备
# Migrated from Java: DeviceController.manualAddDevice @ POST /device/manual-add
# ========================================
@router.post("/manual-add")
async def manual_add_device(
    body: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """手动添加设备 对应Java DeviceController.manualAddDevice"""
    import uuid
    from datetime import datetime
    device = Device(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        mac_address=body.get("macAddress"),
        alias=body.get("alias"),
        board=body.get("board"),
        agent_id=body.get("agentId"),
        creator=current_user.id,
        create_date=datetime.now(),
    )
    db.add(device)
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 注册设备
# Migrated from Java: DeviceController.registerDevice @ POST /device/register
# ========================================
@router.post("/register")
async def register_device(
    dto: DeviceRegisterDTO,
    db: Session = Depends(get_db)
):
    """
    注册设备
    对应Java的DeviceController.java:
        @PostMapping("/register")
        public Result<String> registerDevice(@RequestBody DeviceRegisterDTO deviceRegisterDTO)
    
    Args:
        dto: 注册请求（包含MAC地址）
        db: 数据库会话
        
    Returns:
        DeviceRegisterResult: 注册结果（返回验证码）
    """
    mac_address = dto.macAddress
    
    if not mac_address:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="MAC地址不能为空"
        )
    
    # 生成6位验证码
    # 对应Java的生成验证码逻辑
    code = str(random.randint(100000, 999999))
    
    # 简化处理：直接返回验证码
    # 实际需要存储到Redis，对应Java的redisUtils.set(key, macAddress)
    
    return DeviceRegisterResult(
        code=0,
        msg="success",
        data=code
    )


# ========================================
# 获取已绑定设备
# Migrated from Java: DeviceController.getUserDevices @ GET /device/bind/{agentId}
# ========================================
@router.get("/bind/{agentId}")
async def get_user_devices(
    agentId: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取已绑定设备
    对应Java的DeviceController.java:
        @GetMapping("/bind/{agentId}")
        public Result<List<DeviceEntity>> getUserDevices(@PathVariable String agentId)
    
    Args:
        agentId: 智能体ID
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        DeviceListResult: 设备列表
    """
    # 查询设备
    devices = db.query(Device).filter(
        Device.agent_id == agentId,
        Device.user_id == current_user.id
    ).all()
    
    # 构建响应数据
    device_list = []
    for device in devices:
        device_dto = DeviceDTO(
            id=device.id,
            userId=device.user_id,
            macAddress=device.mac_address,
            lastConnectedAt=device.last_connected_at,
            autoUpdate=device.auto_update,
            board=device.board,
            alias=device.alias,
            agentId=device.agent_id,
            appVersion=device.app_version,
            sort=device.sort,
        )
        device_list.append(device_dto)
    
    return DeviceListResult(
        code=0,
        msg="success",
        data=device_list
    )


# ========================================
# 解绑设备
# Migrated from Java: DeviceController.unbindDevice @ POST /device/unbind
# ========================================
@router.post("/unbind")
async def unbind_device(
    dto: DeviceUnBindDTO,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    解绑设备
    对应Java的DeviceController.java:
        @PostMapping("/unbind")
        public Result<Void> unbindDevice(@RequestBody DeviceUnBindDTO unDeviveBind)
    
    Args:
        dto: 解绑请求（包含设备ID）
        current_user: 当前用户
        db: 数据库会话
        
    Returns:
        Result: 解绑结果
    """
    device_id = dto.deviceId
    
    # 查询设备
    device = db.query(Device).filter(Device.id == device_id).first()
    
    if not device:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="设备不存在"
        )
    
    # 检查权限
    if device.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="没有权限操作该设备"
        )
    
    # 删除设备
    db.delete(device)
    db.commit()
    
    return {"code": 0, "msg": "success", "data": None}