"""
FastAPI 主应用

集成所有模块：
- Middleware: Rate Limiting, Circuit Breaker, IP Whitelist, Request Logging, Auth
- Routers: Admin API, Webhook, Health, Metrics
- Lifespan: Database, Redis, Worker 连接管理
- CORS: 跨域资源共享配置
"""

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from backend.api.config import settings
from backend.api.database import engine, get_db
from backend.api.middleware import (
    IPWhitelistMiddleware,
    auth_middleware,
    limiter,
    rate_limit_middleware,
    request_logging_middleware,
)
from backend.api.observability.logging import setup_logging

logger = structlog.get_logger(__name__)


# ============================================================================
# Lifespan 事件管理
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    启动时:
    - 配置日志系统
    - 测试数据库连接
    - 测试 Redis 连接
    - 初始化 arq worker 连接池
    
    关闭时:
    - 关闭数据库连接
    - 关闭 Redis 连接
    - 关闭 arq worker 连接池
    """
    # === 启动阶段 ===
    logger.info(
        "application_starting",
        env=settings.env,
        debug=settings.debug,
        api_host=settings.api_host,
        api_port=settings.api_port,
    )
    
    # 配置日志系统
    setup_logging()
    
    # 测试数据库连接
    try:
        from sqlalchemy import text
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        logger.info("database_connection_ok")
    except Exception as e:
        logger.error("database_connection_failed", error=str(e), exc_info=True)
        raise
    
    # 测试 Redis 连接
    try:
        import redis.asyncio as aioredis
        redis_client = aioredis.from_url(settings.redis_url)
        await redis_client.ping()
        await redis_client.close()
        logger.info("redis_connection_ok")
    except Exception as e:
        logger.error("redis_connection_failed", error=str(e), exc_info=True)
        raise
    
    # 初始化 arq worker 连接池（可选）
    try:
        from backend.api.tasks.worker import get_redis_pool
        pool = await get_redis_pool()
        logger.info("arq_worker_pool_initialized")
    except Exception as e:
        logger.warning("arq_worker_pool_init_failed", error=str(e))
    
    logger.info("application_started")
    
    yield
    
    # === 关闭阶段 ===
    logger.info("application_shutting_down")
    
    # 关闭数据库连接
    engine.dispose()
    logger.info("database_connections_closed")
    
    # 关闭 arq worker 连接池
    try:
        from backend.api.tasks.worker import close_redis_pool
        await close_redis_pool()
        logger.info("arq_worker_pool_closed")
    except Exception as e:
        logger.warning("arq_worker_pool_close_failed", error=str(e))
    
    logger.info("application_shutdown_complete")


# ============================================================================
# FastAPI 应用初始化
# ============================================================================

app = FastAPI(
    title="TG DGN Bot 后端管理系统",
    description="Telegram Bot 后端 API - 订单管理、支付回调、配置管理、统计分析",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,  # 生产环境禁用 Swagger
    redoc_url="/redoc" if settings.is_development else None,
    openapi_url="/openapi.json" if settings.is_development else None,
)


# ============================================================================
# CORS 配置
# ============================================================================

if settings.is_development:
    # 开发环境：允许所有来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    # 生产环境：限制来源
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://yourdomain.com"],  # 替换为实际域名
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization", "X-API-Key"],
    )


# ============================================================================
# 中间件栈（执行顺序：从下到上）
# ============================================================================

# 1. 请求日志（最外层，记录所有请求）
app.add_middleware(request_logging_middleware)

# 2. IP 白名单（保护管理员 API 和 Webhook）
app.add_middleware(IPWhitelistMiddleware)

# 3. 认证中间件（API Key 验证）
app.add_middleware(auth_middleware)

# 4. Rate Limiting（限频保护）
app.add_middleware(rate_limit_middleware)

# 注册 slowapi limiter
app.state.limiter = limiter


# ============================================================================
# 路由注册
# ============================================================================

from backend.api.routers import admin, webhook, health

# 管理员 API（需要认证）
app.include_router(
    admin.router,
    prefix="/api/admin",
    tags=["管理员接口"],
)

# Webhook API（IP 白名单保护）
app.include_router(
    webhook.router,
    prefix="/api/webhook",
    tags=["回调接口"],
)

# 健康检查（公开访问）
app.include_router(
    health.router,
    prefix="/health",
    tags=["健康检查"],
)


# ============================================================================
# 根路径
# ============================================================================

@app.get("/", tags=["根路径"])
async def root():
    """根路径 - 返回 API 信息"""
    return {
        "name": "TG DGN Bot 后端管理系统",
        "version": "1.0.0",
        "status": "运行中",
        "environment": settings.env,
        "docs": "/docs" if settings.is_development else "已禁用",
    }


@app.get("/metrics", tags=["监控指标"])
async def metrics():
    """Prometheus 指标端点"""
    return JSONResponse(
        content=generate_latest().decode("utf-8"),
        media_type=CONTENT_TYPE_LATEST,
    )


# ============================================================================
# 错误处理
# ============================================================================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception):
    """全局异常处理器"""
    logger.error(
        "unhandled_exception",
        path=request.url.path,
        method=request.method,
        error=str(exc),
        exc_info=True,
    )
    
    # 生产环境隐藏错误详情
    if settings.is_production:
        return JSONResponse(
            status_code=500,
            content={"error": "服务器内部错误"},
        )
    else:
        return JSONResponse(
            status_code=500,
            content={
                "error": "服务器内部错误",
                "detail": str(exc),
                "type": type(exc).__name__,
            },
        )


# ============================================================================
# 运行入口（开发模式）
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.is_development,
        log_level=settings.log_level.lower(),
        workers=1 if settings.is_development else settings.api_workers,
    )
