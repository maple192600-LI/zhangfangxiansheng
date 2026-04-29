#!/usr/bin/env python3
"""
check_canonical_schema.py · Layer-2 guard
=========================================
§C1 · fund_events 12 列基础表锁。

职责:
    - 在 backend/db/tables.py 中定位 `fund_events` ORM 类。
    - 抽取 Column(...) 声明的列名与顺序。
    - 验证 §C1 CANONICAL_12 以**契约序**连续出现（中间不得插入其它列）。
    - 允许的元数据列限于 ALLOWED_META（见下）；任何额外列 → exit 1。
    - 列缺失 / 改名 / 换位 / 非白名单额外列 → exit 1。

契约依据: §T2.1 DDL 显示 fund_events 合法列集 = CANONICAL_12 ∪ ALLOWED_META，
且 CANONICAL_12 必须**连续**（前后可挂 id / batch_id / parser_artifact_id / created_at / updated_at）。

用法:
    python tools/guards/check_canonical_schema.py
    python tools/guards/check_canonical_schema.py --target path/to/tables.py

宪法锚点: 00_governance/00_project_constitution.md §C1
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "backend" / "db" / "tables.py"

# §C1 · 12 列不可变（列序即列号）
CANONICAL_12: list[str] = [
    "business_date",
    "entity_code",
    "entity_name",
    "account_code",
    "account_name",
    "summary",
    "counterparty",
    "amount_in",
    "amount_out",
    "rolling_balance",
    "state",
    "source",
]

TABLE_NAME = "fund_events"

# §T2.1 允许的非 CANONICAL 元数据列（契约明列；其它名称一律视为漂移）
ALLOWED_META: frozenset[str] = frozenset({
    "id",
    "batch_id",
    "parser_artifact_id",
    "created_at",
    "updated_at",
})


def _is_column_call(node: ast.AST) -> bool:
    """识别 SQLAlchemy `Column(...)` 调用（含带模块前缀的 sa.Column）。"""
    if not isinstance(node, ast.Call):
        return False
    fn = node.func
    if isinstance(fn, ast.Name):
        return fn.id == "Column"
    if isinstance(fn, ast.Attribute):
        return fn.attr == "Column"
    return False


def _extract_tablename(class_body: list[ast.stmt]) -> str | None:
    for stmt in class_body:
        if isinstance(stmt, ast.Assign):
            for tgt in stmt.targets:
                if isinstance(tgt, ast.Name) and tgt.id == "__tablename__":
                    if isinstance(stmt.value, ast.Constant) and isinstance(stmt.value.value, str):
                        return stmt.value.value
    return None


def _columns_in_order(class_body: list[ast.stmt]) -> list[str]:
    """按声明顺序提取 `x = Column(...)` 的左值名。"""
    cols: list[str] = []
    for stmt in class_body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1:
            target = stmt.targets[0]
            if isinstance(target, ast.Name) and _is_column_call(stmt.value):
                cols.append(target.id)
    return cols


def find_fund_events_class(tree: ast.Module) -> ast.ClassDef | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if _extract_tablename(node.body) == TABLE_NAME:
                return node
    return None


def verify(target: Path) -> int:
    if not target.exists():
        print(f"[SKIP] 目标文件尚不存在: {target}", file=sys.stderr)
        print("       (fund_events 将在 P0-T2 迁移时落地；guard 暂不强制)", file=sys.stderr)
        return 0

    try:
        tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
    except SyntaxError as e:
        print(f"[FAIL] 无法解析 {target}: {e}", file=sys.stderr)
        return 1

    cls = find_fund_events_class(tree)
    if cls is None:
        print(f"[SKIP] {target} 中未定义 __tablename__='{TABLE_NAME}' 的类", file=sys.stderr)
        print("       (P0-T2 完成前正常；完成后若仍 SKIP 说明未按契约建表)", file=sys.stderr)
        return 0

    actual = _columns_in_order(cls.body)

    # 1) CANONICAL_12 必须以契约序作为连续子序列出现
    canonical_ok = _is_contiguous_in_order(actual, CANONICAL_12)
    # 2) 除 CANONICAL_12 外的其它列必须在 ALLOWED_META 白名单内
    canonical_set = set(CANONICAL_12)
    extras = [c for c in actual if c not in canonical_set]
    disallowed = [c for c in extras if c not in ALLOWED_META]

    if canonical_ok and not disallowed:
        print(
            f"[OK] fund_events 12 列按 §C1 契约序连续出现（+{len(extras)} 元数据列：{extras}）"
        )
        return 0

    # 漂移报告
    print("[FAIL] fund_events 列集合与 §C1 CANONICAL_12 不符", file=sys.stderr)
    print(f"  期望 · CANONICAL_12（{len(CANONICAL_12)} 列，必须连续按列序）:", file=sys.stderr)
    for i, name in enumerate(CANONICAL_12, 1):
        print(f"    {i:>2}. {name}", file=sys.stderr)
    print(f"  期望 · ALLOWED_META 白名单: {sorted(ALLOWED_META)}", file=sys.stderr)
    print(f"  实际（{len(actual)} 列，按声明顺序）:", file=sys.stderr)
    for i, name in enumerate(actual, 1):
        marker = "  ← CANONICAL" if name in canonical_set else (
            "  ← META 白名单" if name in ALLOWED_META else "  ← 非法额外列"
        )
        print(f"    {i:>2}. {name}{marker}", file=sys.stderr)

    if not canonical_ok:
        print("  原因: CANONICAL_12 未按契约序连续出现", file=sys.stderr)
    if disallowed:
        print(f"  原因: 非法额外列（既不在 CANONICAL_12，也不在 ALLOWED_META）: {disallowed}", file=sys.stderr)

    print("", file=sys.stderr)
    print("  修复: 对齐 backend/db/tables.py 中 fund_events 的列定义到 §C1 + §T2.1。", file=sys.stderr)
    print("        任何列集合变更必须走 §ChangeFlow（宪法）。", file=sys.stderr)
    return 1


def _is_contiguous_in_order(actual: list[str], expected: list[str]) -> bool:
    """检查 expected 是否作为**连续子序列**按序出现在 actual 中。"""
    if len(expected) == 0:
        return True
    if len(actual) < len(expected):
        return False
    for start in range(0, len(actual) - len(expected) + 1):
        if actual[start : start + len(expected)] == expected:
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="待扫描的 Python 文件（默认 backend/db/tables.py）")
    args = parser.parse_args()
    return verify(Path(args.target).resolve())


if __name__ == "__main__":
    sys.exit(main())
