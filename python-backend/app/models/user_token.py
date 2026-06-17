"""
用户Token ORM模型
对应Java的SysUserTokenEntity.java

映射sys_user_token表，用于存储用户登录token
"""

from sqlalchemy import Column, BigInteger, String, DateTime
from sqlalchemy.orm import declarative_base

from app.models.user import Base


class UserToken(Base):
    """
    系统用户Token表
    对应Java的SysUserTokenEntity.java
    表名: sys_user_token
    """
    __tablename__ = "sys_user_token"
    
    # 主键ID - 对应Java的@TableId
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 用户ID - 对应Java的userId字段
    user_id = Column(BigInteger, nullable=False, index=True, comment="用户ID")
    
    # Token（32位MD5字符串） - 对应Java的token字段
    token = Column(String(32), nullable=False, unique=True, comment="用户token")
    
    # 过期时间 - 对应Java的expireDate字段
    expire_date = Column(DateTime, nullable=False, comment="过期时间")
    
    # 更新时间 - 对应Java的updateDate字段
    update_date = Column(DateTime, comment="更新时间")
    
    # 创建时间 - 对应Java的createDate字段
    create_date = Column(DateTime, comment="创建时间")