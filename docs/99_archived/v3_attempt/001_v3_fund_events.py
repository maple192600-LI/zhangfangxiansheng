"""v3 · 新建 fund_events 12 列基础表（§C1 / §T2.1）

Revision ID: 001_v3_fund_events
Revises:
Create Date: 2026-04-23 03:00:00.000000

契约锚点：
    docs/00_governance/00_project_constitution.md §C1
    docs/30_contracts/20_database_schema.md §T2.1
    不变量：12 列 CANONICAL_12 列序、列名、枚举值冻结。

注意：
    - FK → parser_artifacts(id) 前向引用。SQLite 在 CREATE 时不校验 FK 目标，
      RUNTIME 通过 PRAGMA foreign_keys=ON 执行校验（要求 002 先 upgrade 才能插入非 NULL parser_artifact_id）。
    - 根据 §T5，v2 fund_events 数据不迁移；若生产 DB 存在旧表需手工 DROP。
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_v3_fund_events"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "fund_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        # ── 12 列 CANONICAL_12 开始（列序冻结，§C1）──
        sa.Column("business_date", sa.Date(), nullable=False),
        sa.Column("entity_code", sa.String(length=50), nullable=False),
        sa.Column("entity_name", sa.String(length=200), nullable=False),
        sa.Column("account_code", sa.String(length=50), nullable=False),
        sa.Column("account_name", sa.String(length=100), nullable=False),
        sa.Column("summary", sa.String(length=500), nullable=True),
        sa.Column("counterparty", sa.String(length=200), nullable=True),
        sa.Column("amount_in", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("amount_out", sa.Numeric(18, 2), nullable=False, server_default="0"),
        sa.Column("rolling_balance", sa.Numeric(18, 2), nullable=True),
        sa.Column("state", sa.String(length=20), nullable=False, server_default="正常"),
        sa.Column("source", sa.String(length=20), nullable=False),
        # ── 12 列 CANONICAL_12 结束 ──
        sa.Column("batch_id", sa.Integer(), nullable=True),
        sa.Column("parser_artifact_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        # CHECK 约束（§C1 不变量）
        sa.CheckConstraint(
            "NOT (amount_in > 0 AND amount_out > 0)",
            name="ck_fund_events_amount_mutex",
        ),
        sa.CheckConstraint(
            "state IN ('正常','待确认','异常','已作废')",
            name="ck_fund_events_state_enum",
        ),
        sa.CheckConstraint(
            "source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')",
            name="ck_fund_events_source_enum",
        ),
        sa.CheckConstraint(
            "amount_in >= 0 AND amount_out >= 0",
            name="ck_fund_events_amount_nonneg",
        ),
        # FK（前向引用，见文件头注释）
        sa.ForeignKeyConstraint(["entity_code"], ["entities.entity_code"]),
        sa.ForeignKeyConstraint(["account_code"], ["accounts.account_code"]),
        sa.ForeignKeyConstraint(
            ["batch_id"], ["import_batches.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(
            ["parser_artifact_id"], ["parser_artifacts.id"], ondelete="SET NULL"
        ),
    )
    op.create_index(
        "idx_fund_events_date_account",
        "fund_events",
        ["business_date", "account_code"],
    )
    op.create_index("idx_fund_events_state", "fund_events", ["state"])
    op.create_index("idx_fund_events_batch", "fund_events", ["batch_id"])


def downgrade() -> None:
    op.drop_index("idx_fund_events_batch", table_name="fund_events")
    op.drop_index("idx_fund_events_state", table_name="fund_events")
    op.drop_index("idx_fund_events_date_account", table_name="fund_events")
    op.drop_table("fund_events")
