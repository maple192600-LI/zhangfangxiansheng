"""baseline + CANONICAL_12 fund_events.

Revision ID: 001_v3_fund_events
Revises:
Create Date: 2026-04-25
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op

revision: str = "001_v3_fund_events"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
    CREATE TABLE IF NOT EXISTS divisions (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      division_code VARCHAR(50) UNIQUE,
      name VARCHAR(100) NOT NULL UNIQUE,
      sort_order INTEGER DEFAULT 0,
      status VARCHAR(20) NOT NULL DEFAULT 'enabled',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS banks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      bank_code VARCHAR(50) NOT NULL UNIQUE,
      bank_name VARCHAR(100) NOT NULL UNIQUE,
      short_name VARCHAR(50),
      cnaps_code VARCHAR(20),
      contact_phone VARCHAR(30),
      website VARCHAR(200),
      notes TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'enabled',
      sort_order INTEGER DEFAULT 0,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_banks_status ON banks(status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS entities (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      division_id INTEGER REFERENCES divisions(id) ON DELETE SET NULL,
      entity_code VARCHAR(50) NOT NULL UNIQUE,
      name VARCHAR(200) NOT NULL,
      short_name VARCHAR(100) NOT NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'enabled',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_entities_division ON entities(division_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS accounts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE RESTRICT,
      bank_id INTEGER REFERENCES banks(id) ON DELETE SET NULL,
      account_code VARCHAR(50) NOT NULL UNIQUE,
      account_alias VARCHAR(100) NOT NULL,
      bank_name VARCHAR(100),
      branch_name VARCHAR(200),
      account_number VARCHAR(100),
      account_last_four VARCHAR(10),
      account_type VARCHAR(50) NOT NULL,
      instrument_type VARCHAR(50) NOT NULL,
      input_method VARCHAR(50) NOT NULL DEFAULT 'manual',
      has_online_banking BOOLEAN NOT NULL DEFAULT 0,
      include_in_daily_report BOOLEAN NOT NULL DEFAULT 1,
      allow_manual_entry BOOLEAN NOT NULL DEFAULT 1,
      currency VARCHAR(20) NOT NULL DEFAULT 'CNY',
      initial_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
      balance_date DATE NOT NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'enabled',
      notes TEXT,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_accounts_entity ON accounts(entity_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS account_aliases (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
      alias_text VARCHAR(100) NOT NULL,
      alias_type VARCHAR(50) NOT NULL,
      created_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_account_aliases_account ON account_aliases(account_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_account_aliases_text ON account_aliases(alias_text)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS manual_field_pool (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      field_code VARCHAR(50) NOT NULL UNIQUE,
      field_name_cn VARCHAR(100) NOT NULL,
      data_type VARCHAR(30) NOT NULL,
      is_core BOOLEAN NOT NULL DEFAULT 0,
      is_default_visible BOOLEAN NOT NULL DEFAULT 1,
      is_disable_allowed BOOLEAN NOT NULL DEFAULT 1,
      is_parse_key BOOLEAN NOT NULL DEFAULT 0,
      is_validation_key BOOLEAN NOT NULL DEFAULT 0,
      is_batch_inheritable BOOLEAN NOT NULL DEFAULT 0,
      options_json TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS manual_template_schemes (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      scheme_code VARCHAR(50) NOT NULL UNIQUE,
      scheme_name VARCHAR(100) NOT NULL,
      description TEXT,
      selected_fields_json TEXT NOT NULL,
      is_default BOOLEAN NOT NULL DEFAULT 0,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS import_batches (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      batch_code VARCHAR(50) NOT NULL UNIQUE,
      source_type VARCHAR(30) NOT NULL,
      source_name VARCHAR(200),
      status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_import_batches_status ON import_batches(status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_import_batches_source ON import_batches(source_type)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS fund_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      business_date DATE NOT NULL,
      entity_code VARCHAR(50) NOT NULL REFERENCES entities(entity_code),
      entity_name VARCHAR(200) NOT NULL,
      account_code VARCHAR(50) NOT NULL REFERENCES accounts(account_code),
      account_name VARCHAR(100) NOT NULL,
      summary VARCHAR(500),
      counterparty VARCHAR(200),
      amount_in NUMERIC(18,2) NOT NULL DEFAULT 0,
      amount_out NUMERIC(18,2) NOT NULL DEFAULT 0,
      rolling_balance NUMERIC(18,2),
      state VARCHAR(20) NOT NULL DEFAULT '正常',
      source VARCHAR(20) NOT NULL,
      batch_id INTEGER REFERENCES import_batches(id) ON DELETE RESTRICT,
      parser_artifact_id INTEGER REFERENCES parser_artifacts(id) ON DELETE SET NULL,
      created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME,
      CHECK (NOT (amount_in > 0 AND amount_out > 0)),
      CHECK (amount_in >= 0 AND amount_out >= 0),
      CHECK (state IN ('正常','待确认','异常','已作废')),
      CHECK (source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据'))
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_fund_events_date_account ON fund_events(business_date, account_code)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fund_events_state ON fund_events(state)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fund_events_batch ON fund_events(batch_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS daily_report_runs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      report_code VARCHAR(50) NOT NULL UNIQUE,
      report_name VARCHAR(200) NOT NULL,
      start_date DATE NOT NULL,
      end_date DATE NOT NULL,
      status VARCHAR(30) NOT NULL DEFAULT 'draft',
      notes TEXT,
      created_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_daily_report_runs_dates ON daily_report_runs(start_date, end_date)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_configs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider VARCHAR(50) NOT NULL,
      display_name VARCHAR(100) NOT NULL,
      api_key_local TEXT NOT NULL,
      base_url VARCHAR(255),
      model_name VARCHAR(100),
      is_default BOOLEAN NOT NULL DEFAULT 0,
      privacy_mode VARCHAR(20) NOT NULL DEFAULT 'standard',
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS ai_call_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      provider VARCHAR(50) NOT NULL,
      model VARCHAR(100),
      endpoint VARCHAR(255),
      status VARCHAR(20) NOT NULL,
      duration_ms INTEGER NOT NULL DEFAULT 0,
      request_size INTEGER NOT NULL DEFAULT 0,
      response_size INTEGER NOT NULL DEFAULT 0,
      error_code VARCHAR(50),
      created_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_ai_call_logs_created ON ai_call_logs(created_at)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS agent_configs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      agent_code VARCHAR(50) NOT NULL UNIQUE,
      agent_name VARCHAR(100) NOT NULL,
      agent_type VARCHAR(30) NOT NULL,
      workspace_dir VARCHAR(200) NOT NULL,
      ai_config_id INTEGER REFERENCES ai_configs(id) ON DELETE SET NULL,
      description TEXT,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_agent_configs_type ON agent_configs(agent_type, status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS operation_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      action VARCHAR(50) NOT NULL,
      module VARCHAR(50) NOT NULL,
      batch_id INTEGER REFERENCES import_batches(id) ON DELETE SET NULL,
      detail_json TEXT NOT NULL,
      created_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_operation_logs_module ON operation_logs(module, created_at)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_operation_logs_batch ON operation_logs(batch_id)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      username VARCHAR(50) NOT NULL UNIQUE,
      password_hash VARCHAR(128) NOT NULL,
      must_change_password BOOLEAN NOT NULL DEFAULT 0,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)

    op.execute("""
    CREATE TABLE IF NOT EXISTS parser_templates (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      template_name VARCHAR(100) NOT NULL,
      template_type VARCHAR(30) NOT NULL,
      file_format VARCHAR(20) NOT NULL,
      header_row INTEGER NOT NULL,
      skip_rows INTEGER NOT NULL DEFAULT 0,
      sample_headers TEXT NOT NULL,
      mapping_json TEXT NOT NULL,
      created_by VARCHAR(30) NOT NULL,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_parser_templates_type ON parser_templates(template_type, status)")

    op.execute("""
    CREATE TABLE IF NOT EXISTS report_templates (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      template_code VARCHAR(50) NOT NULL UNIQUE,
      template_name VARCHAR(100) NOT NULL,
      report_type VARCHAR(30) NOT NULL,
      columns_json TEXT NOT NULL,
      layout_json TEXT,
      group_by VARCHAR(50),
      is_default BOOLEAN NOT NULL DEFAULT 0,
      status VARCHAR(20) NOT NULL DEFAULT 'active',
      created_by VARCHAR(30) NOT NULL DEFAULT 'admin',
      remark TEXT,
      created_at DATETIME NOT NULL,
      updated_at DATETIME NOT NULL
    )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_templates_type ON report_templates(report_type, status)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_report_templates_default ON report_templates(report_type, is_default)")


def downgrade() -> None:
    for table in [
        "report_templates", "parser_templates", "users", "operation_logs",
        "agent_configs", "ai_call_logs", "ai_configs", "daily_report_runs",
        "fund_events", "import_batches", "manual_template_schemes",
        "manual_field_pool", "account_aliases", "accounts", "entities",
        "banks", "divisions",
    ]:
        op.execute(f"DROP TABLE IF EXISTS {table}")
