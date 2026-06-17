"""
依赖注入模块
对应Java的SecurityUser.java和Oauth2Realm.java

提供get_current_user依赖，用于保护需要认证的接口
"""

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.models.user import User
from app.models.user_token import UserToken


def get_current_user(
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> User:
    """
    获取当前用户依赖
    对应Java的SecurityUser.getUser()
    
    流程：
    1. 从Authorization头提取token
    2. 查询sys_user_token表验证token
    3. 检查token是否过期
    4. 返回User对象
    
    Args:
        authorization: Authorization请求头，格式: Bearer {token}
        db: 数据库会话
        
    Returns:
        User: 当前用户对象
        
    Raises:
        HTTPException: 401 - token无效或过期
    """
    # 检查Authorization头是否存在
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 提取token（格式: Bearer {token}）
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="认证格式错误",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证格式错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询token记录
    # 对应Java的Oauth2Realm.doGetAuthenticationInfo()
    user_token = db.query(UserToken).filter(UserToken.token == token).first()
    
    if not user_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token无效",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查token是否过期
    # 对应Java的SysUserTokenServiceImpl.getUserByToken()
    if user_token.expire_date < datetime.now():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token已过期",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 查询用户信息
    user = db.query(User).filter(User.id == user_token.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户不存在",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # 检查用户状态
    if user.status != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户已停用",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return user