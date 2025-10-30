#!/bin/bash
# Stage 7 快速启动脚本
# 同时启动 FastAPI 后端和 Streamlit 前端

set -e

echo "========================================"
echo "  Stage 7: Streamlit 管理界面启动脚本"
echo "========================================"
echo ""

# 切换到项目根目录
cd "$(dirname "$0")/.."

# 加载环境变量
if [ -f .env ]; then
    echo "✅ 加载环境变量..."
    set -a
    source .env
    set +a
else
    echo "❌ .env 文件不存在"
    exit 1
fi

# 检查必需的环境变量
if [ -z "$API_BASE_URL" ] || [ -z "$API_KEY" ]; then
    echo "❌ 缺少必需的环境变量: API_BASE_URL 或 API_KEY"
    echo "请在 .env 文件中配置："
    echo "  API_BASE_URL=http://localhost:8000"
    echo "  API_KEY=your-api-key"
    exit 1
fi

# 创建数据目录
if [ ! -d "./data" ]; then
    echo "📁 创建数据目录..."
    mkdir -p ./data
fi

# 检查 Redis 服务
if ! redis-cli ping &> /dev/null; then
    echo "🔴 Redis 服务未启动，正在启动..."
    redis-server --daemonize yes --port 6379
    sleep 2
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis 服务启动成功"
    else
        echo "❌ Redis 服务启动失败"
        exit 1
    fi
else
    echo "✅ Redis 服务已运行"
fi

# 检查 Python 虚拟环境
if [ ! -f ".venv/bin/python" ]; then
    echo "❌ 虚拟环境不存在: .venv"
    echo "请先创建虚拟环境: python -m venv .venv"
    exit 1
fi

PYTHON_BIN="$(pwd)/.venv/bin/python"
UVICORN_BIN="$(pwd)/.venv/bin/uvicorn"
STREAMLIT_BIN="$(pwd)/.venv/bin/streamlit"

# 停止旧服务
echo "🛑 停止旧服务..."
pkill -f "uvicorn backend.api.main:app" 2>/dev/null || true
pkill -f "streamlit run backend/admin/app.py" 2>/dev/null || true
sleep 2

# 启动 FastAPI 后端
echo ""
echo "🚀 启动 FastAPI 后端 (http://localhost:8000)..."
$UVICORN_BIN backend.api.main:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload \
    > /tmp/fastapi.log 2>&1 &

FASTAPI_PID=$!
echo "   PID: $FASTAPI_PID"
echo "   日志: /tmp/fastapi.log"

# 等待 FastAPI 启动
echo "   等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health/ > /dev/null 2>&1; then
        echo "   ✅ FastAPI 后端启动成功"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ FastAPI 后端启动超时"
        echo "   查看日志: tail -f /tmp/fastapi.log"
        exit 1
    fi
    sleep 1
done

# 启动 Streamlit 前端
echo ""
echo "🚀 启动 Streamlit 前端 (http://localhost:8501)..."
$STREAMLIT_BIN run backend/admin/app.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    > /tmp/streamlit.log 2>&1 &

STREAMLIT_PID=$!
echo "   PID: $STREAMLIT_PID"
echo "   日志: /tmp/streamlit.log"

# 等待 Streamlit 启动
echo "   等待服务启动..."
for i in {1..30}; do
    if curl -s http://localhost:8501 > /dev/null 2>&1; then
        echo "   ✅ Streamlit 前端启动成功"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "   ❌ Streamlit 前端启动超时"
        echo "   查看日志: tail -f /tmp/streamlit.log"
        exit 1
    fi
    sleep 1
done

# 显示服务信息
echo ""
echo "========================================"
echo "  ✅ 服务启动成功！"
echo "========================================"
echo ""
echo "📊 FastAPI 后端:"
echo "   URL: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo "   Health: http://localhost:8000/health/"
echo "   PID: $FASTAPI_PID"
echo "   日志: tail -f /tmp/fastapi.log"
echo ""
echo "🖥️  Streamlit 前端:"
echo "   URL: http://localhost:8501"
echo "   PID: $STREAMLIT_PID"
echo "   日志: tail -f /tmp/streamlit.log"
echo ""
echo "🔑 API Key: ${API_KEY:0:8}***"
echo ""
echo "🛑 停止服务:"
echo "   kill $FASTAPI_PID $STREAMLIT_PID"
echo "   或运行: ./scripts/stop_stage7.sh"
echo ""
echo "========================================"
