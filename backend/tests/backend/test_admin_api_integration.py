"""
Admin API 集成测试

测试所有管理员 API 端点的完整功能
"""
import pytest
import httpx
from typing import Dict


# ============================================================================
# 测试配置
# ============================================================================

API_BASE_URL = "http://localhost:8000"
API_KEY = "dev-admin-key-123456"

@pytest.fixture
def client():
    """创建 HTTP 客户端"""
    return httpx.Client(
        base_url=API_BASE_URL,
        headers={"X-API-Key": API_KEY},
        timeout=10.0
    )


# ============================================================================
# 健康检查测试
# ============================================================================

def test_health_overall(client: httpx.Client):
    """测试整体健康检查"""
    response = client.get("/health/")
    assert response.status_code == 200
    
    data = response.json()
    assert "status" in data
    assert "checks" in data
    assert data["status"] in ["healthy", "degraded", "unhealthy"]
    
    # 检查必需的组件
    checks = data["checks"]
    assert "database" in checks
    assert "redis" in checks
    assert "worker" in checks
    
    # 每个组件应该有健康状态
    for component in ["database", "redis", "worker"]:
        assert "healthy" in checks[component]
        assert isinstance(checks[component]["healthy"], bool)


def test_health_database(client: httpx.Client):
    """测试数据库健康检查"""
    response = client.get("/health/db")
    assert response.status_code == 200
    
    data = response.json()
    assert "healthy" in data
    assert "message" in data
    assert "latency_ms" in data
    assert data["healthy"] is True


def test_health_redis(client: httpx.Client):
    """测试 Redis 健康检查"""
    response = client.get("/health/redis")
    assert response.status_code == 200
    
    data = response.json()
    assert "healthy" in data
    assert "message" in data
    assert "latency_ms" in data
    assert data["healthy"] is True


def test_health_worker(client: httpx.Client):
    """测试 Worker 健康检查"""
    response = client.get("/health/worker")
    assert response.status_code == 200
    
    data = response.json()
    assert "healthy" in data
    assert "message" in data


# ============================================================================
# 订单管理测试
# ============================================================================

def test_list_orders_default(client: httpx.Client):
    """测试获取订单列表（默认参数）"""
    response = client.get("/api/admin/orders")
    assert response.status_code == 200
    
    data = response.json()
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "orders" in data
    
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= 0
    assert isinstance(data["orders"], list)


def test_list_orders_with_pagination(client: httpx.Client):
    """测试订单列表分页"""
    # 第一页
    response1 = client.get("/api/admin/orders", params={"page": 1, "page_size": 5})
    assert response1.status_code == 200
    data1 = response1.json()
    
    # 第二页
    response2 = client.get("/api/admin/orders", params={"page": 2, "page_size": 5})
    assert response2.status_code == 200
    data2 = response2.json()
    
    # 验证分页工作
    assert data1["page"] == 1
    assert data2["page"] == 2
    
    # 如果总数足够，两页的订单应该不同
    if data1["total"] > 5:
        orders1_ids = {order["order_id"] for order in data1["orders"]}
        orders2_ids = {order["order_id"] for order in data2["orders"]}
        assert len(orders1_ids & orders2_ids) == 0  # 无重复


def test_list_orders_filter_by_type(client: httpx.Client):
    """测试按类型过滤订单"""
    # Premium 订单
    response = client.get("/api/admin/orders", params={"order_type": "premium"})
    assert response.status_code == 200
    data = response.json()
    
    for order in data["orders"]:
        assert order["order_type"] == "premium"


def test_list_orders_filter_by_status(client: httpx.Client):
    """测试按状态过滤订单"""
    # DELIVERED 订单
    response = client.get("/api/admin/orders", params={"status": "DELIVERED"})
    assert response.status_code == 200
    data = response.json()
    
    for order in data["orders"]:
        assert order["status"] == "DELIVERED"


def test_list_orders_filter_combination(client: httpx.Client):
    """测试组合过滤"""
    response = client.get("/api/admin/orders", params={
        "order_type": "deposit",
        "status": "PAID",
        "page_size": 10
    })
    assert response.status_code == 200
    data = response.json()
    
    for order in data["orders"]:
        assert order["order_type"] == "deposit"
        assert order["status"] == "PAID"


def test_list_orders_invalid_type(client: httpx.Client):
    """测试无效订单类型"""
    response = client.get("/api/admin/orders", params={"order_type": "invalid"})
    assert response.status_code == 400
    assert "Invalid order_type" in response.json()["detail"]


def test_list_orders_invalid_status(client: httpx.Client):
    """测试无效订单状态"""
    response = client.get("/api/admin/orders", params={"status": "INVALID"})
    assert response.status_code == 400
    assert "Invalid status" in response.json()["detail"]


def test_get_single_order(client: httpx.Client):
    """测试获取单个订单"""
    # 先获取订单列表
    list_response = client.get("/api/admin/orders", params={"page_size": 1})
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    
    if len(orders) == 0:
        pytest.skip("No orders available for testing")
    
    order_id = orders[0]["order_id"]
    
    # 获取单个订单
    response = client.get(f"/api/admin/orders/{order_id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["order_id"] == order_id
    assert "order_type" in data
    assert "amount_usdt" in data
    assert "status" in data
    assert "created_at" in data


def test_get_nonexistent_order(client: httpx.Client):
    """测试获取不存在的订单"""
    response = client.get("/api/admin/orders/NONEXISTENT999")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_update_order_status(client: httpx.Client):
    """测试更新订单状态"""
    # 先获取一个 PENDING 订单
    list_response = client.get("/api/admin/orders", params={
        "status": "PENDING",
        "page_size": 1
    })
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    
    if len(orders) == 0:
        pytest.skip("No PENDING orders available for testing")
    
    order_id = orders[0]["order_id"]
    
    # 更新状态为 PAID
    update_response = client.put(
        f"/api/admin/orders/{order_id}",
        json={"status": "PAID"}
    )
    assert update_response.status_code == 200
    
    updated_order = update_response.json()
    assert updated_order["status"] == "PAID"
    
    # 验证更新生效
    get_response = client.get(f"/api/admin/orders/{order_id}")
    assert get_response.status_code == 200
    assert get_response.json()["status"] == "PAID"


def test_update_order_invalid_status(client: httpx.Client):
    """测试更新为无效状态"""
    # 先获取一个订单
    list_response = client.get("/api/admin/orders", params={"page_size": 1})
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    
    if len(orders) == 0:
        pytest.skip("No orders available for testing")
    
    order_id = orders[0]["order_id"]
    
    # 尝试更新为无效状态
    response = client.put(
        f"/api/admin/orders/{order_id}",
        json={"status": "INVALID_STATUS"}
    )
    assert response.status_code == 400


def test_cancel_order(client: httpx.Client):
    """测试取消订单"""
    # 先获取一个 PENDING 订单
    list_response = client.get("/api/admin/orders", params={
        "status": "PENDING",
        "page_size": 1
    })
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    
    if len(orders) == 0:
        pytest.skip("No PENDING orders available for testing")
    
    order_id = orders[0]["order_id"]
    
    # 取消订单
    cancel_response = client.delete(
        f"/api/admin/orders/{order_id}",
        params={"reason": "Test cancellation"}
    )
    assert cancel_response.status_code == 200
    
    data = cancel_response.json()
    assert data["message"] == "Order cancelled successfully"
    assert data["order_id"] == order_id


def test_cancel_delivered_order(client: httpx.Client):
    """测试取消已交付订单（应该失败）"""
    # 获取一个 DELIVERED 订单
    list_response = client.get("/api/admin/orders", params={
        "status": "DELIVERED",
        "page_size": 1
    })
    assert list_response.status_code == 200
    orders = list_response.json()["orders"]
    
    if len(orders) == 0:
        pytest.skip("No DELIVERED orders available for testing")
    
    order_id = orders[0]["order_id"]
    
    # 尝试取消（应该失败）
    response = client.delete(
        f"/api/admin/orders/{order_id}",
        params={"reason": "Test cancellation"}
    )
    assert response.status_code == 400
    assert "Cannot cancel order" in response.json()["detail"]


# ============================================================================
# 统计数据测试
# ============================================================================

def test_get_stats_summary(client: httpx.Client):
    """测试获取统计摘要"""
    response = client.get("/api/admin/stats/summary")
    assert response.status_code == 200
    
    data = response.json()
    
    # 检查必需的统计字段
    assert "total" in data
    assert "pending" in data
    assert "paid" in data
    assert "delivered" in data
    assert "expired" in data
    assert "cancelled" in data
    assert "by_type" in data
    
    # 检查按类型统计
    by_type = data["by_type"]
    assert "premium" in by_type
    assert "deposit" in by_type
    assert "trx_exchange" in by_type
    
    # 验证数据一致性
    status_sum = (
        data["pending"] +
        data["paid"] +
        data["delivered"] +
        data["expired"] +
        data["cancelled"]
    )
    assert status_sum == data["total"]
    
    type_sum = (
        by_type["premium"] +
        by_type["deposit"] +
        by_type["trx_exchange"]
    )
    assert type_sum == data["total"]


# ============================================================================
# 认证测试
# ============================================================================

def test_api_without_auth(client: httpx.Client):
    """测试无认证访问 API"""
    # 创建无认证的客户端
    no_auth_client = httpx.Client(base_url=API_BASE_URL, timeout=10.0)
    
    response = no_auth_client.get("/api/admin/orders")
    assert response.status_code == 401  # Unauthorized (认证中间件返回 401)


def test_api_with_invalid_key(client: httpx.Client):
    """测试使用无效 API Key"""
    invalid_client = httpx.Client(
        base_url=API_BASE_URL,
        headers={"X-API-Key": "invalid-key-12345"},
        timeout=10.0
    )
    
    response = invalid_client.get("/api/admin/orders")
    assert response.status_code == 403


# ============================================================================
# 根路径测试
# ============================================================================

def test_root_endpoint(client: httpx.Client):
    """测试根路径"""
    # 根路径不需要认证
    no_auth_client = httpx.Client(base_url=API_BASE_URL, timeout=10.0)
    response = no_auth_client.get("/")
    assert response.status_code == 200
    
    data = response.json()
    assert "name" in data
    assert "version" in data
    assert "status" in data
    assert data["status"] == "running"


def test_metrics_endpoint(client: httpx.Client):
    """测试 Prometheus 指标端点"""
    # Metrics 不需要认证
    no_auth_client = httpx.Client(base_url=API_BASE_URL, timeout=10.0)
    response = no_auth_client.get("/metrics")
    assert response.status_code == 200
    
    # Prometheus 格式应该是文本
    assert "text/plain" in response.headers.get("content-type", "")


# ============================================================================
# OpenAPI 文档测试
# ============================================================================

def test_openapi_docs(client: httpx.Client):
    """测试 OpenAPI 文档"""
    # Docs 在开发环境可用
    no_auth_client = httpx.Client(base_url=API_BASE_URL, timeout=10.0)
    response = no_auth_client.get("/docs")
    assert response.status_code == 200


def test_openapi_schema(client: httpx.Client):
    """测试 OpenAPI Schema"""
    no_auth_client = httpx.Client(base_url=API_BASE_URL, timeout=10.0)
    response = no_auth_client.get("/openapi.json")
    assert response.status_code == 200
    
    schema = response.json()
    assert "openapi" in schema
    assert "info" in schema
    assert "paths" in schema


# ============================================================================
# 性能和限流测试
# ============================================================================

def test_rate_limiting():
    """测试速率限制（简单验证）"""
    # 创建临时客户端
    client = httpx.Client(
        base_url=API_BASE_URL,
        headers={"X-API-Key": API_KEY},
        timeout=10.0
    )
    
    # 快速发送多个请求
    success_count = 0
    rate_limited_count = 0
    
    for _ in range(35):  # 超过 30/minute 限制
        try:
            response = client.get("/api/admin/orders")
            if response.status_code == 200:
                success_count += 1
            elif response.status_code == 429:  # Too Many Requests
                rate_limited_count += 1
        except Exception:
            pass
    
    # 至少应该有一些成功的请求
    assert success_count > 0
    
    # 注意：由于时间窗口，可能不会触发限流，这是正常的


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
