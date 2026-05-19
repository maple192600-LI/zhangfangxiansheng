"""Add agent_id and agent_session_id to parser_training_jobs.

Revision ID: 011_parser_training_agent_session
Revises: 010_parser_training_jobs
Create Date: 2026-05-19
"""
from alembic import op
import sqlalchemy as sa

revision = "011_parser_training_agent_session"
down_revision = "010_parser_training_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("parser_training_jobs", sa.Column("agent_id", sa.Integer(), nullable=True))
    op.add_column("parser_training_jobs", sa.Column("agent_session_id", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("parser_training_jobs", "agent_session_id")
    op.drop_column("parser_training_jobs", "agent_id")
