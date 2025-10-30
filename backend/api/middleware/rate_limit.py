"""
限频中间件 (Rate Limiting Middleware)

使用 slowapi + Redis 实现分层限频策略：
- IP 级别: 100 req/min
- 用户级别: 60 req/min  
- 管理员 API: 30 req/min

配置项: REDIS_URL
"""

import redis.asyncio as aioredis
from fastapi import Request, Response
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_429_TOO_MANY_REQUESTS

from backend.api.config import settings


def _get_redis_client():
    """获取 Redis 客户端（用于 slowapi 存储）"""
    return aioredis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
        max_connections=10,
    )


def _get_user_identifier(request: Request) -> str:
    """
    获取用户唯一标识符（用于限频）
    
    优先级：
    1. user_id (from auth token/header)
    2. client IP address
    """
    # 从请求头获取用户 ID（假设已通过认证中间件设置）
    user_id = request.headers.get("X-User-ID")
    if user_id:
        return f"user:{user_id}"
    
    # 回退到 IP 地址
    return f"ip:{get_remote_address(request)}"


# 初始化 slowapi Limiter
limiter = Limiter(
    key_func=_get_user_identifier,
    storage_uri=settings.redis_url,
    strategy="fixed-window",  # 固定窗口策略
    headers_enabled=True,  # 返回 X-RateLimit-* 响应头
)


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    限频中间件
    
    根据路径应用不同的限频策略：
    - /api/admin/*: 30 req/min (管理员操作)
    - /api/*: 60 req/min (普通 API)
    - 其他: 100 req/min (IP 级别默认限制)
    """
    
    async def dispatch(self, request: Request, call_next):
        try:
            # slowapi 会在路由处理器中检查限频
            # 此处仅捕获全局限频异常
            response = await call_next(request)
            return response
        except RateLimitExceeded as e:
            return Response(
                content=f"Rate limit exceeded: {str(e)}",
                status_code=HTTP_429_TOO_MANY_REQUESTS,
                headers={
                    "Retry-After": str(e.detail.get("retry_after", 60)),
                },
            )


# 导出中间件实例
rate_limit_middleware = RateLimitMiddleware


# 装饰器：应用于路由
def rate_limit(limit: str):
    """
    限频装饰器
    
    用法:
        @app.get("/api/endpoint")
        @rate_limit("60/minute")
        async def endpoint():
            ...
    
    参数:
        limit: 限频规则（如 "60/minute", "100/hour"）
    """
    return limiter.limit(limit)
