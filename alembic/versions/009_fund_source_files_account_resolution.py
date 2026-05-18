"""Add source_files, account_resolution_attempts, account_resolution_evidence tables.

Revision ID: 009_fund_source_files_account_resolution
Revises: 008_parser_artifacts_bank_format
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "009_fund_source_files_account_resolution"
down_revision = "008_parser_artifacts_bank_format"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_files",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("batch_id", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(300), nullable=False),
        sa.Column("storage_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sheet_name", sa.String(100), nullable=True),
        sa.Column("format_fingerprint", sa.String(100), nullable=True),
        sa.Column("parser_artifact_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="uploaded"),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["batch_id"], ["import_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parser_artifact_id"], ["parser_artifacts.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "status IN ('uploaded','parsed','needs_rule','needs_account','failed','ready')",
            name="ck_source_files_status",
        ),
    )
    op.create_index("idx_source_files_batch", "source_files", ["batch_id"])
    op.create_index("idx_source_files_hash", "source_files", ["file_hash"])
    op.create_index("idx_source_files_parser", "source_files", ["parser_artifact_id"])
    op.create_index("idx_source_files_status", "source_files", ["status"])

    op.create_table(
        "account_resolution_attempts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_file_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("recommended_entity_code", sa.String(50), nullable=True),
        sa.Column("recommended_account_code", sa.String(50), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("error_code", sa.String(50), nullable=True),
        sa.Column("raw_hints", sa.JSON(), nullable=True),
        sa.Column("candidates", sa.JSON(), nullable=True),
        sa.Column("bank_resolution", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["source_file_id"], ["source_files.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "status IN ('matched','ambiguous','unmatched','conflict')",
            name="ck_account_resolution_attempts_status",
        ),
    )
    op.create_index("idx_account_resolution_source_file", "account_resolution_attempts", ["source_file_id"])

    op.create_table(
        "account_resolution_evidence",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("attempt_id", sa.Integer(), nullable=False),
        sa.Column("evidence_type", sa.String(50), nullable=False),
        sa.Column("evidence_value", sa.Text(), nullable=True),
        sa.Column("matched_entity_code", sa.String(50), nullable=True),
        sa.Column("matched_account_code", sa.String(50), nullable=True),
        sa.Column("weight", sa.Numeric(5, 4), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["attempt_id"], ["account_resolution_attempts.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "evidence_type IN ('account_number','account_last_four','account_name','bank','filename','alias','history','balance_chain','parser_hint','entity_name')",
            name="ck_account_resolution_evidence_type",
        ),
    )
    op.create_index("idx_account_resolution_evidence_attempt", "account_resolution_evidence", ["attempt_id"])


def downgrade() -> None:
    op.drop_table("account_resolution_evidence")
    op.drop_table("account_resolution_attempts")
    op.drop_table("source_files")
