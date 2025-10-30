#!/bin/bash
# Stage 7 停止脚本
# 停止 FastAPI 后端和 Streamlit 前端

echo "🛑 停止 Stage 7 服务..."

# 停止 FastAPI 后端
FASTAPI_PIDS=$(pgrep -f "uvicorn backend.api.main:app")
if [ -n "$FASTAPI_PIDS" ]; then
    echo "   停止 FastAPI 后端 (PID: $FASTAPI_PIDS)..."
    pkill -f "uvicorn backend.api.main:app"
    echo "   ✅ FastAPI 后端已停止"
else
    echo "   ⚠️  FastAPI 后端未运行"
fi

# 停止 Streamlit 前端
STREAMLIT_PIDS=$(pgrep -f "streamlit run backend/admin/app.py")
if [ -n "$STREAMLIT_PIDS" ]; then
    echo "   停止 Streamlit 前端 (PID: $STREAMLIT_PIDS)..."
    pkill -f "streamlit run backend/admin/app.py"
    echo "   ✅ Streamlit 前端已停止"
else
    echo "   ⚠️  Streamlit 前端未运行"
fi

# 清理日志文件（可选）
if [ "$1" == "--clean-logs" ]; then
    echo "   🗑️  清理日志文件..."
    rm -f /tmp/fastapi.log /tmp/streamlit.log
    echo "   ✅ 日志文件已清理"
fi

echo "✅ 所有服务已停止"
