"""
签名验证工具

提供 HMAC-SHA256 签名生成和验证功能。
"""

import hmac
import hashlib
from typing import Optional

from backend.api.config import settings


def generate_trc20_signature(
    order_id: str,
    amount_usdt: float,
    tx_hash: str,
    secret: Optional[str] = None,
) -> str:
    """
    生成 TRC20 回调签名
    
    Args:
        order_id: 订单ID
        amount_usdt: 支付金额（USDT）
        tx_hash: 交易哈希
        secret: HMAC 密钥（默认使用配置）
    
    Returns:
        HMAC-SHA256 签名（十六进制字符串）
    """
    if secret is None:
        secret = settings.trc20_webhook_secret
    
    # 构建签名消息
    message = f"{order_id}{amount_usdt}{tx_hash}"
    
    # 生成 HMAC-SHA256 签名
    signature = hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    
    return signature


def verify_trc20_signature(
    order_id: str,
    amount_usdt: float,
    tx_hash: str,
    signature: str,
    secret: Optional[str] = None,
) -> bool:
    """
    验证 TRC20 回调签名
    
    Args:
        order_id: 订单ID
        amount_usdt: 支付金额（USDT）
        tx_hash: 交易哈希
        signature: 待验证的签名
        secret: HMAC 密钥（默认使用配置）
    
    Returns:
        签名是否有效
    """
    expected_signature = generate_trc20_signature(
        order_id=order_id,
        amount_usdt=amount_usdt,
        tx_hash=tx_hash,
        secret=secret,
    )
    
    # 使用 hmac.compare_digest 防止时序攻击
    return hmac.compare_digest(expected_signature, signature)
