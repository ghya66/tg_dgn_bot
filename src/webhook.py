"""
TRC20支付回调接口
"""
import logging
from typing import Dict, Any
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
import time

from .models import PaymentCallback
from .webhook.trc20_handler import get_trc20_handler
from .payments.order import order_manager
from .signature import signature_validator

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="TRC20 Payment Webhook", version="1.0.0")

# 获取 TRC20 处理器实例
trc20_handler = get_trc20_handler()


@app.on_event("startup")
async def startup_event():
    """应用启动时的初始化"""
    await order_manager.connect()
    logger.info("Order manager connected")


@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时的清理"""
    await order_manager.disconnect()
    logger.info("Order manager disconnected")


@app.post("/webhook/trc20")
async def trc20_webhook(
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, Any]:
    """
    处理TRC20支付回调
    
    预期的回调数据格式:
    {
        "order_id": "订单ID",
        "amount": 123.456,
        "txid": "交易哈希",
        "timestamp": 1635724800,
        "signature": "HMAC签名"
    }
    """
    try:
        # 获取请求体
        body = await request.json()
        
        # 使用TRC20Handler处理回调
        result = await trc20_handler.handle_webhook(body)
        
        if result["success"]:
            logger.info(f"Payment callback processed successfully: {result}")
            return {
                "success": True,
                "message": "Payment callback received and processed",
                "order_id": result.get("order_id")
            }
        else:
            logger.warning(f"Payment callback failed: {result}")
            raise HTTPException(status_code=400, detail=result["error"])
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy", "timestamp": int(time.time())}


@app.get("/stats")
async def get_statistics():
    """获取订单统计信息"""
    try:
        stats = await order_manager.get_order_statistics()
        return {
            "success": True,
            "data": stats,
            "timestamp": int(time.time())
        }
    except Exception as e:
        logger.error(f"Error getting statistics: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/test/create-order")
async def create_test_order(
    user_id: int,
    base_amount: float
):
    """
    创建测试订单（仅用于测试）
    """
    try:
        order = await order_manager.create_order(user_id, base_amount)
        
        if not order:
            raise HTTPException(status_code=400, detail="Failed to create order")
        
        return {
            "success": True,
            "order": {
                "order_id": order.order_id,
                "base_amount": order.base_amount,
                "unique_suffix": order.unique_suffix,
                "total_amount": order.total_amount,
                "status": order.status,
                "expires_at": order.expires_at.isoformat()
            }
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating test order: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/test/simulate-payment")
async def simulate_payment(
    order_id: str,
    tx_hash: str = None
):
    """
    模拟支付回调（仅用于测试）
    """
    try:
        result = await trc20_handler.simulate_payment(order_id, tx_hash)
        
        return result
    
    except Exception as e:
        logger.error(f"Error simulating payment: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)