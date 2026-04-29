"""v3 · 新建 parser_artifacts 表（§T3.1）

Revision ID: 002_v3_parser_artifacts
Revises: 001_v3_fund_events
Create Date: 2026-04-23 03:01:00.000000

契约锚点：docs/30_contracts/20_database_schema.md §T3.1
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_v3_parser_artifacts"
down_revision: Union[str, Sequence[str], None] = "001_v3_fund_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "parser_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("account_code", sa.String(length=50), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("code", sa.Text(), nullable=False),
        sa.Column("primitives_imports", sa.Text(), nullable=False),
        sa.Column("sample_check_log", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=20), nullable=True, server_default="fund.agent"),
        sa.Column("approved_by", sa.String(length=50), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint("kind IN ('bank','manual')", name="ck_parser_artifacts_kind"),
        sa.CheckConstraint(
            "status IN ('draft','approved','retired')",
            name="ck_parser_artifacts_status",
        ),
        sa.UniqueConstraint("name", "version", name="uq_parser_artifacts_name_version"),
    )
    op.create_index("idx_parser_artifacts_name", "parser_artifacts", ["name"])
    op.create_index("idx_parser_artifacts_account", "parser_artifacts", ["account_code"])


def downgrade() -> None:
    op.drop_index("idx_parser_artifacts_account", table_name="parser_artifacts")
    op.drop_index("idx_parser_artifacts_name", table_name="parser_artifacts")
    op.drop_table("parser_artifacts")
