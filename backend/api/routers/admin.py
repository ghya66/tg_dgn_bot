"""
管理员 API 路由

提供订单管理、配置管理、产品管理等 CRUD 端点。

所有端点需要:
- API Key 认证（X-API-Key 头）
- IP 白名单验证（ADMIN_IP_WHITELIST 配置）
- Rate Limiting: 30 req/min
"""

from datetime import datetime
from typing import List, Optional

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy import func

from backend.api.database import get_db
from backend.api.models import Order, OrderStatus, OrderType
from src.database import Order as DBOrder  # 使用 src.database 的 Order 模型

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic 模型（请求/响应）
# ============================================================================

class OrderResponse(BaseModel):
    """订单响应模型"""
    order_id: str
    order_type: str
    amount_usdt: float
    status: str
    recipient: Optional[str] = None
    created_at: str
    paid_at: Optional[str] = None
    delivered_at: Optional[str] = None
    
    class Config:
        from_attributes = True


class OrderListResponse(BaseModel):
    """订单列表响应"""
    total: int
    page: int
    page_size: int
    orders: List[OrderResponse]


class OrderUpdateRequest(BaseModel):
    """订单更新请求"""
    status: Optional[str] = Field(None, description="订单状态")
    notes: Optional[str] = Field(None, description="备注信息")


# ============================================================================
# 订单管理端点
# ============================================================================

@router.get("/orders", response_model=OrderListResponse)
async def list_orders(
    request: Request,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    order_type: Optional[str] = Query(None, description="订单类型过滤"),
    status: Optional[str] = Query(None, description="状态过滤"),
    db: Session = Depends(get_db),
):
    """
    获取订单列表
    
    支持分页和过滤：
    - page: 页码（从 1 开始）
    - page_size: 每页数量（1-100）
    - order_type: 订单类型（premium, deposit, trx_exchange）
    - status: 订单状态（PENDING, PAID, DELIVERED, EXPIRED, CANCELLED）
    """
    # 直接使用 SQLAlchemy 查询 Order 表
    query = db.query(DBOrder)
    
    # 应用过滤条件
    if order_type:
        valid_types = ["premium", "deposit", "trx_exchange"]
        if order_type.lower() not in valid_types:
            raise HTTPException(status_code=400, detail=f"无效的订单类型: {order_type}")
        query = query.filter(DBOrder.order_type == order_type.lower())
    
    if status:
        valid_statuses = ["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"]
        if status.upper() not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效的订单状态: {status}")
        query = query.filter(DBOrder.status == status.upper())
    
    # 查询总数
    total = query.count()
    
    # 查询订单（分页）
    offset = (page - 1) * page_size
    orders = query.order_by(DBOrder.created_at.desc()).offset(offset).limit(page_size).all()
    
    logger.info(
        "admin_list_orders",
        page=page,
        page_size=page_size,
        total=total,
        order_type_filter=order_type,
        status_filter=status,
    )
    
    return OrderListResponse(
        total=total,
        page=page,
        page_size=page_size,
        orders=[
            OrderResponse(
                order_id=order.order_id,
                order_type=order.order_type,
                amount_usdt=float(order.amount_usdt) / 1000,  # 微 USDT 转为 USDT
                status=order.status,
                recipient=order.recipient,
                created_at=order.created_at.isoformat(),
                paid_at=order.paid_at.isoformat() if order.paid_at else None,
                delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
            )
            for order in orders
        ],
    )


@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    request: Request,
    order_id: str,
    db: Session = Depends(get_db),
):
    """
    获取单个订单详情
    """
    # 直接查询 Order 表
    order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    logger.info("admin_get_order", order_id=order_id)
    
    return OrderResponse(
        order_id=order.order_id,
        order_type=order.order_type,
        amount_usdt=float(order.amount_usdt) / 1000,  # 微 USDT 转为 USDT
        status=order.status,
        recipient=order.recipient,
        created_at=order.created_at.isoformat(),
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
    )


@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    request: Request,
    order_id: str,
    update_data: OrderUpdateRequest,
    db: Session = Depends(get_db),
):
    """
    更新订单信息
    
    支持更新：
    - status: 订单状态
    - notes: 备注信息
    """
    # 直接查询 Order 表
    order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 更新状态
    if update_data.status:
        valid_statuses = ["PENDING", "PAID", "DELIVERED", "EXPIRED", "CANCELLED"]
        if update_data.status.upper() not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"无效的订单状态: {update_data.status}")
        
        order.status = update_data.status.upper()
        
        # 更新时间戳
        if order.status == "PAID" and not order.paid_at:
            order.paid_at = datetime.now()
        elif order.status == "DELIVERED" and not order.delivered_at:
            order.delivered_at = datetime.now()
    
    # TODO: 更新备注（需要在 Order 模型中添加 notes 字段）
    
    db.commit()
    db.refresh(order)
    
    logger.info(
        "admin_update_order",
        order_id=order_id,
        updates=update_data.dict(exclude_none=True),
    )
    
    return OrderResponse(
        order_id=order.order_id,
        order_type=order.order_type,
        amount_usdt=float(order.amount_usdt) / 1000,  # 微 USDT 转为 USDT
        status=order.status,
        recipient=order.recipient,
        created_at=order.created_at.isoformat(),
        paid_at=order.paid_at.isoformat() if order.paid_at else None,
        delivered_at=order.delivered_at.isoformat() if order.delivered_at else None,
    )


@router.delete("/orders/{order_id}")
async def cancel_order(
    request: Request,
    order_id: str,
    reason: str = Query(..., description="取消原因"),
    db: Session = Depends(get_db),
):
    """
    取消订单
    """
    # 直接查询 Order 表
    order = db.query(DBOrder).filter(DBOrder.order_id == order_id).first()
    
    if not order:
        raise HTTPException(status_code=404, detail="订单不存在")
    
    # 检查状态是否允许取消
    if order.status not in ["PENDING", "PAID"]:
        raise HTTPException(
            status_code=400,
            detail=f"订单状态为 {order.status}，无法取消",
        )
    
    # 更新为取消状态
    order.status = "CANCELLED"
    db.commit()
    
    logger.info(
        "admin_cancel_order",
        order_id=order_id,
        reason=reason,
    )
    
    return {"message": "订单已成功取消", "order_id": order_id}


# ============================================================================
# 统计端点
# ============================================================================

@router.get("/stats/summary")
async def get_summary_stats(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    获取订单统计摘要
    """
    # 直接使用 SQLAlchemy 聚合查询
    total = db.query(func.count(DBOrder.order_id)).scalar() or 0
    pending = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == "PENDING").scalar() or 0
    paid = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == "PAID").scalar() or 0
    delivered = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == "DELIVERED").scalar() or 0
    expired = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == "EXPIRED").scalar() or 0
    cancelled = db.query(func.count(DBOrder.order_id)).filter(DBOrder.status == "CANCELLED").scalar() or 0
    
    # 按类型统计
    premium = db.query(func.count(DBOrder.order_id)).filter(DBOrder.order_type == "premium").scalar() or 0
    deposit = db.query(func.count(DBOrder.order_id)).filter(DBOrder.order_type == "deposit").scalar() or 0
    trx_exchange = db.query(func.count(DBOrder.order_id)).filter(DBOrder.order_type == "trx_exchange").scalar() or 0
    
    stats = {
        "total": total,
        "pending": pending,
        "paid": paid,
        "delivered": delivered,
        "expired": expired,
        "cancelled": cancelled,
        "by_type": {
            "premium": premium,
            "deposit": deposit,
            "trx_exchange": trx_exchange,
        },
    }
    
    logger.info("admin_get_stats", stats=stats)
    
    return stats
