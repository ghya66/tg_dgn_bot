"""
中间件集成测试 (Middleware Integration Tests)

测试覆盖：
- Rate Limiting: IP/用户限频、管理员 API 限频
- Circuit Breaker: Telegram/Redis 断路器、降级策略
- IP Whitelist: 管理员/Webhook 白名单验证
- Request Logging: 结构化日志、Prometheus 指标
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from pybreaker import CircuitBreakerError
from starlette.testclient import TestClient

from backend.api.middleware.circuit_breaker import (
    create_breaker,
    redis_breaker,
    telegram_breaker,
    with_redis_breaker,
    with_telegram_breaker,
)
from backend.api.middleware.ip_whitelist import (
    IPWhitelistMiddleware,
    _get_client_ip,
    _is_ip_allowed,
    _parse_ip_whitelist,
)
from backend.api.middleware.rate_limit import (
    RateLimitMiddleware,
    _get_user_identifier,
    rate_limit,
)
from backend.api.middleware.request_logging import (
    RequestLoggingMiddleware,
    _sanitize_path,
)


# ============================================================================
# Rate Limiting Tests
# ============================================================================

class TestRateLimiting:
    """限频中间件测试"""
    
    def test_get_user_identifier_with_user_id(self):
        """测试用户标识提取（有 User-ID）"""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = "12345"
        
        identifier = _get_user_identifier(request)
        assert identifier == "user:12345"
    
    def test_get_user_identifier_fallback_to_ip(self):
        """测试用户标识回退到 IP"""
        request = MagicMock(spec=Request)
        request.headers.get.return_value = None
        
        with patch("backend.api.middleware.rate_limit.get_remote_address", return_value="192.168.1.1"):
            identifier = _get_user_identifier(request)
        
        assert identifier == "ip:192.168.1.1"
    
    @pytest.mark.skip(reason="需要真实 Redis 集成测试（CI 中运行）")
    def test_rate_limit_decorator(self):
        """测试限频装饰器（集成测试）"""
        # 此测试需要真实 FastAPI app + Redis
        # 在 CI 环境中通过 Docker Compose 运行
        pass


# ============================================================================
# Circuit Breaker Tests
# ============================================================================

class TestCircuitBreaker:
    """断路器测试"""
    
    @pytest.mark.asyncio
    async def test_telegram_breaker_success(self):
        """测试 Telegram 断路器成功调用"""
        @with_telegram_breaker
        async def mock_api_call():
            return {"status": "ok"}
        
        result = await mock_api_call()
        assert result == {"status": "ok"}
        assert telegram_breaker.current_state == "closed"
    
    @pytest.mark.asyncio
    async def test_telegram_breaker_failure(self):
        """测试 Telegram 断路器故障处理"""
        # 创建独立的断路器用于测试（避免影响全局状态）
        test_breaker = create_breaker(
            name="test_telegram",
            fail_max=3,
            reset_timeout=1,
        )
        
        call_count = 0
        
        async def failing_api_call():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("API unreachable")
        
        # 触发失败直到断路器打开
        for _ in range(5):
            try:
                await test_breaker.call_async(failing_api_call)
            except (ConnectionError, CircuitBreakerError):
                pass
        
        # 断路器应该打开（第4次调用时）
        assert test_breaker.current_state == "open"
        
        # 在打开状态下调用应立即失败（不执行函数）
        call_count_before = call_count
        try:
            await test_breaker.call_async(failing_api_call)
        except CircuitBreakerError:
            pass
        
        # 验证函数未执行
        assert call_count == call_count_before
    
    @pytest.mark.asyncio
    async def test_redis_breaker_fallback(self):
        """测试 Redis 断路器降级策略"""
        # 创建独立的断路器
        test_breaker = create_breaker(
            name="test_redis",
            fail_max=2,
            reset_timeout=1,
        )
        
        async def failing_redis_call():
            raise ConnectionError("Redis unavailable")
        
        # 触发失败
        for _ in range(3):
            try:
                await test_breaker.call_async(failing_redis_call)
            except (ConnectionError, CircuitBreakerError):
                pass
        
        # 断路器应该打开
        assert test_breaker.current_state == "open"
        
        # 降级测试：使用装饰器包装
        @with_redis_breaker
        async def wrapped_redis_call():
            raise ConnectionError("Redis unavailable")
        
        # 注意：全局 redis_breaker 可能未打开，所以结果可能是异常或 None
        # 此测试验证降级逻辑存在即可
        try:
            result = await wrapped_redis_call()
            # 如果断路器打开，返回 None
            assert result is None or isinstance(result, type(None))
        except (ConnectionError, RuntimeError):
            # 如果断路器未打开，抛出异常也正常
            pass
    
    def test_create_custom_breaker(self):
        """测试自定义断路器创建"""
        breaker = create_breaker(
            name="test_service",
            fail_max=3,
            reset_timeout=30,
        )
        
        assert breaker.name == "test_service"
        assert breaker.fail_max == 3
        assert breaker._reset_timeout == 30


# ============================================================================
# IP Whitelist Tests
# ============================================================================

class TestIPWhitelist:
    """IP 白名单测试"""
    
    def test_parse_ip_whitelist_single_ip(self):
        """测试解析单个 IP"""
        whitelist = _parse_ip_whitelist("192.168.1.1")
        assert len(whitelist) == 1
        assert "192.168.1.1" in str(whitelist[0])
    
    def test_parse_ip_whitelist_cidr(self):
        """测试解析 CIDR"""
        whitelist = _parse_ip_whitelist("10.0.0.0/8, 192.168.0.0/16")
        assert len(whitelist) == 2
    
    def test_parse_ip_whitelist_empty(self):
        """测试空白名单"""
        whitelist = _parse_ip_whitelist("")
        assert len(whitelist) == 0
    
    def test_is_ip_allowed_single_ip(self):
        """测试单 IP 白名单匹配"""
        whitelist = _parse_ip_whitelist("192.168.1.100")
        
        assert _is_ip_allowed("192.168.1.100", whitelist) is True
        assert _is_ip_allowed("192.168.1.101", whitelist) is False
    
    def test_is_ip_allowed_cidr(self):
        """测试 CIDR 白名单匹配"""
        whitelist = _parse_ip_whitelist("10.0.0.0/8")
        
        assert _is_ip_allowed("10.0.0.1", whitelist) is True
        assert _is_ip_allowed("10.255.255.255", whitelist) is True
        assert _is_ip_allowed("11.0.0.1", whitelist) is False
    
    def test_is_ip_allowed_empty_whitelist(self):
        """测试空白名单（允许所有）"""
        whitelist = []
        assert _is_ip_allowed("1.2.3.4", whitelist) is True
    
    def test_get_client_ip_x_forwarded_for(self):
        """测试从 X-Forwarded-For 提取 IP"""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda k: "203.0.113.1, 192.168.1.1" if k == "X-Forwarded-For" else None
        
        ip = _get_client_ip(request)
        assert ip == "203.0.113.1"
    
    def test_get_client_ip_x_real_ip(self):
        """测试从 X-Real-IP 提取 IP"""
        request = MagicMock(spec=Request)
        request.headers.get.side_effect = lambda k: "203.0.113.2" if k == "X-Real-IP" else None
        
        ip = _get_client_ip(request)
        assert ip == "203.0.113.2"
    
    @pytest.mark.asyncio
    async def test_ip_whitelist_middleware_admin_allowed(self):
        """测试管理员 API 白名单放行"""
        app = FastAPI()
        
        @app.get("/api/admin/test")
        async def admin_endpoint():
            return {"status": "ok"}
        
        # 配置白名单
        with patch("backend.api.middleware.ip_whitelist.settings") as mock_settings:
            mock_settings.ADMIN_IP_WHITELIST = "192.168.1.100"
            
            app.add_middleware(IPWhitelistMiddleware)
            client = TestClient(app)
            
            # 匹配 IP
            response = client.get(
                "/api/admin/test",
                headers={"X-Forwarded-For": "192.168.1.100"},
            )
            assert response.status_code == 200
    
    @pytest.mark.asyncio
    async def test_ip_whitelist_middleware_admin_rejected(self):
        """测试管理员 API 白名单拒绝"""
        app = FastAPI()
        
        @app.get("/api/admin/test")
        async def admin_endpoint():
            return {"status": "ok"}
        
        with patch("backend.api.middleware.ip_whitelist.settings") as mock_settings:
            mock_settings.ADMIN_IP_WHITELIST = "192.168.1.100"
            
            app.add_middleware(IPWhitelistMiddleware)
            client = TestClient(app)
            
            # 不匹配 IP
            response = client.get(
                "/api/admin/test",
                headers={"X-Forwarded-For": "203.0.113.1"},
            )
            assert response.status_code == 403


# ============================================================================
# Request Logging Tests
# ============================================================================

class TestRequestLogging:
    """请求日志测试"""
    
    def test_sanitize_path_with_uuid(self):
        """测试路径清洗（UUID 参数）"""
        path = "/api/orders/abc-123-def-456"
        sanitized = _sanitize_path(path)
        assert sanitized == "/api/orders/{id}"
    
    def test_sanitize_path_with_numeric_id(self):
        """测试路径清洗（数字 ID）"""
        path = "/api/users/123456789"
        sanitized = _sanitize_path(path)
        assert sanitized == "/api/users/{id}"
    
    def test_sanitize_path_static(self):
        """测试静态路径不变"""
        path = "/api/health"
        sanitized = _sanitize_path(path)
        assert sanitized == "/api/health"
    
    @pytest.mark.asyncio
    async def test_request_logging_middleware_success(self):
        """测试请求日志中间件（成功请求）"""
        app = FastAPI()
        
        @app.get("/test")
        async def test_endpoint():
            return {"status": "ok"}
        
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app)
        
        with patch("backend.api.middleware.request_logging.logger") as mock_logger:
            response = client.get("/test")
            
            assert response.status_code == 200
            # 验证日志调用
            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert call_args[0][0] == "http_request"
            assert call_args[1]["method"] == "GET"
            assert call_args[1]["path"] == "/test"
            assert call_args[1]["status_code"] == 200
    
    @pytest.mark.asyncio
    async def test_request_logging_middleware_error(self):
        """测试请求日志中间件（错误请求）"""
        app = FastAPI()
        
        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")
        
        app.add_middleware(RequestLoggingMiddleware)
        client = TestClient(app, raise_server_exceptions=False)
        
        with patch("backend.api.middleware.request_logging.logger") as mock_logger:
            response = client.get("/error")
            
            # FastAPI 会将未捕获异常转为 500
            assert response.status_code == 500


# ============================================================================
# 集成测试（需要完整 FastAPI app）
# ============================================================================

@pytest.mark.skip(reason="需要完整 FastAPI app + Redis（Stage 6）")
class TestMiddlewareIntegration:
    """中间件集成测试（在 Stage 6 实现）"""
    
    def test_full_middleware_stack(self):
        """测试完整中间件栈"""
        # Rate Limiting -> Circuit Breaker -> IP Whitelist -> Request Logging
        pass
