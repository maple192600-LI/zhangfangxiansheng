from datetime import date

from conftest import add_fund_event, add_import_batch
from services import report_service


def test_daily_report_sums_income_expense_and_opening_balance(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session)
    add_fund_event(db_session, entity, account, batch, income_amount=200, summary_text="receipt")
    add_fund_event(db_session, entity, account, batch, direction="expense", expense_amount=75, summary_text="payment")

    rows = report_service.daily_report(db_session, date(2026, 4, 24), date(2026, 4, 24), entity.id)

    assert rows == [{
        "entity_id": entity.id,
        "entity_name": "Entity001",
        "opening_balance": 1000.0,
        "total_income": 200.0,
        "total_expense": 75.0,
        "net_change": 125.0,
        "ending_balance": 1125.0,
    }]


def test_cash_journal_groups_by_account_and_day(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session)
    add_fund_event(db_session, entity, account, batch, income_amount=200)
    add_fund_event(db_session, entity, account, batch, direction="expense", expense_amount=75)

    blocks = report_service.cash_journal(db_session, date(2026, 4, 24), date(2026, 4, 24), account.id)

    assert len(blocks) == 1
    assert blocks[0]["opening_balance"] == 1000.0
    assert blocks[0]["total_income"] == 200.0
    assert blocks[0]["total_expense"] == 75.0
    assert blocks[0]["ending_balance"] == 1125.0
    assert blocks[0]["rows"] == [{
        "business_date": "2026-04-24",
        "prev_balance": 1000.0,
        "income": 200.0,
        "expense": 75.0,
        "day_balance": 1125.0,
    }]


def test_income_and_expense_lists_page_committed_rows(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session)
    add_fund_event(db_session, entity, account, batch, income_amount=200, summary_text="receipt")
    add_fund_event(db_session, entity, account, batch, direction="expense", expense_amount=75, summary_text="payment")

    income = report_service.income_list(db_session, date(2026, 4, 24), date(2026, 4, 24), entity.id)
    expense = report_service.expense_list(db_session, date(2026, 4, 24), date(2026, 4, 24), entity.id)

    assert income["total"] == 1
    assert income["items"][0]["amount"] == 200.0
    assert income["items"][0]["summary_text"] == "receipt"
    assert expense["total"] == 1
    assert expense["items"][0]["amount"] == 75.0
    assert expense["items"][0]["summary_text"] == "payment"


def test_account_balance_includes_account_rows_and_entity_subtotal(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session)
    add_fund_event(db_session, entity, account, batch, income_amount=200)

    rows = report_service.account_balance(db_session, date(2026, 4, 24), date(2026, 4, 24), entity.id)

    assert len(rows) == 2
    assert rows[0]["is_subtotal"] is False
    assert rows[0]["opening_balance"] == 1000.0
    assert rows[0]["period_income"] == 200.0
    assert rows[0]["ending_balance"] == 1200.0
    assert rows[1]["is_subtotal"] is True
    assert rows[1]["ending_balance"] == 1200.0
