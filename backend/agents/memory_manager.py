"""MemoryManager — 记忆系统编排层

管理 builtin + external Provider（最多 1 个外部）。
负责分发生命周期调用、路由工具调用、清洗 LLM 输出中的记忆标签。
"""
import asyncio
import logging
from enum import Enum, auto
from typing import Optional

from agents.memory_provider import MemoryProvider

logger = logging.getLogger(__name__)


# ── StreamingContextScrubber ──────────────────────────────

class ScrubberState(Enum):
    IDLE = auto()
    INSIDE = auto()


class StreamingContextScrubber:
    """清洗 LLM 输出中的 <memory-context>...</memory-context> 标签"""

    OPEN_TAG = "<memory-context>"
    CLOSE_TAG = "</memory-context>"

    def __init__(self):
        self._state = ScrubberState.IDLE
        self._buffer = ""

    def scrub(self, delta: str) -> str:
        output = []
        self._buffer += delta

        while self._buffer:
            if self._state == ScrubberState.IDLE:
                idx = self._buffer.find(self.OPEN_TAG)
                if idx == -1:
                    last_lt = self._buffer.rfind('<')
                    if last_lt == -1:
                        output.append(self._buffer)
                        self._buffer = ""
                    else:
                        output.append(self._buffer[:last_lt])
                        self._buffer = self._buffer[last_lt:]
                    break
                else:
                    output.append(self._buffer[:idx])
                    self._buffer = self._buffer[idx + len(self.OPEN_TAG):]
                    self._state = ScrubberState.INSIDE

            elif self._state == ScrubberState.INSIDE:
                idx = self._buffer.find(self.CLOSE_TAG)
                if idx == -1:
                    last_slash = self._buffer.rfind('</')
                    if last_slash == -1:
                        self._buffer = ""
                    else:
                        self._buffer = self._buffer[last_slash:]
                    break
                else:
                    self._buffer = self._buffer[idx + len(self.CLOSE_TAG):]
                    self._state = ScrubberState.IDLE

        return "".join(output)

    def flush(self) -> str:
        remaining = self._buffer
        self._buffer = ""
        if self._state == ScrubberState.IDLE:
            return remaining
        return ""


# ── MemoryManager ────────────────────────────────────────

class MemoryManager:
    def __init__(self, builtin_provider: MemoryProvider):
        self._builtin = builtin_provider
        self._external: Optional[MemoryProvider] = None

    def add_external_provider(self, provider: MemoryProvider) -> None:
        if self._external is not None:
            raise ValueError("最多支持 1 个外部 Provider")
        self._external = provider

    @property
    def providers(self) -> list[MemoryProvider]:
        result = [self._builtin]
        if self._external:
            result.append(self._external)
        return result

    async def initialize_all(self, agent_code: str, **kwargs) -> None:
        await self._builtin.initialize(agent_code, **kwargs)
        if self._external:
            await self._external.initialize(agent_code, **kwargs)

    async def prefetch_all(self, session_id: str) -> None:
        tasks = [p.prefetch(session_id) for p in self.providers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def prefetch_with_query(self, session_id: str, query: str) -> None:
        tasks = []
        for p in self.providers:
            if hasattr(p, "prefetch_with_query"):
                tasks.append(p.prefetch_with_query(session_id, query))
            else:
                tasks.append(p.prefetch(session_id))
        await asyncio.gather(*tasks, return_exceptions=True)

    def build_system_prompt(self) -> str:
        blocks = []
        builtin_block = self._builtin.system_prompt_block()
        if builtin_block:
            blocks.append(builtin_block)
        if self._external:
            ext_block = self._external.system_prompt_block()
            if ext_block:
                blocks.append(ext_block)
        if not blocks:
            return ""
        return "\n\n".join(blocks)

    async def sync_all(self, session_id: str, messages: list[dict]) -> None:
        tasks = [p.sync_turn(session_id, messages) for p in self.providers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def route_tool_call(self, tool_name: str, args: dict) -> dict:
        if tool_name.startswith("memory_"):
            return await self._dispatch_builtin(tool_name, args)
        if tool_name.startswith("ext_") and self._external:
            return await self._dispatch_external(tool_name, args)
        return {"ok": False, "error": f"未知记忆工具: {tool_name}"}

    async def _dispatch_builtin(self, tool_name: str, args: dict) -> dict:
        from agents.db_memory_provider import safe_write
        if tool_name == "memory_save":
            db = self._builtin._db
            agent_id = self._builtin._agent_id
            if not db or not agent_id:
                return {"ok": False, "error": "Provider 未初始化"}
            return await safe_write(db, agent_id, args.get("key", ""), args.get("content", args.get("value", "")))
        elif tool_name == "memory_search":
            results = await self._builtin.search(args.get("query", ""), limit=args.get("limit", 10))
            return {"ok": True, "results": results}
        elif tool_name == "memory_list":
            return {"ok": True, "memories": self._builtin._frozen_snapshot or []}
        return {"ok": False, "error": f"未知内置工具: {tool_name}"}

    async def _dispatch_external(self, tool_name: str, args: dict) -> dict:
        return {"ok": False, "error": f"外部 Provider 不支持: {tool_name}"}

    async def on_pre_compress_all(self, messages: list[dict]) -> None:
        tasks = [p.on_pre_compress(messages) for p in self.providers]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def shutdown_all(self) -> None:
        tasks = [p.shutdown() for p in self.providers]
        await asyncio.gather(*tasks, return_exceptions=True)

    def create_scrubber(self) -> StreamingContextScrubber:
        return StreamingContextScrubber()
