"""技能注册表 — SKILL.md 规范 + 三级渐进式加载

设计参考 OpenClaw 三级加载：
  L1: frontmatter 元数据（始终在上下文中，~100 tokens）
  L2: SKILL.md body（触发时加载）
  L3: scripts / references（按需加载）

兼容 Claude Code SKILL.md 规范：
  YAML frontmatter (name, description, when_to_use, allowed-tools, arguments)
  + Markdown body (工作流程、规则)
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from config import DATA_DIR


@dataclass
class SkillMeta:
    """L1: 技能元数据（轻量）"""
    code: str
    name: str = ""
    description: str = ""
    when_to_use: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    arguments: dict = field(default_factory=dict)
    skill_dir: str = ""
    _body_loaded: bool = False
    _body: str = ""

    @property
    def l1_text(self) -> str:
        """L1 摘要文本（注入上下文用）"""
        parts = [f"- {self.name or self.code}"]
        if self.description:
            parts.append(f"  {self.description}")
        if self.when_to_use:
            parts.append(f"  触发: {self.when_to_use}")
        return "\n".join(parts)


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """解析 YAML frontmatter，返回 (metadata_dict, body_text)"""
    import yaml as _yaml
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n?(.*)", content, re.DOTALL)
    if not match:
        return {}, content

    yaml_text = match.group(1)
    body = match.group(2).strip()

    try:
        meta = _yaml.safe_load(yaml_text) or {}
    except Exception:
        meta = {}

    if not isinstance(meta, dict):
        meta = {}
    return meta, body


def load_skill_l1(skill_dir: str) -> Optional[SkillMeta]:
    """加载技能的 L1 元数据"""
    skill_md = os.path.join(skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        # 兼容旧 manifest.yaml 格式
        return _load_legacy_manifest(skill_dir)

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = parse_frontmatter(content)

    dir_name = os.path.basename(skill_dir)
    return SkillMeta(
        code=meta.get("name", dir_name).replace("-", "_"),
        name=meta.get("name", dir_name),
        description=meta.get("description", ""),
        when_to_use=meta.get("when_to_use", ""),
        allowed_tools=meta.get("allowed-tools", []) if isinstance(meta.get("allowed-tools"), list) else [],
        arguments=meta.get("arguments", {}),
        skill_dir=skill_dir,
        _body_loaded=False,
        _body=body,
    )


def load_skill_l2(skill: SkillMeta) -> str:
    """加载技能的 L2 body（SKILL.md 正文）"""
    if skill._body_loaded:
        return skill._body

    skill_md = os.path.join(skill.skill_dir, "SKILL.md")
    if not os.path.isfile(skill_md):
        return ""

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    _, body = parse_frontmatter(content)
    skill._body = body
    skill._body_loaded = True
    return body


def _load_legacy_manifest(skill_dir: str) -> Optional[SkillMeta]:
    """兼容旧的 manifest.yaml 格式"""
    import yaml
    manifest_file = os.path.join(skill_dir, "manifest.yaml")
    if not os.path.isfile(manifest_file):
        return None

    with open(manifest_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    dir_name = os.path.basename(skill_dir)
    return SkillMeta(
        code=data.get("code", dir_name),
        name=data.get("display_name", data.get("name", dir_name)),
        description=data.get("description", ""),
        when_to_use=data.get("when_to_use", ""),
        allowed_tools=data.get("allowed_tools", []),
        arguments=data.get("arguments", {}),
        skill_dir=skill_dir,
    )


class SkillRegistry:
    """技能注册表 — 启动扫描 + 按需触发"""

    def __init__(self):
        self._skills: dict[str, SkillMeta] = {}
        self._loaded = False

    def startup_scan(self, agent_code: Optional[str] = None) -> None:
        """启动时扫描所有技能目录，构建 L1 索引"""
        self._skills.clear()

        # 1. 全局系统技能
        system_dir = os.path.join(DATA_DIR, "agents", "system", "skills")
        if os.path.isdir(system_dir):
            for name in os.listdir(system_dir):
                path = os.path.join(system_dir, name)
                if os.path.isdir(path):
                    meta = load_skill_l1(path)
                    if meta:
                        self._skills[meta.code] = meta

        # 2. Agent 专属技能
        if agent_code:
            agent_dir = os.path.join(DATA_DIR, "agents", agent_code, "skills")
            if os.path.isdir(agent_dir):
                for name in os.listdir(agent_dir):
                    path = os.path.join(agent_dir, name)
                    if os.path.isdir(path):
                        meta = load_skill_l1(path)
                        if meta:
                            self._skills[meta.code] = meta

        self._loaded = True

    def trigger(self, user_input: str) -> list[SkillMeta]:
        """根据用户输入匹配触发技能

        使用双向子串匹配：
        1. 检查技能名称是否出现在用户输入中
        2. 检查用户输入中的词段是否出现在技能描述中
        """
        if not self._loaded:
            return []

        import re as _re
        matched = []
        text_lower = user_input.lower()

        for skill in self._skills.values():
            skill_text = f"{skill.name} {skill.description} {skill.when_to_use}".lower()

            # 1. 技能名称是否在用户输入中
            if skill.name.lower() in text_lower:
                matched.append(skill)
                continue

            # 2. 从用户输入提取片段（中文按2-4字切分，英文按空格分词）
            user_segs = set()
            # 英文词
            for word in text_lower.split():
                if len(word) >= 2:
                    user_segs.add(word)
            # 中文 2-gram, 3-gram, 4-gram
            chinese = _re.sub(r"[a-z0-9\s]", "", text_lower)
            for n in (2, 3, 4):
                for i in range(len(chinese) - n + 1):
                    user_segs.add(chinese[i:i + n])

            # 3. 检查用户输入片段是否出现在技能描述中
            hit = any(seg in skill_text for seg in user_segs if len(seg) >= 2)
            if hit:
                matched.append(skill)

        return matched

    def get_skill(self, code: str) -> Optional[SkillMeta]:
        """按 code 获取技能"""
        return self._skills.get(code)

    def list_skills(self) -> list[SkillMeta]:
        """列出所有已注册技能"""
        return list(self._skills.values())

    def l1_summary_text(self) -> str:
        """生成所有技能的 L1 摘要文本（注入 system prompt）"""
        if not self._skills:
            return ""
        lines = ["以下是你可使用的技能（仅显示摘要，需要时请加载完整技能）："]
        for skill in self._skills.values():
            lines.append(skill.l1_text)
        return "\n".join(lines)


# --- 兼容旧 skill_loader 接口的顶层函数 ---

def get_skill_path(agent_code: str, skill_code: str) -> str:
    """获取 skill 目录路径（替代 skill_loader.get_skill_path）"""
    agent_skill = os.path.join(DATA_DIR, "agents", agent_code, "skills", skill_code)
    if os.path.isdir(agent_skill):
        return agent_skill
    system_skill = os.path.join(DATA_DIR, "agents", "system", "skills", skill_code)
    if os.path.isdir(system_skill):
        return system_skill
    return agent_skill


def load_manifest(skill_path: str) -> Optional[dict]:
    """加载 manifest.yaml（替代 skill_loader.load_manifest）"""
    manifest_file = os.path.join(skill_path, "manifest.yaml")
    if not os.path.isfile(manifest_file):
        return None
    import yaml
    with open(manifest_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_skill(skill_path: str, params: dict, timeout: int = 30) -> dict:
    """执行 skill 的 run.py（替代 skill_loader.run_skill）"""
    from agents_v2.skill_executor import execute_skill_inline, get_skill_run_path
    run_file = get_skill_run_path(skill_path)
    if not run_file:
        return {"ok": False, "error": f"run.py 不存在: {skill_path}"}

    meta = load_skill_l1(skill_path)
    if not meta:
        meta = SkillMeta(code=os.path.basename(skill_path), skill_dir=skill_path)

    return execute_skill_inline(meta, params, params.get("_ctx", None))


def test_skill(skill_path: str, params: dict) -> dict:
    """运行 skill 测试（替代 skill_loader.test_skill）"""
    import json
    result = run_skill(skill_path, params)

    tests_dir = os.path.join(skill_path, "tests")
    expected_file = os.path.join(tests_dir, "expected.json")

    if os.path.isfile(expected_file):
        with open(expected_file, "r", encoding="utf-8") as f:
            expected = json.load(f)
        result["expected"] = expected
        result["match"] = (result.get("result") == expected)

    return result


# 全局单例
skill_registry = SkillRegistry()
