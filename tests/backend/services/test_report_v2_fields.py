import sys
from datetime import date, datetime
from io import BytesIO
from pathlib import Path

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from database import Base
from db.tables import Account, Bank, Division, Entity, FundEvent, ImportBatch, ParserTemplate
from services import bank_import_service, report_service


def _session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _seed_event(db):
    now = datetime.now()
    division = Division(
        division_code="HZ0001",
        name="总部",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(division)
    db.flush()

    entity = Entity(
        division_id=division.id,
        entity_code="DW0001",
        name="测试单位",
        short_name="测试",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(entity)
    db.flush()

    bank = Bank(
        bank_code="YH0001",
        bank_name="测试银行",
        status="enabled",
        created_at=now,
        updated_at=now,
    )
    db.add(bank)
    db.flush()

    account = Account(
        entity_id=entity.id,
        bank_id=bank.id,
        account_code="ZH0001",
        account_alias="基本户",
        account_type="基本户",
        instrument_type="银行存款",
        input_method="网银",
        currency="CNY",
        initial_balance=100,
        balance_date=date(2026, 4, 1),
        status="enabled",
        include_in_daily_report=True,
        created_at=now,
        updated_at=now,
    )
    db.add(account)
    db.flush()

    batch = ImportBatch(
        batch_code="BANK_TEST",
        source_type="bank",
        source_name="test.xlsx",
        status="committed",
        created_at=now,
        updated_at=now,
    )
    db.add(batch)
    db.flush()

    event = FundEvent(
        batch_id=batch.id,
        business_date=date(2026, 4, 24),
        entity_code=entity.entity_code,
        entity_name=entity.name,
        account_code=account.account_code,
        account_name=account.account_alias,
        summary="收款",
        counterparty="客户",
        amount_in=25,
        amount_out=0,
        rolling_balance=None,
        state="正常",
        source="网银导入",
        created_at=now,
        updated_at=now,
    )
    db.add(event)
    db.commit()
    return entity, account


def test_report_queries_use_v2_fund_event_fields_and_relationships():
    db = _session()
    entity, _account = _seed_event(db)

    daily = report_service.daily_report(db, date(2026, 4, 24), date(2026, 4, 24), entity.id)
    income = report_service.income_list(db, date(2026, 4, 24), date(2026, 4, 24), entity.id)

    assert daily[0]["total_income"] == 25
    assert daily[0]["ending_balance"] == 125
    assert income["items"][0]["entity_name"] == "测试单位"
    assert income["items"][0]["account_name"] == "基本户"


def test_bank_upload_preview_commit_then_daily_report_uses_v2_schema(tmp_path, monkeypatch):
    db = _session()
    entity, account = _seed_event(db)
    db.query(FundEvent).delete()
    db.query(ImportBatch).delete()
    db.commit()

    template = ParserTemplate(
        template_name="测试银行模板",
        template_type="bank",
        file_format="xlsx",
        header_row=0,
        skip_rows=0,
        sample_headers='["日期", "单位ID", "账户ID", "摘要", "收入", "支出"]',
        mapping_json=(
            '{"日期": "business_date", "摘要": "summary_text", '
            '"收入": "income_amount", "支出": "expense_amount"}'
        ),
        account_code=account.account_code,
        created_by="test",
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["日期", "单位ID", "账户ID", "摘要", "收入", "支出"])
    ws.append(["2026-04-24", str(entity.id), str(account.id), "测试收款", "50", "0"])
    buf = BytesIO()
    wb.save(buf)

    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(tmp_path))

    uploaded = bank_import_service.upload_file(db, buf.getvalue(), "bank.xlsx")
    assert uploaded["sample_rows"] == [["2026-04-24", str(entity.id), str(account.id), "测试收款", "50", "0"]]
    preview = bank_import_service.preview(db, uploaded["batch_code"], template_id=template.id)
    committed = bank_import_service.commit_by_mapping(db, uploaded["batch_code"], template_id=template.id)
    daily = report_service.daily_report(db, date(2026, 4, 24), date(2026, 4, 24), entity.id)

    assert preview["valid_count"] == 1
    assert committed["inserted_rows"] == 1
    assert daily[0]["total_income"] == 50
    assert daily[0]["ending_balance"] == 150
