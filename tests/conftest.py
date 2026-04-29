import sys
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import openpyxl
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Base
from db.tables import Account, Bank, Division, Entity, FundEvent, ImportBatch


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def chart_of_accounts(db_session):
    return seed_chart_of_accounts(db_session)


def seed_chart_of_accounts(db):
    now = datetime.now()
    division = Division(
        division_code="D001",
        name="Division 001",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(division)
    db.flush()

    entity = Entity(
        division_id=division.id,
        entity_code="E001",
        name="Entity 001 Ltd",
        short_name="Entity001",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(entity)
    db.flush()

    bank = Bank(
        bank_code="B001",
        bank_name="Bank 001",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(bank)
    db.flush()

    account = Account(
        entity_id=entity.id,
        bank_id=bank.id,
        account_code="A001",
        account_alias="Main Account",
        account_type="basic",
        instrument_type="bank_deposit",
        input_method="online",
        currency="CNY",
        initial_balance=1000,
        balance_date=date(2026, 4, 1),
        status="enabled",
        include_in_daily_report=True,
        created_at=now,
        updated_at=now,
    )
    db.add(account)
    db.commit()
    return {"division": division, "entity": entity, "bank": bank, "account": account}


def make_xlsx(rows):
    wb = openpyxl.Workbook()
    ws = wb.active
    for row in rows:
        ws.append(row)
    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


def add_import_batch(db, batch_code="BATCH001", source_type="bank", source_name="bank.xlsx", status="uploaded"):
    batch = ImportBatch(
        batch_code=batch_code,
        source_type=source_type,
        source_name=source_name,
        status=status,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


def add_fund_event(
    db,
    entity,
    account,
    batch=None,
    business_date=date(2026, 4, 24),
    direction="income",
    income_amount=0,
    expense_amount=0,
    summary_text="receipt",
):
    if batch is None:
        batch = add_import_batch(db, batch_code=f"BATCH{datetime.now().timestamp()}", source_type="test")

    event = FundEvent(
        batch_id=batch.id,
        source_type=batch.source_type,
        business_date=business_date,
        entity_id=entity.id,
        account_id=account.id,
        direction=direction,
        income_amount=income_amount,
        expense_amount=expense_amount,
        counterparty_name="Counterparty",
        summary_text=summary_text,
        parse_status="valid",
        raw_data_json="{}",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
