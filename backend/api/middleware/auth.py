"""
认证中间件 (Authentication Middleware)

提供 API Key 认证和用户标识注入。

认证方式:
1. API Key 认证: X-API-Key 请求头
2. 用户标识注入: 通过 API Key 识别用户，注入 X-User-ID 头供限频使用

配置项:
- API_KEYS: 允许的 API Key 列表（逗号分隔）
- API_KEY_HEADER: API Key 请求头名称（默认 X-API-Key）
"""

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from backend.api.config import settings

logger = structlog.get_logger(__name__)


# ============================================================================
# API Key 验证
# ============================================================================

def _validate_api_key(api_key: str) -> tuple[bool, str | None]:
    """
    验证 API Key
    
    参数:
        api_key: API Key 字符串
    
    返回:
        (is_valid, user_id): 验证结果和用户 ID
    """
    allowed_keys = settings.allowed_api_keys
    
    if not allowed_keys:
        # 未配置 API Key，允许所有请求（开发模式）
        logger.warning("no_api_keys_configured")
        return True, "anonymous"
    
    if api_key in allowed_keys:
        # 简单映射：API Key 索引作为用户 ID
        user_id = str(allowed_keys.index(api_key) + 1)
        return True, user_id
    
    return False, None


# ============================================================================
# 认证中间件
# ============================================================================

class AuthMiddleware(BaseHTTPMiddleware):
    """
    API Key 认证中间件
    
    保护所有 /api/* 路径（除了公开端点）。
    
    公开端点:
    - /api/webhook/*: Webhook 使用 IP 白名单保护
    - /health: 健康检查
    - /metrics: Prometheus 指标
    - /docs, /redoc, /openapi.json: API 文档（仅开发环境）
    """
    
    # 公开端点（不需要认证）
    PUBLIC_PATHS = [
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/redoc",
        "/openapi.json",
    ]
    
    # 公开路径前缀
    PUBLIC_PREFIXES = [
        "/api/webhook/",  # Webhook 使用 IP 白名单保护
    ]
    
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        
        # 检查是否为公开路径
        if path in self.PUBLIC_PATHS:
            return await call_next(request)
        
        # 检查是否为公开路径前缀
        for prefix in self.PUBLIC_PREFIXES:
            if path.startswith(prefix):
                return await call_next(request)
        
        # 检查是否需要认证
        if not path.startswith("/api/"):
            # 非 API 路径，不需要认证
            return await call_next(request)
        
        # 提取 API Key
        api_key_header = settings.api_key_header
        api_key = request.headers.get(api_key_header)
        
        if not api_key:
            logger.warning(
                "missing_api_key",
                path=path,
                client_ip=request.client.host if request.client else "unknown",
            )
            return Response(
                content=f"Missing {api_key_header} header",
                status_code=HTTP_401_UNAUTHORIZED,
                headers={"WWW-Authenticate": f'ApiKey realm="{api_key_header}"'},
            )
        
        # 验证 API Key
        is_valid, user_id = _validate_api_key(api_key)
        
        if not is_valid:
            logger.warning(
                "invalid_api_key",
                path=path,
                api_key=api_key[:8] + "..." if len(api_key) > 8 else api_key,
                client_ip=request.client.host if request.client else "unknown",
            )
            return Response(
                content="Invalid API Key",
                status_code=HTTP_403_FORBIDDEN,
            )
        
        # 认证成功，注入用户 ID 到请求头（供限频中间件使用）
        request.scope["headers"].append(
            (b"x-user-id", user_id.encode("utf-8"))
        )
        
        logger.debug(
            "api_key_authenticated",
            path=path,
            user_id=user_id,
        )
        
        response = await call_next(request)
        return response


# 导出中间件
auth_middleware = AuthMiddleware
