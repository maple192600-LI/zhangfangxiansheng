"""parser_artifacts: add bank_id, format_key, match_rules columns.

Revision ID: 008_parser_artifacts_bank_format
Revises: 007_fund_events_preview_nullable_core
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "008_parser_artifacts_bank_format"
down_revision = "007_fund_events_preview_nullable_core"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("parser_artifacts") as batch_op:
        batch_op.add_column(sa.Column("bank_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("format_key", sa.String(100), nullable=True))
        batch_op.add_column(sa.Column(
            "match_rules", sa.JSON(), nullable=False,
            server_default="{}", default={},
        ))
        batch_op.create_foreign_key(
            "fk_parser_artifacts_bank_id", "banks",
            ["bank_id"], ["id"], ondelete="SET NULL",
        )
        batch_op.create_check_constraint(
            "ck_parser_artifacts_kind",
            "kind IN ('bank','manual')",
        )
        batch_op.create_check_constraint(
            "ck_parser_artifacts_status",
            "status IN ('draft','active','retired')",
        )
        batch_op.create_index(
            "idx_parser_artifacts_bank_format",
            ["kind", "bank_id", "format_key", "status"],
        )


def downgrade() -> None:
    with op.batch_alter_table("parser_artifacts") as batch_op:
        batch_op.drop_index("idx_parser_artifacts_bank_format")
        batch_op.drop_constraint("fk_parser_artifacts_bank_id", type_="foreignkey")
        batch_op.drop_column("match_rules")
        batch_op.drop_column("format_key")
        batch_op.drop_column("bank_id")
