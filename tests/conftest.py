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
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault('BOT_TOKEN', 'test_bot_token')
os.environ.setdefault('USDT_TRC20_RECEIVE_ADDR', 'TTestAddress123456789012345678901234')
os.environ.setdefault('WEBHOOK_SECRET', 'test_secret_key')
os.environ.setdefault('REDIS_HOST', 'localhost')
os.environ.setdefault('REDIS_PORT', '6379')
os.environ.setdefault('REDIS_DB', '0')  # 使用 DB 0（与 REDIS_URL 一致）
os.environ.setdefault('ORDER_TIMEOUT_MINUTES', '30')


@pytest.fixture
async def redis_client():
    """提供一个已连接的 Redis 客户端
    
    只有显式请求此固件的测试才会使用（通常是标记了 @pytest.mark.redis 的测试）
    """
    import redis.asyncio as redis
    import asyncio
    
    client = redis.from_url(REDIS_URL, decode_responses=True, socket_timeout=3)
    
    # 等待 Redis 就绪（最多 10 秒）
    redis_available = False
    for _ in range(100):
        try:
            pong = await client.ping()
            if pong:
                redis_available = True
                break
        except Exception:
            await asyncio.sleep(0.1)
    
    if not redis_available:
        await client.aclose()
        pytest.skip("Redis not available, skipping Redis integration tests")
    
    yield client
    await client.aclose()


@pytest.fixture
async def clean_redis(redis_client):
    """清理 Redis 数据库（需要显式请求才会执行）
    
    在测试前后清理数据库，避免测试间污染
    """
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()