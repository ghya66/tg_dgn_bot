"""
数据库配置和模型定义
使用 SQLAlchemy + SQLite
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from datetime import datetime
from typing import Optional
import os

# 数据库配置
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tg_bot.db")

# 创建引擎
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 基础模型
Base = declarative_base()


class User(Base):
    """用户表"""
    __tablename__ = "users"
    
    user_id = Column(Integer, primary_key=True, index=True)
    username = Column(String, nullable=True)
    balance_micro_usdt = Column(Integer, default=0, nullable=False)  # 微USDT (×10^6)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    def get_balance(self) -> float:
        """获取余额（USDT）"""
        return self.balance_micro_usdt / 1_000_000
    
    def set_balance(self, amount: float):
        """设置余额（USDT）"""
        self.balance_micro_usdt = int(amount * 1_000_000)


class DepositOrder(Base):
    """充值订单表"""
    __tablename__ = "deposit_orders"
    
    order_id = Column(String, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    base_amount = Column(Float, nullable=False)  # 基础金额
    unique_suffix = Column(Integer, nullable=False)  # 唯一后缀 (1-999)
    total_amount = Column(Float, nullable=False)  # 总金额
    amount_micro_usdt = Column(Integer, nullable=False)  # 微USDT金额
    status = Column(String, default="PENDING", nullable=False)  # PENDING, PAID, EXPIRED
    tx_hash = Column(String, nullable=True)  # 交易哈希
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    paid_at = Column(DateTime, nullable=True)  # 支付时间
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    
    # 创建索引
    __table_args__ = (
        Index('idx_user_status', 'user_id', 'status'),
        Index('idx_suffix', 'unique_suffix'),
    )


class DebitRecord(Base):
    """扣费记录表"""
    __tablename__ = "debit_records"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, nullable=False, index=True)
    amount_micro_usdt = Column(Integer, nullable=False)  # 扣费金额（微USDT）
    order_type = Column(String, nullable=False)  # 订单类型（premium/energy等）
    related_order_id = Column(String, nullable=True)  # 关联订单ID
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    
    def get_amount(self) -> float:
        """获取扣费金额（USDT）"""
        return self.amount_micro_usdt / 1_000_000


class SuffixAllocation(Base):
    """后缀分配记录表（持久化）"""
    __tablename__ = "suffix_allocations"
    
    suffix = Column(Integer, primary_key=True)  # 1-999
    order_id = Column(String, nullable=True, index=True)  # 当前分配的订单ID
    allocated_at = Column(DateTime, nullable=True)  # 分配时间
    expires_at = Column(DateTime, nullable=True)  # 过期时间


class AddressQueryLog(Base):
    """地址查询限频记录表"""
    __tablename__ = "address_query_logs"
    
    user_id = Column(Integer, primary_key=True, index=True)
    last_query_at = Column(DateTime, nullable=False)  # 最后查询时间
    query_count = Column(Integer, default=1, nullable=False)  # 查询次数


def init_db():
    """初始化数据库（创建所有表）"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """获取数据库会话"""
    db = SessionLocal()
    try:
        return db
    finally:
        pass  # 由调用者负责关闭


def close_db(db: Session):
    """关闭数据库会话"""
    db.close()
