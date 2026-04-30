"""旧接口兼容层 — 所有函数已迁移到 skill_registry 和 skill_executor"""

from agents_v2.skill_registry import get_skill_path, load_manifest, run_skill, test_skill

__all__ = ["get_skill_path", "load_manifest", "run_skill", "test_skill"]
