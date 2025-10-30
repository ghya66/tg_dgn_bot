"""
OpenTelemetry 分布式追踪
实现 Span 注入和上下文传播
"""
from typing import Optional, Dict, Any, Callable
from functools import wraps
from contextvars import ContextVar
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.trace import Status, StatusCode, SpanKind
from backend.api.config import settings

# 全局 tracer
_tracer: Optional[trace.Tracer] = None

# 当前 span 上下文
_current_span: ContextVar[Optional[trace.Span]] = ContextVar("current_span", default=None)


def setup_tracing(service_name: str = "tg_dgn_bot_backend") -> None:
    """
    配置 OpenTelemetry 追踪
    
    Args:
        service_name: 服务名称
    """
    global _tracer
    
    # 创建资源（包含服务信息）
    resource = Resource.create({
        "service.name": service_name,
        "service.version": "1.0.0",
        "deployment.environment": settings.env,
    })
    
    # 创建 TracerProvider
    provider = TracerProvider(resource=resource)
    
    # 配置导出器
    if settings.otlp_endpoint:
        # 生产环境：导出到 OTLP Collector（Jaeger/Zipkin）
        otlp_exporter = OTLPSpanExporter(endpoint=settings.otlp_endpoint)
        provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
    else:
        # 开发环境：输出到控制台
        console_exporter = ConsoleSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(console_exporter))
    
    # 设置全局 provider
    trace.set_tracer_provider(provider)
    
    # 获取 tracer
    _tracer = trace.get_tracer(__name__)


def get_tracer() -> trace.Tracer:
    """获取 tracer 实例"""
    global _tracer
    if _tracer is None:
        setup_tracing()
    return _tracer


def create_span(
    name: str,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
) -> trace.Span:
    """
    创建新 span
    
    Args:
        name: Span 名称
        kind: Span 类型（INTERNAL/SERVER/CLIENT/PRODUCER/CONSUMER）
        attributes: Span 属性
    
    Returns:
        span: Span 对象
    
    Example:
        >>> with create_span("process_payment", attributes={"order_id": "PREM001"}):
        ...     # 业务逻辑
        ...     pass
    """
    tracer = get_tracer()
    span = tracer.start_span(name, kind=kind)
    
    if attributes:
        for key, value in attributes.items():
            span.set_attribute(key, value)
    
    _current_span.set(span)
    return span


def get_current_span() -> Optional[trace.Span]:
    """获取当前 span"""
    return _current_span.get()


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None) -> None:
    """
    添加 span 事件
    
    Args:
        name: 事件名称
        attributes: 事件属性
    
    Example:
        >>> add_span_event("order_validated", {"order_id": "PREM001", "valid": True})
    """
    span = get_current_span()
    if span:
        span.add_event(name, attributes or {})


def set_span_status(status_code: StatusCode, description: Optional[str] = None) -> None:
    """
    设置 span 状态
    
    Args:
        status_code: 状态码（UNSET/OK/ERROR）
        description: 状态描述
    
    Example:
        >>> set_span_status(StatusCode.ERROR, "Payment failed: API timeout")
    """
    span = get_current_span()
    if span:
        span.set_status(Status(status_code=status_code, description=description))


def trace_function(
    name: Optional[str] = None,
    kind: SpanKind = SpanKind.INTERNAL,
    attributes: Optional[Dict[str, Any]] = None
):
    """
    函数追踪装饰器
    
    Args:
        name: Span 名称（默认使用函数名）
        kind: Span 类型
        attributes: Span 属性
    
    Example:
        >>> @trace_function(name="calculate_amount", attributes={"currency": "USDT"})
        ... def calculate_amount(duration: int) -> float:
        ...     return duration * 10.0
    """
    def decorator(func: Callable) -> Callable:
        span_name = name or f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            with create_span(span_name, kind=kind, attributes=attributes):
                try:
                    result = func(*args, **kwargs)
                    set_span_status(StatusCode.OK)
                    return result
                except Exception as e:
                    set_span_status(StatusCode.ERROR, str(e))
                    raise
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            with create_span(span_name, kind=kind, attributes=attributes):
                try:
                    result = await func(*args, **kwargs)
                    set_span_status(StatusCode.OK)
                    return result
                except Exception as e:
                    set_span_status(StatusCode.ERROR, str(e))
                    raise
        
        # 根据函数类型选择包装器
        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def trace_repository(name: Optional[str] = None):
    """
    Repository 层追踪装饰器
    
    Example:
        >>> @trace_repository("get_order_by_id")
        ... def get_order_by_id(self, order_id: str):
        ...     return self.session.query(Order).filter_by(order_id=order_id).first()
    """
    return trace_function(name=name, kind=SpanKind.INTERNAL)


def trace_service(name: Optional[str] = None):
    """
    Service 层追踪装饰器
    
    Example:
        >>> @trace_service("create_premium_order")
        ... def create_premium_order(self, user_id: int, duration: int):
        ...     # 业务逻辑
        ...     pass
    """
    return trace_function(name=name, kind=SpanKind.INTERNAL)


def trace_task(name: Optional[str] = None):
    """
    任务追踪装饰器
    
    Example:
        >>> @trace_task("deliver_premium_task")
        ... async def deliver_premium_task(ctx, order_id: str):
        ...     # 任务逻辑
        ...     pass
    """
    return trace_function(name=name, kind=SpanKind.CONSUMER)


def trace_http_client(name: Optional[str] = None):
    """
    HTTP 客户端追踪装饰器
    
    Example:
        >>> @trace_http_client("call_telegram_api")
        ... async def call_telegram_api(method: str, params: dict):
        ...     # API 调用
        ...     pass
    """
    return trace_function(name=name, kind=SpanKind.CLIENT)


# 初始化追踪（仅在启用时）
if settings.otlp_endpoint or settings.is_development:
    setup_tracing()
