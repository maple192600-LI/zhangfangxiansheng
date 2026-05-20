"""add Fund Agent artifact tables.

Revision ID: 002_add_v3_artifacts
Revises: 001_v3_fund_events
Create Date: 2026-04-25
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "002_add_v3_artifacts"
down_revision: Union[str, Sequence[str], None] = "001_v3_fund_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS parser_artifacts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name VARCHAR(100) NOT NULL,
      kind VARCHAR(20) NOT NULL,
      account_code VARCHAR(50),
      version INTEGER NOT NULL DEFAULT 1,
      status VARCHAR(20) NOT NULL DEFAULT 'draft',
      code TEXT NOT NULL,
      primitives_imports JSON NOT NULL,
      sample_check_log JSON NOT NULL DEFAULT '{}',
      confidence DECIMAL(5,4),
      created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
      approved_by VARCHAR(50),
      approved_at DATETIME,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME,
      CHECK (kind IN ('bank','manual')),
      CHECK (status IN ('draft','active','retired')),
      UNIQUE(name, version)
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_parser_artifacts_account ON parser_artifacts(account_code, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_parser_artifacts_kind ON parser_artifacts(kind, status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS rule_artifacts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name VARCHAR(100) NOT NULL,
      template_id INTEGER REFERENCES report_templates(id),
      version INTEGER NOT NULL DEFAULT 1,
      status VARCHAR(20) NOT NULL DEFAULT 'draft',
      placeholder_bindings JSON NOT NULL,
      loop_spec JSON,
      loop_config JSON,
      primitives_imports JSON NOT NULL,
      sample_check_log JSON NOT NULL DEFAULT '{}',
      confidence DECIMAL(5,4),
      created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
      approved_by VARCHAR(50),
      approved_at DATETIME,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME,
      CHECK (status IN ('draft','active','retired'))
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_rule_artifacts_template ON rule_artifacts(template_id, status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS template_inference_job (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      template_file VARCHAR(255),
      original_filename VARCHAR(300),
      file_path VARCHAR(500),
      stage VARCHAR(20),
      status VARCHAR(20) NOT NULL DEFAULT 'pending',
      stage_a_output JSON,
      stage_b_output JSON,
      stage_c_decision VARCHAR(20),
      rule_artifact_id INTEGER REFERENCES rule_artifacts(id),
      error_message TEXT,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME,
      CHECK (status IN ('pending','reviewed','approved','rejected'))
    )
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS template_inference_job")
    op.execute("DROP TABLE IF EXISTS rule_artifacts")
    op.execute("DROP TABLE IF EXISTS parser_artifacts")
