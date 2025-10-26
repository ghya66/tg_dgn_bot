"""
测试配置
"""
import pytest
import os
import sys

# 添加src目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

# 配置pytest异步测试
pytest_plugins = ['pytest_asyncio']

# 设置测试环境变量
os.environ.setdefault('BOT_TOKEN', 'test_bot_token')
os.environ.setdefault('USDT_TRC20_RECEIVE_ADDR', 'TTestAddress123456789012345678901234')
os.environ.setdefault('WEBHOOK_SECRET', 'test_secret_key')
os.environ.setdefault('REDIS_HOST', 'localhost')
os.environ.setdefault('REDIS_PORT', '6379')
os.environ.setdefault('REDIS_DB', '1')  # 使用测试数据库
os.environ.setdefault('ORDER_TIMEOUT_MINUTES', '30')