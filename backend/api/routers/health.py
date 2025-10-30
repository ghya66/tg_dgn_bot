"""
健康检查 API 路由

提供服务健康状态检查端点。

用于:
- Kubernetes liveness/readiness probes
- 负载均衡器健康检查
- 监控告警
"""

from typing import Dict, Any

import structlog
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from backend.api.database import get_db
from backend.api.infrastructure.redis_client import get_redis

logger = structlog.get_logger(__name__)

router = APIRouter()


# ============================================================================
# Pydantic 模型
# ============================================================================

class HealthStatus(BaseModel):
    """健康状态响应"""
    status: str  # healthy | degraded | unhealthy
    checks: Dict[str, Any]


class ComponentCheck(BaseModel):
    """组件健康检查"""
    healthy: bool
    message: str
    latency_ms: float = 0.0


# ============================================================================
# 健康检查端点
# ============================================================================

@router.get("/", response_model=HealthStatus)
async def overall_health(
    request: Request,
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    整体健康检查
    
    检查所有关键组件:
    - 数据库连接
    - Redis 连接
    - 工作队列（arq worker）
    
    状态定义:
    - healthy: 所有组件正常
    - degraded: 部分组件异常（非关键）
    - unhealthy: 关键组件异常
    """
    checks = {}
    
    # 1. 检查数据库
    db_check = await _check_database(db)
    checks["database"] = db_check.dict()
    
    # 2. 检查 Redis
    redis_check = await _check_redis(redis)
    checks["redis"] = redis_check.dict()
    
    # 3. 检查 Worker（通过 Redis 队列）
    worker_check = await _check_worker(redis)
    checks["worker"] = worker_check.dict()
    
    # 计算整体状态
    critical_components = ["database", "redis"]
    critical_healthy = all(checks[c]["healthy"] for c in critical_components)
    all_healthy = all(check["healthy"] for check in checks.values())
    
    if all_healthy:
        overall_status = "healthy"
    elif critical_healthy:
        overall_status = "degraded"
    else:
        overall_status = "unhealthy"
    
    logger.info(
        "health_check_overall",
        status=overall_status,
        checks=checks,
    )
    
    return HealthStatus(status=overall_status, checks=checks)


@router.get("/db", response_model=ComponentCheck)
async def database_health(
    request: Request,
    db: Session = Depends(get_db),
):
    """
    数据库健康检查
    
    执行简单查询验证连接：SELECT 1
    """
    check = await _check_database(db)
    
    logger.info(
        "health_check_database",
        healthy=check.healthy,
        latency_ms=check.latency_ms,
    )
    
    return check


@router.get("/redis", response_model=ComponentCheck)
async def redis_health(
    request: Request,
    redis: Redis = Depends(get_redis),
):
    """
    Redis 健康检查
    
    执行 PING 命令验证连接。
    """
    check = await _check_redis(redis)
    
    logger.info(
        "health_check_redis",
        healthy=check.healthy,
        latency_ms=check.latency_ms,
    )
    
    return check


@router.get("/worker", response_model=ComponentCheck)
async def worker_health(
    request: Request,
    redis: Redis = Depends(get_redis),
):
    """
    Worker 健康检查
    
    检查 arq 工作队列是否有活跃 worker。
    """
    check = await _check_worker(redis)
    
    logger.info(
        "health_check_worker",
        healthy=check.healthy,
    )
    
    return check


# ============================================================================
# 内部检查函数
# ============================================================================

async def _check_database(db: Session) -> ComponentCheck:
    """检查数据库连接"""
    import time
    
    try:
        start = time.time()
        db.execute(text("SELECT 1"))
        latency = (time.time() - start) * 1000  # 转换为毫秒
        
        return ComponentCheck(
            healthy=True,
            message="数据库连接正常",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error("database_health_check_failed", error=str(e))
        return ComponentCheck(
            healthy=False,
            message=f"数据库错误: {str(e)}",
        )


async def _check_redis(redis: Redis) -> ComponentCheck:
    """检查 Redis 连接"""
    import time
    
    try:
        start = time.time()
        await redis.ping()
        latency = (time.time() - start) * 1000
        
        return ComponentCheck(
            healthy=True,
            message="Redis 连接正常",
            latency_ms=round(latency, 2),
        )
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        return ComponentCheck(
            healthy=False,
            message=f"Redis 错误: {str(e)}",
        )


async def _check_worker(redis: Redis) -> ComponentCheck:
    """检查 arq worker 状态"""
    try:
        # 检查 arq 队列长度（队列键: arq:queue）
        queue_length = await redis.llen("arq:queue")
        
        # 检查是否有活跃的 worker（通过心跳键检测）
        # arq worker 会定期更新 arq:worker:<worker_id> 键
        worker_keys = await redis.keys("arq:worker:*")
        active_workers = len(worker_keys)
        
        if active_workers > 0:
            return ComponentCheck(
                healthy=True,
                message=f"{active_workers} 个 Worker 活跃，{queue_length} 个任务待处理",
            )
        else:
            # 没有活跃 worker（可能是降级状态）
            return ComponentCheck(
                healthy=False,
                message=f"未发现活跃 Worker，{queue_length} 个任务待处理",
            )
    
    except Exception as e:
        logger.error("worker_health_check_failed", error=str(e))
        return ComponentCheck(
            healthy=False,
            message=f"Worker 检查错误: {str(e)}",
        )
