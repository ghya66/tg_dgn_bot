"""
支付处理模块
包含金额匹配、订单状态管理等核心逻辑
"""
import asyncio
from typing import Optional, List
import redis.asyncio as redis
from datetime import datetime, timedelta
import json

from .models import Order, OrderStatus, PaymentCallback
from .suffix_generator import suffix_generator
from .config import settings


class PaymentProcessor:
    """支付处理器"""
    
    def __init__(self):
        self.redis_client = None
    
    async def connect(self):
        """连接Redis"""
        if not self.redis_client:
            self.redis_client = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                db=settings.redis_db,
                decode_responses=True
            )
    
    async def disconnect(self):
        """断开Redis连接"""
        if self.redis_client:
            await self.redis_client.close()
    
    def calculate_total_amount(self, base_amount: float, suffix: int) -> float:
        """
        计算总金额 = 基础金额 + 唯一后缀/1000
        
        Args:
            base_amount: 基础金额
            suffix: 唯一后缀 (1-999)
            
        Returns:
            总金额
        """
        return base_amount + (suffix / 1000.0)
    
    def amounts_match(self, amount1: float, amount2: float) -> bool:
        """
        使用整数化方式比较金额，避免浮点误差
        
        Args:
            amount1: 金额1
            amount2: 金额2
            
        Returns:
            是否匹配
        """
        # 转换为微USDT (乘以10^6)
        micro_amount1 = int(round(amount1 * 1000000))
        micro_amount2 = int(round(amount2 * 1000000))
        
        return micro_amount1 == micro_amount2
    
    async def create_order(self, user_id: int, base_amount: float) -> Optional[Order]:
        """
        创建新订单
        
        Args:
            user_id: 用户ID
            base_amount: 基础金额
            
        Returns:
            创建的订单或None（如果创建失败）
        """
        await self.connect()
        
        # 分配唯一后缀
        order_id_temp = f"temp_{user_id}_{int(datetime.now().timestamp())}"
        suffix = await suffix_generator.allocate_suffix(order_id_temp)
        
        if suffix is None:
            return None
        
        # 计算总金额
        total_amount = self.calculate_total_amount(base_amount, suffix)
        
        # 创建订单
        order = Order(
            base_amount=base_amount,
            unique_suffix=suffix,
            total_amount=total_amount,
            user_id=user_id,
            expires_at=datetime.now() + timedelta(minutes=settings.order_timeout_minutes)
        )
        
        # 更新后缀绑定到真实订单ID
        await suffix_generator.release_suffix(suffix, order_id_temp)
        if not await suffix_generator._reserve_suffix(suffix, order.order_id):
            # 如果重新绑定失败，说明后缀被占用了，重试
            return await self.create_order(user_id, base_amount)
        
        # 保存订单到Redis
        await self._save_order(order)
        
        return order
    
    async def _save_order(self, order: Order) -> bool:
        """保存订单到Redis"""
        await self.connect()
        
        order_key = f"order:{order.order_id}"
        amount_key = f"amount:{order.amount_in_micro_usdt}"
        
        # 序列化订单数据
        order_data = order.dict()
        order_data["created_at"] = order.created_at.isoformat()
        order_data["updated_at"] = order.updated_at.isoformat()
        order_data["expires_at"] = order.expires_at.isoformat()
        
        pipe = self.redis_client.pipeline()
        
        # 保存订单数据
        pipe.set(
            order_key,
            json.dumps(order_data),
            ex=settings.order_timeout_minutes * 60 + 300  # 额外5分钟缓冲
        )
        
        # 创建金额到订单ID的映射
        pipe.set(
            amount_key,
            order.order_id,
            ex=settings.order_timeout_minutes * 60 + 300
        )
        
        results = await pipe.execute()
        return all(results)
    
    async def get_order(self, order_id: str) -> Optional[Order]:
        """根据订单ID获取订单"""
        await self.connect()
        
        order_key = f"order:{order_id}"
        order_data = await self.redis_client.get(order_key)
        
        if not order_data:
            return None
        
        try:
            data = json.loads(order_data)
            # 反序列化时间字段
            data["created_at"] = datetime.fromisoformat(data["created_at"])
            data["updated_at"] = datetime.fromisoformat(data["updated_at"])
            data["expires_at"] = datetime.fromisoformat(data["expires_at"])
            
            return Order(**data)
        except (json.JSONDecodeError, ValueError, TypeError):
            return None
    
    async def find_order_by_amount(self, amount: float) -> Optional[Order]:
        """根据金额查找订单"""
        await self.connect()
        
        # 转换为微USDT
        micro_amount = int(round(amount * 1000000))
        amount_key = f"amount:{micro_amount}"
        
        order_id = await self.redis_client.get(amount_key)
        if not order_id:
            return None
        
        return await self.get_order(order_id)
    
    async def update_order_status(self, order_id: str, new_status: OrderStatus) -> bool:
        """
        幂等更新订单状态
        
        Args:
            order_id: 订单ID
            new_status: 新状态
            
        Returns:
            是否更新成功
        """
        await self.connect()
        
        order = await self.get_order(order_id)
        if not order:
            return False
        
        # 状态转换验证
        if not self._is_valid_status_transition(order.status, new_status):
            return False
        
        # 更新状态
        order.update_status(new_status)
        
        # 如果订单完成或取消，释放唯一后缀
        if new_status in [OrderStatus.PAID, OrderStatus.CANCELLED, OrderStatus.EXPIRED]:
            await suffix_generator.release_suffix(order.unique_suffix, order_id)
        
        # 保存更新后的订单
        return await self._save_order(order)
    
    def _is_valid_status_transition(self, current: OrderStatus, new: OrderStatus) -> bool:
        """验证状态转换是否有效"""
        valid_transitions = {
            OrderStatus.PENDING: [OrderStatus.PAID, OrderStatus.EXPIRED, OrderStatus.CANCELLED],
            OrderStatus.PAID: [],  # 已支付状态不可转换
            OrderStatus.EXPIRED: [],  # 已过期状态不可转换
            OrderStatus.CANCELLED: []  # 已取消状态不可转换
        }
        
        return new in valid_transitions.get(current, [])
    
    async def process_payment_callback(self, callback: PaymentCallback) -> bool:
        """
        处理支付回调
        
        Args:
            callback: 支付回调数据
            
        Returns:
            是否处理成功
        """
        # 查找匹配的订单
        order = await self.find_order_by_amount(callback.amount)
        
        if not order:
            # 没有找到匹配的订单
            return False
        
        # 验证订单ID是否匹配
        if order.order_id != callback.order_id:
            return False
        
        # 验证金额是否精确匹配
        if not self.amounts_match(order.total_amount, callback.amount):
            return False
        
        # 检查订单是否已过期
        if order.is_expired:
            await self.update_order_status(order.order_id, OrderStatus.EXPIRED)
            return False
        
        # 更新订单状态为已支付（幂等操作）
        return await self.update_order_status(order.order_id, OrderStatus.PAID)
    
    async def cleanup_expired_orders(self) -> int:
        """清理过期订单"""
        await self.connect()
        
        # 获取所有订单key
        pattern = "order:*"
        keys = await self.redis_client.keys(pattern)
        
        expired_count = 0
        
        for key in keys:
            order_id = key.split(":", 1)[1]
            order = await self.get_order(order_id)
            
            if order and order.is_expired and order.status == OrderStatus.PENDING:
                await self.update_order_status(order_id, OrderStatus.EXPIRED)
                expired_count += 1
        
        return expired_count
    
    async def get_order_statistics(self) -> dict:
        """获取订单统计信息"""
        await self.connect()
        
        pattern = "order:*"
        keys = await self.redis_client.keys(pattern)
        
        stats = {
            "total_orders": 0,
            "pending_orders": 0,
            "paid_orders": 0,
            "expired_orders": 0,
            "cancelled_orders": 0,
            "active_suffixes": 0
        }
        
        for key in keys:
            order_id = key.split(":", 1)[1]
            order = await self.get_order(order_id)
            
            if order:
                stats["total_orders"] += 1
                if order.status == OrderStatus.PENDING:
                    stats["pending_orders"] += 1
                elif order.status == OrderStatus.PAID:
                    stats["paid_orders"] += 1
                elif order.status == OrderStatus.EXPIRED:
                    stats["expired_orders"] += 1
                elif order.status == OrderStatus.CANCELLED:
                    stats["cancelled_orders"] += 1
        
        # 获取活跃后缀数量
        stats["active_suffixes"] = await suffix_generator.cleanup_expired_suffixes()
        
        return stats


# 全局实例
payment_processor = PaymentProcessor()