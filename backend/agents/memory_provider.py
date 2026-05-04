"""MemoryProvider ABC — 记忆系统抽象基类

5 阶段生命周期：initialize → system_prompt_block → prefetch → sync_turn → shutdown
冻结快照 + 注入检测 + 可选钩子。
"""
import re
from abc import ABC, abstractmethod


# ── 注入检测 ─────────────────────────────────────────────

_INJECTION_PATTERNS = [
    (r'忽略\s*(所有|之前|上面).*指令', "prompt_injection"),
    (r'假装\s*(是|你)', "role_manipulation"),
    (r'不要.*告诉.*用户', "deception_hide"),
    (r'\bsystem\s*:\s*', "role_injection"),
]


def scan_memory_value(value: str) -> str | None:
    """扫描记忆值，返回威胁 ID 或 None"""
    for char in ('​', '‌', '﻿'):
        if char in value:
            return "invisible_unicode"
    for pattern, threat_id in _INJECTION_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            return threat_id
    return None


# ── ABC ──────────────────────────────────────────────────

class MemoryProvider(ABC):
    """记忆提供者抽象基类"""

    def __init__(self):
        self._frozen_snapshot: list[dict] | None = None
        self._agent_code: str = ""

    @abstractmethod
    async def initialize(self, agent_code: str, **kwargs) -> None:
        """Agent 启动时调用一次"""

    @abstractmethod
    def system_prompt_block(self) -> str:
        """返回注入 system prompt 的记忆文本块"""

    @abstractmethod
    async def prefetch(self, session_id: str) -> list[dict]:
        """预加载记忆并冻结快照"""

    @abstractmethod
    async def sync_turn(self, session_id: str, messages: list[dict]) -> None:
        """每轮对话后同步记忆"""

    @abstractmethod
    async def shutdown(self) -> None:
        """清理资源"""

    @abstractmethod
    async def delete(self, memory_id: int) -> bool:
        """删除一条记忆"""

    @abstractmethod
    async def update(self, memory_id: int, key: str, content: str) -> dict | None:
        """更新一条记忆"""

    # 可选钩子
    async def on_session_switch(self, old_sid: str, new_sid: str) -> None:
        pass

    async def on_pre_compress(self, messages: list[dict]) -> str:
        return ""

    async def on_memory_write(self, key: str, value: str) -> None:
        pass

    async def on_skill_used(self, skill_name: str) -> None:
        pass
