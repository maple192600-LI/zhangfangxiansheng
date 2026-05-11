"""Artifact sandbox boundary definitions.

Defines the configuration and policy for artifact code execution.
Actual exec implementation will come in Phase E1.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from core.artifact_ast_guard import (
    ALLOWED_MODULE_PREFIXES,
    BLOCKED_BUILTINS,
    BLOCKED_IMPORT_MODULES,
)

DEFAULT_TIMEOUT_SECONDS = 60


@dataclass(frozen=True)
class ArtifactSandboxConfig:
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS
    allowed_module_prefixes: tuple[str, ...] = ALLOWED_MODULE_PREFIXES
    blocked_import_modules: frozenset[str] = field(default_factory=lambda: BLOCKED_IMPORT_MODULES)
    blocked_builtins: frozenset[str] = field(default_factory=lambda: BLOCKED_BUILTINS)
    max_output_rows: int = 50_000


def get_default_sandbox_config() -> ArtifactSandboxConfig:
    return ArtifactSandboxConfig()
