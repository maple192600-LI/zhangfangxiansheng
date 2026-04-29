#!/usr/bin/env python3
"""
check_contract_hash.py · Layer-2 guard
======================================
§C1-C9 宪法 SHA256 锁。

职责:
    - 计算 docs/00_governance/00_project_constitution.md 的 SHA256。
    - 与 contracts.lock 中存档的哈希比较。
    - 任何差异 → exit 1（宪法被改动，需走 §ChangeFlow）。

用法:
    python tools/guards/check_contract_hash.py              # 校验
    python tools/guards/check_contract_hash.py --update     # 重算并写回 contracts.lock
    python tools/guards/check_contract_hash.py --target <path> --lock <path>

宪法锚点: 00_governance/00_project_constitution.md §ChangeFlow

违反规约 = CRITICAL（违反 §ChangeFlow）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONSTITUTION = REPO_ROOT / "docs" / "00_governance" / "00_project_constitution.md"
DEFAULT_LOCK = REPO_ROOT / "contracts.lock"

# 目前锁定的契约文件清单。后续若追加其它 FROZEN 文件（例如 20_database_schema.md），
# 通过 §ChangeFlow 补入此清单并 `--update`。
LOCKED_FILES = [
    "docs/00_governance/00_project_constitution.md",
]


def sha256_of(path: Path) -> str:
    """以字节流计算 SHA256。换行与编码差异不做标准化：字面内容即契约。"""
    h = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_lock_payload(repo_root: Path, files: list[str]) -> dict:
    entries: dict[str, str] = {}
    for rel in files:
        target = repo_root / rel
        if not target.exists():
            raise FileNotFoundError(f"契约文件不存在: {target}")
        entries[rel] = sha256_of(target)
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "algorithm": "sha256",
        "files": entries,
    }


def write_lock(lock_path: Path, payload: dict) -> None:
    lock_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_lock(lock_path: Path) -> dict:
    return json.loads(lock_path.read_text(encoding="utf-8"))


def verify(repo_root: Path, lock_path: Path, files: list[str]) -> int:
    """返回 0 表示全部匹配，1 表示有漂移。"""
    if not lock_path.exists():
        print(f"[FAIL] contracts.lock 不存在: {lock_path}", file=sys.stderr)
        print("       首次使用请运行: python tools/guards/check_contract_hash.py --update", file=sys.stderr)
        return 1

    lock = load_lock(lock_path)
    recorded: dict[str, str] = lock.get("files", {})

    drift: list[tuple[str, str, str]] = []  # (rel, expected, actual)
    missing: list[str] = []

    for rel in files:
        target = repo_root / rel
        if not target.exists():
            missing.append(rel)
            continue
        actual = sha256_of(target)
        expected = recorded.get(rel)
        if expected is None:
            drift.append((rel, "<未登记>", actual))
        elif expected != actual:
            drift.append((rel, expected, actual))

    if missing:
        for rel in missing:
            print(f"[FAIL] 契约文件缺失: {rel}", file=sys.stderr)
        return 1

    if drift:
        print("[FAIL] 契约文件 SHA256 漂移（疑似未经 §ChangeFlow 修改）:", file=sys.stderr)
        for rel, exp, act in drift:
            print(f"  - {rel}", file=sys.stderr)
            print(f"      expected: {exp}", file=sys.stderr)
            print(f"      actual:   {act}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  修复步骤:", file=sys.stderr)
        print("    1. 确认修改是否获得用户书面同意（§ChangeFlow 第 1 步）", file=sys.stderr)
        print("    2. 若同意 → python tools/guards/check_contract_hash.py --update", file=sys.stderr)
        print("    3. 若未同意 → git checkout -- docs/00_governance/00_project_constitution.md", file=sys.stderr)
        return 1

    print(f"[OK] contracts.lock 校验通过（{len(files)} 个契约文件）")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo-root", default=str(REPO_ROOT), help="仓库根目录")
    parser.add_argument("--lock", default=None, help="contracts.lock 路径（默认 <repo-root>/contracts.lock）")
    parser.add_argument("--update", action="store_true", help="重算并写回 lock（通常只在 §ChangeFlow 结尾执行）")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    lock_path = Path(args.lock).resolve() if args.lock else (repo_root / "contracts.lock")

    if args.update:
        payload = build_lock_payload(repo_root, LOCKED_FILES)
        write_lock(lock_path, payload)
        print(f"[OK] contracts.lock 已重算 → {lock_path}")
        for rel, digest in payload["files"].items():
            print(f"     {rel}: {digest}")
        return 0

    return verify(repo_root, lock_path, LOCKED_FILES)


if __name__ == "__main__":
    sys.exit(main())
