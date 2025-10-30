#!/bin/bash
# FastAPI 启动脚本

set -e

# ============================================================================
# 环境变量加载
# ============================================================================

if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found"
fi

# ============================================================================
# 配置检查
# ============================================================================

echo "Checking configuration..."
python scripts/validate_config.py || {
    echo "Configuration validation failed"
    exit 1
}

# ============================================================================
# 数据库迁移
# ============================================================================

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
    echo "Running database migrations..."
    alembic upgrade head
fi

# ============================================================================
# 启动 FastAPI 服务
# ============================================================================

echo "Starting FastAPI application..."

# 获取配置（默认值）
API_HOST="${API_HOST:-0.0.0.0}"
API_PORT="${API_PORT:-8000}"
API_WORKERS="${API_WORKERS:-4}"
ENV="${ENV:-development}"

# 根据环境选择启动方式
if [ "$ENV" = "production" ]; then
    # 生产环境：使用 Gunicorn + Uvicorn workers
    echo "Starting in PRODUCTION mode..."
    exec gunicorn backend.api.main:app \
        --workers "$API_WORKERS" \
        --worker-class uvicorn.workers.UvicornWorker \
        --bind "${API_HOST}:${API_PORT}" \
        --timeout 60 \
        --graceful-timeout 30 \
        --access-logfile - \
        --error-logfile - \
        --log-level info
else
    # 开发环境：使用 Uvicorn 热重载
    echo "Starting in DEVELOPMENT mode..."
    exec uvicorn backend.api.main:app \
        --host "$API_HOST" \
        --port "$API_PORT" \
        --reload \
        --log-level debug
fi
