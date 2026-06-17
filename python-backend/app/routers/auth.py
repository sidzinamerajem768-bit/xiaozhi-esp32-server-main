"""
认证路由模块
对应Java的LoginController.java

提供登录接口和用户信息获取接口
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, timedelta
import uuid
import hashlib

from app.database import get_db
from app.models.user import User
from app.models.user_token import UserToken
from app.schemas.user import (
    LoginRequest, TokenResponse, UserInfoResponse, 
    TokenResult, UserInfoResult, RegisterRequest,
    PasswordChangeRequest, PasswordRetrieveRequest
)
from app.deps import get_current_user

# 密码验证工具
from passlib.context import CryptContext

# 创建密码上下文 - 对应Java的BCryptPasswordEncoder
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# 创建路由器
# 对应Java的@RestController
router = APIRouter(
    prefix="/user",
    tags=["认证管理"],
)


# ========================================
# Token生成函数
# 对应Java的TokenGenerator.java
# ========================================
def generate_token() -> str:
    """
    生成32位MD5 Token
    对应Java的TokenGenerator.generateValue()
    
    流程：
    1. 生成UUID
    2. 计算MD5哈希
    3. 返回32位十六进制字符串
    
    Returns:
        str: 32位MD5字符串
    """
    # 生成UUID - 对应Java的UUID.randomUUID().toString()
    uuid_str = str(uuid.uuid4())
    
    # 计算MD5 - 对应Java的MessageDigest.getInstance("MD5")
    md5_hash = hashlib.md5(uuid_str.encode()).hexdigest()
    
    return md5_hash


# ========================================
# Token有效期常量
# 对应Java的SysUserTokenServiceImpl.EXPIRE
# ========================================
EXPIRE_SECONDS = 3600 * 12  # 12小时


# ========================================
# 登录接口
# 对应Java的LoginController.login()
# ========================================
@router.post("/login")
async def login(
    request: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    用户登录
    对应Java的LoginController.java:
        @PostMapping("/login")
        public Result<TokenDTO> login(@RequestBody LoginDTO login)
    
    流程：
    1. 查询用户
    2. 验证密码（bcrypt）
    3. 生成token（UUID + MD5）
    4. 存储token到sys_user_token
    5. 返回TokenResponse
    
    Args:
        request: 登录请求
        db: 数据库会话
        
    Returns:
        TokenResult: Token响应（统一格式）
        
    Raises:
        HTTPException: 401 - 用户名或密码错误
    """
    # 查询用户 - 对应Java的sysUserService.getByUsername()
    user = db.query(User).filter(User.username == request.username).first()
    
    # 判断用户是否存在 - 对应Java的判断userDTO == null
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    # 验证密码 - 对应Java的PasswordUtils.matches()
    # 注意：Java前端使用SM2加密密码，Python后端暂不实现SM2解密
    if not pwd_context.verify(request.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已停用",
        )
    
    # 当前时间
    now = datetime.now()
    
    # 过期时间 - 对应Java的expireTime = new Date(now.getTime() + EXPIRE * 1000)
    expire_date = now + timedelta(seconds=EXPIRE_SECONDS)
    
    # 查询是否已有token记录 - 对应Java的baseDao.getByUserId(userId)
    user_token = db.query(UserToken).filter(UserToken.user_id == user.id).first()
    
    if user_token:
        # 判断token是否过期
        if user_token.expire_date < now:
            token = generate_token()
        else:
            token = user_token.token
        # 更新token - 使用原生SQL
        db.execute(
            text("UPDATE sys_user_token SET token = :tk, update_date = :ud, expire_date = :ed WHERE user_id = :uid"),
            {"tk": token, "ud": now, "ed": expire_date, "uid": user.id}
        )
    else:
        token = generate_token()
        # 创建token - 使用原生SQL（避免ID问题）
        max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM sys_user_token")).scalar()
        db.execute(
            text("INSERT INTO sys_user_token (id, user_id, token, expire_date, update_date, create_date) VALUES (:id, :uid, :tk, :ed, :ud, :cd)"),
            {"id": max_id, "uid": user.id, "tk": token, "ed": expire_date, "ud": now, "cd": now}
        )
    db.commit()
    
    # 返回Token响应 - 对应Java的return new Result<TokenDTO>().ok(tokenDTO)
    return TokenResult(
        code=0,
        msg="success",
        data=TokenResponse(
            token=token,
            expire=EXPIRE_SECONDS,
            clientHash=None,  # 暂不实现客户端指纹
        )
    )


# ========================================
# 用户信息获取接口
# 对应Java的LoginController.info()
# ========================================
@router.get("/info")
async def get_user_info(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户信息
    对应Java的LoginController.java:
        @GetMapping("/info")
        public Result<UserDetail> info()
    
    Args:
        current_user: 当前用户（通过get_current_user依赖注入）
        
    Returns:
        UserInfoResult: 用户信息响应（统一格式）
    """
    return UserInfoResult(
        code=0,
        msg="success",
        data=UserInfoResponse(
            id=current_user.id,
            username=current_user.username,
            superAdmin=current_user.super_admin,
            status=current_user.status,
        )
    )


# ========================================
# 测试接口：获取当前用户（简化版）
# 用于验证token是否有效
# ========================================
@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    获取当前用户（测试接口）
    用于验证token是否有效
    
    Args:
        current_user: 当前用户（通过get_current_user依赖注入）
        
    Returns:
        UserInfoResponse: 用户信息响应
    """
    return UserInfoResponse(
        id=current_user.id,
        username=current_user.username,
        superAdmin=current_user.super_admin,
        status=current_user.status,
    )


# ========================================
# 用户注册接口
# Migrated from Java: LoginController.register @ POST /user/register
# ========================================
@router.post("/register")
async def register(
    request: RegisterRequest,
    db: Session = Depends(get_db)
):
    """用户注册 对应Java LoginController.register"""
    from sqlalchemy import text
    # 检查用户是否已存在
    existing = db.execute(text("SELECT id FROM sys_user WHERE username = :un"), {"un": request.username}).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号已注册")
    # 使用原生SQL插入（避免ORM映射问题）
    hashed = pwd_context.hash(request.password)
    now = datetime.now()
    # 先获取当前最大ID
    max_id = db.execute(text("SELECT COALESCE(MAX(id), 0) + 1 FROM sys_user")).scalar()
    db.execute(
        text("INSERT INTO sys_user (id, username, password, status, create_date) VALUES (:id, :un, :pw, :st, :cd)"),
        {"id": max_id, "un": request.username, "pw": hashed, "st": 1, "cd": now}
    )
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 公共配置获取接口
# Migrated from Java: LoginController.pubConfig @ GET /user/pub-config
# ========================================
@router.get("/pub-config")
async def pub_config():
    """获取公共配置 对应Java LoginController.pubConfig"""
    config = {
        "enableMobileRegister": True, "version": "1.0.0", "year": "2026",
        "allowUserRegister": True, "mobileAreaList": [{"code": "+86", "name": "中国"}],
        "beianIcpNum": "", "beianGaNum": "", "name": "小智ESP32", "sm2PublicKey": "",
    }
    return {"code": 0, "msg": "success", "data": config}


# ========================================
# 修改密码接口
# Migrated from Java: LoginController.changePassword @ PUT /user/change-password
# ========================================
@router.put("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """修改密码 对应Java LoginController.changePassword"""
    if not pwd_context.verify(request.oldPassword, current_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")
    current_user.password = pwd_context.hash(request.newPassword)
    db.commit()
    return {"code": 0, "msg": "success", "data": None}


# ========================================
# 找回密码接口
# Migrated from Java: LoginController.retrievePassword @ PUT /user/retrieve-password
# ========================================
@router.put("/retrieve-password")
async def retrieve_password(
    request: PasswordRetrieveRequest,
    db: Session = Depends(get_db)
):
    """找回密码 对应Java LoginController.retrievePassword"""
    user = db.query(User).filter(User.username == request.phone).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该手机号未注册")
    user.password = pwd_context.hash(request.password)
    db.commit()
    return {"code": 0, "msg": "success", "data": None}