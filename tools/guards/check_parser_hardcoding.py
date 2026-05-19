"""Parser hardcoding guard — reject parsers with hardcoded account/entity defaults.

Scans:
  - backend/fund/artifacts/parsers/ (if exists)
Checks:
  - DEFAULT_ACCOUNT_CODE = "..." (non-empty)
  - DEFAULT_ENTITY_CODE = "..." (non-empty)
  - Hardcoded account_code / entity_code as default return values
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
PARSER_DIR = REPO_ROOT / "backend" / "fund" / "artifacts" / "parsers"


def _resolve_root() -> Path:
    import argparse
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--repo-root", type=str, default=None)
    args, _ = parser.parse_known_args()
    if args.repo_root:
        return Path(args.repo_root)
    return REPO_ROOT


_BLOCKED_PATTERNS = [
    (re.compile(r'DEFAULT_ACCOUNT_CODE\s*=\s*["\'][^"\']+["\']', re.I),
     "DEFAULT_ACCOUNT_CODE 非空默认值"),
    (re.compile(r'DEFAULT_ENTITY_CODE\s*=\s*["\'][^"\']+["\']', re.I),
     "DEFAULT_ENTITY_CODE 非空默认值"),
    (re.compile(r'default_account_code\s*=\s*["\'][A-Z]\d{3}["\']', re.I),
     "硬编码具体 account_code"),
    (re.compile(r'default_entity_code\s*=\s*["\'][A-Z]\d{3}["\']', re.I),
     "硬编码具体 entity_code"),
]

_EXEMPT_SUFFIXES = ("_test.py", "_tests.py", "conftest.py")


def check_parser_files() -> list[tuple[str, str]]:
    """Return list of (file, reason) for violations."""
    violations = []

    root = _resolve_root()
    parser_dir = root / "backend" / "fund" / "artifacts" / "parsers"

    if not parser_dir.is_dir():
        return violations

    for dirpath, _dirs, files in os.walk(parser_dir):
        for fname in files:
            if not fname.endswith(".py"):
                continue
            if any(fname.endswith(s) for s in _EXEMPT_SUFFIXES):
                continue

            fpath = Path(dirpath) / fname
            content = fpath.read_text(encoding="utf-8", errors="replace")

            for pattern, reason in _BLOCKED_PATTERNS:
                m = pattern.search(content)
                if m:
                    rel = fpath.relative_to(root)
                    violations.append((str(rel), f"{reason}: {m.group()[:60]}"))

    return violations


def main():
    violations = check_parser_files()
    if violations:
        print(f"[FAIL] 发现 {len(violations)} 处 parser 硬编码违规:")
        for fpath, reason in violations:
            print(f"  {fpath}: {reason}")
        sys.exit(1)

    print("[OK] parser hardcoding guard 通过，无硬编码账户/单位")
    sys.exit(0)


if __name__ == "__main__":
    main()
