"""
订单数据模型
"""
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
import uuid


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "PENDING"  # 待支付
    PAID = "PAID"        # 已支付
    EXPIRED = "EXPIRED"  # 已过期
    CANCELLED = "CANCELLED"  # 已取消


class Order(BaseModel):
    """订单模型"""
    order_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    base_amount: float = Field(..., description="基础金额")
    unique_suffix: int = Field(..., description="唯一后缀 (1-999)")
    total_amount: float = Field(..., description="总金额 = 基础金额 + 唯一后缀/1000")
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    user_id: int = Field(..., description="用户ID")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime = Field(..., description="过期时间")
    
    @property
    def is_expired(self) -> bool:
        """检查订单是否过期"""
        return datetime.now() > self.expires_at
    
    @property
    def amount_in_micro_usdt(self) -> int:
        """返回以微USDT为单位的金额（避免浮点误差）"""
        return int(self.total_amount * 1000000)
    
    def update_status(self, new_status: OrderStatus) -> None:
        """更新订单状态"""
        self.status = new_status
        self.updated_at = datetime.now()
    
    class Config:
        use_enum_values = True


class PaymentCallback(BaseModel):
    """支付回调数据模型"""
    order_id: str
    amount: float  # USDT金额
    tx_hash: str
    block_number: int
    timestamp: int
    signature: str = Field(..., description="HMAC签名")
    
    @property
    def amount_in_micro_usdt(self) -> int:
        """返回以微USDT为单位的金额"""
        return int(self.amount * 1000000)