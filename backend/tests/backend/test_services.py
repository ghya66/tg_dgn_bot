"""
测试 Service 层
"""
import pytest
from unittest.mock import Mock, MagicMock
from datetime import datetime, timedelta
from backend.api.services.premium_service import PremiumService
from backend.api.services.wallet_service import WalletService
from backend.api.services.order_service import OrderService


@pytest.fixture
def mock_repos():
    """创建 Mock Repositories"""
    order_repo = Mock()
    user_repo = Mock()
    setting_repo = Mock()
    
    return order_repo, user_repo, setting_repo


class TestPremiumService:
    """测试 PremiumService"""
    
    def test_validate_duration(self, mock_repos):
        """测试时长验证"""
        order_repo, user_repo, setting_repo = mock_repos
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        assert service.validate_duration(3) is True
        assert service.validate_duration(6) is True
        assert service.validate_duration(12) is True
        assert service.validate_duration(1) is False
        assert service.validate_duration(24) is False
    
    def test_calculate_amount(self, mock_repos):
        """测试金额计算"""
        order_repo, user_repo, setting_repo = mock_repos
        setting_repo.get_value.return_value = 10.0
        
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        amount = service.calculate_amount(3)
        assert amount == 10.0
        
        setting_repo.get_value.assert_called_with("premium_price_3m", default=10.0)
    
    def test_create_premium_order_success(self, mock_repos):
        """测试创建Premium订单（成功）"""
        order_repo, user_repo, setting_repo = mock_repos
        
        # Mock 返回值
        user_repo.get_or_create.return_value = Mock(user_id=123)
        setting_repo.get_value.side_effect = lambda key, default=None: {
            "premium_price_3m": 10.0,
            "order_timeout_minutes": 30,
            "usdt_trc20_receive_addr": "TTestAddress"
        }.get(key, default)
        
        mock_order = Mock(
            order_id="PREM001",
            user_id=123,
            status="pending",
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        order_repo.create_order.return_value = mock_order
        
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        # 创建订单
        result = service.create_premium_order(
            user_id=123,
            duration_months=3,
            recipient="@testuser",
            unique_suffix="456"
        )
        
        assert result["order_id"] == "PREM001"
        assert result["pay_amount"] == 10.456
        assert result["base_amount"] == 10.0
        assert result["recipient"] == "@testuser"
        
        order_repo.create_order.assert_called_once()
    
    def test_create_premium_order_invalid_duration(self, mock_repos):
        """测试创建Premium订单（无效时长）"""
        order_repo, user_repo, setting_repo = mock_repos
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        with pytest.raises(ValueError, match="Invalid duration"):
            service.create_premium_order(
                user_id=123,
                duration_months=99,
                recipient="@testuser",
                unique_suffix="456"
            )
    
    def test_process_payment_success(self, mock_repos):
        """测试处理支付（成功）"""
        order_repo, user_repo, setting_repo = mock_repos
        
        # Mock 待支付订单
        mock_order = Mock(status="PENDING")
        order_repo.get_by_order_id.return_value = mock_order
        
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        result = service.process_payment("PREM001")
        
        assert result is True
        order_repo.update_status.assert_called_once_with("PREM001", "PAID")
    
    def test_process_payment_not_found(self, mock_repos):
        """测试处理支付（订单不存在）"""
        order_repo, user_repo, setting_repo = mock_repos
        order_repo.get_by_order_id.return_value = None
        
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        result = service.process_payment("NOTFOUND")
        assert result is False
    
    def test_process_payment_already_paid(self, mock_repos):
        """测试处理支付（已支付）"""
        order_repo, user_repo, setting_repo = mock_repos
        
        # Mock 已支付订单
        mock_order = Mock(status="PAID")
        order_repo.get_by_order_id.return_value = mock_order
        
        service = PremiumService(order_repo, user_repo, setting_repo)
        
        result = service.process_payment("PREM001")
        assert result is False


class TestWalletService:
    """测试 WalletService"""
    
    def test_get_balance(self, mock_repos):
        """测试获取余额"""
        order_repo, user_repo, setting_repo = mock_repos
        user_repo.get_balance.return_value = 100.0
        
        service = WalletService(order_repo, user_repo, setting_repo)
        
        balance = service.get_balance(123)
        assert balance == 100.0
        user_repo.get_balance.assert_called_once_with(123)
    
    def test_create_deposit_order(self, mock_repos):
        """测试创建充值订单"""
        order_repo, user_repo, setting_repo = mock_repos
        
        user_repo.get_or_create.return_value = Mock(user_id=123)
        setting_repo.get_value.side_effect = lambda key, default=None: {
            "order_timeout_minutes": 30,
            "usdt_trc20_receive_addr": "TTestAddress"
        }.get(key, default)
        
        mock_order = Mock(
            order_id="DEP001",
            user_id=123,
            status="pending",
            expires_at=datetime.now() + timedelta(minutes=30)
        )
        order_repo.create_order.return_value = mock_order
        
        service = WalletService(order_repo, user_repo, setting_repo)
        
        result = service.create_deposit_order(
            user_id=123,
            amount=50.0,
            unique_suffix="789"
        )
        
        assert result["order_id"] == "DEP001"
        assert result["pay_amount"] == 50.789
        assert result["base_amount"] == 50.0
    
    def test_process_deposit_success(self, mock_repos):
        """测试处理充值（成功）"""
        order_repo, user_repo, setting_repo = mock_repos
        
        mock_order = Mock(
            status="pending",
            user_id=123,
            base_amount=50.0
        )
        order_repo.get_by_order_id.return_value = mock_order
        
        service = WalletService(order_repo, user_repo, setting_repo)
        
        result = service.process_deposit("DEP001")
        
        assert result is True
        order_repo.update_status.assert_called_once_with("DEP001", "paid")
        user_repo.update_balance.assert_called_once_with(123, 50.0)
    
    def test_debit_success(self, mock_repos):
        """测试扣费（成功）"""
        order_repo, user_repo, setting_repo = mock_repos
        user_repo.debit_balance.return_value = Mock()
        
        service = WalletService(order_repo, user_repo, setting_repo)
        
        result = service.debit(123, 30.0, reason="test")
        
        assert result is True
        user_repo.debit_balance.assert_called_once_with(123, 30.0)
    
    def test_debit_insufficient_balance(self, mock_repos):
        """测试扣费（余额不足）"""
        order_repo, user_repo, setting_repo = mock_repos
        user_repo.debit_balance.side_effect = ValueError("Insufficient balance")
        
        service = WalletService(order_repo, user_repo, setting_repo)
        
        result = service.debit(123, 999.0)
        assert result is False


class TestOrderService:
    """测试 OrderService"""
    
    def test_get_order(self, mock_repos):
        """测试获取订单详情"""
        order_repo, _, setting_repo = mock_repos
        
        mock_order = Mock(
            order_id="ORD001",
            user_id=123,
            order_type="premium",
            base_amount=10.0,
            total_amount=10.456,
            status="paid",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1),
            metadata={}
        )
        order_repo.get_by_order_id.return_value = mock_order
        
        service = OrderService(order_repo, setting_repo)
        
        result = service.get_order("ORD001")
        
        assert result is not None
        assert result["order_id"] == "ORD001"
        assert result["status"] == "paid"
    
    def test_get_order_not_found(self, mock_repos):
        """测试获取订单（不存在）"""
        order_repo, _, setting_repo = mock_repos
        order_repo.get_by_order_id.return_value = None
        
        service = OrderService(order_repo, setting_repo)
        
        result = service.get_order("NOTFOUND")
        assert result is None
    
    def test_cancel_order_success(self, mock_repos):
        """测试取消订单（成功）"""
        order_repo, _, setting_repo = mock_repos
        
        mock_order = Mock(status="pending")
        order_repo.get_by_order_id.return_value = mock_order
        
        service = OrderService(order_repo, setting_repo)
        
        result = service.cancel_order("ORD001")
        
        assert result is True
        order_repo.update_status.assert_called_once_with("ORD001", "cancelled")
    
    def test_cancel_order_already_paid(self, mock_repos):
        """测试取消订单（已支付）"""
        order_repo, _, setting_repo = mock_repos
        
        mock_order = Mock(status="paid")
        order_repo.get_by_order_id.return_value = mock_order
        
        service = OrderService(order_repo, setting_repo)
        
        result = service.cancel_order("ORD001")
        assert result is False
    
    def test_expire_pending_orders(self, mock_repos):
        """测试过期待支付订单"""
        order_repo, _, setting_repo = mock_repos
        
        # Mock 3个过期订单
        mock_orders = [
            Mock(order_id=f"ORD{i}") for i in range(3)
        ]
        order_repo.get_pending_orders.return_value = mock_orders
        
        service = OrderService(order_repo, setting_repo)
        
        count = service.expire_pending_orders()
        
        assert count == 3
        assert order_repo.update_status.call_count == 3
