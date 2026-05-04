"""技能注册表 — SKILL.md 规范 + 三级渐进式加载

设计参考 OpenClaw 三级加载：
  L1: frontmatter 元数据（始终在上下文中，~100 tokens）
  L2: SKILL.md body（触发时加载）
  L3: 完整目录 assets（按需加载）

兼容 Claude Code SKILL.md 规范 + 热更新（mtime）
"""
import os
import re
from dataclasses import dataclass, field
from typing import Optional

from config import AGENTS_ROOT


@dataclass
class SkillMeta:
    """技能索引条目"""
    code: str
    name: str = ""
    description: str = ""
    when_to_use: str = ""
    allowed_tools: list[str] = field(default_factory=list)
    arguments: dict = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    skill_dir: str = ""
    _body_loaded: bool = False
    _body: str = ""
    _l3_assets: Optional[dict] = None
    _mtime: float = 0.0

    @property
    def l1_text(self) -> str:
        parts = [f"- {self.name or self.code}"]
        if self.description:
            parts.append(f"  {self.description}")
        if self.when_to_use:
            parts.append(f"  触发: {self.when_to_use}")
        return "\n".join(parts)

    def load_l2(self) -> str:
        """L2: 加载完整 SKILL.md body"""
        if self._body_loaded:
            return self._body
        skill_md = os.path.join(self.skill_dir, "SKILL.md")
        if not os.path.isfile(skill_md):
            return ""
        with open(skill_md, "r", encoding="utf-8") as f:
            content = f.read()
        _, body = parse_frontmatter(content)
        self._body = body
        self._body_loaded = True
        return body

    def load_l3(self) -> dict:
        """L3: 加载完整目录 assets"""
        if self._l3_assets is not None:
            return self._l3_assets
        body = self.load_l2()
        assets = {}
        skill_path = self.skill_dir
        if os.path.isdir(skill_path):
            for root, dirs, files in os.walk(skill_path):
                for fname in files:
                    if fname == "SKILL.md":
                        continue
                    fpath = os.path.join(root, fname)
                    rel = os.path.relpath(fpath, skill_path).replace("\\", "/")
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            assets[rel] = f.read()
                    except Exception:
                        pass
        self._l3_assets = {"body": body, "assets": assets}
        return self._l3_assets


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
        return _load_legacy_manifest(skill_dir)

    with open(skill_md, "r", encoding="utf-8") as f:
        content = f.read()

    meta, body = parse_frontmatter(content)
    dir_name = os.path.basename(skill_dir)

    triggers = meta.get("triggers", [])
    if isinstance(triggers, str):
        triggers = [t.strip() for t in triggers.split(",")]

    return SkillMeta(
        code=meta.get("name", dir_name).replace("-", "_"),
        name=meta.get("name", dir_name),
        description=meta.get("description", ""),
        when_to_use=meta.get("when_to_use", ""),
        allowed_tools=meta.get("allowed-tools", []) if isinstance(meta.get("allowed-tools"), list) else [],
        arguments=meta.get("arguments", {}),
        triggers=triggers,
        skill_dir=skill_dir,
        _body_loaded=False,
        _body=body,
        _mtime=os.path.getmtime(skill_md),
    )


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


def load_skill_l2(skill: SkillMeta) -> str:
    """L2: 加载完整 SKILL.md body（兼容接口）"""
    return skill.load_l2()


def _extract_ngrams(text: str, n: int = 2) -> set[str]:
    """从文本中提取 n-gram"""
    cleaned = re.sub(r'[\s\W]+', '', text)
    if len(cleaned) < n:
        return {cleaned} if cleaned else set()
    return {cleaned[i:i + n] for i in range(len(cleaned) - n + 1)}


class SkillRegistry:
    """技能注册表 — 启动扫描 + 按需触发 + 热更新"""

    def __init__(self):
        self._skills: dict[str, SkillMeta] = {}
        self._loaded = False

    def startup_scan(self, agent_code: Optional[str] = None) -> None:
        """启动时扫描所有技能目录，构建 L1 索引"""
        self._skills.clear()

        system_dir = os.path.join(AGENTS_ROOT, "system", "skills")
        if os.path.isdir(system_dir):
            for name in os.listdir(system_dir):
                path = os.path.join(system_dir, name)
                if os.path.isdir(path):
                    meta = load_skill_l1(path)
                    if meta:
                        self._skills[meta.code] = meta

        if agent_code:
            agent_dir = os.path.join(AGENTS_ROOT, agent_code, "skills")
            if os.path.isdir(agent_dir):
                for name in os.listdir(agent_dir):
                    path = os.path.join(agent_dir, name)
                    if os.path.isdir(path):
                        meta = load_skill_l1(path)
                        if meta:
                            self._skills[meta.code] = meta

        self._loaded = True

    def hot_reload(self) -> list[str]:
        """热更新：检查 mtime 变化"""
        changed = []
        for code, skill in list(self._skills.items()):
            skill_md = os.path.join(skill.skill_dir, "SKILL.md")
            if not os.path.isfile(skill_md):
                del self._skills[code]
                changed.append(code)
                continue
            mtime = os.path.getmtime(skill_md)
            if mtime > skill._mtime:
                new_meta = load_skill_l1(skill.skill_dir)
                if new_meta:
                    self._skills[code] = new_meta
                changed.append(code)
        return changed

    def trigger(self, user_input: str) -> list[SkillMeta]:
        """根据用户输入匹配触发技能

        优先匹配 triggers 字段（精确 n-gram），回退到双向子串匹配。
        """
        if not self._loaded:
            return []

        matched = []
        text_lower = user_input.lower()

        for skill in self._skills.values():
            # 1. triggers 字段匹配（优先）
            if skill.triggers:
                user_ngrams = _extract_ngrams(text_lower, n=2)
                for trigger in skill.triggers:
                    trigger_ngrams = _extract_ngrams(trigger.lower(), n=2)
                    overlap = user_ngrams & trigger_ngrams
                    if len(overlap) >= max(1, len(trigger_ngrams) * 0.5):
                        matched.append(skill)
                        break
                else:
                    continue
                continue

            # 2. 回退：名称 + 描述匹配
            skill_text = f"{skill.name} {skill.description} {skill.when_to_use}".lower()

            if skill.name.lower() in text_lower:
                matched.append(skill)
                continue

            user_segs = set()
            for word in text_lower.split():
                if len(word) >= 2:
                    user_segs.add(word)
            chinese = re.sub(r"[a-z0-9\s]", "", text_lower)
            for n in (2, 3, 4):
                for i in range(len(chinese) - n + 1):
                    user_segs.add(chinese[i:i + n])

            if any(seg in skill_text for seg in user_segs if len(seg) >= 2):
                matched.append(skill)

        return matched

    def get_skill(self, code: str) -> Optional[SkillMeta]:
        return self._skills.get(code)

    def list_skills(self) -> list[SkillMeta]:
        return list(self._skills.values())

    def l1_summary_text(self) -> str:
        if not self._skills:
            return ""
        lines = ["以下是你可使用的技能（仅显示摘要，需要时请加载完整技能）："]
        for skill in self._skills.values():
            lines.append(skill.l1_text)
        return "\n".join(lines)


# --- 兼容旧 skill_loader 接口的顶层函数 ---

def get_skill_path(agent_code: str, skill_code: str) -> str:
    agent_skill = os.path.join(AGENTS_ROOT, agent_code, "skills", skill_code)
    if os.path.isdir(agent_skill):
        return agent_skill
    system_skill = os.path.join(AGENTS_ROOT, "system", "skills", skill_code)
    if os.path.isdir(system_skill):
        return system_skill
    return agent_skill


def load_manifest(skill_path: str) -> Optional[dict]:
    manifest_file = os.path.join(skill_path, "manifest.yaml")
    if not os.path.isfile(manifest_file):
        return None
    import yaml
    with open(manifest_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_skill(skill_path: str, params: dict, timeout: int = 30) -> dict:
    from agents.skill_executor import execute_skill_inline, get_skill_run_path
    run_file = get_skill_run_path(skill_path)
    if not run_file:
        return {"ok": False, "error": f"run.py 不存在: {skill_path}"}
    meta = load_skill_l1(skill_path)
    if not meta:
        meta = SkillMeta(code=os.path.basename(skill_path), skill_dir=skill_path)
    return execute_skill_inline(meta, params, params.get("_ctx", None))


def test_skill(skill_path: str, params: dict) -> dict:
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


skill_registry = SkillRegistry()
