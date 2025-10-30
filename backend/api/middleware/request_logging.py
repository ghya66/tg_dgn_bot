"""
请求日志中间件 (Request Logging Middleware)

记录所有 HTTP 请求的结构化日志，并集成 Prometheus 指标。

日志字段:
- method: HTTP 方法
- path: 请求路径
- status_code: 响应状态码
- duration_ms: 请求处理时长（毫秒）
- client_ip: 客户端 IP
- user_agent: User-Agent 头

指标:
- http_requests_total: 请求总数（按 method、path、status 标签）
- http_request_duration_seconds: 请求处理时长（histogram）
"""

import time
from typing import Callable

import structlog
from fastapi import Request, Response
from prometheus_client import Counter, Histogram
from starlette.middleware.base import BaseHTTPMiddleware

logger = structlog.get_logger(__name__)


# ============================================================================
# Prometheus 指标
# ============================================================================

# 注意：使用不同的指标名称以避免与 observability/metrics.py 冲突
http_middleware_requests_total = Counter(
    "http_middleware_requests_total",
    "Total HTTP requests (from middleware)",
    ["method", "path", "status_code"],
)

http_middleware_request_duration_seconds = Histogram(
    "http_middleware_request_duration_seconds",
    "HTTP request duration in seconds (from middleware)",
    ["method", "path"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],  # 10ms ~ 5s
)


# ============================================================================
# 辅助函数
# ============================================================================

def _get_client_ip(request: Request) -> str:
    """获取客户端 IP（同 ip_whitelist 模块）"""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip.strip()
    
    return request.client.host if request.client else "unknown"


def _sanitize_path(path: str) -> str:
    """
    清洗路径，移除动态参数（防止 Prometheus 标签爆炸）
    
    示例:
        /api/orders/abc123 -> /api/orders/{id}
        /api/admin/settings/rate_limit -> /api/admin/settings/{key}
    """
    parts = path.split("/")
    
    # 替换常见的动态参数
    sanitized = []
    for i, part in enumerate(parts):
        if not part:
            continue
        
        # 检查是否为 UUID/数字 ID
        if len(part) > 8 and (part.isdigit() or "-" in part):
            sanitized.append("{id}")
        else:
            sanitized.append(part)
    
    return "/" + "/".join(sanitized)


# ============================================================================
# 中间件
# ============================================================================

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    请求日志中间件
    
    记录所有请求的结构化日志，并更新 Prometheus 指标。
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 记录请求开始时间
        start_time = time.perf_counter()
        
        # 提取请求信息
        method = request.method
        path = request.url.path
        client_ip = _get_client_ip(request)
        user_agent = request.headers.get("User-Agent", "unknown")
        
        # 处理请求
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as e:
            # 捕获未处理异常（仍会向上抛出）
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                "request_exception",
                method=method,
                path=path,
                client_ip=client_ip,
                duration_ms=round(duration_ms, 2),
                error=str(e),
                exc_info=True,
            )
            raise
        
        # 计算处理时长
        duration_ms = (time.perf_counter() - start_time) * 1000
        
        # 记录日志
        log_level = "info"
        if status_code >= 500:
            log_level = "error"
        elif status_code >= 400:
            log_level = "warning"
        
        log_func = getattr(logger, log_level)
        log_func(
            "http_request",
            method=method,
            path=path,
            status_code=status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=client_ip,
            user_agent=user_agent,
        )
        
        # 更新 Prometheus 指标
        sanitized_path = _sanitize_path(path)
        
        http_middleware_requests_total.labels(
            method=method,
            path=sanitized_path,
            status_code=status_code,
        ).inc()
        
        http_middleware_request_duration_seconds.labels(
            method=method,
            path=sanitized_path,
        ).observe(duration_ms / 1000)
        
        return response


# 导出中间件实例
request_logging_middleware = RequestLoggingMiddleware
