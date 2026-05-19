"""Add parser_training_jobs table.

Revision ID: 010_parser_training_jobs
Revises: 009_fund_source_files_account_resolution
Create Date: 2026-05-18
"""
from alembic import op
import sqlalchemy as sa

revision = "010_parser_training_jobs"
down_revision = "009_fund_source_files_account_resolution"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "parser_training_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("job_code", sa.String(30), nullable=False, unique=True),
        sa.Column("original_filename", sa.String(300), nullable=False),
        sa.Column("sample_file_path", sa.String(500), nullable=False),
        sa.Column("file_hash", sa.String(64), nullable=False),
        sa.Column("format", sa.String(10), nullable=False),
        sa.Column("format_fingerprint", sa.String(100), nullable=True),
        sa.Column("identity_hints_json", sa.Text(), nullable=True),
        sa.Column("context_snapshot_json", sa.Text(), nullable=True),
        sa.Column("headers_json", sa.Text(), nullable=True),
        sa.Column("sample_rows_json", sa.Text(), nullable=True),
        sa.Column("row_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("candidate_code", sa.Text(), nullable=True),
        sa.Column("candidate_notes", sa.Text(), nullable=True),
        sa.Column("trial_result_json", sa.Text(), nullable=True),
        sa.Column("trial_status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("status", sa.String(30), nullable=False, server_default="sample_uploaded"),
        sa.Column("parser_artifact_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default="CURRENT_TIMESTAMP"),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["parser_artifact_id"], ["parser_artifacts.id"], ondelete="SET NULL"),
        sa.CheckConstraint(
            "trial_status IN ('pending','success','failed')",
            name="ck_parser_training_jobs_trial_status",
        ),
        sa.CheckConstraint(
            "status IN ('sample_uploaded','candidate_ready','trial_success','trial_failed','active_parser_saved')",
            name="ck_parser_training_jobs_status",
        ),
    )
    op.create_index("idx_parser_training_jobs_code", "parser_training_jobs", ["job_code"])
    op.create_index("idx_parser_training_jobs_status", "parser_training_jobs", ["status"])


def downgrade() -> None:
    op.drop_index("idx_parser_training_jobs_status")
    op.drop_index("idx_parser_training_jobs_code")
    op.drop_table("parser_training_jobs")
