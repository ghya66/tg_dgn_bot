"""
统计查询功能

提供订单、用户、收入等统计数据。
"""
import logging
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy import func, inspect
from src.database import SessionLocal, engine, Order, User

logger = logging.getLogger(__name__)


class StatsManager:
    """统计管理器"""
    
    def __init__(self):
        """初始化统计管理器"""
        # 直接使用 src.database 的 SessionLocal，无需创建独立引擎
        self.SessionLocal = SessionLocal
        
        # 启动验证：确认数据库引擎和表存在
        logger.info(f"StatsManager 使用数据库: {engine.url}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        
        if "orders" not in tables:
            logger.warning("数据库中未找到 orders 表，统计功能可能异常")
        else:
            logger.info(f"数据库表验证成功，共 {len(tables)} 个表")
    
    def get_order_stats(self) -> Dict:
        """获取订单统计"""
        session = self.SessionLocal()
        try:
            # 总订单数
            total = session.query(func.count(Order.order_id)).scalar() or 0
            
            # 按状态统计
            pending = session.query(func.count(Order.order_id)).filter(
                Order.status == "PENDING"
            ).scalar() or 0
            
            paid = session.query(func.count(Order.order_id)).filter(
                Order.status == "PAID"
            ).scalar() or 0
            
            delivered = session.query(func.count(Order.order_id)).filter(
                Order.status == "DELIVERED"
            ).scalar() or 0
            
            expired = session.query(func.count(Order.order_id)).filter(
                Order.status == "EXPIRED"
            ).scalar() or 0
            
            cancelled = session.query(func.count(Order.order_id)).filter(
                Order.status == "CANCELLED"
            ).scalar() or 0
            
            # 按类型统计
            by_type = {}
            for order_type in ["premium", "deposit", "trx_exchange", "energy"]:
                count = session.query(func.count(Order.order_id)).filter(
                    Order.order_type == order_type
                ).scalar() or 0
                by_type[order_type] = count
            
            return {
                "total": total,
                "pending": pending,
                "paid": paid,
                "delivered": delivered,
                "expired": expired,
                "cancelled": cancelled,
                "by_type": by_type
            }
        finally:
            session.close()
    
    def get_user_stats(self) -> Dict:
        """获取用户统计"""
        session = self.SessionLocal()
        try:
            total = session.query(User).count()
            
            # 今日新增
            today = datetime.now().date()
            today_new = session.query(User).filter(
                func.date(User.created_at) == today
            ).count()
            
            # 本周新增
            week_ago = datetime.now() - timedelta(days=7)
            week_new = session.query(User).filter(
                User.created_at >= week_ago
            ).count()
            
            return {
                "total": total,
                "today_new": today_new,
                "week_new": week_new
            }
        finally:
            session.close()
    
    def get_revenue_stats(self) -> Dict:
        """获取收入统计"""
        session = self.SessionLocal()
        try:
            # 总收入（已支付+已交付订单）
            total_revenue = session.query(
                func.sum(Order.base_amount)
            ).filter(
                Order.status.in_(["PAID", "DELIVERED"])
            ).scalar() or 0.0
            
            # 今日收入
            today = datetime.now().date()
            today_revenue = session.query(
                func.sum(Order.base_amount)
            ).filter(
                Order.status.in_(["PAID", "DELIVERED"]),
                func.date(Order.paid_at) == today
            ).scalar() or 0.0
            
            # 本周收入
            week_ago = datetime.now() - timedelta(days=7)
            week_revenue = session.query(
                func.sum(Order.base_amount)
            ).filter(
                Order.status.in_(["PAID", "DELIVERED"]),
                Order.paid_at >= week_ago
            ).scalar() or 0.0
            
            # 本月收入
            month_start = datetime.now().replace(day=1, hour=0, minute=0, second=0)
            month_revenue = session.query(
                func.sum(Order.base_amount)
            ).filter(
                Order.status.in_(["PAID", "DELIVERED"]),
                Order.paid_at >= month_start
            ).scalar() or 0.0
            
            return {
                "total": round(total_revenue, 2),
                "today": round(today_revenue, 2),
                "week": round(week_revenue, 2),
                "month": round(month_revenue, 2)
            }
        finally:
            session.close()


# 全局统计管理器实例
stats_manager = StatsManager()
