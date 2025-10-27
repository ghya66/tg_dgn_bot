"""
Premium 交付服务：检查余额、发送 giftPremiumSubscription、处理失败
"""
import logging
from typing import Dict, List, Optional
from telegram import Bot
from telegram.error import TelegramError
from ..models import Order, OrderStatus

logger = logging.getLogger(__name__)


class DeliveryResult:
    """单个收件人的交付结果"""
    def __init__(self, username: str, success: bool, error: Optional[str] = None, user_id: Optional[int] = None):
        self.username = username
        self.success = success
        self.error = error
        self.user_id = user_id


class PremiumDeliveryService:
    """Premium 会员交付服务"""
    
    def __init__(self, bot: Bot, order_manager):
        """
        初始化交付服务
        
        Args:
            bot: Telegram Bot 实例
            order_manager: 订单管理器实例
        """
        self.bot = bot
        self.order_manager = order_manager
    
    async def check_star_balance(self) -> int:
        """
        检查机器人 XTR (Stars) 余额
        
        Returns:
            可用余额
        """
        try:
            balance = await self.bot.get_star_transactions(limit=1)  # 获取交易记录以推算余额
            # 注意：python-telegram-bot v21 可能没有直接的 getMyStarBalance API
            # 这里使用占位逻辑，实际需要查看最新 API 文档
            logger.info(f"Current XTR balance check: {balance}")
            return 0  # 占位返回，需要替换为实际 API
        except TelegramError as e:
            logger.error(f"Failed to check XTR balance: {e}")
            return 0
    
    async def deliver_premium(self, order: Order) -> Dict[str, DeliveryResult]:
        """
        执行 Premium 交付（幂等）
        
        Args:
            order: 已支付的订单
            
        Returns:
            交付结果字典 {username: DeliveryResult}
        """
        if order.order_type != "premium":
            raise ValueError("Order type must be 'premium'")
        
        if not order.recipients or not order.premium_months:
            raise ValueError("Invalid premium order: missing recipients or months")
        
        results = {}
        success_count = 0
        
        for username in order.recipients:
            try:
                # 1. 尝试通过用户名获取 user_id
                user_id = await self._resolve_username(username)
                
                if not user_id:
                    results[username] = DeliveryResult(
                        username=username,
                        success=False,
                        error="User not found or not bound"
                    )
                    continue
                
                # 2. 调用 giftPremiumSubscription
                await self.bot.send_gift(
                    user_id=user_id,
                    gift_id=self._get_gift_id(order.premium_months),
                    text=f"🎁 您的 {order.premium_months} 个月 Premium 会员已到账！"
                )
                
                results[username] = DeliveryResult(
                    username=username,
                    success=True,
                    user_id=user_id
                )
                success_count += 1
                logger.info(f"Premium delivered to {username} (user_id={user_id})")
                
            except TelegramError as e:
                logger.error(f"Failed to deliver to {username}: {e}")
                results[username] = DeliveryResult(
                    username=username,
                    success=False,
                    error=str(e)
                )
        
        # 3. 更新订单状态
        new_status = self._determine_status(success_count, len(order.recipients))
        await self.order_manager.update_order_status(
            order.order_id,
            new_status,
            delivery_results={
                username: {
                    "success": result.success,
                    "error": result.error,
                    "user_id": result.user_id
                }
                for username, result in results.items()
            }
        )
        
        return results
    
    async def _resolve_username(self, username: str) -> Optional[int]:
        """
        解析用户名为 user_id（通过绑定记录或缓存）
        
        Args:
            username: Telegram 用户名
            
        Returns:
            user_id 或 None
        """
        # TODO: 实现绑定记录查询逻辑
        # 1. 查询 Redis 绑定表: bind:{username} -> user_id
        # 2. 如果未绑定，生成深链接让用户绑定
        return None
    
    def _get_gift_id(self, months: int) -> str:
        """
        根据月数获取礼物 ID
        
        Args:
            months: Premium 月数
            
        Returns:
            礼物 ID
        """
        # TODO: 替换为实际的礼物 ID
        gift_map = {
            3: "premium_3_months",
            6: "premium_6_months",
            12: "premium_12_months"
        }
        return gift_map.get(months, "premium_3_months")
    
    def _determine_status(self, success_count: int, total_count: int) -> OrderStatus:
        """
        根据交付结果确定订单状态
        
        Args:
            success_count: 成功数量
            total_count: 总数量
            
        Returns:
            订单状态
        """
        if success_count == 0:
            return OrderStatus.PAID  # 全部失败，保持已支付状态
        elif success_count == total_count:
            return OrderStatus.DELIVERED  # 全部成功
        else:
            return OrderStatus.PARTIAL  # 部分成功
