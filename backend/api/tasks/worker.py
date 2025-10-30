"""
arq Worker 配置
处理异步任务（Premium 交付、订单过期等）
"""
from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from backend.api.config import settings


class WorkerSettings:
    """arq Worker 配置"""
    
    # Redis 连接配置
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    
    # 任务函数列表（在 worker 启动时导入）
    functions = []
    
    # 任务配置
    max_jobs = settings.arq_max_jobs  # 最大并发任务数
    job_timeout = settings.arq_job_timeout  # 任务超时时间(秒)
    
    # 重试配置
    max_tries = settings.arq_max_tries  # 最大重试次数
    retry_jobs = True  # 启用任务重试
    
    # 定时任务配置（Cron Jobs）
    cron_jobs = []
    
    # Worker 配置
    allow_abort_jobs = True  # 允许中止任务
    poll_delay = 0.5  # 轮询延迟(秒)
    
    # 日志配置
    log_results = True  # 记录任务结果
    
    @classmethod
    def register_task(cls, func):
        """注册任务函数"""
        if func not in cls.functions:
            cls.functions.append(func)
        return func
    
    @classmethod
    def register_cron(cls, cron_spec):
        """注册定时任务装饰器"""
        def decorator(func):
            if func not in cls.functions:
                cls.functions.append(func)
            cls.cron_jobs.append(cron_spec)
            return func
        return decorator


# 全局 Redis 连接池（单例模式）
_redis_pool: Optional[ArqRedis] = None


async def get_redis_pool() -> ArqRedis:
    """
    获取全局 Redis 连接池（单例）
    避免每次调用时创建新连接
    """
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = await create_pool(WorkerSettings.redis_settings)
    return _redis_pool


async def close_redis_pool() -> None:
    """
    关闭 Redis 连接池
    应用关闭时调用
    """
    global _redis_pool
    if _redis_pool:
        await _redis_pool.close()
        _redis_pool = None


async def enqueue_task(task_name: str, *args, **kwargs) -> Optional[str]:
    """
    将任务加入队列
    
    Args:
        task_name: 任务函数名
        *args: 任务参数
        **kwargs: 任务关键字参数
    
    Returns:
        job_id: 任务ID
    """
    pool = await get_redis_pool()
    job = await pool.enqueue_job(task_name, *args, **kwargs)
    return job.job_id if job else None


async def get_job_result(job_id: str) -> Optional[any]:
    """
    获取任务结果
    
    Args:
        job_id: 任务ID
    
    Returns:
        result: 任务结果，None 表示未完成
    """
    pool = await get_redis_pool()
    job = await pool.get_job_result(job_id)
    return job


# 导入任务函数（避免循环导入）
def setup_tasks():
    """设置任务函数列表"""
    from backend.api.tasks.premium_task import deliver_premium_task
    from backend.api.tasks.order_task import expire_pending_orders_task
    
    WorkerSettings.functions = [
        deliver_premium_task,
        expire_pending_orders_task,
    ]
    
    # 定时任务：每 5 分钟检查过期订单
    from arq.cron import cron
    WorkerSettings.cron_jobs = [
        cron(expire_pending_orders_task, minute={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})
    ]


# 在 worker 启动时调用
setup_tasks()
