"""上下文引擎测试 — 压缩 + 组装 + 会话摘要

按 python-testing 技能规范编写
"""
import pytest
from agents.context import (
    estimate_tokens,
    should_compact,
    compact_messages,
    CompactResult,
    ContextEngine,
)


class TestToken估算:
    """验证 token 估算函数"""

    def test_空消息列表返回零(self):
        assert estimate_tokens([]) == 0

    def test_单条消息返回正数(self):
        msgs = [{"role": "user", "content": "你好"}]
        result = estimate_tokens(msgs)
        assert result > 0

    def test_长文本比短文本估算更多(self):
        short = [{"role": "user", "content": "hi"}]
        long = [{"role": "user", "content": "这是一段很长的文本内容" * 100}]
        assert estimate_tokens(long) > estimate_tokens(short)


class Test压缩判断:
    """验证是否需要压缩的判断逻辑"""

    def test_小消息不触发压缩(self):
        msgs = [{"role": "user", "content": "你好"}]
        assert not should_compact(msgs)

    def test_超大消息触发压缩(self):
        # 制造接近阈值的消息
        msgs = [{"role": "user", "content": "x" * 500000}]
        assert should_compact(msgs, max_context=100, reserve=10)


class Test消息压缩:
    """验证消息压缩核心逻辑"""

    @pytest.fixture
    def 标准消息列表(self):
        """30条对话 + 1条system"""
        return (
            [{"role": "system", "content": "你是助手"}]
            + [{"role": "user", "content": f"第{i}条消息"} for i in range(30)]
        )

    def test_保留system消息(self, 标准消息列表):
        result = compact_messages(标准消息列表, keep_recent=10)
        assert result.messages[0]["role"] == "system"

    def test_保留最近10条(self, 标准消息列表):
        result = compact_messages(标准消息列表, keep_recent=10)
        assert result.removed_count == 20

    def test_返回frozen_dataclass(self, 标准消息列表):
        result = compact_messages(标准消息列表, keep_recent=10)
        assert isinstance(result, CompactResult)
        assert isinstance(result.messages, tuple)

    def test_短消息不压缩(self):
        msgs = [{"role": "user", "content": "hi"}]
        result = compact_messages(msgs, keep_recent=10)
        assert result.removed_count == 0

    def test_空消息不崩溃(self):
        result = compact_messages([], keep_recent=10)
        assert result.removed_count == 0
        assert len(result.messages) == 0

    def test_已有摘要会保留在占位消息中(self, 标准消息列表):
        result = compact_messages(标准消息列表, existing_summary="之前的摘要", keep_recent=10)
        summary_msg = result.messages[1]
        assert "之前的摘要" in summary_msg["content"]


class TestContextEngine:
    """验证上下文引擎生命周期"""

    @pytest.fixture
    def engine(self):
        return ContextEngine(max_context=1000, reserve=100)

    def test_小消息不需要压缩(self, engine):
        msgs = [{"role": "user", "content": "hi"}]
        assert not engine.needs_compaction(msgs)

    def test_会话摘要更新和读取(self, engine):
        engine.update_summary(1, "测试摘要")
        assert engine.get_summary(1) == "测试摘要"

    def test_清理会话后摘要消失(self, engine):
        engine.update_summary(1, "测试摘要")
        engine.cleanup_session(1)
        assert engine.get_summary(1) == ""

    def test_组装注入记忆(self, engine):
        msgs = [{"role": "system", "content": "系统"}, {"role": "user", "content": "你好"}]
        result = engine.assemble(msgs, memory_text="记忆内容")
        assert len(result) == 3  # system + memory_injection + user
        assert "记忆内容" in result[1]["content"]

    def test_组装注入技能(self, engine):
        msgs = [{"role": "system", "content": "系统"}, {"role": "user", "content": "你好"}]
        result = engine.assemble(msgs, skill_hints="技能提示")
        assert "技能提示" in result[1]["content"]

    def test_空消息列表组装不崩溃(self, engine):
        result = engine.assemble([])
        assert result == []
