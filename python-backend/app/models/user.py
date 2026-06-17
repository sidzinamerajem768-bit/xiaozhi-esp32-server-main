"""
用户ORM模型
对应Java的SysUserEntity.java

映射sys_user表，不新建表，只读取现有数据
"""

from sqlalchemy import Column, BigInteger, String, Integer, DateTime
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class User(Base):
    """
    系统用户表
    对应Java的SysUserEntity.java
    表名: sys_user
    """
    __tablename__ = "sys_user"
    
    # 主键ID - 对应Java的@TableId
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    
    # 用户名（手机号） - 对应Java的username字段
    username = Column(String(50), nullable=False, unique=True, comment="用户名/手机号")
    
    # 密码（BCrypt加密） - 对应Java的password字段
    password = Column(String(100), nullable=False, comment="密码（BCrypt加密）")
    
    # 超级管理员标识 - 对应Java的superAdmin字段
    # 注意：Java字段名是superAdmin，数据库字段名可能是super_admin
    super_admin = Column(Integer, default=0, comment="超级管理员 0：否 1：是")
    
    # 状态 - 对应Java的status字段
    status = Column(Integer, default=1, comment="状态 0：停用 1：正常")
    
    # 创建者 - 对应Java的creator字段（继承自BaseEntity）
    creator = Column(BigInteger, comment="创建者")
    
    # 创建时间 - 对应Java的createDate字段（继承自BaseEntity）
    create_date = Column(DateTime, comment="创建时间")
    
    # 更新者 - 对应Java的updater字段
    updater = Column(BigInteger, comment="更新者")
    
    # 更新时间 - 对应Java的updateDate字段
    update_date = Column(DateTime, comment="更新时间")