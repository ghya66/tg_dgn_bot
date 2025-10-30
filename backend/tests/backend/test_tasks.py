"""
测试异步任务
"""
import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.api.tasks.premium_task import (
    deliver_premium_task,
    batch_deliver_premiums,
    PremiumDeliveryError,
    TelegramAPIError
)
from backend.api.tasks.order_task import (
    expire_pending_orders_task,
    cancel_order_task
)
from src.database import Base, DepositOrder


@pytest.fixture
def db_session():
    """创建测试数据库会话"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    
    session = Session(engine)
    yield session
    
    session.close()


@pytest.fixture
def mock_order(db_session):
    """创建测试订单"""
    order = DepositOrder(
        order_id="PREM001",
        user_id=123,
        base_amount=10.0,
        unique_suffix=456,
        total_amount=10.456,
        amount_micro_usdt=10_456_000,
        status="PAID",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(hours=1)
    )
    order.metadata = {
        "duration_months": 3,
        "recipient": "@testuser"
    }
    db_session.add(order)
    db_session.commit()
    return order


class TestPremiumDeliveryTask:
    """测试 Premium 交付任务"""
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.SessionLocal")
    @patch("backend.api.tasks.premium_task._call_telegram_gift_premium")
    async def test_deliver_premium_success(
        self,
        mock_telegram_api,
        mock_session_local,
        db_session,
        mock_order
    ):
        """测试 Premium 交付成功"""
        # Mock 数据库会话
        mock_session_local.return_value = db_session
        
        # Mock Telegram API 调用
        mock_telegram_api.return_value = {
            "ok": True,
            "result": {"user_id": "@testuser", "duration_months": 3}
        }
        
        # 执行任务
        result = await deliver_premium_task({}, "PREM001")
        
        assert result["success"] is True
        assert result["order_id"] == "PREM001"
        assert result["recipient"] == "@testuser"
        assert result["duration_months"] == 3
        
        # 验证订单状态已更新
        updated_order = db_session.query(DepositOrder).filter_by(order_id="PREM001").first()
        assert updated_order.status == "DELIVERED"
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.SessionLocal")
    async def test_deliver_premium_order_not_found(self, mock_session_local, db_session):
        """测试订单不存在"""
        mock_session_local.return_value = db_session
        
        with pytest.raises(PremiumDeliveryError, match="Order not found"):
            await deliver_premium_task({}, "NOTFOUND")
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.SessionLocal")
    async def test_deliver_premium_order_not_paid(
        self,
        mock_session_local,
        db_session,
        mock_order
    ):
        """测试订单未支付"""
        mock_session_local.return_value = db_session
        
        # 修改订单状态为 PENDING
        mock_order.status = "PENDING"
        db_session.commit()
        
        result = await deliver_premium_task({}, "PREM001")
        
        assert result["success"] is False
        assert "PENDING" in result["reason"]
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.SessionLocal")
    async def test_deliver_premium_recipient_missing(
        self,
        mock_session_local,
        db_session,
        mock_order
    ):
        """测试收件人缺失"""
        mock_session_local.return_value = db_session
        
        # 移除 recipient
        mock_order.metadata = {"duration_months": 3}
        db_session.commit()
        
        with pytest.raises(PremiumDeliveryError, match="Recipient not found"):
            await deliver_premium_task({}, "PREM001")
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.SessionLocal")
    @patch("backend.api.tasks.premium_task._call_telegram_gift_premium")
    async def test_deliver_premium_telegram_api_error(
        self,
        mock_telegram_api,
        mock_session_local,
        db_session,
        mock_order
    ):
        """测试 Telegram API 调用失败"""
        mock_session_local.return_value = db_session
        
        # Mock API 调用失败
        mock_telegram_api.side_effect = TelegramAPIError("API error")
        
        with pytest.raises(TelegramAPIError):
            await deliver_premium_task({}, "PREM001")
        
        # 验证订单状态已更新为 PARTIAL
        updated_order = db_session.query(DepositOrder).filter_by(order_id="PREM001").first()
        assert updated_order.status == "PARTIAL"
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.premium_task.deliver_premium_task")
    async def test_batch_deliver_premiums(self, mock_deliver_task):
        """测试批量交付"""
        # Mock 单个交付任务
        mock_deliver_task.side_effect = [
            {"success": True, "order_id": "PREM001"},
            {"success": True, "order_id": "PREM002"},
            Exception("Delivery failed")
        ]
        
        result = await batch_deliver_premiums({}, ["PREM001", "PREM002", "PREM003"])
        
        assert result["total"] == 3
        assert result["success"] == 2
        assert result["failed"] == 1


class TestOrderTask:
    """测试订单任务"""
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.order_task.SessionLocal")
    async def test_expire_pending_orders(self, mock_session_local, db_session):
        """测试订单过期检查"""
        mock_session_local.return_value = db_session
        
        # 创建过期订单
        expired_order = DepositOrder(
            order_id="PREM_EXPIRED",
            user_id=123,
            base_amount=10.0,
            unique_suffix=789,
            total_amount=10.789,
            amount_micro_usdt=10_789_000,
            status="PENDING",
            created_at=datetime.now() - timedelta(hours=2),
            expires_at=datetime.now() - timedelta(hours=1)
        )
        db_session.add(expired_order)
        db_session.commit()
        
        # 执行任务
        result = await expire_pending_orders_task({})
        
        assert result["total"] >= 1
        assert result["expired"] >= 1
        
        # 验证订单状态已更新
        updated_order = db_session.query(DepositOrder).filter_by(order_id="PREM_EXPIRED").first()
        assert updated_order.status == "EXPIRED"
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.order_task.SessionLocal")
    async def test_cancel_order_success(self, mock_session_local, db_session):
        """测试取消订单"""
        mock_session_local.return_value = db_session
        
        # 创建待支付订单
        order = DepositOrder(
            order_id="PREM_CANCEL",
            user_id=123,
            base_amount=10.0,
            unique_suffix=999,
            total_amount=10.999,
            amount_micro_usdt=10_999_000,
            status="PENDING",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        db_session.add(order)
        db_session.commit()
        
        # 执行任务
        result = await cancel_order_task({}, "PREM_CANCEL", "user_requested")
        
        assert result["success"] is True
        assert result["order_id"] == "PREM_CANCEL"
        
        # 验证订单状态已更新
        updated_order = db_session.query(DepositOrder).filter_by(order_id="PREM_CANCEL").first()
        assert updated_order.status == "CANCELLED"
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.order_task.SessionLocal")
    async def test_cancel_order_not_found(self, mock_session_local, db_session):
        """测试取消不存在的订单"""
        mock_session_local.return_value = db_session
        
        result = await cancel_order_task({}, "NOTFOUND", "user_requested")
        
        assert result["success"] is False
        assert "not found" in result["reason"]
    
    @pytest.mark.asyncio
    @patch("backend.api.tasks.order_task.SessionLocal")
    async def test_cancel_order_already_paid(self, mock_session_local, db_session):
        """测试取消已支付订单"""
        mock_session_local.return_value = db_session
        
        # 创建已支付订单
        order = DepositOrder(
            order_id="PREM_PAID",
            user_id=123,
            base_amount=10.0,
            unique_suffix=888,
            total_amount=10.888,
            amount_micro_usdt=10_888_000,
            status="PAID",
            created_at=datetime.now(),
            expires_at=datetime.now() + timedelta(hours=1)
        )
        db_session.add(order)
        db_session.commit()
        
        result = await cancel_order_task({}, "PREM_PAID", "user_requested")
        
        assert result["success"] is False
        assert "PAID" in result["reason"]
