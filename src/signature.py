"""
HMAC签名验证模块
"""
import hmac
import hashlib
import json
from typing import Dict, Any

from .config import settings


class SignatureValidator:
    """HMAC签名验证器"""
    
    @staticmethod
    def generate_signature(data: Dict[str, Any], secret: str = None) -> str:
        """
        生成HMAC签名
        
        Args:
            data: 要签名的数据
            secret: 签名密钥，默认使用配置中的密钥
            
        Returns:
            十六进制格式的签名
        """
        if secret is None:
            secret = settings.webhook_secret
        
        # 将数据按key排序后序列化
        sorted_data = dict(sorted(data.items()))
        message = json.dumps(sorted_data, separators=(',', ':'), ensure_ascii=True)
        
        # 生成HMAC-SHA256签名
        signature = hmac.new(
            secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    @staticmethod
    def verify_signature(data: Dict[str, Any], signature: str, secret: str = None) -> bool:
        """
        验证HMAC签名
        
        Args:
            data: 要验证的数据
            signature: 提供的签名
            secret: 签名密钥，默认使用配置中的密钥
            
        Returns:
            签名是否有效
        """
        if secret is None:
            secret = settings.webhook_secret
        
        # 生成期望的签名
        expected_signature = SignatureValidator.generate_signature(data, secret)
        
        # 使用常数时间比较避免时间攻击
        return hmac.compare_digest(expected_signature, signature)
    
    @staticmethod
    def prepare_callback_data(order_id: str, amount: float, tx_hash: str, 
                            block_number: int, timestamp: int) -> Dict[str, Any]:
        """
        准备回调数据（不包含签名）
        
        Args:
            order_id: 订单ID
            amount: 金额
            tx_hash: 交易哈希
            block_number: 区块号
            timestamp: 时间戳
            
        Returns:
            回调数据字典
        """
        return {
            "order_id": order_id,
            "amount": amount,
            "txid": tx_hash,  # TRC20Handler 期望 txid 字段
            "block_number": block_number,
            "timestamp": timestamp
        }
    
    @staticmethod
    def create_signed_callback(order_id: str, amount: float, tx_hash: str,
                             block_number: int, timestamp: int, secret: str = None) -> Dict[str, Any]:
        """
        创建带签名的回调数据
        
        Args:
            order_id: 订单ID
            amount: 金额
            tx_hash: 交易哈希
            block_number: 区块号
            timestamp: 时间戳
            secret: 签名密钥
            
        Returns:
            包含签名的完整回调数据
        """
        # 准备基础数据
        data = SignatureValidator.prepare_callback_data(
            order_id, amount, tx_hash, block_number, timestamp
        )
        
        # 生成签名
        signature = SignatureValidator.generate_signature(data, secret)
        
        # 添加签名到数据中
        data["signature"] = signature
        
        return data


# 全局实例
signature_validator = SignatureValidator()