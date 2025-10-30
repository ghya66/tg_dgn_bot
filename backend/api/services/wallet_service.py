"""
Wallet Service 层
处理钱包业务逻辑
"""
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.api.repositories.order_repository import OrderRepository
from backend.api.repositories.user_repository import UserRepository
from backend.api.repositories.setting_repository import SettingRepository


class WalletService:
    """钱包业务服务"""
    
    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        setting_repo: SettingRepository
    ):
        self.order_repo = order_repo
        self.user_repo = user_repo
        self.setting_repo = setting_repo
    
    def get_balance(self, user_id: int) -> float:
        """获取用户余额"""
        return self.user_repo.get_balance(user_id)
    
    def create_deposit_order(
        self,
        user_id: int,
        amount: float,
        unique_suffix: str,
        username: Optional[str] = None
    ) -> Dict:
        """创建充值订单"""
        
        # 确保用户存在
        user = self.user_repo.get_or_create(user_id, username)
        
        # 计算总金额（基础金额 + 唯一后缀）
        suffix_decimal = float(f"0.{unique_suffix}")
        total_amount = amount + suffix_decimal
        
        # 获取超时配置
        timeout_minutes = self.setting_repo.get_value("order_timeout_minutes", default=30)
        
        # 创建订单
        order = self.order_repo.create_order(
            user_id=user_id,
            order_type="deposit",
            base_amount=amount,
            unique_suffix=unique_suffix,
            total_amount=total_amount,
            timeout_minutes=timeout_minutes
        )
        
        # 获取收款地址
        receive_addr = self.setting_repo.get_value("usdt_trc20_receive_addr", default="")
        
        return {
            "order_id": order.order_id,
            "user_id": user_id,
            "pay_address": receive_addr,
            "pay_amount": total_amount,
            "base_amount": amount,
            "unique_suffix": unique_suffix,
            "status": order.status,
            "expires_at": order.expires_at.isoformat(),
        }
    
    def process_deposit(self, order_id: str) -> bool:
        """处理充值回调"""
        order = self.order_repo.get_by_order_id(order_id)
        
        if not order:
            return False
        
        if order.status != "pending":
            return False  # 非待支付状态
        
        # 更新订单状态
        self.order_repo.update_status(order_id, "paid")
        
        # 增加用户余额
        self.user_repo.update_balance(order.user_id, order.base_amount)
        
        return True
    
    def debit(self, user_id: int, amount: float, reason: str = "") -> bool:
        """扣除余额"""
        try:
            self.user_repo.debit_balance(user_id, amount)
            
            # TODO: 记录扣费记录到 debit_records 表
            # 这里可以扩展记录扣费历史
            
            return True
        except ValueError:
            # 余额不足
            return False
    
    def get_deposit_history(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict]:
        """获取充值历史"""
        orders = self.order_repo.get_user_orders(
            user_id=user_id,
            order_type="deposit",
            status="paid",  # 只返回已支付的
            skip=skip,
            limit=limit
        )
        
        return [
            {
                "order_id": order.order_id,
                "amount": order.base_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
            }
            for order in orders
        ]
    
    def get_user_summary(self, user_id: int) -> Dict:
        """获取用户钱包摘要"""
        user = self.user_repo.get_by_user_id(user_id)
        
        if not user:
            return {
                "user_id": user_id,
                "balance": 0.0,
                "total_deposits": 0,
                "total_orders": 0
            }
        
        total_deposits = self.order_repo.count_user_orders(user_id, status="paid")
        total_orders = self.order_repo.count_user_orders(user_id)
        
        return {
            "user_id": user_id,
            "balance": user.balance,
            "total_deposits": total_deposits,
            "total_orders": total_orders
        }
