"""
Premium 会员交付任务
使用 tenacity 重试机制处理 Telegram API 调用失败
"""
import structlog
import logging
from typing import Dict, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from sqlalchemy.orm import Session
from backend.api.config import settings
from backend.api.repositories.order_repository import OrderRepository
from src.database import SessionLocal

logger = structlog.get_logger(__name__)
logging_logger = logging.getLogger(__name__)


class PremiumDeliveryError(Exception):
    """Premium 交付异常"""
    pass


class TelegramAPIError(Exception):
    """Telegram API 调用异常"""
    pass


@retry(
    stop=stop_after_attempt(settings.arq_max_tries),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    retry=retry_if_exception_type(TelegramAPIError),
    before_sleep=before_sleep_log(logging_logger, logging.INFO),
    reraise=True
)
async def _call_telegram_gift_premium(
    recipient: str,
    duration_months: int,
    bot_token: str
) -> Dict:
    """
    调用 Telegram API 赠送 Premium
    带指数退避重试机制
    
    Args:
        recipient: 收件人 username
        duration_months: 时长（月）
        bot_token: Bot Token
    
    Returns:
        API 响应结果
    
    Raises:
        TelegramAPIError: API 调用失败
    """
    import httpx
    
    # TODO: 实际调用 Telegram giftPremiumSubscription API
    # 这里使用 mock 实现
    
    logger.info(
        "calling_telegram_api",
        recipient=recipient,
        duration_months=duration_months
    )
    
    # Mock: 模拟 API 调用
    # 生产环境需要替换为真实 API 调用
    try:
        async with httpx.AsyncClient() as client:
            # 示例：Telegram Bot API 调用
            # response = await client.post(
            #     f"https://api.telegram.org/bot{bot_token}/giftPremiumSubscription",
            #     json={
            #         "user_id": recipient,
            #         "premium_subscription_months": duration_months
            #     }
            # )
            # response.raise_for_status()
            # return response.json()
            
            # Mock 返回成功
            return {
                "ok": True,
                "result": {
                    "user_id": recipient,
                    "duration_months": duration_months,
                    "delivered_at": "2025-10-29T12:00:00Z"
                }
            }
    except httpx.HTTPError as e:
        logger.error("telegram_api_error", error=str(e), recipient=recipient)
        raise TelegramAPIError(f"Telegram API call failed: {e}")


async def deliver_premium_task(ctx: Dict, order_id: str) -> Dict:
    """
    Premium 交付任务
    
    Args:
        ctx: arq 上下文
        order_id: 订单ID
    
    Returns:
        result: 交付结果
    """
    logger.info("premium_delivery_started", order_id=order_id)
    
    db: Session = SessionLocal()
    try:
        # 1. 查询订单
        order_repo = OrderRepository(db)
        order = order_repo.get_by_order_id(order_id)
        
        if not order:
            logger.error("order_not_found", order_id=order_id)
            raise PremiumDeliveryError(f"Order not found: {order_id}")
        
        if order.status != "PAID":
            logger.warning("order_not_paid", order_id=order_id, status=order.status)
            return {
                "success": False,
                "reason": f"Order status is {order.status}, expected PAID"
            }
        
        # 2. 获取订单元数据
        recipient = getattr(order, 'metadata', {}).get('recipient')
        duration_months = getattr(order, 'metadata', {}).get('duration_months', 3)
        
        if not recipient:
            logger.error("recipient_missing", order_id=order_id)
            raise PremiumDeliveryError(f"Recipient not found in order metadata")
        
        # 3. 调用 Telegram API（带重试）
        try:
            result = await _call_telegram_gift_premium(
                recipient=recipient,
                duration_months=duration_months,
                bot_token=settings.bot_token
            )
            
            # 4. 更新订单状态为已交付
            order_repo.update_status(order_id, "DELIVERED")
            db.commit()  # 显式提交事务
            
            logger.info(
                "premium_delivered",
                order_id=order_id,
                recipient=recipient,
                duration_months=duration_months
            )
            
            return {
                "success": True,
                "order_id": order_id,
                "recipient": recipient,
                "duration_months": duration_months,
                "telegram_result": result
            }
        
        except TelegramAPIError as e:
            # 重试耗尽后标记为部分完成
            order_repo.update_status(order_id, "PARTIAL")
            db.commit()  # 提交状态更新
            logger.error(
                "premium_delivery_failed",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            raise
    
    except Exception as e:
        db.rollback()  # 回滚事务
        logger.error(
            "deliver_task_error",
            order_id=order_id,
            error=str(e),
            exc_info=True
        )
        raise
    finally:
        db.close()


async def batch_deliver_premiums(ctx: Dict, order_ids: list[str]) -> Dict:
    """
    批量交付 Premium
    
    Args:
        ctx: arq 上下文
        order_ids: 订单ID列表
    
    Returns:
        result: 批量交付结果
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    results = []
    
    for order_id in order_ids:
        try:
            result = await deliver_premium_task(ctx, order_id)
            results.append({"order_id": order_id, "result": result})
        except (PremiumDeliveryError, TelegramAPIError, SQLAlchemyError) as e:
            logger.error(
                "task_failed",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            results.append({"order_id": order_id, "error": str(e)})
        except Exception as e:
            # 记录未预期的异常并继续
            logger.critical(
                "unexpected_error",
                order_id=order_id,
                error=str(e),
                exc_info=True
            )
            results.append({"order_id": order_id, "error": f"Unexpected: {str(e)}"})
    
    success_count = sum(1 for r in results if r.get("result", {}).get("success"))
    
    logger.info(
        "batch_delivery_completed",
        total=len(order_ids),
        success=success_count,
        failed=len(order_ids) - success_count
    )
    
    return {
        "total": len(order_ids),
        "success": success_count,
        "failed": len(order_ids) - success_count,
        "results": results
    }
