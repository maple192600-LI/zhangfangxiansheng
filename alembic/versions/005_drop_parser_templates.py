"""drop parser_templates table

Revision ID: 005_drop_parser_templates
Revises: 004_agent_v2
Create Date: 2026-05-10
"""
from alembic import op
import sqlalchemy as sa

revision = "005_drop_parser_templates"
down_revision = "004_agent_v2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_index("idx_parser_templates_type", table_name="parser_templates")
    op.drop_table("parser_templates")


def downgrade() -> None:
    op.create_table(
        "parser_templates",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("template_name", sa.String(100), nullable=False),
        sa.Column("template_type", sa.String(30), nullable=False),
        sa.Column("file_format", sa.String(20), nullable=False),
        sa.Column("header_row", sa.Integer, nullable=False),
        sa.Column("skip_rows", sa.Integer, nullable=False, server_default="0"),
        sa.Column("sample_headers", sa.Text, nullable=False),
        sa.Column("mapping_json", sa.Text, nullable=False),
        sa.Column("account_code", sa.String(30), nullable=True),
        sa.Column("created_by", sa.String(30), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
    )
    op.create_index(
        "idx_parser_templates_type",
        "parser_templates",
        ["template_type", "status"],
    )
