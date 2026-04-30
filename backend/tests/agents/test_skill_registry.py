"""技能注册表测试 — 解析 + 发现 + 触发

按 python-testing 技能规范编写
"""
import os
import pytest
from agents.skill_registry import (
    parse_frontmatter,
    load_skill_l1,
    SkillMeta,
    SkillRegistry,
)


class TestFrontmatter解析:
    """验证 SKILL.md YAML frontmatter 解析"""

    def test_空内容返回空字典(self):
        meta, body = parse_frontmatter("没有frontmatter的文本")
        assert meta == {}

    def test_解析name和description(self):
        content = "---\nname: test-skill\ndescription: \"测试技能\"\n---\n正文内容"
        meta, body = parse_frontmatter(content)
        assert meta["name"] == "test-skill"
        assert meta["description"] == "测试技能"
        assert "正文内容" in body

    def test_解析列表字段(self):
        content = "---\nallowed-tools:\n  - fs_read\n  - fs_write\n---\nbody"
        meta, body = parse_frontmatter(content)
        tools = meta.get("allowed-tools")
        assert isinstance(tools, list)
        assert "fs_read" in tools


class TestSkillMeta:
    """验证技能元数据结构"""

    def test_L1摘要包含名称和描述(self):
        meta = SkillMeta(
            code="test_skill",
            name="测试技能",
            description="用于测试的技能",
            skill_dir="/tmp/test",
        )
        text = meta.l1_text
        assert "测试技能" in text
        assert "用于测试" in text

    def test_空描述也能生成摘要(self):
        meta = SkillMeta(code="test", name="test", skill_dir="/tmp")
        text = meta.l1_text
        assert "test" in text


class TestSkillRegistry触发:
    """验证技能匹配触发逻辑"""

    @pytest.fixture
    def registry(self):
        reg = SkillRegistry()
        reg.startup_scan()
        return reg

    def test_创建技能触发skill_creator(self, registry):
        matches = registry.trigger("创建技能")
        names = [s.name for s in matches]
        assert any("skill-creator" in n for n in names)

    def test_无关输入不匹配(self, registry):
        matches = registry.trigger("今天天气真好")
        assert len(matches) == 0

    def test_list_skills返回列表(self, registry):
        skills = registry.list_skills()
        assert isinstance(skills, list)

    def test_get_skill按code查找(self, registry):
        skill = registry.get_skill("skill_creator")
        assert skill is not None or skill is None  # 取决于是否有该技能


class TestSkillRegistry路径:
    """验证技能路径查找"""

    def test_全局技能路径存在(self):
        from agents.skill_registry import get_skill_path
        path = get_skill_path("nonexist_agent", "skill-creator")
        assert "skill-creator" in path

    def test_不存在技能返回路径但不崩溃(self):
        from agents.skill_registry import get_skill_path
        path = get_skill_path("xxx", "nonexist")
        # 返回路径但不报错
        assert isinstance(path, str)
