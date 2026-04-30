"""Session 并发锁

防止同一 session 的 run_turn 并发执行。
使用 asyncio.Lock 按 session_id 隔离。
"""
import asyncio
from typing import Optional


_locks: dict[int, asyncio.Lock] = {}


def get_session_lock(session_id: int) -> asyncio.Lock:
    """获取指定 session 的锁（懒创建）"""
    if session_id not in _locks:
        _locks[session_id] = asyncio.Lock()
    return _locks[session_id]


def cleanup_lock(session_id: int) -> None:
    """会话结束后清理锁，防止内存泄漏"""
    _locks.pop(session_id, None)


def active_lock_count() -> int:
    """当前活跃锁数量（调试用）"""
    return sum(1 for lock in _locks.values() if lock.locked())
