"""
测试充值订单的 TRC20 回调处理
"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database import Base
from src.wallet.wallet_manager import WalletManager
from src.webhook.trc20_handler import TRC20Handler
from src.models import PaymentCallback


@pytest.fixture
def test_db():
    """创建测试数据库"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


@pytest.fixture
def wallet(test_db):
    """创建钱包管理器"""
    return WalletManager(db=test_db)


@pytest.fixture
def handler(test_db):
    """创建TRC20处理器，注入测试数据库"""
    return TRC20Handler(db_session=test_db)


@pytest.mark.asyncio
async def test_deposit_callback_success(wallet, handler):
    """测试充值回调成功"""
    # 创建充值订单
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    # 创建回调数据
    callback = PaymentCallback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123",
        block_number=12345678,
        timestamp=1234567890,
        signature="test_signature",
        order_type="deposit"
    )
    
    # 处理回调
    result = await handler._process_deposit_payment(callback)
    
    assert result["success"] is True
    assert result["order_type"] == "deposit"
    assert "充值成功" in result["message"]
    
    # 验证余额
    balance = wallet.get_balance(user_id=123456)
    assert balance == 10.123


@pytest.mark.asyncio
async def test_deposit_callback_idempotent(wallet, handler):
    """测试充值回调幂等性"""
    # 创建充值订单
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    callback = PaymentCallback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123",
        block_number=12345678,
        timestamp=1234567890,
        signature="test_signature",
        order_type="deposit"
    )
    
    # 第一次处理
    result1 = await handler._process_deposit_payment(callback)
    
    # 第二次处理（幂等）
    result2 = await handler._process_deposit_payment(callback)
    
    assert result1["success"] is True
    assert result2["success"] is True
    assert "幂等" in result2["message"]
    
    # 余额只入账一次
    balance = wallet.get_balance(user_id=123456)
    assert balance == 10.123


@pytest.mark.asyncio
async def test_deposit_callback_amount_mismatch(wallet, handler):
    """测试金额不匹配"""
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    callback = PaymentCallback(
        order_id=order.order_id,
        amount=10.456,  # 错误金额
        tx_hash="test_tx_hash_123",
        block_number=12345678,
        timestamp=1234567890,
        signature="test_signature",
        order_type="deposit"
    )
    
    result = await handler._process_deposit_payment(callback)
    
    assert result["success"] is False
    assert "金额不匹配" in result["error"]
    
    # 余额未变化
    balance = wallet.get_balance(user_id=123456)
    assert balance == 0.0


@pytest.mark.asyncio
async def test_deposit_callback_order_not_found(handler):
    """测试订单不存在"""
    callback = PaymentCallback(
        order_id="non_existent_order",
        amount=10.123,
        tx_hash="test_tx_hash_123",
        block_number=12345678,
        timestamp=1234567890,
        signature="test_signature",
        order_type="deposit"
    )
    
    result = await handler._process_deposit_payment(callback)
    
    assert result["success"] is False
    assert "不存在" in result["error"]
