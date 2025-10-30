import asyncio
import pytest

from src.health import HealthService


class _FakeRedisOK:
    async def ping(self):
        return True


class _FakeRedisFail:
    async def ping(self):
        raise RuntimeError("boom")


class _FakeSessionOK:
    def execute(self, *_args, **_kwargs):
        return 1

    def close(self):
        pass


class _FakeSessionFail:
    def execute(self, *_args, **_kwargs):
        raise RuntimeError("db down")

    def close(self):
        pass


@pytest.mark.asyncio
async def test_health_all_ok():
    svc = HealthService()
    result = await svc.check_all(redis_client=_FakeRedisOK(), session_factory=lambda: _FakeSessionOK())
    assert result['ok'] is True
    assert result['redis']['ok'] is True
    assert result['db']['ok'] is True


@pytest.mark.asyncio
async def test_health_redis_fail():
    svc = HealthService()
    result = await svc.check_all(redis_client=_FakeRedisFail(), session_factory=lambda: _FakeSessionOK())
    assert result['ok'] is False
    assert result['redis']['ok'] is False
    assert result['db']['ok'] is True


def test_health_db_fail():
    svc = HealthService()
    # 仅测试同步的 DB 检查分支
    ok, msg = svc.check_db(session_factory=lambda: _FakeSessionFail())
    assert ok is False
    assert "db down" in msg.lower()
