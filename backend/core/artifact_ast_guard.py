"""AST whitelist guard for artifact code.

Validates that artifact Python code only imports allowed modules
and does not use dangerous builtins.
"""
from __future__ import annotations

import ast
from typing import Sequence

class PrimitivesViolationError(RuntimeError):
    """Artifact code imports modules outside the primitives whitelist."""

    def __init__(self, artifact_id: int, disallowed: list[str]) -> None:
        self.artifact_id = artifact_id
        self.disallowed = disallowed
        super().__init__(
            f"Artifact {artifact_id} imports disallowed modules: {disallowed}"
        )

ALLOWED_MODULE_PREFIXES: tuple[str, ...] = (
    "fund.primitives.",
    "fund.artifacts.",
    "datetime",
    "decimal",
    "typing",
    "re",
    "collections",
    "itertools",
)

BLOCKED_BUILTINS: frozenset[str] = frozenset({
    "open",
    "eval",
    "exec",
    "compile",
    "__import__",
    "breakpoint",
    "memoryview",
    "globals",
    "locals",
    "vars",
    "dir",
})

BLOCKED_IMPORT_MODULES: frozenset[str] = frozenset({
    "os",
    "sys",
    "subprocess",
    "pathlib",
    "socket",
    "requests",
    "http",
    "urllib",
    "pandas",
    "numpy",
    "importlib",
    "shutil",
    "tempfile",
    "signal",
    "ctypes",
    "multiprocessing",
    "threading",
    "asyncio",
    "builtins",
})


def validate_artifact_code(code: str, artifact_id: int = 0) -> None:
    """Validate artifact code against the AST whitelist.

    Raises PrimitivesViolationError if disallowed imports or builtins are found.
    """
    violations: list[str] = []

    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise PrimitivesViolationError(artifact_id, [f"SyntaxError: {e}"])

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if not _is_module_allowed(alias.name):
                    violations.append(f"import {alias.name}")

        elif isinstance(node, ast.ImportFrom):
            if node.module and not _is_module_allowed(node.module):
                violations.append(f"from {node.module} import ...")

        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_BUILTINS:
                violations.append(f"{node.func.id}(...)")

            if isinstance(node.func, ast.Attribute):
                if (isinstance(node.func.value, ast.Name)
                        and node.func.value.id in ("importlib",)
                        and node.func.attr == "import_module"):
                    violations.append("importlib.import_module(...)")

        elif isinstance(node, ast.Name):
            if node.id in BLOCKED_BUILTINS:
                violations.append(node.id)

    if violations:
        raise PrimitivesViolationError(artifact_id, violations)


def _is_module_allowed(module_name: str) -> bool:
    if module_name in BLOCKED_IMPORT_MODULES:
        return False
    return any(module_name == prefix.rstrip(".") or module_name.startswith(prefix)
                for prefix in ALLOWED_MODULE_PREFIXES)


def explain_sandbox_policy() -> dict:
    return {
        "allowed_module_prefixes": list(ALLOWED_MODULE_PREFIXES),
        "blocked_import_modules": sorted(BLOCKED_IMPORT_MODULES),
        "blocked_builtins": sorted(BLOCKED_BUILTINS),
        "timeout_seconds": 60,
    }
