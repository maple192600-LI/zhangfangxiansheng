"""fund_events: allow nullable core fields for preview rows.

Revision ID: 007_fund_events_preview_nullable_core
Revises: 006_add_workflow_tables
Create Date: 2026-05-17
"""
from alembic import op
import sqlalchemy as sa

revision = "007_fund_events_preview_nullable_core"
down_revision = "006_add_workflow_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("fund_events") as batch_op:
        batch_op.alter_column("business_date", nullable=True)
        batch_op.alter_column("entity_code", nullable=True)
        batch_op.alter_column("account_code", nullable=True)
        batch_op.create_check_constraint(
            "ck_fund_events_amount_mutex",
            "NOT (amount_in > 0 AND amount_out > 0)",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_amount_nonneg",
            "amount_in >= 0 AND amount_out >= 0",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_state_enum",
            "state IN ('正常','待确认','异常','已作废')",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_source_enum",
            "source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_normal_core_required",
            "state != '正常' OR (business_date IS NOT NULL AND entity_code IS NOT NULL AND entity_code != '' AND account_code IS NOT NULL AND account_code != '')",
        )


def downgrade() -> None:
    with op.batch_alter_table("fund_events") as batch_op:
        batch_op.drop_constraint("ck_fund_events_normal_core_required", type_="check")
        batch_op.alter_column("account_code", nullable=False)
        batch_op.alter_column("entity_code", nullable=False)
        batch_op.alter_column("business_date", nullable=False)
        batch_op.create_check_constraint(
            "ck_fund_events_amount_mutex",
            "NOT (amount_in > 0 AND amount_out > 0)",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_amount_nonneg",
            "amount_in >= 0 AND amount_out >= 0",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_state_enum",
            "state IN ('正常','待确认','异常','已作废')",
        )
        batch_op.create_check_constraint(
            "ck_fund_events_source_enum",
            "source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')",
        )
