"""
集成测试：验证完整的支付流程
"""
import pytest
import asyncio
import time
from unittest.mock import AsyncMock, patch

from src.payments.suffix_manager import SuffixManager
from src.payments.amount_calculator import AmountCalculator
from src.payments.order import OrderManager
from src.webhook.trc20_handler import TRC20Handler
from src.signature import SignatureValidator
from src.models import OrderStatus, OrderType


@pytest.mark.asyncio
async def test_complete_payment_flow():
    """测试完整的支付流程：创建订单 -> 模拟回调 -> 验证状态更新"""
    
    # 1. 初始化组件（模拟Redis）
    from unittest.mock import MagicMock
    suffix_manager = SuffixManager()
    suffix_manager.redis_client = MagicMock()
    suffix_manager.redis_client.keys = AsyncMock(return_value=[])
    suffix_manager.redis_client.set = AsyncMock(return_value=True)
    suffix_manager.redis_client.eval = AsyncMock(return_value=1)  # 用于 release_suffix
    
    order_manager = OrderManager()
    order_manager.redis_client = MagicMock()
    
    # 2. 配置 Redis pipeline mock
    mock_pipeline = MagicMock()
    mock_pipeline.set = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[True, True])
    order_manager.redis_client.pipeline.return_value = mock_pipeline
    
    # 3. 创建订单
    with patch('src.payments.order.suffix_manager', suffix_manager):
        order = await order_manager.create_order(user_id=12345, base_amount=10.0)
    
    assert order is not None
    assert order.user_id == 12345
    assert order.base_amount == 10.0
    assert 1 <= order.unique_suffix <= 999
    assert order.total_amount == AmountCalculator.generate_payment_amount(10.0, order.unique_suffix)
    assert order.status == OrderStatus.PENDING
    
    # 5. 模拟获取订单（用于回调处理）
    def mock_get_order(order_id):
        if order_id == order.order_id:
            return order
        return None
    
    order_manager.get_order = AsyncMock(side_effect=mock_get_order)
    
    # 6. 模拟查找订单by金额
    def mock_find_by_amount(amount):
        if AmountCalculator.verify_amount(order.total_amount, amount):
            return order
        return None
    
    order_manager.find_order_by_amount = AsyncMock(side_effect=mock_find_by_amount)
    
    # 7. 模拟状态更新
    order_manager.update_order_status = AsyncMock(return_value=True)
    
    # 8. 创建签名的回调数据
    callback_data = SignatureValidator.create_signed_callback(
        order_id=order.order_id,
        amount=order.total_amount,
        tx_hash="test_integration_tx",
        block_number=12345678,
        timestamp=int(time.time())
    )
    
    # 9. 创建 TRC20Handler 实例并处理回调
    handler = TRC20Handler(delivery_service=None)
    with patch('src.webhook.trc20_handler.order_manager', order_manager):
        result = await handler.handle_webhook(callback_data)
    
    # 10. 验证处理结果
    print(f"Result: {result}")
    assert result["success"] is True
    assert result["order_id"] == order.order_id
    
    # 11. 验证订单状态被更新
    order_manager.update_order_status.assert_called_once_with(
        order.order_id, 
        OrderStatus.PAID,
        "test_integration_tx"
    )
    
    print(f"✅ 集成测试通过：订单 {order.order_id} 成功处理支付 {order.total_amount} USDT")


@pytest.mark.redis  # 复杂的并发测试，需要更完整的mock
@pytest.mark.asyncio
@pytest.mark.redis
async def test_concurrent_order_creation(clean_redis, redis_client):
    """测试并发创建订单（使用真实 Redis，100个并发请求）"""
    
    from src.payments.suffix_manager import suffix_manager
    from src.payments.order import order_manager
    
    # 注入真实 Redis 客户端
    suffix_manager.redis_client = redis_client
    order_manager.redis_client = redis_client
    
    # 创建100个并发订单（降低数量避免超时）
    tasks = []
    for i in range(100):
        task = order_manager.create_order(
            user_id=10000 + i,
            base_amount=float(i + 1)  # 不同的基础金额
        )
        tasks.append(task)
    
    # 执行所有并发任务
    orders = await asyncio.gather(*tasks)
    
    # 验证结果
    successful_orders = [o for o in orders if o is not None]
    assert len(successful_orders) == 100, f"只有 {len(successful_orders)} 个订单创建成功"
    
    # 验证所有后缀唯一
    suffixes = [o.unique_suffix for o in successful_orders]
    assert len(set(suffixes)) == len(suffixes), "存在重复的后缀"
    
    # 验证所有金额唯一
    amounts = [o.total_amount for o in successful_orders]
    assert len(set(amounts)) == len(amounts), "存在重复的金额"
    
    print(f"✅ 并发测试通过：成功创建 {len(successful_orders)} 个唯一订单")


@pytest.mark.asyncio
async def test_payment_callback_validation():
    """测试支付回调验证流程"""
    
    # 测试各种无效回调
    invalid_callbacks = [
        # 缺少字段
        {
            "order_id": "test_order",
            "amount": 10.123
            # 缺少其他字段
        },
        # 无效签名
        {
            "order_id": "test_order",
            "amount": 10.123,
            "txid": "test_tx",
            "timestamp": int(time.time()),
            "signature": "invalid_signature"
        },
        # 金额格式错误
        {
            "order_id": "test_order",
            "amount": 10.0,  # 没有3位小数
            "txid": "test_tx",
            "timestamp": int(time.time()),
            "signature": "valid_signature"
        }
    ]
    
    # 创建 TRC20Handler 实例
    handler = TRC20Handler(delivery_service=None)
    
    for i, callback in enumerate(invalid_callbacks):
        result = await handler.handle_webhook(callback)
        assert result["success"] is False, f"回调 {i+1} 应该失败但成功了"
        print(f"✅ 无效回调 {i+1} 正确被拒绝：{result['error']}")


def test_amount_precision():
    """测试金额精度处理"""
    
    # 测试浮点精度问题
    test_cases = [
        (10.0, 123, 10.123),
        (5.5, 456, 5.956),
        (0.0, 1, 0.001),
        (999.0, 999, 999.999)
    ]
    
    for base, suffix, expected in test_cases:
        # 生成金额
        generated = AmountCalculator.generate_payment_amount(base, suffix)
        assert abs(generated - expected) < 0.0001, f"金额生成错误：{generated} != {expected}"
        
        # 验证金额匹配
        assert AmountCalculator.verify_amount(generated, expected), f"金额验证失败：{generated} vs {expected}"
        
        # 提取后缀
        extracted_suffix = AmountCalculator.extract_suffix_from_amount(generated, base)
        assert extracted_suffix == suffix, f"后缀提取错误：{extracted_suffix} != {suffix}"
    
    print("✅ 金额精度测试通过")


def test_signature_security():
    """测试签名安全性"""
    
    # 原始数据
    data = {
        "order_id": "test_order_123",
        "amount": 10.123,
        "txid": "test_tx_hash",
        "timestamp": int(time.time())
    }
    
    secret = "test_secret_key"
    
    # 生成签名
    signature = SignatureValidator.generate_signature(data, secret)
    
    # 验证正确签名
    assert SignatureValidator.verify_signature(data, signature, secret), "正确签名验证失败"
    
    # 验证错误签名
    assert not SignatureValidator.verify_signature(data, "wrong_signature", secret), "错误签名应该失败"
    
    # 验证错误密钥
    assert not SignatureValidator.verify_signature(data, signature, "wrong_secret"), "错误密钥应该失败"
    
    # 验证数据篡改
    tampered_data = data.copy()
    tampered_data["amount"] = 20.123
    assert not SignatureValidator.verify_signature(tampered_data, signature, secret), "篡改数据应该失败"
    
    print("✅ 签名安全性测试通过")


if __name__ == "__main__":
    # 运行所有测试
    asyncio.run(test_complete_payment_flow())
    asyncio.run(test_concurrent_order_creation())
    asyncio.run(test_payment_callback_validation())
    test_amount_precision()
    test_signature_security()
    
    print("\n🎉 所有集成测试通过！")