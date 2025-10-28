#!/bin/bash
# Telegram Bot 启动脚本

set -e

echo "🚀 启动 Telegram Bot..."

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "❌ 错误: .env 文件不存在"
    echo "请复制 .env.example 并配置："
    echo "  cp .env.example .env"
    exit 1
fi

# 检查 Python 版本
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}' | cut -d. -f1,2)
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo "❌ 错误: Python 版本需要 >= $REQUIRED_VERSION (当前: $PYTHON_VERSION)"
    exit 1
fi

echo "✅ Python 版本检查通过: $PYTHON_VERSION"

# 检查依赖
if ! python3 -c "import telegram" 2>/dev/null; then
    echo "⚠️  警告: python-telegram-bot 未安装"
    echo "正在安装依赖..."
    pip3 install -r requirements.txt
fi

# 检查 Redis 连接
echo "🔍 检查 Redis 连接..."
if ! python3 -c "import redis; r = redis.from_url('redis://localhost:6379/0'); r.ping()" 2>/dev/null; then
    echo "⚠️  警告: Redis 连接失败"
    echo "请确保 Redis 正在运行："
    echo "  sudo systemctl start redis"
    echo "  或使用 Docker: docker run -d -p 6379:6379 redis:7-alpine"
    read -p "是否继续？ (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 初始化数据库
echo "📦 初始化数据库..."
python3 -c "from src.database import init_db; init_db()"
echo "✅ 数据库初始化完成"

# 启动 Bot
echo "🤖 启动 Bot..."
python3 -m src.bot

# 捕获退出信号
trap 'echo "⏹️  停止 Bot..."; kill $!; exit 0' SIGINT SIGTERM

wait
