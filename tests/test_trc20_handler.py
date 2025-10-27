"""
TRC20处理器测试
"""
import pytest
import time
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta

from src.webhook.trc20_handler import TRC20Handler
from src.models import Order, OrderStatus


class TestTRC20Handler:
    """TRC20处理器测试类"""
    
    @pytest.fixture
    def handler(self):
        """创建 TRC20Handler 实例"""
        return TRC20Handler()
    
    def test_validate_tron_address(self):
        """测试波场地址验证"""
        # 有效地址
        valid_addresses = [
            "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",
            "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "TPYmHEhy5n8TCEfYGqW2rPxsghSfzghPDn"
        ]
        
        for addr in valid_addresses:
            assert TRC20Handler.validate_tron_address(addr) is True
        
        # 无效地址
        invalid_addresses = [
            "0x1234567890123456789012345678901234567890",  # ETH地址
            "1BvBMSEYstWetqTFn5Au4m4GFg7xJaNVN2",  # BTC地址
            "TLyqzVGLV1srkB7dToTAEqgDSfPtXRJZY",  # 长度不够
            "ALyqzVGLV1srkB7dToTAEqgDSfPtXRJZYH",  # 不以T开头
            "",  # 空字符串
            "invalid_address"  # 完全无效
        ]
        
        for addr in invalid_addresses:
            assert TRC20Handler.validate_tron_address(addr) is False
    
    @pytest.mark.asyncio
    async def test_handle_webhook_success(self, handler):
        """测试成功处理webhook"""
        # 模拟有效的回调数据
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123,
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time()),
            "signature": "valid_signature"
        }
        
        with patch('src.webhook.trc20_handler.signature_validator') as mock_validator:
            with patch.object(handler, '_process_payment') as mock_process:
                # 模拟签名验证成功
                mock_validator.verify_signature.return_value = True
                
                # 模拟支付处理成功
                mock_process.return_value = {
                    "success": True,
                    "order_id": "test_order_123"
                }
                
                result = await handler.handle_webhook(payload)
                
                assert result["success"] is True
                assert result["order_id"] == "test_order_123"
                
                # 验证调用
                mock_validator.verify_signature.assert_called_once()
                mock_process.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_handle_webhook_missing_fields(self, handler):
        """测试缺少必需字段的webhook"""
        # 缺少signature字段
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123,
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time())
        }
        
        result = await handler.handle_webhook(payload)
        
        assert result["success"] is False
        assert "Missing required field: signature" in result["error"]
    
    @pytest.mark.asyncio
    async def test_handle_webhook_invalid_signature(self, handler):
        """测试无效签名的webhook"""
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123,
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time()),
            "signature": "invalid_signature"
        }
        
        with patch('src.webhook.trc20_handler.signature_validator') as mock_validator:
            # 模拟签名验证失败
            mock_validator.verify_signature.return_value = False
            
            result = await handler.handle_webhook(payload)
            
            assert result["success"] is False
            assert result["error"] == "Invalid signature"
    
    @pytest.mark.asyncio
    async def test_process_payment_success(self, handler):
        """测试成功处理支付"""
        from src.models import PaymentCallback
        
        # 创建测试订单
        order = Order(
            order_id="test_order_123",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        # 创建回调数据
        callback = PaymentCallback(
            order_id="test_order_123",
            amount=10.123,
            tx_hash="test_tx_hash",
            block_number=12345678,
            timestamp=int(time.time()),
            signature="test_signature"
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            with patch('src.webhook.trc20_handler.AmountCalculator') as mock_calculator:
                # 模拟订单查找成功
                mock_manager.find_order_by_amount = AsyncMock(return_value=order)
                
                # 模拟金额匹配
                mock_calculator.verify_amount.return_value = True
                
                # 模拟状态更新成功
                mock_manager.update_order_status = AsyncMock(return_value=True)
                
                result = await handler._process_payment(callback)
                
                assert result["success"] is True
                assert result["order_id"] == "test_order_123"
                assert result["tx_hash"] == "test_tx_hash"
    
    @pytest.mark.asyncio
    async def test_process_payment_order_not_found(self, handler):
        """测试订单未找到"""
        from src.models import PaymentCallback
        
        callback = PaymentCallback(
            order_id="nonexistent_order",
            amount=10.123,
            tx_hash="test_tx_hash",
            block_number=12345678,
            timestamp=int(time.time()),
            signature="test_signature"
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            # 模拟订单未找到
            mock_manager.find_order_by_amount = AsyncMock(return_value=None)
            
            result = await handler._process_payment(callback)
            
            assert result["success"] is False
            assert "Order not found" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment_order_id_mismatch(self, handler):
        """测试订单ID不匹配"""
        from src.models import PaymentCallback
        
        # 创建测试订单
        order = Order(
            order_id="different_order_id",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        callback = PaymentCallback(
            order_id="test_order_123",
            amount=10.123,
            tx_hash="test_tx_hash",
            block_number=12345678,
            timestamp=int(time.time()),
            signature="test_signature"
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            # 模拟找到订单但ID不匹配
            mock_manager.find_order_by_amount = AsyncMock(return_value=order)
            
            result = await handler._process_payment(callback)
            
            assert result["success"] is False
            assert "Order ID mismatch" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment_amount_mismatch(self, handler):
        """测试金额不匹配"""
        from src.models import PaymentCallback
        
        order = Order(
            order_id="test_order_123",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        callback = PaymentCallback(
            order_id="test_order_123",
            amount=10.456,  # 不匹配的金额
            tx_hash="test_tx_hash",
            block_number=12345678,
            timestamp=int(time.time()),
            signature="test_signature"
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            with patch('src.webhook.trc20_handler.AmountCalculator') as mock_calculator:
                # 模拟订单查找成功
                mock_manager.find_order_by_amount = AsyncMock(return_value=order)
                
                # 模拟金额不匹配
                mock_calculator.verify_amount.return_value = False
                
                result = await handler._process_payment(callback)
                
                assert result["success"] is False
                assert "Amount mismatch" in result["error"]
    
    @pytest.mark.asyncio
    async def test_process_payment_expired_order(self, handler):
        """测试过期订单"""
        from src.models import PaymentCallback
        
        # 创建过期订单
        order = Order(
            order_id="test_order_123",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() - timedelta(minutes=5)  # 过期
        )
        
        callback = PaymentCallback(
            order_id="test_order_123",
            amount=10.123,
            tx_hash="test_tx_hash",
            block_number=12345678,
            timestamp=int(time.time()),
            signature="test_signature"
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            with patch('src.webhook.trc20_handler.AmountCalculator') as mock_calculator:
                # 模拟订单查找成功
                mock_manager.find_order_by_amount = AsyncMock(return_value=order)
                
                # 模拟金额匹配
                mock_calculator.verify_amount.return_value = True
                
                # 模拟状态更新成功
                mock_manager.update_order_status = AsyncMock(return_value=True)
                
                result = await handler._process_payment(callback)
                
                assert result["success"] is False
                assert "Order expired" in result["error"]
    
    @pytest.mark.asyncio
    async def test_simulate_payment(self, handler):
        """测试模拟支付"""
        order = Order(
            order_id="test_order_123",
            base_amount=10.0,
            unique_suffix=123,
            total_amount=10.123,
            user_id=12345,
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        
        with patch('src.webhook.trc20_handler.order_manager') as mock_manager:
            with patch('src.webhook.trc20_handler.signature_validator') as mock_validator:
                with patch('src.webhook.trc20_handler.TRC20Handler.handle_webhook') as mock_handle:
                    # 模拟获取订单成功
                    mock_manager.get_order = AsyncMock(return_value=order)
                    
                    # 模拟签名生成
                    mock_validator.create_signed_callback.return_value = {
                        "order_id": "test_order_123",
                        "amount": 10.123,
                        "txid": "simulated_tx_hash",
                        "timestamp": int(time.time()),
                        "signature": "simulated_signature"
                    }
                    
                    # 模拟处理成功
                    mock_handle.return_value = {
                        "success": True,
                        "order_id": "test_order_123"
                    }
                    
                    result = await handler.simulate_payment("test_order_123")
                    
                    assert result["success"] is True
                    assert result["simulation"] is True
                    assert "callback_data" in result
    
    def test_validate_webhook_payload_valid(self, handler):
        """测试有效的webhook载荷验证"""
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123,
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time()),
            "signature": "valid_signature"
        }
        
        result = handler.validate_webhook_payload(payload)
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
    
    def test_validate_webhook_payload_missing_fields(self, handler):
        """测试缺少字段的载荷验证"""
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123
            # 缺少 txid, timestamp, signature
        }
        
        result = handler.validate_webhook_payload(payload)
        
        assert result["valid"] is False
        assert len(result["errors"]) == 3  # 缺少3个字段
        assert any("Missing field: txid" in error for error in result["errors"])
        assert any("Missing field: timestamp" in error for error in result["errors"])
        assert any("Missing field: signature" in error for error in result["errors"])
    
    def test_validate_webhook_payload_invalid_types(self, handler):
        """测试无效类型的载荷验证"""
        payload = {
            "order_id": 123,  # 应该是字符串
            "amount": "10.123",  # 应该是数字
            "txid": 12345,  # 应该是字符串
            "timestamp": "invalid",  # 应该是整数
            "signature": 456  # 应该是字符串
        }
        
        result = handler.validate_webhook_payload(payload)
        
        assert result["valid"] is False
        assert len(result["errors"]) >= 4  # 多个类型错误
    
    def test_validate_webhook_payload_invalid_amount(self, handler):
        """测试无效金额的载荷验证"""
        payload = {
            "order_id": "test_order_123",
            "amount": 10.0,  # 无效：没有3位小数后缀
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time()),
            "signature": "valid_signature"
        }
        
        result = handler.validate_webhook_payload(payload)
        
        assert result["valid"] is False
        assert any("Invalid payment amount" in error for error in result["errors"])
    
    def test_validate_webhook_payload_old_timestamp(self, handler):
        """测试过旧时间戳的载荷验证"""
        payload = {
            "order_id": "test_order_123",
            "amount": 10.123,
            "txid": "test_tx_hash_12345",
            "timestamp": int(time.time()) - 400,  # 400秒前（超过5分钟）
            "signature": "valid_signature"
        }
        
        result = handler.validate_webhook_payload(payload)
        
        assert result["valid"] is False
        assert any("Timestamp too old" in error for error in result["errors"])