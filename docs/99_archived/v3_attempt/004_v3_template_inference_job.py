"""v3 · 新建 template_inference_job 表（§T3.3）

Revision ID: 004_v3_template_inference_job
Revises: 003_v3_rule_artifacts
Create Date: 2026-04-23 03:03:00.000000

契约锚点：docs/30_contracts/20_database_schema.md §T3.3
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_v3_template_inference_job"
down_revision: Union[str, Sequence[str], None] = "003_v3_rule_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "template_inference_job",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("original_filename", sa.String(length=300), nullable=False),
        sa.Column("file_path", sa.String(length=500), nullable=False),
        sa.Column("detected_placeholders", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("rule_draft_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','reviewed','approved','rejected')",
            name="ck_template_inference_job_status",
        ),
        sa.ForeignKeyConstraint(["rule_draft_id"], ["rule_artifacts.id"]),
    )


def downgrade() -> None:
    op.drop_table("template_inference_job")
