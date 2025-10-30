"""
结构化日志配置
使用 structlog 实现 JSON 格式日志（生产环境）和彩色控制台日志（开发环境）
"""
import sys
import logging
import structlog
from typing import Any
from backend.api.config import settings


def setup_logging() -> None:
    """
    配置 structlog 日志系统
    
    开发环境：彩色控制台输出
    生产环境：JSON 格式输出
    """
    # 配置标准 logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )
    
    # 共享的 processors
    shared_processors = [
        structlog.contextvars.merge_contextvars,  # 合并上下文变量
        structlog.stdlib.add_log_level,  # 添加日志级别
        structlog.stdlib.add_logger_name,  # 添加 logger 名称
        structlog.processors.TimeStamper(fmt="iso"),  # ISO 时间戳
        structlog.processors.StackInfoRenderer(),  # 堆栈信息
        structlog.processors.format_exc_info,  # 格式化异常信息
    ]
    
    # 根据环境选择输出格式
    if settings.is_production or settings.log_json_format:
        # 生产环境：JSON 格式
        processors = shared_processors + [
            structlog.processors.dict_tracebacks,  # 异常字典化
            structlog.processors.JSONRenderer(),  # JSON 渲染
        ]
    else:
        # 开发环境：彩色控制台
        processors = shared_processors + [
            structlog.dev.ConsoleRenderer(
                colors=True,  # 启用颜色
                exception_formatter=structlog.dev.plain_traceback,
            )
        ]
    
    # 配置 structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """
    获取 logger 实例
    
    Args:
        name: logger 名称（通常使用 __name__）
    
    Returns:
        logger: structlog BoundLogger 实例
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("user_login", user_id=123, username="test")
        >>> logger.error("payment_failed", order_id="PREM001", error="API timeout")
    """
    return structlog.get_logger(name)


def bind_context(**kwargs: Any) -> None:
    """
    绑定上下文变量到当前线程/协程
    
    Args:
        **kwargs: 上下文键值对
    
    Example:
        >>> bind_context(request_id="abc123", user_id=456)
        >>> logger.info("processing")  # 自动包含 request_id 和 user_id
    """
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(**kwargs)


def clear_context() -> None:
    """清除上下文变量"""
    structlog.contextvars.clear_contextvars()


# 初始化日志系统
setup_logging()
