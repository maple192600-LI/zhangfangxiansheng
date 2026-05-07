#!/usr/bin/env python3
"""Guard: block tracked runtime data, dependencies, logs, and product/ contamination."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_TRACKED_PATTERNS = [
    re.compile(r"(^|/)node_modules/"),
    re.compile(r"(^|/)\.venv/"),
    re.compile(r"(^|/)venv/"),
    re.compile(r"(^|/)runtime/"),
    re.compile(r"(^|/)downloads?/"),
    re.compile(r"\.log$", re.I),
    re.compile(r"\.db(-wal|-shm)?$", re.I),
    re.compile(r"^backend/data/uploads/"),
    re.compile(r"^backend/data/template_uploads/"),
    re.compile(r"^backend/data/generated_reports/"),
]

PRODUCT_FORBIDDEN = [
    re.compile(r"^product/.*\.(md|xlsx|xls|csv|json|log|db)$", re.I),
    re.compile(r"^product/(docs|fixtures|runtime|samples|tests?)/", re.I),
]


def git_ls_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return []
    return [line.strip().replace("\\", "/") for line in result.stdout.splitlines() if line.strip()]


def main() -> int:
    problems: list[str] = []
    for path in git_ls_files():
        for pattern in FORBIDDEN_TRACKED_PATTERNS:
            if pattern.search(path):
                problems.append(f"tracked runtime/dependency artifact: {path}")
                break
        for pattern in PRODUCT_FORBIDDEN:
            if pattern.search(path):
                problems.append(f"product/ contains non-product artifact: {path}")
                break

    if problems:
        print("[FAIL] 仓库跟踪了运行时/依赖/日志/临时产物:", file=sys.stderr)
        for item in problems[:100]:
            print(f"  {item}", file=sys.stderr)
        if len(problems) > 100:
            print(f"  ... 还有 {len(problems) - 100} 项", file=sys.stderr)
        print("  修复: 从 git 跟踪中移除这些产物，并确保 .gitignore 覆盖。", file=sys.stderr)
        return 1

    print("[OK] 未发现被跟踪的运行时/依赖/日志/临时产物")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
