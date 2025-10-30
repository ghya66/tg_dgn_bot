"""
用户 Repository
提供用户数据访问接口
"""
from typing import Optional
from sqlalchemy.orm import Session
from backend.api.repositories.base_repository import BaseRepository


class UserRepository(BaseRepository):
    """用户 Repository"""
    
    def __init__(self, session: Session):
        # 动态导入避免循环依赖
        from src.database import User as DBUser
        super().__init__(DBUser, session)
    
    def get_by_user_id(self, user_id: int) -> Optional[any]:
        """根据Telegram用户ID获取用户"""
        return self.session.query(self.model).filter_by(user_id=user_id).first()
    
    def get_or_create(self, user_id: int, username: Optional[str] = None) -> any:
        """获取或创建用户"""
        user = self.get_by_user_id(user_id)
        
        if not user:
            from src.database import User as DBUser
            user = DBUser(user_id=user_id, username=username, balance_micro_usdt=0)
            self.session.add(user)
            self.session.commit()
            self.session.refresh(user)
        
        return user
    
    def update_balance(self, user_id: int, amount: float) -> Optional[any]:
        """更新用户余额（增加）"""
        user = self.get_by_user_id(user_id)
        if not user:
            return None
        
        user.balance_micro_usdt += int(amount * 1_000_000)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def debit_balance(self, user_id: int, amount: float) -> Optional[any]:
        """扣除用户余额"""
        user = self.get_by_user_id(user_id)
        if not user:
            return None
        
        current_balance = user.get_balance()
        if current_balance < amount:
            raise ValueError(f"Insufficient balance: {current_balance} < {amount}")
        
        user.balance_micro_usdt -= int(amount * 1_000_000)
        self.session.commit()
        self.session.refresh(user)
        return user
    
    def get_balance(self, user_id: int) -> float:
        """获取用户余额"""
        user = self.get_by_user_id(user_id)
        return user.get_balance() if user else 0.0
