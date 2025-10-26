"""
TRC20 Webhook 回调处理器
路由：POST /webhook/trc20
验证 HMAC 签名、解析 JSON、金额匹配后更新订单状态
"""
import logging
from typing import Dict, Any
import time
import re

from ..models import PaymentCallback
from ..signature import signature_validator
from ..payments.order import order_manager
from ..payments.amount_calculator import AmountCalculator
from ..config import settings

# 配置日志
logger = logging.getLogger(__name__)


class TRC20Handler:
    """TRC20回调处理器"""
    
    @staticmethod
    def validate_tron_address(address: str) -> bool:
        """
        验证波场地址格式
        
        Args:
            address: 波场地址
            
        Returns:
            是否为有效的波场地址
        """
        # 波场地址以T开头，长度为34位，包含Base58字符
        tron_pattern = r'^T[A-HJ-NP-Z1-9a-km-z]{33}$'
        return bool(re.match(tron_pattern, address))
    
    @staticmethod
    async def handle_webhook(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        处理TRC20支付回调
        
        Args:
            payload: 回调数据
            
        Returns:
            处理结果
        """
        try:
            # 验证必需字段
            required_fields = ["order_id", "amount", "txid", "timestamp", "signature"]
            for field in required_fields:
                if field not in payload:
                    return {
                        "success": False,
                        "error": f"Missing required field: {field}"
                    }
            
            # 提取签名
            signature = payload.pop("signature")
            
            # 验证签名
            if not signature_validator.verify_signature(payload, signature):
                logger.warning(f"Invalid signature for order {payload.get('order_id')}")
                return {
                    "success": False,
                    "error": "Invalid signature"
                }
            
            # 创建回调对象
            callback = PaymentCallback(
                order_id=payload["order_id"],
                amount=payload["amount"],
                tx_hash=payload["txid"],
                block_number=payload.get("block_number", 0),
                timestamp=payload["timestamp"],
                signature=signature
            )
            
            # 处理支付确认
            result = await TRC20Handler._process_payment(callback)
            
            logger.info(f"Processed payment callback for order {callback.order_id}: {result}")
            
            return result
        
        except Exception as e:
            logger.error(f"Error handling webhook: {str(e)}")
            return {
                "success": False,
                "error": "Internal server error"
            }
    
    @staticmethod
    async def _process_payment(callback: PaymentCallback) -> Dict[str, Any]:
        """
        处理支付确认
        
        Args:
            callback: 支付回调数据
            
        Returns:
            处理结果
        """
        try:
            # 查找匹配的订单
            order = await order_manager.find_order_by_amount(callback.amount)
            
            if not order:
                return {
                    "success": False,
                    "error": "Order not found for amount",
                    "order_id": callback.order_id
                }
            
            # 验证订单ID是否匹配
            if order.order_id != callback.order_id:
                return {
                    "success": False,
                    "error": "Order ID mismatch",
                    "expected": order.order_id,
                    "received": callback.order_id
                }
            
            # 验证金额是否精确匹配
            if not AmountCalculator.verify_amount(order.total_amount, callback.amount):
                return {
                    "success": False,
                    "error": "Amount mismatch",
                    "expected": order.total_amount,
                    "received": callback.amount
                }
            
            # 检查订单是否已过期
            if order.is_expired:
                await order_manager.update_order_status(order.order_id, OrderStatus.EXPIRED)
                return {
                    "success": False,
                    "error": "Order expired",
                    "order_id": order.order_id
                }
            
            # 更新订单状态为已支付（幂等操作）
            success = await order_manager.update_order_status(
                order.order_id, 
                OrderStatus.PAID,
                callback.tx_hash
            )
            
            if success:
                return {
                    "success": True,
                    "message": "Payment processed successfully",
                    "order_id": order.order_id,
                    "tx_hash": callback.tx_hash
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update order status",
                    "order_id": order.order_id
                }
        
        except Exception as e:
            logger.error(f"Error processing payment for order {callback.order_id}: {str(e)}")
            return {
                "success": False,
                "error": f"Processing error: {str(e)}",
                "order_id": callback.order_id
            }
    
    @staticmethod
    async def simulate_payment(order_id: str, tx_hash: str = None) -> Dict[str, Any]:
        """
        模拟支付回调（用于测试）
        
        Args:
            order_id: 订单ID
            tx_hash: 交易哈希（可选）
            
        Returns:
            模拟结果
        """
        try:
            # 获取订单信息
            order = await order_manager.get_order(order_id)
            if not order:
                return {
                    "success": False,
                    "error": "Order not found",
                    "order_id": order_id
                }
            
            # 生成模拟交易哈希
            if not tx_hash:
                tx_hash = f"test_tx_{int(time.time())}_{order_id[:8]}"
            
            # 创建签名的回调数据
            callback_data = signature_validator.create_signed_callback(
                order_id=order_id,
                amount=order.total_amount,
                tx_hash=tx_hash,
                block_number=int(time.time()),  # 使用时间戳作为块号
                timestamp=int(time.time())
            )
            
            # 处理回调
            result = await TRC20Handler.handle_webhook(callback_data)
            
            result["simulation"] = True
            result["callback_data"] = callback_data
            
            return result
        
        except Exception as e:
            logger.error(f"Error simulating payment: {str(e)}")
            return {
                "success": False,
                "error": f"Simulation error: {str(e)}",
                "order_id": order_id
            }
    
    @staticmethod
    def validate_webhook_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证webhook载荷格式
        
        Args:
            payload: 载荷数据
            
        Returns:
            验证结果
        """
        errors = []
        
        # 检查必需字段
        required_fields = {
            "order_id": str,
            "amount": (int, float),
            "txid": str,
            "timestamp": int,
            "signature": str
        }
        
        for field, expected_type in required_fields.items():
            if field not in payload:
                errors.append(f"Missing field: {field}")
            elif not isinstance(payload[field], expected_type):
                errors.append(f"Invalid type for {field}: expected {expected_type.__name__}")
        
        # 验证金额范围
        if "amount" in payload:
            amount = payload["amount"]
            if not AmountCalculator.is_valid_payment_amount(amount):
                errors.append(f"Invalid payment amount: {amount}")
        
        # 验证交易哈希格式
        if "txid" in payload:
            txid = payload["txid"]
            if not isinstance(txid, str) or len(txid) < 10:
                errors.append(f"Invalid transaction hash: {txid}")
        
        # 验证时间戳
        if "timestamp" in payload:
            timestamp = payload["timestamp"]
            current_time = int(time.time())
            # 允许5分钟的时间差
            if abs(current_time - timestamp) > 300:
                errors.append(f"Timestamp too old or future: {timestamp}")
        
        if errors:
            return {
                "valid": False,
                "errors": errors
            }
        
        return {
            "valid": True,
            "errors": []
        }


# 创建全局实例
trc20_handler = TRC20Handler()