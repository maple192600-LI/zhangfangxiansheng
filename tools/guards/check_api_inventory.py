#!/usr/bin/env python3
"""
check_api_inventory.py · Layer-2 guard
======================================
§C7 · API 端点总数上限 42。

职责:
    - 扫描 backend/api/**/*.py 的 FastAPI 路由装饰器。
    - 收集 (method, path) 唯一对，计数。
    - 总数 > 42 → exit 1。

用法:
    python tools/guards/check_api_inventory.py
    python tools/guards/check_api_inventory.py --target backend/api --limit 42
    python tools/guards/check_api_inventory.py --list   # 只打印清单

宪法锚点: 00_governance/00_project_constitution.md §C7
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "backend" / "api"

DEFAULT_LIMIT = 42

HTTP_METHODS: frozenset[str] = frozenset({
    "get", "post", "put", "delete", "patch", "head", "options",
})


def _decorator_info(dec: ast.expr) -> tuple[str, str] | None:
    """从装饰器 AST 中抽 (method, path)。

    识别:
        @router.get("/x")
        @app.post("/x", ...)
        @api_router.put("/x")
    不识别:
        @router.get  # 无调用
        @something_else(...)
    """
    if not isinstance(dec, ast.Call):
        return None
    fn = dec.func
    if not isinstance(fn, ast.Attribute):
        return None
    method = fn.attr.lower()
    if method not in HTTP_METHODS:
        return None
    if not dec.args:
        return None
    first = dec.args[0]
    if isinstance(first, ast.Constant) and isinstance(first.value, str):
        return (method.upper(), first.value)
    return None


def extract_routes(py_file: Path) -> list[tuple[str, str, int]]:
    """返回 [(METHOD, path, lineno), ...]。"""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError:
        return []
    routes: list[tuple[str, str, int]] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                info = _decorator_info(dec)
                if info:
                    method, path = info
                    routes.append((method, path, node.lineno))
    return routes


def scan_directory(target: Path) -> list[tuple[str, str, Path, int]]:
    """[(METHOD, path, file, line), ...] 全局去重后返回。"""
    out: list[tuple[str, str, Path, int]] = []
    seen: set[tuple[str, str]] = set()
    for py in sorted(target.rglob("*.py")):
        if py.name == "__init__.py":
            continue
        for method, path, line in extract_routes(py):
            key = (method, path)
            if key in seen:
                continue
            seen.add(key)
            out.append((method, path, py, line))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="API 目录（默认 backend/api）")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT, help=f"端点总数上限（默认 {DEFAULT_LIMIT}）")
    parser.add_argument("--list", action="store_true", help="只打印端点清单，不做阈值检查")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    if not target.exists():
        print(f"[SKIP] API 目录不存在: {target}", file=sys.stderr)
        return 0

    routes = scan_directory(target)
    count = len(routes)

    if args.list:
        for method, path, file, line in routes:
            rel = file.relative_to(REPO_ROOT) if file.is_absolute() else file
            print(f"  {method:<6} {path:<50}  {rel}:{line}")
        print(f"---\n  总计: {count} 端点")
        return 0

    if count > args.limit:
        print(f"[FAIL] API 端点 {count} > 上限 {args.limit}（§C7 冻结为 42）", file=sys.stderr)
        print("  超限端点列表:", file=sys.stderr)
        for i, (method, path, file, line) in enumerate(routes, 1):
            marker = "  " if i <= args.limit else "!!"
            rel = file.relative_to(REPO_ROOT) if file.is_absolute() else file
            print(f"  {marker} {i:>3}. {method:<6} {path:<50}  {rel}:{line}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  修复: 合并 / 删除多余端点，或走 §ChangeFlow 扩容 42 → 新数字并同步 23_api_contracts.md。", file=sys.stderr)
        return 1

    print(f"[OK] API 端点总数 {count} / {args.limit}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
