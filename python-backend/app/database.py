"""
数据库连接模块
对应Java的MyBatis Plus配置和Druid连接池

使用SQLAlchemy 2.0语法连接MySQL数据库
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Generator

from app.config import get_settings


# 获取配置
settings = get_settings()

# 创建数据库引擎
# 对应Java的spring.datasource.druid配置
# pool_pre_ping=True 对应Java的test-while-idle: true
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,  # 连接池健康检查，对应Java的druid.test-while-idle
    pool_size=10,        # 连接池大小，对应Java的druid.initial-size: 10
    max_overflow=20,     # 最大溢出连接，对应Java的druid.max-active: 100 (这里保守设置)
    echo=False,          # 不打印SQL语句，生产环境建议关闭
)

# 创建会话工厂
# 对应Java的SqlSession
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    获取数据库会话的依赖注入函数
    对应Java的@Autowired注入SqlSession
    
    使用方式:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            users = db.query(User).all()
            return users
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()