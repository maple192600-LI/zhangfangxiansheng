#!/usr/bin/env python3
"""Guard: block known parallel implementation paths and newly versioned authority names."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN_TRACKED_PATH_PARTS = {
    "backend/agents_v2/",
    "backend/api/agent_v2.py",
    "frontend/src/api/agentV2.js",
}

AUTHORITY_DOCS = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "docs/README.md",
    "docs/00_governance/01_scope_and_order.md",
    "docs/00_governance/02_user_constraints.md",
    "docs/00_governance/03_tech_constraints.md",
    "docs/00_governance/04_coding_conventions.md",
    "docs/00_governance/05_testing_strategy.md",
    "docs/00_governance/08_anti_drift.md",
    "docs/00_governance/09_agent_capability.md",
    "docs/20_execution/12_bank_import_execution.md",
    "docs/20_execution/13_manual_flow_execution.md",
    "docs/20_execution/14_base_data_and_report_execution.md",
    "docs/20_execution/16_agent_system_execution.md",
    "docs/20_execution/17_skill_system_design.md",
]

FORBIDDEN_TERMS = [
    "Agent V2",
    "AgentV2",
    "agent_v2",
    "agents_v2",
    "skills_v2",
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
    tracked = git_ls_files()
    for path in tracked:
        for part in FORBIDDEN_TRACKED_PATH_PARTS:
            if part in path:
                problems.append(f"tracked parallel implementation path: {path}")

    for rel in AUTHORITY_DOCS:
        path = REPO_ROOT / rel
        if not path.exists():
            problems.append(f"authority doc missing: {rel}")
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for term in FORBIDDEN_TERMS:
            if term in text:
                problems.append(f"{rel}: contains forbidden legacy term `{term}`")

    if problems:
        print("[FAIL] 发现平行实现或权威文档版本化命名:", file=sys.stderr)
        for item in problems:
            print(f"  {item}", file=sys.stderr)
        return 1

    print("[OK] 未发现新增平行实现或权威文档版本化命名")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
