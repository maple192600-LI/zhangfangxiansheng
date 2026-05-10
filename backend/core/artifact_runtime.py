"""Runtime execution for Fund Agent artifacts.

ParserArtifact 执行器负责银行流水确定性解析。
RuleArtifact 执行器负责报表填充。

当前 run_parser / run_rule 为 deprecated 占位，实际解析由
bank_import_service 通过 artifact_runtime.run_parser 调用。
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
        "ParserArtifact 执行器暂未就绪。请通过 AI 智能体创建银行流水解析器后重试。"
    )


def run_rule(db: Session, artifact_id: int, ctx: dict[str, Any]) -> Workbook:
    """Execute active RuleArtifact — deprecated."""
    raise ValueError(
        "RuleArtifact 执行器暂未就绪。"
    )
