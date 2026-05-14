"""add workflow tables

Revision ID: 006_add_workflow_tables
Revises: 005_drop_parser_templates
Create Date: 2026-05-13
"""
from alembic import op
import sqlalchemy as sa

revision = "006_add_workflow_tables"
down_revision = "005_drop_parser_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "workflows",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("workflow_code", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("current_version", sa.Integer, nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(50), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.CheckConstraint("status IN ('draft','active','archived')", name="ck_workflows_status"),
    )
    op.create_index("idx_workflows_status", "workflows", ["status"])

    op.create_table(
        "workflow_versions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.Integer, sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column("version", sa.Integer, nullable=False),
        sa.Column("graph_json", sa.Text, nullable=False),
        sa.Column("change_summary", sa.Text, nullable=True),
        sa.Column("created_by", sa.String(50), nullable=False, server_default="agent"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_workflow_versions_workflow", "workflow_versions", ["workflow_id"])
    op.create_index(
        "ux_workflow_versions_workflow_version",
        "workflow_versions",
        ["workflow_id", "version"],
        unique=True,
    )

    op.create_table(
        "workflow_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("workflow_id", sa.Integer, sa.ForeignKey("workflows.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "workflow_version_id",
            sa.Integer,
            sa.ForeignKey("workflow_versions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("workflow_code", sa.String(80), nullable=False),
        sa.Column("workflow_version", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("output_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed','paused','cancelled')",
            name="ck_workflow_runs_status",
        ),
    )
    op.create_index("idx_workflow_runs_workflow", "workflow_runs", ["workflow_id"])
    op.create_index("idx_workflow_runs_version", "workflow_runs", ["workflow_version_id"])
    op.create_index("idx_workflow_runs_status", "workflow_runs", ["status"])

    op.create_table(
        "workflow_run_steps",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("run_id", sa.Integer, sa.ForeignKey("workflow_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("node_id", sa.String(80), nullable=False),
        sa.Column("node_type", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("input_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("output_json", sa.Text, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column("started_at", sa.DateTime, nullable=True),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','running','completed','failed','skipped','paused')",
            name="ck_workflow_run_steps_status",
        ),
    )
    op.create_index("idx_workflow_run_steps_run", "workflow_run_steps", ["run_id"])
    op.create_index("idx_workflow_run_steps_node", "workflow_run_steps", ["run_id", "node_id"])


def downgrade() -> None:
    op.drop_index("idx_workflow_run_steps_node", table_name="workflow_run_steps")
    op.drop_index("idx_workflow_run_steps_run", table_name="workflow_run_steps")
    op.drop_table("workflow_run_steps")
    op.drop_index("idx_workflow_runs_status", table_name="workflow_runs")
    op.drop_index("idx_workflow_runs_version", table_name="workflow_runs")
    op.drop_index("idx_workflow_runs_workflow", table_name="workflow_runs")
    op.drop_table("workflow_runs")
    op.drop_index("ux_workflow_versions_workflow_version", table_name="workflow_versions")
    op.drop_index("idx_workflow_versions_workflow", table_name="workflow_versions")
    op.drop_table("workflow_versions")
    op.drop_index("idx_workflows_status", table_name="workflows")
    op.drop_table("workflows")
