"""
断路器模块 (Circuit Breaker)

使用 pybreaker 实现自动故障保护：
- Telegram API: 5 次失败后熔断，60 秒恢复
- Redis: 3 次失败后熔断，30 秒恢复

状态：
- CLOSED: 正常工作
- OPEN: 熔断状态（快速失败）
- HALF_OPEN: 半开状态（尝试恢复）
"""

import functools
from typing import Any, Callable

import httpx
import structlog
from pybreaker import CircuitBreaker, CircuitBreakerError
from redis.exceptions import RedisError

logger = structlog.get_logger(__name__)


# ============================================================================
# Telegram API 断路器
# ============================================================================

class TelegramBreakerListener:
    """Telegram API 断路器监听器"""
    
    def before_call(self, breaker, func, *args, **kwargs):
        """调用前"""
        pass
    
    def success(self, breaker):
        """成功"""
        pass
    
    def failure(self, breaker, exception):
        """失败"""
        logger.warning(
            "telegram_api_call_failed",
            failure_count=breaker.fail_counter,
            exception=str(exception),
        )
    
    def state_change(self, breaker, old_state, new_state):
        """状态转换"""
        logger.warning(
            "telegram_api_circuit_state_changed",
            old_state=str(old_state),
            new_state=str(new_state),
            failure_count=breaker.fail_counter,
        )


telegram_breaker = CircuitBreaker(
    fail_max=5,  # 5 次失败后打开
    reset_timeout=60,  # 60 秒后尝试半开
    exclude=[httpx.HTTPStatusError],  # HTTP 4xx/5xx 不触发熔断（业务错误）
    name="telegram_api",
    listeners=[TelegramBreakerListener()],
)


def with_telegram_breaker(func: Callable) -> Callable:
    """
    装饰器：为 Telegram API 调用添加断路器保护
    
    用法:
        @with_telegram_breaker
        async def call_telegram_api():
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await telegram_breaker.call_async(func, *args, **kwargs)
        except CircuitBreakerError:
            logger.error(
                "telegram_api_circuit_open",
                function=func.__name__,
                state=str(telegram_breaker.current_state),
            )
            raise RuntimeError(
                "Telegram API is temporarily unavailable (circuit breaker open)"
            )
    return wrapper


# ============================================================================
# Redis 断路器
# ============================================================================

class RedisBreakerListener:
    """Redis 断路器监听器"""
    
    def before_call(self, breaker, func, *args, **kwargs):
        """调用前"""
        pass
    
    def success(self, breaker):
        """成功"""
        pass
    
    def failure(self, breaker, exception):
        """失败"""
        logger.warning(
            "redis_call_failed",
            failure_count=breaker.fail_counter,
            exception=str(exception),
        )
    
    def state_change(self, breaker, old_state, new_state):
        """状态转换"""
        logger.warning(
            "redis_circuit_state_changed",
            old_state=str(old_state),
            new_state=str(new_state),
            failure_count=breaker.fail_counter,
        )


redis_breaker = CircuitBreaker(
    fail_max=3,  # 3 次失败后打开
    reset_timeout=30,  # 30 秒后尝试半开
    exclude=[],  # 所有 Redis 错误都触发熔断
    name="redis",
    listeners=[RedisBreakerListener()],
)


def with_redis_breaker(func: Callable) -> Callable:
    """
    装饰器：为 Redis 调用添加断路器保护
    
    用法:
        @with_redis_breaker
        async def call_redis():
            ...
    """
    @functools.wraps(func)
    async def wrapper(*args, **kwargs) -> Any:
        try:
            return await redis_breaker.call_async(func, *args, **kwargs)
        except CircuitBreakerError:
            logger.error(
                "redis_circuit_open",
                function=func.__name__,
                state=str(redis_breaker.current_state),
            )
            # 降级策略：返回 None 或默认值
            logger.warning(
                "redis_fallback_activated",
                function=func.__name__,
            )
            return None
    return wrapper


# ============================================================================
# 通用断路器工厂
# ============================================================================

def create_breaker(
    name: str,
    fail_max: int = 5,
    reset_timeout: int = 60,
    exclude: list = None,
) -> CircuitBreaker:
    """
    创建自定义断路器
    
    参数:
        name: 断路器名称
        fail_max: 最大失败次数
        reset_timeout: 恢复超时（秒）
        exclude: 排除的异常类型（不触发熔断）
    """
    class CustomBreakerListener:
        """自定义断路器监听器"""
        
        def before_call(self, breaker, func, *args, **kwargs):
            pass
        
        def success(self, breaker):
            pass
        
        def failure(self, breaker, exception):
            logger.warning(
                "circuit_breaker_failure",
                name=name,
                failure_count=breaker.fail_counter,
            )
        
        def state_change(self, breaker, old_state, new_state):
            logger.info(
                "circuit_breaker_state_changed",
                name=name,
                old_state=str(old_state),
                new_state=str(new_state),
            )
    
    return CircuitBreaker(
        fail_max=fail_max,
        reset_timeout=reset_timeout,
        exclude=exclude or [],
        name=name,
        listeners=[CustomBreakerListener()],
    )
