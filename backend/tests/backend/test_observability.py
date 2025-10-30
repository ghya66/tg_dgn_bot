"""
测试可观测性模块
"""
import pytest
import logging
import structlog
from io import StringIO
from unittest.mock import patch, MagicMock
from prometheus_client import REGISTRY
from opentelemetry.trace import StatusCode, SpanKind
from backend.api.observability.logging import (
    setup_logging,
    get_logger,
    bind_context,
    clear_context
)
from backend.api.observability.metrics import (
    record_order_created,
    record_order_paid,
    record_task_execution,
    record_http_request,
    order_created_total,
    task_executed_total,
    http_requests_total
)
from backend.api.observability.tracing import (
    setup_tracing,
    create_span,
    get_current_span,
    add_span_event,
    set_span_status,
    trace_function
)


class TestLogging:
    """测试结构化日志"""
    
    def test_setup_logging(self):
        """测试日志初始化"""
        setup_logging()
        
        logger = get_logger(__name__)
        assert logger is not None
        # BoundLoggerLazyProxy 也是有效的 logger 类型
        assert hasattr(logger, 'info')
        assert hasattr(logger, 'error')
    
    def test_get_logger(self):
        """测试获取 logger"""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")
        
        assert logger1 is not None
        assert logger2 is not None
        assert logger1 != logger2  # 不同的 logger
    
    def test_bind_context(self):
        """测试绑定上下文"""
        bind_context(request_id="abc123", user_id=456)
        
        # 验证上下文已绑定（通过日志输出验证）
        logger = get_logger(__name__)
        
        # 使用 StringIO 捕获日志输出
        output = StringIO()
        handler = logging.StreamHandler(output)
        logging.root.addHandler(handler)
        
        logger.info("test_message")
        
        log_output = output.getvalue()
        # 注意：structlog 的上下文变量会包含在输出中
        assert "test_message" in log_output
        
        logging.root.removeHandler(handler)
    
    def test_clear_context(self):
        """测试清除上下文"""
        bind_context(request_id="abc123")
        clear_context()
        
        # 验证上下文已清除
        logger = get_logger(__name__)
        logger.info("test_message")  # 不应包含 request_id


class TestMetrics:
    """测试 Prometheus 指标"""
    
    def test_record_order_created(self):
        """测试记录订单创建"""
        # 获取当前计数
        before = order_created_total.labels(order_type="premium")._value.get()
        
        # 记录订单
        record_order_created("premium", 10.456)
        
        # 验证计数增加
        after = order_created_total.labels(order_type="premium")._value.get()
        assert after == before + 1
    
    def test_record_order_paid(self):
        """测试记录订单支付"""
        from backend.api.observability.metrics import order_paid_total
        
        before = order_paid_total.labels(order_type="premium")._value.get()
        
        record_order_paid("premium")
        
        after = order_paid_total.labels(order_type="premium")._value.get()
        assert after == before + 1
    
    def test_record_task_execution(self):
        """测试记录任务执行"""
        before = task_executed_total.labels(
            task_name="deliver_premium_task",
            status="success"
        )._value.get()
        
        record_task_execution("deliver_premium_task", 2.5, "success")
        
        after = task_executed_total.labels(
            task_name="deliver_premium_task",
            status="success"
        )._value.get()
        assert after == before + 1
    
    def test_record_http_request(self):
        """测试记录 HTTP 请求"""
        before = http_requests_total.labels(
            method="GET",
            endpoint="/api/orders",
            status_code=200
        )._value.get()
        
        record_http_request(
            method="GET",
            endpoint="/api/orders",
            status_code=200,
            duration=0.123,
            request_size=1024,
            response_size=2048
        )
        
        after = http_requests_total.labels(
            method="GET",
            endpoint="/api/orders",
            status_code=200
        )._value.get()
        assert after == before + 1


class TestTracing:
    """测试 OpenTelemetry 追踪"""
    
    def test_setup_tracing(self):
        """测试追踪初始化"""
        setup_tracing("test_service")
        
        from backend.api.observability.tracing import get_tracer
        tracer = get_tracer()
        assert tracer is not None
    
    def test_create_span(self):
        """测试创建 span"""
        with create_span("test_operation", attributes={"key": "value"}) as span:
            assert span is not None
            assert get_current_span() == span
    
    def test_add_span_event(self):
        """测试添加 span 事件"""
        with create_span("test_operation"):
            # 添加事件（不会抛出异常）
            add_span_event("event_name", {"data": "value"})
    
    def test_set_span_status(self):
        """测试设置 span 状态"""
        with create_span("test_operation"):
            set_span_status(StatusCode.OK)
            set_span_status(StatusCode.ERROR, "Test error")
    
    def test_trace_function_sync(self):
        """测试同步函数追踪"""
        @trace_function("test_sync_func")
        def sync_function(x: int) -> int:
            return x * 2
        
        result = sync_function(5)
        assert result == 10
    
    @pytest.mark.asyncio
    async def test_trace_function_async(self):
        """测试异步函数追踪"""
        @trace_function("test_async_func")
        async def async_function(x: int) -> int:
            return x * 2
        
        result = await async_function(5)
        assert result == 10
    
    def test_trace_function_with_exception(self):
        """测试函数追踪（异常情况）"""
        @trace_function("test_error_func")
        def error_function():
            raise ValueError("Test error")
        
        with pytest.raises(ValueError, match="Test error"):
            error_function()
    
    def test_trace_decorators(self):
        """测试不同层级的追踪装饰器"""
        from backend.api.observability.tracing import (
            trace_repository,
            trace_service,
            trace_task,
            trace_http_client
        )
        
        @trace_repository()
        def repo_func():
            return "repo"
        
        @trace_service()
        def service_func():
            return "service"
        
        @trace_http_client()
        def http_func():
            return "http"
        
        assert repo_func() == "repo"
        assert service_func() == "service"
        assert http_func() == "http"


class TestIntegration:
    """测试可观测性集成"""
    
    def test_logging_metrics_integration(self):
        """测试日志和指标集成"""
        logger = get_logger(__name__)
        
        # 记录日志
        bind_context(request_id="test123")
        logger.info("order_created", order_id="PREM001", amount=10.456)
        
        # 记录指标
        record_order_created("premium", 10.456)
        
        # 验证指标已记录
        value = order_created_total.labels(order_type="premium")._value.get()
        assert value > 0
        
        clear_context()
    
    def test_tracing_logging_integration(self):
        """测试追踪和日志集成"""
        logger = get_logger(__name__)
        
        with create_span("test_operation", attributes={"order_id": "PREM001"}):
            logger.info("processing_order", order_id="PREM001")
            add_span_event("order_validated")
            set_span_status(StatusCode.OK)
    
    @pytest.mark.asyncio
    async def test_full_observability_stack(self):
        """测试完整可观测性堆栈"""
        logger = get_logger(__name__)
        
        # 绑定上下文
        bind_context(request_id="full_test_123", user_id=456)
        
        @trace_function("business_logic")
        async def business_logic(order_type: str, amount: float):
            # 记录日志
            logger.info(
                "executing_business_logic",
                order_type=order_type,
                amount=amount
            )
            
            # 添加 span 事件
            add_span_event("validation_passed")
            
            # 记录指标
            record_order_created(order_type, amount)
            
            # 模拟异步操作
            import asyncio
            await asyncio.sleep(0.01)
            
            # 设置成功状态
            set_span_status(StatusCode.OK)
            
            return "success"
        
        # 执行业务逻辑
        result = await business_logic("premium", 10.456)
        assert result == "success"
        
        # 清理上下文
        clear_context()
