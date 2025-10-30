"""
订单 Repository
提供订单数据访问接口
"""
from typing import Optional, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import and_
from backend.api.repositories.base_repository import BaseRepository


class DepositOrder:
    """临时订单模型（从 src.database 导入会在后面集成）"""
    pass


class OrderRepository(BaseRepository):
    """订单 Repository"""
    
    def __init__(self, session: Session):
        # 动态导入避免循环依赖
        from src.database import DepositOrder as DBDepositOrder
        super().__init__(DBDepositOrder, session)
    
    def get_by_order_id(self, order_id: str) -> Optional[any]:
        """根据订单ID获取订单"""
        return self.session.query(self.model).filter_by(order_id=order_id).first()
    
    def get_by_suffix(self, suffix: str) -> Optional[any]:
        """根据唯一后缀获取订单"""
        return self.session.query(self.model).filter_by(unique_suffix=int(suffix)).first()
    
    def get_user_orders(
        self,
        user_id: int,
        status: Optional[str] = None,
        order_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 20
    ) -> List[any]:
        """获取用户订单列表"""
        query = self.session.query(self.model).filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status.upper())
        
        # Note: DepositOrder 表没有 order_type 字段，这里忽略过滤
        # 实际应该通过 order_id 前缀判断，或者扩展数据库字段
        
        return query.order_by(self.model.created_at.desc()).offset(skip).limit(limit).all()
    
    def create_order(
        self,
        user_id: int,
        order_type: str,
        base_amount: float,
        unique_suffix: str,
        total_amount: float,
        timeout_minutes: int = 30,
        **metadata
    ) -> any:
        """创建订单"""
        from src.database import DepositOrder as DBDepositOrder
        import uuid
        
        # 生成订单ID
        order_id = f"{order_type.upper()[:4]}{uuid.uuid4().hex[:8]}"
        
        # 计算微USDT金额
        amount_micro_usdt = int(total_amount * 1_000_000)
        
        order = DBDepositOrder(
            order_id=order_id,
            user_id=user_id,
            base_amount=base_amount,
            unique_suffix=int(unique_suffix),
            total_amount=total_amount,
            amount_micro_usdt=amount_micro_usdt,
            status="PENDING",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(minutes=timeout_minutes)
        )
        
        # 将 metadata 存储到 order 对象属性（非数据库字段）
        order.metadata = metadata
        
        self.session.add(order)
        self.session.commit()
        self.session.refresh(order)
        return order
    
    def update_status(self, order_id: str, status: str) -> Optional[any]:
        """更新订单状态"""
        order = self.get_by_order_id(order_id)
        if not order:
            return None
        
        order.status = status
        order.updated_at = datetime.now()
        self.session.commit()
        self.session.refresh(order)
        return order
    
    def get_pending_orders(self, before: datetime) -> List[any]:
        """获取待支付订单（用于过期检查）"""
        return self.session.query(self.model).filter(
            and_(
                self.model.status == "PENDING",
                self.model.expires_at < before
            )
        ).all()
    
    def get_paid_orders_by_date(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[any]:
        """获取指定日期范围的已支付订单"""
        return self.session.query(self.model).filter(
            and_(
                self.model.status == "PAID",
                self.model.created_at >= start_date,
                self.model.created_at <= end_date
            )
        ).all()
    
    def count_user_orders(self, user_id: int, status: Optional[str] = None) -> int:
        """统计用户订单数"""
        query = self.session.query(self.model).filter_by(user_id=user_id)
        
        if status:
            query = query.filter_by(status=status)
        
        return query.count()
    
    def find_by_filters(
        self,
        filters: dict,
        limit: int = 20,
        offset: int = 0
    ) -> List[any]:
        """根据过滤条件查询订单（管理员使用）"""
        query = self.session.query(self.model)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model, key):
                # 对于枚举类型，取其 value
                if hasattr(value, 'value'):
                    query = query.filter(getattr(self.model, key) == value.value)
                else:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.order_by(self.model.created_at.desc()).offset(offset).limit(limit).all()
    
    def count_by_filters(self, filters: dict) -> int:
        """统计符合条件的订单数（管理员使用）"""
        query = self.session.query(self.model)
        
        # 应用过滤条件
        for key, value in filters.items():
            if hasattr(self.model, key):
                # 对于枚举类型，取其 value
                if hasattr(value, 'value'):
                    query = query.filter(getattr(self.model, key) == value.value)
                else:
                    query = query.filter(getattr(self.model, key) == value)
        
        return query.count()
    
    def find_by_order_id(self, order_id: str) -> Optional[any]:
        """根据订单ID查询订单（别名方法）"""
        return self.get_by_order_id(order_id)
