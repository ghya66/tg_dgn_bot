"""
测试 Premium 订单创建和管理
"""
import pytest
import asyncio
from src.models import OrderType, OrderStatus
from src.payments.order import order_manager
from src.payments.suffix_manager import suffix_manager


# 标记为需要 Redis 的测试
pytestmark = pytest.mark.redis


@pytest.fixture
async def setup_redis(redis_client):
    """设置 Redis 环境（直接使用 conftest 的 redis_client）"""
    # 直接使用从 conftest.py 获得的 redis_client
    # 不需要再次 connect/disconnect，只需清理数据
    await redis_client.flushdb()
    
    # 设置全局管理器的 Redis 连接
    suffix_manager.redis_client = redis_client
    order_manager.redis_client = redis_client
    
    yield
    
    # 清理测试数据（但不关闭连接，由 conftest.py 管理）
    await redis_client.flushdb()


@pytest.mark.asyncio
async def test_create_premium_order(setup_redis):
    """测试创建 Premium 订单"""
    recipients = ["alice", "bob", "charlie"]
    
    order = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=recipients
    )
    
    assert order is not None
    assert order.order_type == OrderType.PREMIUM
    assert order.premium_months == 3
    assert order.recipients == recipients
    assert order.status == OrderStatus.PENDING
    assert order.base_amount == 10.0
    assert order.total_amount > 10.0  # 包含唯一后缀


@pytest.mark.asyncio
async def test_premium_order_status_transitions(setup_redis):
    """测试 Premium 订单状态转换"""
    order = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=6,
        recipients=["alice"]
    )
    
    # PENDING → PAID
    success = await order_manager.update_order_status(
        order.order_id,
        OrderStatus.PAID
    )
    assert success is True
    
    # PAID → DELIVERED
    success = await order_manager.update_order_status(
        order.order_id,
        OrderStatus.DELIVERED
    )
    assert success is True
    
    # 验证最终状态
    updated_order = await order_manager.get_order(order.order_id)
    assert updated_order.status == OrderStatus.DELIVERED


@pytest.mark.asyncio
async def test_premium_order_partial_delivery(setup_redis):
    """测试 Premium 订单部分交付"""
    recipients = ["alice", "bob", "charlie"]
    order = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=recipients
    )
    
    # 模拟部分交付
    delivery_results = {
        "alice": {"success": True, "error": None},
        "bob": {"success": False, "error": "User not found"},
        "charlie": {"success": True, "error": None}
    }
    
    # PENDING → PAID
    await order_manager.update_order_status(order.order_id, OrderStatus.PAID)
    
    # PAID → PARTIAL
    success = await order_manager.update_order_status(
        order.order_id,
        OrderStatus.PARTIAL,
        delivery_results=delivery_results
    )
    assert success is True
    
    # 验证交付结果
    updated_order = await order_manager.get_order(order.order_id)
    assert updated_order.status == OrderStatus.PARTIAL
    assert updated_order.delivery_results == delivery_results


@pytest.mark.asyncio
async def test_premium_order_with_multiple_recipients(setup_redis):
    """测试多收件人 Premium 订单"""
    recipients = [f"user{i}" for i in range(10)]
    
    order = await order_manager.create_order(
        user_id=123456,
        base_amount=30.0,
        order_type=OrderType.PREMIUM,
        premium_months=12,
        recipients=recipients
    )
    
    assert order is not None
    assert len(order.recipients) == 10
    assert order.premium_months == 12


@pytest.mark.asyncio
async def test_premium_order_persistence(setup_redis):
    """测试 Premium 订单持久化"""
    recipients = ["alice", "bob"]
    order = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=recipients
    )
    
    # 重新获取订单
    retrieved_order = await order_manager.get_order(order.order_id)
    
    assert retrieved_order is not None
    assert retrieved_order.order_id == order.order_id
    assert retrieved_order.order_type == OrderType.PREMIUM
    assert retrieved_order.premium_months == 3
    assert retrieved_order.recipients == recipients


@pytest.mark.asyncio
async def test_premium_order_amount_calculation(setup_redis):
    """测试 Premium 订单金额计算"""
    order1 = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=["alice"]
    )
    
    order2 = await order_manager.create_order(
        user_id=123456,
        base_amount=10.0,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=["bob"]
    )
    
    # 两个订单应该有不同的唯一后缀
    assert order1.unique_suffix != order2.unique_suffix
    
    # 两个订单应该有不同的总金额
    assert order1.total_amount != order2.total_amount
    
    # 金额应该在合理范围内
    assert 10.001 <= order1.total_amount <= 10.999
    assert 10.001 <= order2.total_amount <= 10.999
