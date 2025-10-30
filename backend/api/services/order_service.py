"""
Order Service 层
处理通用订单业务逻辑
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.api.repositories.order_repository import OrderRepository
from backend.api.repositories.setting_repository import SettingRepository


class OrderService:
    """订单业务服务"""
    
    def __init__(
        self,
        order_repo: OrderRepository,
        setting_repo: SettingRepository
    ):
        self.order_repo = order_repo
        self.setting_repo = setting_repo
    
    def get_order(self, order_id: str) -> Optional[Dict]:
        """获取订单详情"""
        order = self.order_repo.get_by_order_id(order_id)
        
        if not order:
            return None
        
        return {
            "order_id": order.order_id,
            "user_id": order.user_id,
            "order_type": order.order_type,
            "base_amount": order.base_amount,
            "total_amount": order.total_amount,
            "status": order.status,
            "created_at": order.created_at.isoformat(),
            "expires_at": order.expires_at.isoformat(),
            "is_expired": order.expires_at < datetime.now(),
            "metadata": order.metadata
        }
    
    def get_order_by_suffix(self, suffix: str) -> Optional[Dict]:
        """根据唯一后缀获取订单"""
        order = self.order_repo.get_by_suffix(suffix)
        
        if not order:
            return None
        
        return self.get_order(order.order_id)
    
    def cancel_order(self, order_id: str) -> bool:
        """取消订单"""
        order = self.order_repo.get_by_order_id(order_id)
        
        if not order:
            return False
        
        if order.status != "pending":
            return False  # 只能取消待支付订单
        
        self.order_repo.update_status(order_id, "cancelled")
        return True
    
    def expire_pending_orders(self) -> int:
        """过期待支付订单（定时任务调用）"""
        now = datetime.now()
        pending_orders = self.order_repo.get_pending_orders(before=now)
        
        expired_count = 0
        for order in pending_orders:
            self.order_repo.update_status(order.order_id, "expired")
            expired_count += 1
        
        return expired_count
    
    def get_statistics(
        self,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict:
        """获取订单统计"""
        
        # 默认统计今天
        if not start_date:
            start_date = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        
        if not end_date:
            end_date = datetime.now()
        
        paid_orders = self.order_repo.get_paid_orders_by_date(start_date, end_date)
        
        total_amount = sum(order.total_amount for order in paid_orders)
        
        # 按类型统计
        type_stats = {}
        for order in paid_orders:
            order_type = order.order_type
            if order_type not in type_stats:
                type_stats[order_type] = {"count": 0, "amount": 0.0}
            
            type_stats[order_type]["count"] += 1
            type_stats[order_type]["amount"] += order.total_amount
        
        return {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "total_orders": len(paid_orders),
            "total_amount": total_amount,
            "by_type": type_stats
        }
    
    def get_recent_orders(
        self,
        limit: int = 50,
        order_type: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict]:
        """获取最近订单列表（管理后台使用）"""
        # 这里简化实现，实际可以扩展更多过滤条件
        orders = self.order_repo.get_all(skip=0, limit=limit)
        
        result = []
        for order in orders:
            # 过滤条件
            if order_type and order.order_type != order_type:
                continue
            if status and order.status != status:
                continue
            
            result.append({
                "order_id": order.order_id,
                "user_id": order.user_id,
                "order_type": order.order_type,
                "amount": order.total_amount,
                "status": order.status,
                "created_at": order.created_at.isoformat()
            })
        
        return result
