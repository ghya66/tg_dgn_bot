"""
后缀生成器测试
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, patch
import time

from src.payments.suffix_manager import SuffixManager


@pytest.fixture
def suffix_generator():
    """创建后缀生成器实例"""
    generator = SuffixManager()
    
    # 模拟Redis客户端
    from unittest.mock import MagicMock
    generator.redis_client = MagicMock()
    
    # 配置 Redis pipeline mock
    mock_pipeline = MagicMock()
    mock_pipeline.get = MagicMock()
    mock_pipeline.ttl = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[None, -2])
    generator.redis_client.pipeline.return_value = mock_pipeline
    
    # 配置其他 Redis 方法
    generator.redis_client.set = AsyncMock(return_value=True)
    generator.redis_client.get = AsyncMock(return_value=None)
    generator.redis_client.keys = AsyncMock(return_value=[])
    generator.redis_client.delete = AsyncMock(return_value=1)
    generator.redis_client.eval = AsyncMock(return_value=1)  # 用于 Lua 脚本
    
    return generator


@pytest.mark.asyncio
async def test_allocate_suffix_success(suffix_generator):
    """测试成功分配后缀"""
    # 模拟Redis返回空的已使用后缀列表
    suffix_generator.redis_client.keys.return_value = []
    suffix_generator.redis_client.set.return_value = True
    
    order_id = "test_order_123"
    suffix = await suffix_generator.allocate_suffix(order_id)
    
    assert suffix is not None
    assert 1 <= suffix <= 999
    
    # 验证Redis调用
    suffix_generator.redis_client.keys.assert_called()
    suffix_generator.redis_client.set.assert_called()


@pytest.mark.asyncio
async def test_allocate_suffix_with_conflicts(suffix_generator):
    """测试有冲突时的后缀分配"""
    # 模拟前10个后缀已被使用
    suffix_generator.redis_client.keys.return_value = [
        f"suffix:{i}" for i in range(1, 11)
    ]
    suffix_generator.redis_client.set.return_value = True
    
    order_id = "test_order_123"
    suffix = await suffix_generator.allocate_suffix(order_id)
    
    assert suffix is not None
    assert suffix >= 11  # 应该分配第11个或更后的后缀


@pytest.mark.asyncio
async def test_allocate_suffix_all_occupied(suffix_generator):
    """测试所有后缀都被占用的情况"""
    # 模拟所有后缀都被使用
    suffix_generator.redis_client.keys.return_value = [
        f"suffix:{i}" for i in range(1, 1000)
    ]
    
    order_id = "test_order_123"
    suffix = await suffix_generator.allocate_suffix(order_id)
    
    assert suffix is None


@pytest.mark.asyncio
async def test_release_suffix_success(suffix_generator):
    """测试成功释放后缀"""
    # 模拟Lua脚本返回成功
    suffix_generator.redis_client.eval.return_value = 1
    
    result = await suffix_generator.release_suffix(123, "test_order_123")
    
    assert result is True
    suffix_generator.redis_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_release_suffix_wrong_order(suffix_generator):
    """测试用错误的订单ID释放后缀"""
    # 模拟Lua脚本返回失败（订单ID不匹配）
    suffix_generator.redis_client.eval.return_value = 0
    
    result = await suffix_generator.release_suffix(123, "wrong_order_id")
    
    assert result is False


@pytest.mark.asyncio
async def test_extend_suffix_lease(suffix_generator):
    """测试延长后缀租期"""
    # 模拟Lua脚本返回成功
    suffix_generator.redis_client.eval.return_value = 1
    
    result = await suffix_generator.extend_suffix_lease(123, "test_order_123")
    
    assert result is True
    suffix_generator.redis_client.eval.assert_called_once()


@pytest.mark.asyncio
async def test_get_suffix_info(suffix_generator):
    """测试获取后缀信息"""
    # 模拟Redis返回后缀信息
    suffix_generator.redis_client.pipeline.return_value.execute = AsyncMock(return_value=[
        "test_order_123",  # GET结果
        3600  # TTL结果
    ])
    
    info = await suffix_generator.get_suffix_info(123)
    
    assert info is not None
    assert info["suffix"] == 123
    assert info["order_id"] == "test_order_123"
    assert info["ttl_seconds"] == 3600


@pytest.mark.asyncio
async def test_get_suffix_info_not_found(suffix_generator):
    """测试获取不存在的后缀信息"""
    # 模拟Redis返回None
    suffix_generator.redis_client.pipeline.return_value.execute = AsyncMock(return_value=[
        None,  # GET结果
        -2     # TTL结果（key不存在）
    ])
    
    info = await suffix_generator.get_suffix_info(123)
    
    assert info is None


@pytest.mark.asyncio
async def test_concurrent_allocations():
    """测试并发分配后缀（模拟300个并发请求）"""
    generator = SuffixManager()
    generator.redis_client = AsyncMock()
    
    # 模拟逐步占用后缀的情况
    allocated_suffixes = set()
    
    def mock_keys(*args, **kwargs):
        return [f"suffix:{s}" for s in allocated_suffixes]
    
    def mock_set(key, value, nx=True, ex=None):
        if nx:
            suffix = int(key.split(":")[1])
            if suffix not in allocated_suffixes:
                allocated_suffixes.add(suffix)
                return True
            return False
        return True
    
    generator.redis_client.keys.side_effect = mock_keys
    generator.redis_client.set.side_effect = mock_set
    
    # 创建300个并发任务
    tasks = []
    for i in range(300):
        order_id = f"order_{i}"
        task = generator.allocate_suffix(order_id)
        tasks.append(task)
    
    # 执行所有任务
    results = await asyncio.gather(*tasks)
    
    # 验证结果
    successful_allocations = [r for r in results if r is not None]
    assert len(successful_allocations) == 300  # 所有分配都应该成功
    assert len(set(successful_allocations)) == 300  # 没有重复的后缀
    assert all(1 <= s <= 999 for s in successful_allocations)  # 所有后缀在有效范围内


@pytest.mark.asyncio
async def test_cleanup_expired_suffixes(suffix_generator):
    """测试后缀过期机制"""
    # 模拟一些后缀即将过期
    current_time = int(time.time())
    
    # 设置不同TTL的后缀
    suffix_generator.redis_client.keys.return_value = [
        "suffix:1", "suffix:2", "suffix:3"
    ]
    
    def mock_pipeline_execute():
        mock_pipeline = AsyncMock()
        mock_pipeline.execute.return_value = [
            ["order_1", 10],    # 10秒后过期
            ["order_2", 3600],  # 1小时后过期
            ["order_3", -1]     # 永不过期（不应该发生）
        ]
        return mock_pipeline
    
    suffix_generator.redis_client.pipeline.return_value = mock_pipeline_execute()
    
    # 清理过期后缀
    active_count = await suffix_generator.cleanup_expired()
    
    assert active_count == 3  # 返回当前活跃的后缀数量