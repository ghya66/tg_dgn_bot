"""
API 集成测试

测试所有 API 端点的完整功能。

覆盖范围:
- 认证流程
- 管理员 API（订单、统计）
- Webhook API（TRC20 回调）
- 健康检查 API
- 中间件集成（限流、日志、白名单）
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.api.main import app
from backend.api.database import get_db
from backend.api.infrastructure import get_redis


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def test_db():
    """创建测试数据库（内存 SQLite）"""
    from src.database import Base
    
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    TestingSessionLocal = sessionmaker(bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
    
    app.dependency_overrides[get_db] = override_get_db
    yield TestingSessionLocal()
    app.dependency_overrides.clear()


@pytest.fixture
def mock_redis():
    """Mock Redis 客户端"""
    redis_mock = Mock()
    redis_mock.ping = Mock(return_value=True)
    redis_mock.llen = Mock(return_value=0)
    redis_mock.keys = Mock(return_value=[b"arq:worker:test"])
    
    async def override_get_redis():
        yield redis_mock
    
    app.dependency_overrides[get_redis] = override_get_redis
    yield redis_mock
    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db, mock_redis):
    """测试客户端"""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """有效的 API Key"""
    return "test-api-key-123"


@pytest.fixture
def auth_headers(valid_api_key):
    """认证头"""
    return {"X-API-Key": valid_api_key}


# ============================================================================
# 根路径测试
# ============================================================================

def test_root_endpoint(client):
    """测试根路径返回 API 信息"""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "TG DGN Bot Backend API"
    assert data["status"] == "running"


# ============================================================================
# 认证测试
# ============================================================================

def test_admin_api_requires_auth(client):
    """测试管理员 API 需要认证"""
    response = client.get("/api/admin/orders")
    assert response.status_code == 401
    assert "Missing API Key" in response.json()["detail"]


def test_admin_api_invalid_key(client):
    """测试无效 API Key 被拒绝"""
    response = client.get(
        "/api/admin/orders",
        headers={"X-API-Key": "invalid-key"},
    )
    assert response.status_code == 403
    assert "Invalid API Key" in response.json()["detail"]


@pytest.mark.skip("需要配置有效的 API Key")
def test_admin_api_valid_key(client, auth_headers):
    """测试有效 API Key 可以访问"""
    response = client.get("/api/admin/orders", headers=auth_headers)
    assert response.status_code in [200, 429]  # 200 成功 or 429 限流


# ============================================================================
# 管理员 API - 订单列表测试
# ============================================================================

@pytest.mark.skip("需要配置有效的 API Key")
def test_list_orders_empty(client, auth_headers):
    """测试查询空订单列表"""
    response = client.get("/api/admin/orders", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["orders"] == []


@pytest.mark.skip("需要配置有效的 API Key")
def test_list_orders_with_filters(client, auth_headers, test_db):
    """测试订单列表过滤功能"""
    # 创建测试订单
    from src.database import DepositOrder
    from datetime import datetime, timedelta
    
    order = DepositOrder(
        order_id="PREM12345678",
        user_id=123,
        base_amount=10.0,
        unique_suffix=123,
        total_amount=10.123,
        amount_micro_usdt=10_123_000,
        status="PENDING",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    test_db.add(order)
    test_db.commit()
    
    # 测试过滤
    response = client.get(
        "/api/admin/orders?status=PENDING",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1


@pytest.mark.skip("需要配置有效的 API Key")
def test_list_orders_pagination(client, auth_headers):
    """测试订单列表分页"""
    response = client.get(
        "/api/admin/orders?page=1&page_size=10",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 10


# ============================================================================
# 管理员 API - 单个订单测试
# ============================================================================

@pytest.mark.skip("需要配置有效的 API Key")
def test_get_order_not_found(client, auth_headers):
    """测试查询不存在的订单"""
    response = client.get("/api/admin/orders/NONEXIST", headers=auth_headers)
    assert response.status_code == 404


@pytest.mark.skip("需要配置有效的 API Key")
def test_get_order_success(client, auth_headers, test_db):
    """测试查询订单详情"""
    # 创建测试订单
    from src.database import DepositOrder
    from datetime import datetime, timedelta
    
    order = DepositOrder(
        order_id="TEST12345678",
        user_id=123,
        base_amount=10.0,
        unique_suffix=456,
        total_amount=10.456,
        amount_micro_usdt=10_456_000,
        status="PAID",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    test_db.add(order)
    test_db.commit()
    
    response = client.get("/api/admin/orders/TEST12345678", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["order_id"] == "TEST12345678"
    assert data["status"] == "PAID"


# ============================================================================
# 管理员 API - 更新订单测试
# ============================================================================

@pytest.mark.skip("需要配置有效的 API Key")
def test_update_order_status(client, auth_headers, test_db):
    """测试更新订单状态"""
    # 创建测试订单
    from src.database import DepositOrder
    from datetime import datetime, timedelta
    
    order = DepositOrder(
        order_id="UPDATE123456",
        user_id=123,
        base_amount=10.0,
        unique_suffix=789,
        total_amount=10.789,
        amount_micro_usdt=10_789_000,
        status="PAID",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    test_db.add(order)
    test_db.commit()
    
    # 更新状态
    response = client.put(
        "/api/admin/orders/UPDATE123456",
        headers=auth_headers,
        json={"status": "DELIVERED"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "DELIVERED"


# ============================================================================
# 管理员 API - 取消订单测试
# ============================================================================

@pytest.mark.skip("需要配置有效的 API Key")
def test_cancel_order(client, auth_headers, test_db):
    """测试取消订单"""
    # 创建测试订单
    from src.database import DepositOrder
    from datetime import datetime, timedelta
    
    order = DepositOrder(
        order_id="CANCEL123456",
        user_id=123,
        base_amount=10.0,
        unique_suffix=111,
        total_amount=10.111,
        amount_micro_usdt=10_111_000,
        status="PENDING",
        created_at=datetime.now(),
        expires_at=datetime.now() + timedelta(minutes=30),
    )
    test_db.add(order)
    test_db.commit()
    
    # 取消订单
    response = client.delete(
        "/api/admin/orders/CANCEL123456?reason=test",
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "cancelled successfully" in response.json()["message"]


# ============================================================================
# 管理员 API - 统计测试
# ============================================================================

@pytest.mark.skip("需要配置有效的 API Key")
def test_get_summary_stats(client, auth_headers):
    """测试获取统计摘要"""
    response = client.get("/api/admin/stats/summary", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "by_type" in data


# ============================================================================
# Webhook API 测试
# ============================================================================

def test_webhook_health(client):
    """测试 Webhook 健康检查（公开访问）"""
    response = client.get("/api/webhook/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.skip("需要 Mock 签名验证")
def test_trc20_callback_invalid_signature(client):
    """测试 TRC20 回调签名验证失败"""
    payload = {
        "order_id": "TEST12345678",
        "tx_hash": "abc123",
        "from_address": "TTest123",
        "to_address": "TTest456",
        "amount_usdt": 10.123,
        "block_number": 12345,
        "timestamp": 1234567890,
    }
    
    response = client.post(
        "/api/webhook/trc20",
        json=payload,
        headers={"X-Signature": "invalid-signature"},
    )
    assert response.status_code == 400


# ============================================================================
# 健康检查 API 测试
# ============================================================================

def test_health_overall(client, mock_redis):
    """测试整体健康检查"""
    response = client.get("/health/")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "checks" in data


def test_health_database(client):
    """测试数据库健康检查"""
    response = client.get("/health/db")
    assert response.status_code == 200
    data = response.json()
    assert data["healthy"] is True


def test_health_redis(client, mock_redis):
    """测试 Redis 健康检查"""
    response = client.get("/health/redis")
    assert response.status_code == 200
    data = response.json()
    assert data["healthy"] is True


def test_health_worker(client, mock_redis):
    """测试 Worker 健康检查"""
    response = client.get("/health/worker")
    assert response.status_code == 200
    # Worker 状态取决于 Mock 配置


# ============================================================================
# Metrics 端点测试
# ============================================================================

def test_metrics_endpoint(client):
    """测试 Prometheus 指标端点"""
    response = client.get("/metrics")
    assert response.status_code == 200
    # Prometheus 格式文本
    assert "text/plain" in response.headers["content-type"]
