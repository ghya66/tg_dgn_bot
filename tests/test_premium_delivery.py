"""
测试 Premium 交付服务
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from telegram import Bot
from telegram.error import TelegramError
from src.premium.delivery import PremiumDeliveryService, DeliveryResult
from src.models import Order, OrderType, OrderStatus
from src.payments.order import order_manager
from datetime import datetime, timedelta


@pytest.fixture
def mock_bot():
    """创建模拟 Bot"""
    bot = AsyncMock(spec=Bot)
    bot.send_gift = AsyncMock()
    bot.get_star_transactions = AsyncMock(return_value=[])
    return bot


@pytest.fixture
def delivery_service(mock_bot):
    """创建交付服务"""
    return PremiumDeliveryService(mock_bot, order_manager)


@pytest.fixture
def sample_order():
    """创建示例订单"""
    return Order(
        order_id="test-order-123",
        base_amount=10.0,
        unique_suffix=123,
        total_amount=10.123,
        user_id=123456,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=["alice", "bob", "charlie"],
        status=OrderStatus.PAID,
        expires_at=datetime.now() + timedelta(minutes=30)
    )


@pytest.mark.asyncio
async def test_delivery_result_creation():
    """测试交付结果创建"""
    result = DeliveryResult(
        username="alice",
        success=True,
        user_id=123456
    )
    
    assert result.username == "alice"
    assert result.success is True
    assert result.user_id == 123456
    assert result.error is None


@pytest.mark.asyncio
async def test_delivery_result_with_error():
    """测试带错误的交付结果"""
    result = DeliveryResult(
        username="bob",
        success=False,
        error="User not found"
    )
    
    assert result.username == "bob"
    assert result.success is False
    assert result.error == "User not found"


@pytest.mark.asyncio
async def test_check_star_balance(delivery_service, mock_bot):
    """测试检查 XTR 余额"""
    balance = await delivery_service.check_star_balance()
    
    # 目前返回 0（占位实现）
    assert balance == 0
    mock_bot.get_star_transactions.assert_called_once()


@pytest.mark.asyncio
async def test_get_gift_id(delivery_service):
    """测试礼物 ID 映射"""
    assert delivery_service._get_gift_id(3) == "premium_3_months"
    assert delivery_service._get_gift_id(6) == "premium_6_months"
    assert delivery_service._get_gift_id(12) == "premium_12_months"
    
    # 无效月数应该返回默认值
    assert delivery_service._get_gift_id(99) == "premium_3_months"


@pytest.mark.asyncio
async def test_determine_status(delivery_service):
    """测试状态判断"""
    # 全部失败
    assert delivery_service._determine_status(0, 3) == OrderStatus.PAID
    
    # 全部成功
    assert delivery_service._determine_status(3, 3) == OrderStatus.DELIVERED
    
    # 部分成功
    assert delivery_service._determine_status(2, 3) == OrderStatus.PARTIAL


@pytest.mark.asyncio
async def test_deliver_premium_invalid_order_type(delivery_service):
    """测试无效订单类型"""
    order = Order(
        order_id="test-123",
        base_amount=10.0,
        unique_suffix=123,
        total_amount=10.123,
        user_id=123456,
        order_type=OrderType.OTHER,  # 非 Premium 类型
        expires_at=datetime.now() + timedelta(minutes=30)
    )
    
    with pytest.raises(ValueError, match="Order type must be 'premium'"):
        await delivery_service.deliver_premium(order)


@pytest.mark.asyncio
async def test_deliver_premium_missing_recipients(delivery_service):
    """测试缺少收件人"""
    order = Order(
        order_id="test-123",
        base_amount=10.0,
        unique_suffix=123,
        total_amount=10.123,
        user_id=123456,
        order_type=OrderType.PREMIUM,
        premium_months=3,
        recipients=None,  # 缺少收件人
        expires_at=datetime.now() + timedelta(minutes=30)
    )
    
    with pytest.raises(ValueError, match="Invalid premium order"):
        await delivery_service.deliver_premium(order)


@pytest.mark.asyncio
async def test_resolve_username_not_found(delivery_service):
    """测试解析用户名（未找到）"""
    # 当前实现返回 None（占位）
    user_id = await delivery_service._resolve_username("alice")
    assert user_id is None


@pytest.mark.redis  # 标记为需要 Redis 的集成测试
class TestPremiumDeliveryIntegration:
    """Premium 交付集成测试"""
    
    @pytest.mark.asyncio
    async def test_full_delivery_flow(self, delivery_service, sample_order, mock_bot):
        """测试完整交付流程"""
        # 模拟所有用户未绑定（当前实现）
        results = await delivery_service.deliver_premium(sample_order)
        
        # 所有收件人都应该失败（因为未实现绑定功能）
        assert len(results) == 3
        for username, result in results.items():
            assert result.success is False
            assert result.error == "User not found or not bound"
        
        # Bot 不应该被调用（因为没有成功解析用户）
        mock_bot.send_gift.assert_not_called()
