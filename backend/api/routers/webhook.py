"""
Webhook API 路由

处理 TRC20 支付回调通知。

安全措施:
- IP 白名单验证（IPWhitelistMiddleware）
- HMAC-SHA256 签名验证
- 幂等性保证（order_id 唯一）
"""

import structlog
from fastapi import APIRouter, Depends, HTTPException, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.middleware import limiter
from backend.api.services.order_service import OrderService

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic 模型
# ============================================================================

class TRC20CallbackRequest(BaseModel):
    """TRC20 支付回调请求"""
    order_id: str = Field(..., description="订单ID")
    tx_hash: str = Field(..., description="交易哈希")
    from_address: str = Field(..., description="付款地址")
    to_address: str = Field(..., description="收款地址")
    amount_usdt: float = Field(..., gt=0, description="支付金额（USDT）")
    block_number: int = Field(..., ge=0, description="区块高度")
    timestamp: int = Field(..., ge=0, description="时间戳")


class TRC20CallbackResponse(BaseModel):
    """TRC20 回调响应"""
    success: bool
    order_id: str
    message: str


# ============================================================================
# Webhook 端点
# ============================================================================

@router.post("/trc20", response_model=TRC20CallbackResponse)
@limiter.limit("100/minute")  # 更高的限流（支付回调频繁）
async def trc20_callback(
    request: Request,
    callback_data: TRC20CallbackRequest,
    x_signature: str = Header(..., description="HMAC-SHA256 签名"),
    db: Session = Depends(get_db),
):
    """
    TRC20 支付回调端点
    
    安全机制:
    1. IP 白名单验证（中间件）
    2. HMAC-SHA256 签名验证
    3. 幂等性保证
    
    Headers:
    - X-Signature: HMAC-SHA256(secret, order_id + amount_usdt + tx_hash)
    
    Request Body:
    - order_id: 订单ID
    - tx_hash: 链上交易哈希
    - from_address: 付款地址
    - to_address: 收款地址（应匹配系统配置）
    - amount_usdt: 支付金额（USDT）
    - block_number: 区块高度
    - timestamp: 时间戳
    
    Response:
    - 200: 处理成功（幂等：重复请求也返回 200）
    - 400: 签名验证失败或金额不匹配
    - 404: 订单不存在
    - 500: 内部错误
    """
    logger.info(
        "trc20_callback_received",
        order_id=callback_data.order_id,
        tx_hash=callback_data.tx_hash,
        amount_usdt=callback_data.amount_usdt,
    )
    
    # 1. 验证签名
    from backend.api.utils.signature import verify_trc20_signature
    
    is_valid = verify_trc20_signature(
        order_id=callback_data.order_id,
        amount_usdt=callback_data.amount_usdt,
        tx_hash=callback_data.tx_hash,
        signature=x_signature,
    )
    
    if not is_valid:
        logger.warning(
            "trc20_callback_invalid_signature",
            order_id=callback_data.order_id,
            signature=x_signature,
        )
        raise HTTPException(status_code=400, detail="Invalid signature")
    
    # 2. 处理订单支付
    order_service = OrderService(db)
    
    try:
        result = order_service.process_payment(
            order_id=callback_data.order_id,
            tx_hash=callback_data.tx_hash,
            paid_amount_usdt=callback_data.amount_usdt,
            from_address=callback_data.from_address,
        )
        
        logger.info(
            "trc20_callback_processed",
            order_id=callback_data.order_id,
            status=result["status"],
            message=result["message"],
        )
        
        return TRC20CallbackResponse(
            success=True,
            order_id=callback_data.order_id,
            message=result["message"],
        )
    
    except ValueError as e:
        # 金额不匹配、订单不存在等业务错误
        logger.warning(
            "trc20_callback_business_error",
            order_id=callback_data.order_id,
            error=str(e),
        )
        raise HTTPException(status_code=400, detail=str(e))
    
    except Exception as e:
        # 未预期的错误
        logger.error(
            "trc20_callback_unexpected_error",
            order_id=callback_data.order_id,
            error=str(e),
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail="Internal server error")


# ============================================================================
# 健康检查端点（Webhook 特定）
# ============================================================================

@router.get("/health")
async def webhook_health():
    """
    Webhook 服务健康检查
    
    用于监控 Webhook 服务是否正常运行。
    """
    return {
        "status": "healthy",
        "service": "webhook",
        "endpoints": {
            "trc20": "/api/webhook/trc20",
        },
    }
