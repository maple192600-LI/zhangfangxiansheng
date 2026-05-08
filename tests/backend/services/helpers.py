from datetime import date, datetime
from io import BytesIO

import openpyxl

from db.tables import FundEvent, ImportBatch


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

    amount_in = income_amount if direction == "income" else 0
    amount_out = expense_amount if direction == "expense" else 0
    event = FundEvent(
        batch_id=batch.id,
        business_date=business_date,
        entity_code=entity.entity_code,
        entity_name=entity.name,
        account_code=account.account_code,
        account_name=account.account_alias,
        summary=summary_text,
        counterparty="Counterparty",
        amount_in=amount_in,
        amount_out=amount_out,
        rolling_balance=None,
        state="正常",
        source="网银导入",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
