"""Runtime execution for Fund Agent artifacts.

NOTE: The old fund agent system has been removed. This module is retained
for backward compatibility with existing parser/rule artifacts but the
lazy imports to agents.fund have been disabled. New bank imports use
the template-based commit path (commit_by_mapping) instead.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator, Optional

from openpyxl import load_workbook
from openpyxl.workbook.workbook import Workbook
from sqlalchemy.orm import Session

from core import runtime_guard
from db.tables import AIConfig, ParserArtifact, RuleArtifact


def run_parser(
    db: Session,
    artifact_id: int,
    file_path: str,
    ctx: Optional[dict[str, Any]] = None,
) -> Iterator[dict[str, Any]]:
    """Execute active ParserArtifact — deprecated, no longer available."""
    raise ValueError(
        "旧版 Fund Agent 解析器已移除。请使用「银行流水导入」页面的模板映射方式导入。"
    )


def run_rule(db: Session, artifact_id: int, ctx: dict[str, Any]) -> Workbook:
    """Execute active RuleArtifact — deprecated."""
    raise ValueError(
        "旧版 Fund Agent 规则引擎已移除。"
    )
