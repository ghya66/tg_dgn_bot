from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.api.config import settings

# ============================================================================
# Engine 和 SessionLocal 配置
# ============================================================================

# 创建 engine（生产环境使用连接池）
engine = create_engine(
    settings.database_url,
    echo=settings.is_development,  # 开发环境输出 SQL
    pool_pre_ping=True,  # 连接前检查有效性
    pool_size=10,  # 连接池大小
    max_overflow=20,  # 最大溢出连接
)

# Session 工厂
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ============================================================================
# 依赖注入函数
# ============================================================================

def get_db() -> Generator[Session, None, None]:
    """
    FastAPI 依赖注入 - 获取数据库 session
    
    Usage:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
