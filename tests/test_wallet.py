"""
测试钱包管理功能
"""
import pytest
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import uuid

from src.database import Base, User, DepositOrder, DebitRecord, init_db
from src.wallet.wallet_manager import WalletManager


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
    """创建钱包管理器实例"""
    return WalletManager(db=test_db)


def test_create_user(wallet):
    """测试创建用户"""
    user = wallet.get_or_create_user(user_id=123456, username="testuser")
    
    assert user.user_id == 123456
    assert user.username == "testuser"
    assert user.balance_micro_usdt == 0
    assert user.get_balance() == 0.0


def test_get_balance(wallet):
    """测试查询余额"""
    balance = wallet.get_balance(user_id=123456)
    assert balance == 0.0


def test_create_deposit_order(wallet):
    """测试创建充值订单"""
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    assert order.user_id == 123456
    assert order.base_amount == 10.0
    assert order.unique_suffix == 123
    assert order.total_amount == 10.123
    assert order.amount_micro_usdt == 10_123_000
    assert order.status == "PENDING"


def test_process_deposit_callback_success(wallet):
    """测试处理充值回调（成功）"""
    # 创建订单
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    # 处理回调
    success, message = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    assert success is True
    assert "充值成功" in message
    
    # 验证余额
    balance = wallet.get_balance(user_id=123456)
    assert balance == 10.123
    
    # 验证订单状态
    updated_order = wallet.get_deposit_order(order.order_id)
    assert updated_order.status == "PAID"
    assert updated_order.tx_hash == "test_tx_hash_123"


def test_process_deposit_callback_idempotent(wallet):
    """测试充值回调幂等性"""
    # 创建订单
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    # 第一次回调
    success1, _ = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    # 第二次回调（重复）
    success2, message2 = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    assert success1 is True
    assert success2 is True
    assert "幂等" in message2
    
    # 余额只入账一次
    balance = wallet.get_balance(user_id=123456)
    assert balance == 10.123


def test_process_deposit_callback_amount_mismatch(wallet):
    """测试金额不匹配"""
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    # 金额不匹配
    success, message = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.456,  # 错误的金额
        tx_hash="test_tx_hash_123"
    )
    
    assert success is False
    assert "金额不匹配" in message
    
    # 余额未变化
    balance = wallet.get_balance(user_id=123456)
    assert balance == 0.0


def test_process_deposit_callback_expired(wallet):
    """测试过期订单"""
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    
    # 手动设置订单过期
    order.expires_at = datetime.now() - timedelta(minutes=1)
    wallet.db.commit()
    
    # 处理回调
    success, message = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    assert success is False
    assert "过期" in message


def test_process_deposit_callback_order_not_found(wallet):
    """测试订单不存在"""
    success, message = wallet.process_deposit_callback(
        order_id="non_existent_order",
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    assert success is False
    assert "不存在" in message


def test_debit_success(wallet):
    """测试扣费成功"""
    # 先充值
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    # 扣费
    success = wallet.debit(
        user_id=123456,
        amount=5.0,
        order_type="premium",
        related_order_id="test_order_123"
    )
    
    assert success is True
    
    # 验证余额
    balance = wallet.get_balance(user_id=123456)
    assert balance == pytest.approx(5.123, abs=0.001)


def test_debit_insufficient_balance(wallet):
    """测试余额不足"""
    # 余额为0
    success = wallet.debit(
        user_id=123456,
        amount=10.0,
        order_type="premium"
    )
    
    assert success is False
    
    # 余额未变化
    balance = wallet.get_balance(user_id=123456)
    assert balance == 0.0


def test_debit_concurrent_protection(wallet):
    """测试并发扣费保护"""
    # 先充值
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.123,
        tx_hash="test_tx_hash_123"
    )
    
    # 第一次扣费（成功）
    success1 = wallet.debit(
        user_id=123456,
        amount=10.0,
        order_type="premium"
    )
    
    # 第二次扣费（失败，余额不足）
    success2 = wallet.debit(
        user_id=123456,
        amount=10.0,
        order_type="premium"
    )
    
    assert success1 is True
    assert success2 is False
    
    # 验证余额
    balance = wallet.get_balance(user_id=123456)
    assert balance == pytest.approx(0.123, abs=0.001)


def test_amount_integer_calculation(wallet):
    """测试金额整数化计算"""
    # 创建订单
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.50,
        unique_suffix=456,
        timeout_minutes=30
    )
    
    # 验证金额计算
    assert order.total_amount == 10.956
    assert order.amount_micro_usdt == 10_956_000
    
    # 测试精确匹配
    success, _ = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.956,
        tx_hash="test_tx_hash"
    )
    assert success is True


def test_amount_integer_mismatch(wallet):
    """测试金额整数化不匹配"""
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=10.50,
        unique_suffix=456,
        timeout_minutes=30
    )
    
    # 微小差异（浮点误差）
    success, _ = wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=10.956001,  # 微小差异
        tx_hash="test_tx_hash"
    )
    
    # 整数化后不匹配
    assert success is False


def test_get_user_deposits(wallet):
    """测试查询用户充值记录"""
    # 创建多个订单
    for i in range(3):
        order = wallet.create_deposit_order(
            user_id=123456,
            base_amount=10.0,
            unique_suffix=100 + i,
            timeout_minutes=30
        )
        if i < 2:  # 前两个订单支付
            wallet.process_deposit_callback(
                order_id=order.order_id,
                amount=order.total_amount,
                tx_hash=f"tx_{i}"
            )
    
    # 查询记录
    deposits = wallet.get_user_deposits(user_id=123456, limit=10)
    
    assert len(deposits) == 3
    assert sum(1 for d in deposits if d.status == "PAID") == 2
    assert sum(1 for d in deposits if d.status == "PENDING") == 1


def test_get_user_debits(wallet):
    """测试查询用户扣费记录"""
    # 先充值
    order = wallet.create_deposit_order(
        user_id=123456,
        base_amount=100.0,
        unique_suffix=123,
        timeout_minutes=30
    )
    wallet.process_deposit_callback(
        order_id=order.order_id,
        amount=100.123,
        tx_hash="test_tx_hash"
    )
    
    # 多次扣费
    for i in range(3):
        wallet.debit(
            user_id=123456,
            amount=10.0,
            order_type="premium",
            related_order_id=f"order_{i}"
        )
    
    # 查询记录
    debits = wallet.get_user_debits(user_id=123456, limit=10)
    
    assert len(debits) == 3
    assert all(d.get_amount() == 10.0 for d in debits)


def test_multiple_users(wallet):
    """测试多用户场景"""
    # 用户1充值
    order1 = wallet.create_deposit_order(
        user_id=111,
        base_amount=10.0,
        unique_suffix=111,
        timeout_minutes=30
    )
    wallet.process_deposit_callback(
        order_id=order1.order_id,
        amount=10.111,
        tx_hash="tx_1"
    )
    
    # 用户2充值
    order2 = wallet.create_deposit_order(
        user_id=222,
        base_amount=20.0,
        unique_suffix=222,
        timeout_minutes=30
    )
    wallet.process_deposit_callback(
        order_id=order2.order_id,
        amount=20.222,
        tx_hash="tx_2"
    )
    
    # 验证余额
    balance1 = wallet.get_balance(user_id=111)
    balance2 = wallet.get_balance(user_id=222)
    
    assert balance1 == pytest.approx(10.111, abs=0.001)
    assert balance2 == pytest.approx(20.222, abs=0.001)
