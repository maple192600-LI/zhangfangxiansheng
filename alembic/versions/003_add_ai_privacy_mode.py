"""add ai_configs privacy_mode.

Revision ID: 003_add_ai_privacy_mode
Revises: 002_add_v3_artifacts
Create Date: 2026-04-26
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

revision: str = "003_add_ai_privacy_mode"
down_revision: Union[str, Sequence[str], None] = "002_add_v3_artifacts"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    columns = {row[1] for row in conn.execute(text("PRAGMA table_info(ai_configs)"))}
    if "privacy_mode" not in columns:
        op.execute("ALTER TABLE ai_configs ADD COLUMN privacy_mode VARCHAR(20) NOT NULL DEFAULT 'standard'")


def downgrade() -> None:
    pass
