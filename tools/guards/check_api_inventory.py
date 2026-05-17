#!/usr/bin/env python3
"""
check_api_inventory.py · Layer-2 guard
======================================
API inventory consistency guard.

职责:
    - 扫描 backend/api/**/*.py 的 FastAPI 路由装饰器。
    - 解析每个文件的 APIRouter prefix。
    - 解析 main.py 的 include_router prefix。
    - 拼接 effective path = include_prefix + router_prefix + decorator_path。
    - 收集 (method, effective_path) 唯一对，计数。
    - 检测重复 effective path → exit 1。

用法:
    python tools/guards/check_api_inventory.py              # 检查重复路由
    python tools/guards/check_api_inventory.py --list       # 打印清单
    python tools/guards/check_api_inventory.py --target <dir>
    python tools/guards/check_api_inventory.py --allow-duplicates  # 仅诊断
"""
from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = REPO_ROOT / "backend" / "api"
DEFAULT_MAIN = REPO_ROOT / "backend" / "main.py"

HTTP_METHODS: frozenset[str] = frozenset({
    "get", "post", "put", "delete", "patch", "head", "options",
})


def _normalize_path(*parts: str) -> str:
    """拼接路径段并规范化斜杠。"""
    combined = "/".join(p.strip("/") for p in parts if p)
    return "/" + combined if not combined.startswith("/") else combined


def _decorator_info(dec: ast.expr) -> tuple[str, str] | None:
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


def extract_router_prefix(py_file: Path) -> str:
    """从文件 AST 中提取 router = APIRouter(prefix="...") 的 prefix。"""
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except SyntaxError:
        return ""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not (isinstance(target, ast.Name) and target.id == "router"):
                continue
            if not isinstance(node.value, ast.Call):
                continue
            if not (isinstance(node.value.func, ast.Name) and node.value.func.id == "APIRouter"):
                continue
            for kw in node.value.keywords:
                if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                    return kw.value.value
    return ""


def parse_main_router_mapping(main_py: Path) -> dict[str, str]:
    """解析 main.py 中 include_router 的 module→prefix 映射。

    返回 {module_name: include_prefix}，例如 {"manual_flow": "/api"}。
    """
    if not main_py.exists():
        return {}
    try:
        content = main_py.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return {}

    # 从 import 行提取 module→local_var 映射
    # from api.xxx import router as xxx_router
    import_map: dict[str, str] = {}
    for m in re.finditer(
        r"from\s+api\.(\w+)\s+import\s+router\s+as\s+(\w+)", content
    ):
        import_map[m.group(2)] = m.group(1)

    # 从 include_router 行提取 local_var→prefix 映射
    prefix_map: dict[str, str] = {}
    for m in re.finditer(
        r"app\.include_router\((\w+)(?:\s*,\s*prefix\s*=\s*[\"']([^\"']*)[\"'])?\s*\)",
        content,
    ):
        var = m.group(1)
        prefix = m.group(2) or ""
        prefix_map[var] = prefix

    # 组合：module_name → include_prefix
    result: dict[str, str] = {}
    for var, module in import_map.items():
        if var in prefix_map:
            result[module] = prefix_map[var]
    return result


def scan_directory(
    target: Path,
    main_py: Path | None = None,
) -> list[tuple[str, str, str, Path, int]]:
    """扫描 API 目录，返回 [(METHOD, local_path, effective_path, file, line), ...]。"""
    # 解析 main.py 的 include prefix 映射
    module_prefix: dict[str, str] = {}
    if main_py and main_py.exists():
        module_prefix = parse_main_router_mapping(main_py)

    out: list[tuple[str, str, str, Path, int]] = []
    for py in sorted(target.rglob("*.py")):
        if py.name == "__init__.py":
            continue

        # 路由模块名（文件名去掉 .py）
        module_name = py.stem
        # include_router prefix
        include_prefix = module_prefix.get(module_name, "")
        # APIRouter prefix
        router_prefix = extract_router_prefix(py)

        for method, path, line in extract_routes(py):
            effective = _normalize_path(include_prefix, router_prefix, path)
            out.append((method, path, effective, py, line))

    return out


def find_duplicates(
    routes: list[tuple[str, str, str, Path, int]],
) -> list[list[tuple[str, str, str, Path, int]]]:
    """按 effective path 分组，返回重复组。"""
    from collections import defaultdict
    groups: dict[tuple[str, str], list[tuple[str, str, str, Path, int]]] = defaultdict(list)
    for entry in routes:
        groups[(entry[0], entry[2])].append(entry)
    return [g for g in groups.values() if len(g) >= 2]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--target", default=str(DEFAULT_TARGET), help="API 目录（默认 backend/api）")
    parser.add_argument("--main", default=str(DEFAULT_MAIN), help="main.py 路径（默认 backend/main.py）")
    parser.add_argument("--allow-duplicates", action="store_true", help="允许重复路由（仅诊断用）")
    parser.add_argument("--limit", type=int, default=None, help="兼容参数，不再用于默认失败条件")
    parser.add_argument("--list", action="store_true", help="只打印端点清单，不做检查")
    args = parser.parse_args()

    target = Path(args.target).resolve()
    main_py = Path(args.main).resolve()
    if not target.exists():
        print(f"[SKIP] API 目录不存在: {target}", file=sys.stderr)
        return 0

    routes = scan_directory(target, main_py=main_py)

    # 按 effective path 去重
    seen: set[tuple[str, str]] = set()
    unique: list[tuple[str, str, str, Path, int]] = []
    for entry in routes:
        key = (entry[0], entry[2])
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    count = len(unique)

    if args.list:
        for method, _, effective, file, line in unique:
            rel = file.relative_to(REPO_ROOT) if file.is_absolute() else file
            print(f"  {method:<6} {effective:<55}  {rel}:{line}")
        print(f"---\n  总计: {count} 端点")
        return 0

    dup_groups = find_duplicates(routes)
    dup_count = sum(len(g) for g in dup_groups)

    if dup_count > 0 and not args.allow_duplicates:
        print(f"[FAIL] 发现重复 API route identity（{dup_count} 个重复条目）:", file=sys.stderr)
        for group in dup_groups:
            method, _, effective = group[0][0], group[0][1], group[0][2]
            print(f"  {method} {effective}:", file=sys.stderr)
            for _, _, _, file, line in group:
                rel = file.relative_to(REPO_ROOT) if file.is_absolute() else file
                print(f"    - {rel}:{line}", file=sys.stderr)
        return 1

    print(f"[OK] API inventory: {count} endpoints, {dup_count} duplicate route identities")
    return 0


if __name__ == "__main__":
    sys.exit(main())
