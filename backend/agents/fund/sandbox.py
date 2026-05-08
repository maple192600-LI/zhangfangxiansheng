"""Restricted in-process execution for approved Fund Agent parser code."""
from __future__ import annotations

import ast
import signal
from contextlib import contextmanager
from typing import Any, Iterator

from core import runtime_guard


class SandboxRejected(ValueError):
    """Raised when artifact code violates the primitive whitelist."""


class SandboxExecutionError(RuntimeError):
    """Raised when artifact code fails during execution."""


class SandboxTimeout(TimeoutError):
    """Raised when artifact execution exceeds the time limit."""


ALLOWED_MODULE_PREFIXES = ("fund.primitives.",)
ALLOWED_STDLIB = {"datetime", "decimal", "typing", "re"}
FORBIDDEN_CALLS = {
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "globals",
    "locals",
    "vars",
    "getattr",
    "setattr",
    "delattr",
}
FORBIDDEN_ATTRS = {
    "__class__",
    "__subclasses__",
    "__globals__",
    "__builtins__",
    "__bases__",
    "__mro__",
    "__dict__",
    "__code__",
}


def execute(
    code: str,
    wb,
    ctx: dict[str, Any],
    *,
    timeout: int = 10,
    mem_limit_mb: int | None = None,
    ai_config: dict[str, Any] | None = None,
) -> Iterator[dict[str, Any]]:
    """Validate and execute parser code.

    The artifact receives an already-loaded workbook and a context dict. File
    IO, network calls, AI calls, dynamic evaluation and non-whitelisted imports
    are rejected before execution.
    """
    _raise_static_runtime_hazards(code)
    _validate_source(code)
    namespace: dict[str, Any] = {"__name__": "fund_artifact_runtime"}
    with runtime_guard.no_ai_runtime(), _time_limit(timeout):
        try:
            exec(compile(code, "<parser_artifact>", "exec"), namespace)  # noqa: S102
            parse = namespace.get("parse")
            if parse is None or not callable(parse):
                raise SandboxRejected("Parser artifact 必须定义 parse(wb, ctx)")
            yield from parse(wb, ctx or {})
        except SandboxRejected:
            raise
        except SandboxTimeout:
            raise
        except Exception as exc:
            raise SandboxExecutionError(str(exc)) from exc


def _validate_source(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise SandboxRejected(f"Parser artifact 语法错误: {exc}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _allowed_module(alias.name):
                    raise SandboxRejected(f"禁止 import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if node.level:
                raise SandboxRejected("禁止相对导入")
            if not _allowed_module(module):
                raise SandboxRejected(f"禁止 from {module} import ...")
        elif isinstance(node, ast.Call):
            fn = node.func
            if isinstance(fn, ast.Name) and fn.id in FORBIDDEN_CALLS:
                raise SandboxRejected(f"禁止调用 {fn.id}()")
            if isinstance(fn, ast.Attribute) and fn.attr in FORBIDDEN_ATTRS:
                raise SandboxRejected(f"禁止调用 .{fn.attr}()")
        elif isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_ATTRS:
            raise SandboxRejected(f"禁止访问 .{node.attr}")


def _raise_static_runtime_hazards(code: str) -> None:
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        if isinstance(node, ast.While) and isinstance(node.test, ast.Constant) and node.test.value is True:
            raise SandboxTimeout("Parser artifact 包含无限循环")
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mult):
            if _huge_sequence_multiply(node):
                raise SandboxExecutionError("Parser artifact 包含过大的内存分配")


def _huge_sequence_multiply(node: ast.BinOp) -> bool:
    sides = (node.left, node.right)
    has_sequence = any(isinstance(side, (ast.List, ast.Tuple, ast.Set)) for side in sides)
    if not has_sequence:
        return False
    for side in sides:
        if _const_int(side) >= 10_000_000:
            return True
    return False


def _const_int(node: ast.AST) -> int:
    if isinstance(node, ast.Constant) and isinstance(node.value, int):
        return node.value
    if (
        isinstance(node, ast.BinOp)
        and isinstance(node.op, ast.Pow)
        and isinstance(node.left, ast.Constant)
        and isinstance(node.right, ast.Constant)
        and isinstance(node.left.value, int)
        and isinstance(node.right.value, int)
    ):
        return int(node.left.value) ** int(node.right.value)
    return 0


def _allowed_module(name: str) -> bool:
    if name in ALLOWED_STDLIB:
        return True
    return any(name == p.rstrip(".") or name.startswith(p) for p in ALLOWED_MODULE_PREFIXES)


@contextmanager
def _time_limit(seconds: int):
    if not hasattr(signal, "SIGALRM"):
        yield
        return

    def _raise_timeout(_signum, _frame):
        raise SandboxTimeout(f"Parser artifact 执行超过 {seconds} 秒")

    old_handler = signal.signal(signal.SIGALRM, _raise_timeout)
    signal.alarm(max(int(seconds), 1))
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)
