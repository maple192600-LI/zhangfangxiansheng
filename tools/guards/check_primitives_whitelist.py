#!/usr/bin/env python3
"""
check_primitives_whitelist.py · Layer-2 guard
=============================================
§C5 · 基元库白名单 AST 扫描。

职责:
    - 对 Parser/Rule artifact 源码做 AST 扫描。
    - 禁止：非白名单 import、open/eval/exec/compile/__import__、
            __class__/__subclasses__/__globals__ 等 dunder 反射。
    - 违反任一条 → exit 1。

用法:
    python tools/guards/check_primitives_whitelist.py [target ...]
    # target 可以是文件或目录；省略则扫描默认 artifact 目录。

宪法锚点: 00_governance/00_project_constitution.md §C5 + §P8
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = [
    REPO_ROOT / "backend" / "fund" / "artifacts",
    REPO_ROOT / "artifacts",
]

# §P8.1 · 允许的 import 根
ALLOWED_MODULE_PREFIXES: tuple[str, ...] = (
    "fund.primitives.",
)
ALLOWED_STDLIB: frozenset[str] = frozenset({
    "datetime",
    "decimal",
    "typing",
    "re",
})

# §P8.2 · 显式禁用调用名
FORBIDDEN_CALLS: frozenset[str] = frozenset({
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "vars",
    "getattr",   # 可被用于反射绕过，artifact 场景不需要
    "setattr",
    "delattr",
})

# §P8.3 · 禁止的 dunder 属性访问
FORBIDDEN_ATTRS: frozenset[str] = frozenset({
    "__class__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__bases__",
    "__mro__",
    "__dict__",
    "__code__",
})


class Violation:
    __slots__ = ("file", "line", "col", "kind", "detail")

    def __init__(self, file: Path, line: int, col: int, kind: str, detail: str) -> None:
        self.file = file
        self.line = line
        self.col = col
        self.kind = kind
        self.detail = detail

    def render(self) -> str:
        return f"{self.file}:{self.line}:{self.col}  [{self.kind}]  {self.detail}"


def _is_allowed_module(name: str) -> bool:
    if name in ALLOWED_STDLIB:
        return True
    for prefix in ALLOWED_MODULE_PREFIXES:
        if name == prefix.rstrip(".") or name.startswith(prefix):
            return True
    return False


def scan_source(path: Path, source: str) -> list[Violation]:
    vios: list[Violation] = []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as e:
        vios.append(Violation(path, e.lineno or 0, e.offset or 0, "syntax", str(e)))
        return vios

    for node in ast.walk(tree):
        # import x, y
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_allowed_module(alias.name.split(".")[0] if alias.name in ALLOWED_STDLIB else alias.name):
                    vios.append(Violation(path, node.lineno, node.col_offset, "import",
                                          f"禁止 `import {alias.name}`（不在基元库 / stdlib 白名单）"))

        # from x import y
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level and node.level > 0:
                vios.append(Violation(path, node.lineno, node.col_offset, "import",
                                      f"禁止相对导入（level={node.level}）"))
                continue
            if not _is_allowed_module(module):
                vios.append(Violation(path, node.lineno, node.col_offset, "import",
                                      f"禁止 `from {module} import ...`（不在基元库 / stdlib 白名单）"))

        # 禁用调用
        elif isinstance(node, ast.Call):
            fn = node.func
            name: str | None = None
            if isinstance(fn, ast.Name):
                name = fn.id
            elif isinstance(fn, ast.Attribute):
                # 允许属性调用（如 Decimal.from_float），但阻断 x.__class__ 这种路径
                if fn.attr in FORBIDDEN_ATTRS:
                    vios.append(Violation(path, node.lineno, node.col_offset, "attr-call",
                                          f"禁止调用 dunder `.{fn.attr}(...)`"))
            if name and name in FORBIDDEN_CALLS:
                vios.append(Violation(path, node.lineno, node.col_offset, "call",
                                      f"禁止内置 `{name}(...)`"))

        # 禁用属性访问（读侧面）
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_ATTRS:
                vios.append(Violation(path, node.lineno, node.col_offset, "attr",
                                      f"禁止访问 dunder 属性 `.{node.attr}`"))

    return vios


def iter_python_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for t in targets:
        if not t.exists():
            continue
        if t.is_file() and t.suffix == ".py":
            files.append(t)
        elif t.is_dir():
            files.extend(sorted(t.rglob("*.py")))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", help="待扫描的 .py 文件或目录；省略则扫描默认 artifact 目录")
    args = parser.parse_args()

    if args.targets:
        targets = [Path(t).resolve() for t in args.targets]
    else:
        targets = [t for t in DEFAULT_TARGETS if t.exists()]

    files = iter_python_files(targets)

    if not files:
        print("[SKIP] 未找到 artifact 源码（P0-T5 Agent 上线前正常）")
        return 0

    all_violations: list[Violation] = []
    for f in files:
        src = f.read_text(encoding="utf-8")
        all_violations.extend(scan_source(f, src))

    if all_violations:
        print(f"[FAIL] 基元库白名单扫描命中 {len(all_violations)} 处违规:", file=sys.stderr)
        for v in all_violations:
            print(f"  {v.render()}", file=sys.stderr)
        print("", file=sys.stderr)
        print("  修复: 仅允许 `from fund.primitives.* import ...` 以及 stdlib 子集 {datetime, decimal, typing, re}", file=sys.stderr)
        print("        任何缺口走 §ChangeFlow，绝不在 artifact 内临时实现。", file=sys.stderr)
        return 1

    print(f"[OK] 基元库白名单扫描通过（{len(files)} 个文件）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
