#!/usr/bin/env python3
"""Guard: deterministic runtime paths must not call LLM providers."""
from __future__ import annotations

import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

TARGETS = [
    REPO_ROOT / "backend" / "core" / "artifact_runtime.py",
    REPO_ROOT / "backend" / "fund",
    REPO_ROOT / "backend" / "services" / "report_service.py",
]

FORBIDDEN_IMPORTS = {
    "openai",
    "anthropic",
    "httpx",
    "requests",
    "core.ai_call",
    "core.ai_parse_utils",
    "agents.provider",
}

FORBIDDEN_NAMES = {
    "chat",
    "stream_chat",
    "call_agent_for_mapping",
}


def iter_files() -> list[Path]:
    out: list[Path] = []
    for target in TARGETS:
        if target.is_file():
            out.append(target)
        elif target.is_dir():
            out.extend(sorted(target.rglob("*.py")))
    return out


def scan(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [f"{path}:{exc.lineno}: syntax error: {exc}"]

    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".")[0]
                if alias.name in FORBIDDEN_IMPORTS or root in FORBIDDEN_IMPORTS:
                    problems.append(f"{path}:{node.lineno}: forbidden runtime import `{alias.name}`")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            root = module.split(".")[0]
            if module in FORBIDDEN_IMPORTS or root in FORBIDDEN_IMPORTS:
                problems.append(f"{path}:{node.lineno}: forbidden runtime import `from {module}`")
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_NAMES:
                problems.append(f"{path}:{node.lineno}: forbidden runtime call `{fn.id}(...)`")
            elif isinstance(fn, ast.Attribute) and fn.attr in FORBIDDEN_NAMES:
                problems.append(f"{path}:{node.lineno}: forbidden runtime call `.{fn.attr}(...)`")
    return problems


def main() -> int:
    files = iter_files()
    problems: list[str] = []
    for path in files:
        problems.extend(scan(path))

    if problems:
        print("[FAIL] 确定性执行路径存在 LLM/网络调用风险:", file=sys.stderr)
        for item in problems:
            rel = item.replace(str(REPO_ROOT) + "\\", "").replace(str(REPO_ROOT) + "/", "")
            print(f"  {rel}", file=sys.stderr)
        return 1

    print(f"[OK] 确定性执行路径未发现 LLM 调用（{len(files)} 个文件）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
