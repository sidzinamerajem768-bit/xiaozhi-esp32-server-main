"""
配置管理模块
对应Java的application.yml配置读取

使用pydantic-settings从.env文件读取配置
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    应用配置类
    对应Java的application.yml配置结构
    """
    
    # 数据库配置 - 对应Java的spring.datasource.druid
    database_url: str = "mysql+pymysql://root:password@127.0.0.1:3306/xiaozhi_esp32_server"
    
    # 认证配置 - 对应Java的TokenGenerator和SysUserTokenServiceImpl
    secret_key: str = "your-secret-key-at-least-32-characters-long"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 720  # 12小时，对应Java的EXPIRE=3600*12
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    """
    获取配置实例（单例模式）
    对应Java的@ConfigurationProperties单例注入
    """
    return Settings()