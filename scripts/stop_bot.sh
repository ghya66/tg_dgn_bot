#!/bin/bash
# Telegram Bot 停止脚本

echo "⏹️  停止 Telegram Bot..."

# 查找 Bot 进程
BOT_PID=$(pgrep -f "python3.*src.bot" | head -n1)

if [ -z "$BOT_PID" ]; then
    echo "ℹ️  Bot 未运行"
    exit 0
fi

# 发送 SIGTERM 信号
echo "📤 发送停止信号到进程 $BOT_PID..."
kill -TERM "$BOT_PID"

# 等待进程结束
for i in {1..10}; do
    if ! kill -0 "$BOT_PID" 2>/dev/null; then
        echo "✅ Bot 已停止"
        exit 0
    fi
    echo "⏳ 等待 Bot 停止... ($i/10)"
    sleep 1
done

# 强制结束
echo "⚠️  强制停止 Bot..."
kill -9 "$BOT_PID" 2>/dev/null || true
echo "✅ Bot 已强制停止"
