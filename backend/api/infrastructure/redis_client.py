"""
Redis 客户端管理

提供 Redis 连接池和依赖注入函数。
"""

from typing import AsyncGenerator

import redis.asyncio as aioredis
from redis.asyncio import Redis

from backend.api.config import settings

# ============================================================================
# Redis 连接池（全局单例）
# ============================================================================

_redis_pool: Redis | None = None


async def get_redis_pool() -> Redis:
    """
    获取 Redis 连接池（单例）
    
    Returns:
        Redis 客户端实例
    """
    global _redis_pool
    
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,  # 连接池大小
        )
    
    return _redis_pool


async def close_redis_pool():
    """关闭 Redis 连接池"""
    global _redis_pool
    
    if _redis_pool is not None:
        await _redis_pool.close()
        _redis_pool = None


# ============================================================================
# 依赖注入函数
# ============================================================================

async def get_redis() -> AsyncGenerator[Redis, None]:
    """
    FastAPI 依赖注入 - 获取 Redis 客户端
    
    Usage:
        @app.get("/cache")
        async def read_cache(redis: Redis = Depends(get_redis)):
            ...
    """
    redis_client = await get_redis_pool()
    try:
        yield redis_client
    finally:
        # 连接池管理，不需要手动关闭单个连接
        pass
