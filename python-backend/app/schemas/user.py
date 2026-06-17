"""
用户相关Pydantic Schema
对应Java的LoginDTO.java和TokenDTO.java

用于请求参数验证和响应数据序列化
"""

from pydantic import BaseModel, Field
from typing import Optional


# ========================================
# 登录请求Schema
# 对应Java的LoginDTO.java
# ========================================
class LoginRequest(BaseModel):
    """
    登录请求
    对应Java的LoginDTO.java
    
    注意：Java前端使用SM2加密密码传输，Python后端暂不实现SM2解密
    """
    username: str = Field(..., description="用户名（手机号）")
    password: str = Field(..., description="密码")
    captchaId: Optional[str] = Field(None, description="验证码唯一标识（暂不实现）")
    mobileCaptcha: Optional[str] = Field(None, description="短信验证码（暂不实现）")


# ========================================
# Token响应Schema
# 对应Java的TokenDTO.java
# ========================================
class TokenResponse(BaseModel):
    """
    Token响应
    对应Java的TokenDTO.java
    """
    token: str = Field(..., description="32位MD5字符串")
    expire: int = Field(..., description="过期时间（秒）")
    clientHash: Optional[str] = Field(None, description="客户端指纹")


# ========================================
# 用户信息响应Schema
# 对应Java的UserDetail.java
# ========================================
class UserInfoResponse(BaseModel):
    """
    用户信息响应
    对应Java的UserDetail.java（简化版）
    """
    id: Optional[int] = Field(None, description="用户ID")
    username: Optional[str] = Field(None, description="用户名（手机号）")
    superAdmin: Optional[int] = Field(0, description="超级管理员标识")
    status: Optional[int] = Field(1, description="状态")


# ========================================
# 统一响应格式
# 对应Java的Result.java
# ========================================
class Result(BaseModel):
    """
    统一响应格式
    对应Java的Result.java
    
    Java返回格式:
    {
        "code": 0,
        "msg": "success",
        "data": {...}
    }
    """
    code: int = Field(0, description="响应码，0表示成功")
    msg: str = Field("success", description="响应消息")
    data: Optional[dict] = Field(None, description="响应数据")


class TokenResult(Result):
    """
    Token响应（统一格式）
    """
    data: Optional[TokenResponse] = Field(None, description="Token数据")


class UserInfoResult(Result):
    """
    用户信息响应（统一格式）
    """
    data: Optional[UserInfoResponse] = Field(None, description="用户信息数据")


# ========================================
# 注册请求Schema
# ========================================
class RegisterRequest(BaseModel):
    """
    注册请求
    """
    username: str = Field(..., description="用户名（手机号）")
    password: str = Field(..., description="密码")
    mobileCaptcha: Optional[str] = Field(None, description="短信验证码")


# ========================================
# 修改密码请求Schema
# ========================================
class PasswordChangeRequest(BaseModel):
    """
    修改密码请求
    """
    oldPassword: str = Field(..., description="旧密码")
    newPassword: str = Field(..., description="新密码")


# ========================================
# 找回密码请求Schema
# ========================================
class PasswordRetrieveRequest(BaseModel):
    """
    找回密码请求
    """
    phone: str = Field(..., description="手机号")
    password: str = Field(..., description="新密码")
    code: Optional[str] = Field(None, description="短信验证码")