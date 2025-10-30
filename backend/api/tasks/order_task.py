"""
订单管理任务
处理订单过期检查等定时任务
"""
import structlog
from typing import Dict
from datetime import datetime
from sqlalchemy.orm import Session
from backend.api.repositories.order_repository import OrderRepository
from src.database import SessionLocal

logger = structlog.get_logger(__name__)


async def expire_pending_orders_task(ctx: Dict) -> Dict:
    """
    订单过期检查任务
    每 5 分钟执行一次，将过期的待支付订单标记为已过期
    
    Args:
        ctx: arq 上下文
    
    Returns:
        result: 过期订单统计
    """
    from sqlalchemy.exc import SQLAlchemyError
    
    logger.info("expire_orders_task_started")
    
    db: Session = SessionLocal()
    try:
        order_repo = OrderRepository(db)
        
        # 查询所有过期的待支付订单
        now = datetime.now()
        pending_orders = order_repo.get_pending_orders(before=now)
        
        expired_count = 0
        for order in pending_orders:
            try:
                order_repo.update_status(order.order_id, "EXPIRED")
                expired_count += 1
                
                logger.info(
                    "order_expired",
                    order_id=order.order_id,
                    user_id=order.user_id,
                    created_at=order.created_at.isoformat(),
                    expires_at=order.expires_at.isoformat()
                )
            except SQLAlchemyError as e:
                logger.error(
                    "expire_order_db_error",
                    order_id=order.order_id,
                    error=str(e),
                    exc_info=True
                )
                db.rollback()  # 回滚失败的订单更新
            except Exception as e:
                logger.critical(
                    "unexpected_error",
                    order_id=order.order_id,
                    error=str(e),
                    exc_info=True
                )
                db.rollback()
        
        logger.info(
            "expire_orders_task_completed",
            total=len(pending_orders),
            expired=expired_count
        )
        
        return {
            "total": len(pending_orders),
            "expired": expired_count,
            "checked_at": now.isoformat()
        }
    
    finally:
        db.close()


async def cancel_order_task(ctx: Dict, order_id: str, reason: str = "user_requested") -> Dict:
    """
    取消订单任务
    
    Args:
        ctx: arq 上下文
        order_id: 订单ID
        reason: 取消原因
    
    Returns:
        result: 取消结果
    """
    logger.info("cancel_order_started", order_id=order_id, reason=reason)
    
    db: Session = SessionLocal()
    try:
        order_repo = OrderRepository(db)
        order = order_repo.get_by_order_id(order_id)
        
        if not order:
            logger.error("order_not_found", order_id=order_id)
            return {"success": False, "reason": "Order not found"}
        
        if order.status != "PENDING":
            logger.warning(
                "order_cannot_cancel",
                order_id=order_id,
                status=order.status
            )
            return {
                "success": False,
                "reason": f"Order status is {order.status}, can only cancel PENDING orders"
            }
        
        order_repo.update_status(order_id, "CANCELLED")
        
        logger.info("order_cancelled", order_id=order_id, reason=reason)
        
        return {
            "success": True,
            "order_id": order_id,
            "reason": reason,
            "cancelled_at": datetime.now().isoformat()
        }
    
    finally:
        db.close()
