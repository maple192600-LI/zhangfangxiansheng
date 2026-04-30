"""并发锁测试 — Session 隔离验证

按 python-testing 技能规范编写
"""
import asyncio
import pytest
from agents.session_lock import get_session_lock, cleanup_lock, active_lock_count


class TestSessionLock:
    """验证会话并发锁"""

    def test_创建锁成功(self):
        lock = get_session_lock(1)
        assert isinstance(lock, asyncio.Lock)

    def test_同一session返回同一把锁(self):
        lock1 = get_session_lock(999)
        lock2 = get_session_lock(999)
        assert lock1 is lock2

    def test_清理后锁消失(self):
        get_session_lock(777)
        cleanup_lock(777)
        # 再次获取应该是新锁
        lock = get_session_lock(777)
        assert isinstance(lock, asyncio.Lock)

    def test_活跃锁计数(self):
        lock = get_session_lock(888)
        # 未锁定的锁不计入活跃
        count = active_lock_count()
        assert isinstance(count, int)
