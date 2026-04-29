#!/usr/bin/env python3
"""
check_placeholder_binding.py · Layer-2 guard
============================================
§C2 · 现金日记账月账模板 18 占位符锁。

职责:
    - 加载 Rule artifact JSON（文件或目录批扫）。
    - 校验 `placeholder_bindings.keys() ∪ loop.columns.keys()` 恰好等于 §C2 的 18 占位符集合。
    - 漏绑 / 多绑 / 错名 → exit 1。

用法:
    python tools/guards/check_placeholder_binding.py [target ...]
    # target 可以是 .json 文件或目录；省略则扫描默认 rules 目录。

宪法锚点: 00_governance/00_project_constitution.md §C2
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [
    REPO_ROOT / "backend" / "fund" / "artifacts" / "rules",
    REPO_ROOT / "artifacts" / "rules",
]

# §C2 · 18 占位符不可变
PLACEHOLDERS_18: frozenset[str] = frozenset({
    "报表标题",
    "开始期间",
    "结束期间",
    "板块",
    "核算方式",
    "开户行",
    "账户信息",
    "银行编号",
    "月",
    "日",
    "月初余额",
    "摘要",
    "收入",
    "支出",
    "余额",
    "本月收入小计",
    "本月支出小计",
    "月末余额",
})


def _collect_placeholders(rule: dict) -> set[str]:
    keys: set[str] = set()
    bindings = rule.get("placeholder_bindings") or {}
    if isinstance(bindings, dict):
        keys.update(bindings.keys())
    loop = rule.get("loop") or {}
    cols = loop.get("columns") or {} if isinstance(loop, dict) else {}
    if isinstance(cols, dict):
        keys.update(cols.keys())
    return keys


def verify_one(path: Path) -> tuple[bool, list[str]]:
    """(passed, messages). messages 非空表示问题描述。"""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        return False, [f"无法解析 JSON: {e}"]

    # 支持整文件就是 rule，或包含 "rule" 字段
    rule = data.get("rule") if isinstance(data, dict) and "rule" in data else data
    if not isinstance(rule, dict):
        return False, ["rule 根对象必须是 JSON object"]

    actual = _collect_placeholders(rule)
    missing = PLACEHOLDERS_18 - actual
    extra = actual - PLACEHOLDERS_18

    if not missing and not extra:
        return True, []

    msgs: list[str] = []
    msgs.append(f"占位符数量: 期望 {len(PLACEHOLDERS_18)}，实际 {len(actual)}")
    if missing:
        msgs.append(f"缺失（未绑定）: {sorted(missing)}")
    if extra:
        msgs.append(f"多余（非 §C2 清单）: {sorted(extra)}")
    return False, msgs


def iter_rule_files(targets: list[Path]) -> list[Path]:
    out: list[Path] = []
    for t in targets:
        if not t.exists():
            continue
        if t.is_file() and t.suffix == ".json":
            out.append(t)
        elif t.is_dir():
            out.extend(sorted(t.rglob("*.json")))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", help="Rule JSON 文件或目录；省略则扫描默认 rules 目录")
    args = parser.parse_args()

    if args.targets:
        targets = [Path(t).resolve() for t in args.targets]
    else:
        targets = [t for t in DEFAULT_TARGETS if t.exists()]

    files = iter_rule_files(targets)

    if not files:
        print("[SKIP] 未找到 Rule artifact JSON（P1-T3/T4 上线前正常）")
        return 0

    failed: list[tuple[Path, list[str]]] = []
    for f in files:
        passed, msgs = verify_one(f)
        if not passed:
            failed.append((f, msgs))

    if failed:
        print(f"[FAIL] 占位符绑定校验未通过（{len(failed)}/{len(files)} 个 Rule）", file=sys.stderr)
        for path, msgs in failed:
            print(f"  {path}", file=sys.stderr)
            for m in msgs:
                print(f"    - {m}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  修复: bindings + loop.columns 必须恰好覆盖 §C2 的 18 个占位符，一个不多一个不少。", file=sys.stderr)
        print("        占位符变更必须走 §ChangeFlow。", file=sys.stderr)
        return 1

    print(f"[OK] 占位符绑定校验通过（{len(files)} 个 Rule 各自覆盖 18/18）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
