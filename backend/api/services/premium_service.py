"""
Premium Service 层
处理 Premium 会员业务逻辑
"""
from typing import Optional, Dict, List
from datetime import datetime
from sqlalchemy.orm import Session
from backend.api.repositories.order_repository import OrderRepository
from backend.api.repositories.user_repository import UserRepository
from backend.api.repositories.setting_repository import SettingRepository


class PremiumService:
    """Premium 业务服务"""
    
    def __init__(
        self,
        order_repo: OrderRepository,
        user_repo: UserRepository,
        setting_repo: SettingRepository
    ):
        self.order_repo = order_repo
        self.user_repo = user_repo
        self.setting_repo = setting_repo
    
    def calculate_amount(self, duration_months: int) -> float:
        """计算 Premium 金额"""
        price_key = f"premium_price_{duration_months}m"
        base_price = self.setting_repo.get_value(price_key, default=10.0)
        return float(base_price)
    
    def validate_duration(self, duration_months: int) -> bool:
        """验证时长是否有效"""
        return duration_months in [3, 6, 12]
    
    def create_premium_order(
        self,
        user_id: int,
        duration_months: int,
        recipient: str,
        unique_suffix: str,
        username: Optional[str] = None
    ) -> Dict:
        """创建 Premium 订单"""
        
        # 验证时长
        if not self.validate_duration(duration_months):
            raise ValueError(f"Invalid duration: {duration_months}")
        
        # 确保用户存在
        user = self.user_repo.get_or_create(user_id, username)
        
        # 计算金额
        base_amount = self.calculate_amount(duration_months)
        suffix_decimal = float(f"0.{unique_suffix}")
        total_amount = base_amount + suffix_decimal
        
        # 获取超时配置
        timeout_minutes = self.setting_repo.get_value("order_timeout_minutes", default=30)
        
        # 创建订单
        order = self.order_repo.create_order(
            user_id=user_id,
            order_type="premium",
            base_amount=base_amount,
            unique_suffix=unique_suffix,
            total_amount=total_amount,
            timeout_minutes=timeout_minutes,
            duration_months=duration_months,
            recipient=recipient
        )
        
        # 获取收款地址
        receive_addr = self.setting_repo.get_value("usdt_trc20_receive_addr", default="")
        
        return {
            "order_id": order.order_id,
            "user_id": user_id,
            "pay_address": receive_addr,
            "pay_amount": total_amount,
            "base_amount": base_amount,
            "unique_suffix": unique_suffix,
            "duration_months": duration_months,
            "recipient": recipient,
            "status": order.status,
            "expires_at": order.expires_at.isoformat(),
        }
    
    def process_payment(self, order_id: str) -> bool:
        """处理支付回调（更新订单状态）"""
        order = self.order_repo.get_by_order_id(order_id)
        
        if not order:
            return False
        
        if order.status != "PENDING":
            return False  # 非待支付状态
        
        # 更新订单状态为已支付
        self.order_repo.update_status(order_id, "PAID")
        return True
    
    def get_order_status(self, order_id: str) -> Optional[Dict]:
        """获取订单状态"""
        order = self.order_repo.get_by_order_id(order_id)
        
        if not order:
            return None
        
        return {
            "order_id": order.order_id,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "expires_at": order.expires_at.isoformat(),
            "is_expired": order.expires_at < datetime.now()
        }
    
    def get_user_premium_orders(
        self,
        user_id: int,
        skip: int = 0,
        limit: int = 20
    ) -> List[Dict]:
        """获取用户的 Premium 订单列表"""
        orders = self.order_repo.get_user_orders(
            user_id=user_id,
            order_type="premium",
            skip=skip,
            limit=limit
        )
        
        return [
            {
                "order_id": order.order_id,
                "amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat(),
                "metadata": order.metadata
            }
            for order in orders
        ]
