"""Skill 加载与执行

从 manifest.yaml + run.py 加载 skill，执行并返回结果。
"""
import importlib.util
import json
import os
import time
from typing import Any, Optional

import yaml

from config import DATA_DIR


def get_skill_path(agent_code: str, skill_code: str) -> str:
    """获取 skill 目录路径"""
    # 先查 agent 专属目录
    agent_skill = os.path.join(DATA_DIR, "agents", agent_code, "skills", skill_code)
    if os.path.isdir(agent_skill):
        return agent_skill
    # 再查全局 system 目录
    system_skill = os.path.join(DATA_DIR, "agents", "system", "skills", skill_code)
    if os.path.isdir(system_skill):
        return system_skill
    return agent_skill


def load_manifest(skill_path: str) -> Optional[dict]:
    """加载 manifest.yaml"""
    manifest_file = os.path.join(skill_path, "manifest.yaml")
    if not os.path.isfile(manifest_file):
        return None
    with open(manifest_file, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_skill(skill_path: str, params: dict, timeout: int = 30) -> dict:
    """执行 skill 的 run.py

    Returns:
        {"ok": True, "result": ..., "duration_ms": ...} 或 {"ok": False, "error": ...}
    """
    run_file = os.path.join(skill_path, "run.py")
    if not os.path.isfile(run_file):
        return {"ok": False, "error": f"run.py 不存在: {skill_path}"}

    manifest = load_manifest(skill_path)
    if manifest and manifest.get("runtime", {}).get("timeout_ms"):
        timeout = manifest["runtime"]["timeout_ms"] // 1000

    started = time.time()
    try:
        # 动态加载 run.py 模块
        spec = importlib.util.spec_from_file_location("skill_run", run_file)
        mod = importlib.util.module_from_spec(spec)

        # 注入参数到模块
        mod.SKILL_PARAMS = params
        mod.SKILL_DIR = skill_path

        spec.loader.exec_module(mod)

        # 调用 run 函数
        if not hasattr(mod, "run"):
            return {"ok": False, "error": "run.py 缺少 run(params) 函数"}

        result = mod.run(params)

        duration = int((time.time() - started) * 1000)
        return {"ok": True, "result": result, "duration_ms": duration}

    except Exception as e:
        duration = int((time.time() - started) * 1000)
        return {"ok": False, "error": str(e), "duration_ms": duration}


def test_skill(skill_path: str, params: dict) -> dict:
    """运行 skill 测试

    检查 tests/ 目录是否有 expected.json，对比结果
    """
    result = run_skill(skill_path, params)

    tests_dir = os.path.join(skill_path, "tests")
    expected_file = os.path.join(tests_dir, "expected.json")

    if os.path.isfile(expected_file):
        with open(expected_file, "r", encoding="utf-8") as f:
            expected = json.load(f)
        result["expected"] = expected
        result["match"] = (result.get("result") == expected)

    return result
