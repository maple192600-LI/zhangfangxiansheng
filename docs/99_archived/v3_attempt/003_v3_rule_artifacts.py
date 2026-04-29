"""v3 · 新建 rule_artifacts 表（§T3.2）

Revision ID: 003_v3_rule_artifacts
Revises: 002_v3_parser_artifacts
Create Date: 2026-04-23 03:02:00.000000

契约锚点：docs/30_contracts/20_database_schema.md §T3.2
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_v3_rule_artifacts"
down_revision: Union[str, Sequence[str], None] = "002_v3_parser_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "rule_artifacts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("placeholder_bindings", sa.Text(), nullable=False),
        sa.Column("loop_spec", sa.Text(), nullable=False),
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
        sa.CheckConstraint(
            "status IN ('draft','approved','retired')",
            name="ck_rule_artifacts_status",
        ),
        sa.UniqueConstraint("name", "version", name="uq_rule_artifacts_name_version"),
        sa.ForeignKeyConstraint(["template_id"], ["report_templates.id"]),
    )


def downgrade() -> None:
    op.drop_table("rule_artifacts")
