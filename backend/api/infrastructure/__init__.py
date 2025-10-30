"""
基础设施模块
"""

from .redis_client import get_redis, get_redis_pool, close_redis_pool

__all__ = [
    "get_redis",
    "get_redis_pool",
    "close_redis_pool",
]
