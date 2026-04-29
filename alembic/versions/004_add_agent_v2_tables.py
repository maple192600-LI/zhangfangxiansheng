"""add agent_v2 tables

Revision ID: 004_agent_v2
Revises: 003_add_ai_privacy_mode
Create Date: 2026-04-27
"""
from alembic import op
import sqlalchemy as sa

revision = "004_agent_v2"
down_revision = "003_add_ai_privacy_mode"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "agents_v2",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_code", sa.String(50), nullable=False, unique=True),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("role_prompt", sa.Text, nullable=False, server_default=""),
        sa.Column("ai_config_id", sa.Integer, sa.ForeignKey("ai_configs.id", ondelete="SET NULL"), nullable=True),
        sa.Column("workspace_path", sa.String(500), nullable=False),
        sa.Column("permission_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("sort_order", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_by", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_agents_v2_status", "agents_v2", ["status"])

    op.create_table(
        "skills_v2",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("skill_code", sa.String(80), nullable=False, unique=True),
        sa.Column("display_name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("owner_agent_id", sa.Integer, sa.ForeignKey("agents_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("manifest_json", sa.Text, nullable=False, server_default="{}"),
        sa.Column("source_path", sa.String(500), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("verified_at", sa.DateTime, nullable=True),
        sa.Column("test_pass_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("test_fail_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("updated_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_skills_v2_status", "skills_v2", ["status"])

    op.create_table(
        "agent_sessions",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("title", sa.String(200), nullable=True),
        sa.Column("context_summary", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_active_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_agent_sessions_agent", "agent_sessions", ["agent_id"])

    op.create_table(
        "agent_messages",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("agent_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text, nullable=True),
        sa.Column("tool_call_json", sa.Text, nullable=True),
        sa.Column("tool_result_json", sa.Text, nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_agent_messages_session", "agent_messages", ["session_id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("skill_id", sa.Integer, sa.ForeignKey("skills_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents_v2.id", ondelete="SET NULL"), nullable=True),
        sa.Column("session_id", sa.Integer, sa.ForeignKey("agent_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("inputs_json", sa.Text, nullable=True),
        sa.Column("outputs_json", sa.Text, nullable=True),
        sa.Column("logs", sa.Text, nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("duration_ms", sa.Integer, nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_agent_runs_agent", "agent_runs", ["agent_id"])

    op.create_table(
        "agent_memories",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.Integer, sa.ForeignKey("agents_v2.id", ondelete="CASCADE"), nullable=False),
        sa.Column("key", sa.String(200), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("scope", sa.String(30), nullable=False, server_default="agent"),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=False, server_default="1.0"),
        sa.Column("source", sa.String(50), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("last_used_at", sa.DateTime, nullable=False, server_default=sa.text("CURRENT_TIMESTAMP")),
    )
    op.create_index("idx_agent_memories_agent", "agent_memories", ["agent_id"])
    op.create_index("idx_agent_memories_key", "agent_memories", ["agent_id", "key"])


def downgrade() -> None:
    op.drop_table("agent_memories")
    op.drop_table("agent_runs")
    op.drop_table("agent_messages")
    op.drop_table("agent_sessions")
    op.drop_table("skills_v2")
    op.drop_table("agents_v2")
