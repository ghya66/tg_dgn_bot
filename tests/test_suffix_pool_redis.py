"""
后缀池 Redis 集成测试

测试真实 Redis 环境下的后缀分配、释放、TTL 过期等功能
"""
import asyncio
import pytest
import time

from src.payments.suffix_manager import suffix_manager

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.redis,  # 标记为需要 Redis 的测试
    pytest.mark.timeout(15),  # 防止死锁
]


@pytest.mark.asyncio
async def test_suffix_allocate_basic(clean_redis, redis_client):
    """基本的后缀分配功能"""
    # 注入真实的 Redis 客户端
    suffix_manager.redis_client = redis_client
    
    order_id = "test_order_001"
    suffix = await suffix_manager.allocate_suffix(order_id)
    
    assert suffix is not None
    assert 1 <= suffix <= 999
    
    # 验证 Redis 中存储了正确的数据
    key = f"suffix:{suffix}"
    stored_order_id = await redis_client.get(key)
    assert stored_order_id == order_id


@pytest.mark.asyncio
async def test_suffix_unique_concurrent(clean_redis, redis_client):
    """并发获取应当唯一、不撞车"""
    suffix_manager.redis_client = redis_client
    
    N = 50
    results = []
    
    async def worker(idx):
        order_id = f"order_{idx:04d}"
        s = await suffix_manager.allocate_suffix(order_id)
        results.append(s)
    
    await asyncio.gather(*[worker(i) for i in range(N)])
    
    # 所有分配的后缀应该唯一
    assert len(results) == len(set(results)), f"发现重复后缀: {results}"
    assert all(1 <= s <= 999 for s in results if s is not None)


@pytest.mark.asyncio
async def test_suffix_release_and_reuse(clean_redis, redis_client):
    """释放后缀后应该能够重新使用"""
    suffix_manager.redis_client = redis_client
    
    order_id_1 = "test_order_001"
    suffix = await suffix_manager.allocate_suffix(order_id_1)
    assert suffix is not None
    
    # 释放后缀
    released = await suffix_manager.release_suffix(suffix, order_id_1)
    assert released is True
    
    # 验证 Redis 中已删除
    key = f"suffix:{suffix}"
    value = await redis_client.get(key)
    assert value is None
    
    # 再次分配，应该能拿到刚才释放的后缀
    # （因为它是第一个可用的）
    got_suffixes = set()
    for i in range(20):
        order_id = f"test_order_{i:03d}"
        s = await suffix_manager.allocate_suffix(order_id)
        got_suffixes.add(s)
    
    assert suffix in got_suffixes


@pytest.mark.asyncio
async def test_suffix_release_wrong_order_id(clean_redis, redis_client):
    """使用错误的 order_id 应该无法释放后缀"""
    suffix_manager.redis_client = redis_client
    
    order_id_1 = "test_order_001"
    suffix = await suffix_manager.allocate_suffix(order_id_1)
    assert suffix is not None
    
    # 尝试用错误的 order_id 释放
    wrong_order_id = "wrong_order"
    released = await suffix_manager.release_suffix(suffix, wrong_order_id)
    assert released is False
    
    # 验证后缀仍然被占用
    key = f"suffix:{suffix}"
    value = await redis_client.get(key)
    assert value == order_id_1


@pytest.mark.asyncio
async def test_suffix_ttl_expire(clean_redis, redis_client):
    """过期自动释放（无需手动 release）"""
    suffix_manager.redis_client = redis_client
    
    # 修改过期时间为 1 秒（仅用于测试）
    original_timeout = suffix_manager.redis_client
    
    order_id = "test_order_ttl"
    
    # 手动分配并设置短 TTL
    suffix = await suffix_manager.allocate_suffix(order_id)
    assert suffix is not None
    
    key = f"suffix:{suffix}"
    
    # 重新设置 TTL 为 1 秒
    await redis_client.expire(key, 1)
    
    # 验证当前存在
    value = await redis_client.get(key)
    assert value == order_id
    
    # 等待过期
    await asyncio.sleep(1.3)
    
    # 验证已过期
    value = await redis_client.get(key)
    assert value is None
    
    # 该后缀应该可以被重新分配
    got_suffixes = set()
    for i in range(20):
        s = await suffix_manager.allocate_suffix(f"order_{i}")
        got_suffixes.add(s)
    
    assert suffix in got_suffixes


@pytest.mark.asyncio
async def test_suffix_extend_lease(clean_redis, redis_client):
    """延长后缀租期"""
    suffix_manager.redis_client = redis_client
    
    order_id = "test_order_extend"
    suffix = await suffix_manager.allocate_suffix(order_id)
    assert suffix is not None
    
    key = f"suffix:{suffix}"
    
    # 手动设置一个较短的 TTL（10秒）
    await redis_client.expire(key, 10)
    
    # 获取初始 TTL
    ttl_before = await redis_client.ttl(key)
    assert 0 < ttl_before <= 10
    
    # 等待一段时间让 TTL 减少
    await asyncio.sleep(2)
    
    # 延长租期（会恢复到默认的 30*60 秒）
    extended = await suffix_manager.extend_suffix_lease(suffix, order_id)
    assert extended is True
    
    # 获取延长后的 TTL
    ttl_after = await redis_client.ttl(key)
    
    # TTL 应该明显比之前更长（应该接近 30*60 = 1800 秒）
    assert ttl_after > 100  # 至少应该大于 100 秒


@pytest.mark.asyncio
async def test_suffix_extend_lease_wrong_order_id(clean_redis, redis_client):
    """使用错误的 order_id 无法延长租期"""
    suffix_manager.redis_client = redis_client
    
    order_id = "test_order_extend"
    suffix = await suffix_manager.allocate_suffix(order_id)
    assert suffix is not None
    
    # 尝试用错误的 order_id 延长
    wrong_order_id = "wrong_order"
    extended = await suffix_manager.extend_suffix_lease(suffix, wrong_order_id)
    assert extended is False


@pytest.mark.asyncio
async def test_suffix_get_info(clean_redis, redis_client):
    """获取后缀信息"""
    suffix_manager.redis_client = redis_client
    
    order_id = "test_order_info"
    suffix = await suffix_manager.allocate_suffix(order_id)
    assert suffix is not None
    
    # 获取后缀信息
    info = await suffix_manager.get_suffix_info(suffix)
    assert info is not None
    assert info["suffix"] == suffix
    assert info["order_id"] == order_id
    assert info["ttl_seconds"] > 0
    assert info["expires_at"] is not None


@pytest.mark.asyncio
async def test_suffix_get_info_not_exists(clean_redis, redis_client):
    """获取不存在的后缀信息"""
    suffix_manager.redis_client = redis_client
    
    # 查询一个未分配的后缀
    info = await suffix_manager.get_suffix_info(888)
    assert info is None


@pytest.mark.asyncio
async def test_suffix_pool_exhaustion(clean_redis, redis_client):
    """后缀池耗尽场景"""
    suffix_manager.redis_client = redis_client
    
    # 尝试分配大量后缀（不超过999）
    allocated = []
    
    # 分配 100 个后缀
    for i in range(100):
        order_id = f"order_{i:04d}"
        suffix = await suffix_manager.allocate_suffix(order_id)
        if suffix is not None:
            allocated.append(suffix)
    
    # 应该都能成功分配
    assert len(allocated) == 100
    assert len(set(allocated)) == 100  # 无重复


@pytest.mark.asyncio
async def test_suffix_stress_test(clean_redis, redis_client):
    """压力测试：模拟高并发场景"""
    suffix_manager.redis_client = redis_client
    
    N = 200  # 200 个并发订单
    results = []
    errors = []
    
    async def worker(idx):
        try:
            order_id = f"stress_order_{idx:05d}"
            suffix = await suffix_manager.allocate_suffix(order_id)
            if suffix is not None:
                results.append((idx, suffix))
        except Exception as e:
            errors.append((idx, str(e)))
    
    # 并发执行
    await asyncio.gather(*[worker(i) for i in range(N)])
    
    # 验证结果
    assert len(errors) == 0, f"出现错误: {errors[:5]}"
    assert len(results) == N, f"只成功分配了 {len(results)}/{N} 个后缀"
    
    suffixes = [s for _, s in results]
    assert len(suffixes) == len(set(suffixes)), "发现重复的后缀"


@pytest.mark.asyncio
async def test_suffix_cleanup_expired(clean_redis, redis_client):
    """清理过期后缀统计"""
    suffix_manager.redis_client = redis_client
    
    # 分配几个后缀
    for i in range(5):
        await suffix_manager.allocate_suffix(f"order_{i}")
    
    # 获取当前活跃数量
    count = await suffix_manager.cleanup_expired()
    assert count == 5
    
    # 手动设置一个后缀为极短 TTL
    await redis_client.expire("suffix:1", 1)
    await asyncio.sleep(1.2)
    
    # 再次统计，应该少一个
    count = await suffix_manager.cleanup_expired()
    assert count == 4
