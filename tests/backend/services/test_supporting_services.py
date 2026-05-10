import json
import zipfile
from datetime import date, datetime

import pytest

from conftest import add_fund_event, add_import_batch, make_xlsx
from db.schemas import (
    AccountCreate,
    AccountUpdate,
    AliasCreate,
    BankCreate,
    BankUpdate,
    DivisionCreate,
    DivisionUpdate,
    EntityCreate,
    EntityUpdate,
    InitialBalanceSet,
    ManualSchemeCreate,
    ManualSchemeUpdate,
)
from db.tables import DailyReportRun, FundEvent, ManualFieldPool, ManualTemplateScheme, OperationLog
from services import (
    auth_service,
    backup_service,
    bank_service,
    base_data_service,
    dashboard_service,
    export_service,
    home_service,
    manual_flow_service,
    manual_scheme_service,
    master_data_service,
    report_template_service,
    reset_service,
)


CORE_MANUAL_FIELDS = [
    "entity_match_key",
    "account_match_key",
    "business_date",
    "summary_text",
    "counterparty_name",
    "income_amount",
    "expense_amount",
]


def _seed_manual_fields(db_session):
    for idx, field_code in enumerate(CORE_MANUAL_FIELDS, 1):
        db_session.add(ManualFieldPool(
            id=idx,
            field_code=field_code,
            field_name_cn=field_code,
            data_type="text",
            is_core=True,
            is_default_visible=True,
            is_disable_allowed=False,
            is_parse_key=False,
            is_validation_key=False,
            is_batch_inheritable=False,
            status="active",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        ))
    db_session.commit()


def _seed_manual_scheme(db_session):
    _seed_manual_fields(db_session)
    scheme = ManualTemplateScheme(
        scheme_code="manual_multi_subject_basic",
        scheme_name="Manual Basic",
        description="test",
        selected_fields_json=json.dumps(CORE_MANUAL_FIELDS),
        is_default=True,
        status="active",
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add(scheme)
    db_session.commit()
    return scheme


def test_master_data_crud_usage_alias_and_batch_actions(db_session):
    division = master_data_service.create_division(db_session, DivisionCreate(name="North"))
    updated_division = master_data_service.update_division(
        db_session,
        division.id,
        DivisionUpdate(name="North Updated", sort_order=2),
    )
    entity = master_data_service.create_entity(
        db_session,
        EntityCreate(division_id=division.id, name="Entity North", short_name="EN"),
    )
    account = master_data_service.create_account(
        db_session,
        AccountCreate(
            entity_id=entity.id,
            account_alias="Cash",
            account_type="cash",
            instrument_type="cash",
            initial_balance=10,
            balance_date=date(2026, 4, 1),
        ),
    )
    alias = master_data_service.create_alias(
        db_session,
        account.id,
        AliasCreate(alias_text="cash-alias", alias_type="manual"),
    )

    assert updated_division.name == "North Updated"
    assert master_data_service.list_divisions(db_session, "enabled")[0].id == division.id
    assert master_data_service.list_entities(db_session, keyword="North").total == 1
    assert master_data_service.list_accounts(db_session, keyword="Cash").total == 1
    assert master_data_service.get_accounts_tree(db_session)[0].accounts[0].id == account.id
    assert master_data_service.get_division_usage(db_session, division.id)["unit_count"] == 1
    assert master_data_service.get_entity_usage(db_session, entity.id)["account_count"] == 1
    assert master_data_service.list_aliases(db_session, account.id)[0].id == alias.id

    master_data_service.update_entity(db_session, entity.id, EntityUpdate(short_name="ENU"))
    master_data_service.update_account(db_session, account.id, AccountUpdate(account_alias="Cash Updated"))
    master_data_service.set_initial_balance(
        db_session,
        account.id,
        InitialBalanceSet(initial_balance=99, balance_date=date(2026, 4, 2)),
    )
    master_data_service.delete_alias(db_session, account.id, alias.id)
    assert master_data_service.batch_action_accounts(db_session, [account.id], "disable")["success"] == 1
    assert master_data_service.batch_action_entities(db_session, [entity.id], "delete")["failed"]
    assert master_data_service.batch_action_divisions(db_session, [division.id], "disable")["success"] == 1


def test_bank_service_crud_usage_and_batch_actions(db_session, chart_of_accounts):
    created = bank_service.create_bank(
        db_session,
        BankCreate(bank_name="Independent Bank", short_name="IB", sort_order=3),
    )
    updated = bank_service.update_bank(
        db_session,
        created.id,
        BankUpdate(bank_name="Independent Bank Updated", short_name="IBU"),
    )

    assert updated.short_name == "IBU"
    assert bank_service.get_bank(db_session, created.id).id == created.id
    assert bank_service.list_banks(db_session, keyword="Independent").total == 1
    assert bank_service.batch_action_banks(db_session, [created.id], "disable")["success"] == 1
    bank_service.delete_bank(db_session, created.id)
    assert bank_service.get_bank(db_session, created.id) is None

    linked_bank = chart_of_accounts["bank"]
    assert bank_service.get_bank_usage(db_session, linked_bank.id)["account_count"] == 1
    with pytest.raises(ValueError):
        bank_service.delete_bank(db_session, linked_bank.id)


def test_base_data_query_rebuild_and_factory_reset(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session)
    add_fund_event(db_session, entity, account, batch, amount_in=50, summary="receipt")
    add_fund_event(db_session, entity, account, batch, amount_out=20, summary="payment")

    queried = base_data_service.query_base_data(
        db_session,
        date_from="2026-04-24",
        date_to="2026-04-24",
        entity_id=entity.id,
        keyword="receipt",
    )
    rebuilt = base_data_service.rebuild_rolling_balance(db_session, account.id)

    assert queried["total"] == 1
    assert queried["items"][0]["summary_text"] == "receipt"
    assert rebuilt["affected_accounts"] == 1
    assert rebuilt["updated_events"] == 2

    reset = reset_service.factory_reset(db_session)
    assert "message" in reset
    assert db_session.query(FundEvent).count() == 0


def test_dashboard_and_home_services_return_workbench_state(db_session, chart_of_accounts):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session, status="uploaded")
    add_fund_event(db_session, entity, account, batch, amount_in=50)
    db_session.add(DailyReportRun(
        report_code="R001",
        report_name="Daily",
        start_date=date.today(),
        end_date=date.today(),
        status="confirmed",
        created_at=datetime.now(),
    ))
    db_session.add(OperationLog(action="backup_create", module="backup", detail_json="{}", created_at=datetime.now()))
    db_session.commit()

    metrics = dashboard_service.get_metrics(db_session, "2026-04-01", "2026-04-30")
    trends = dashboard_service.get_trends(db_session, days=1)
    composition = dashboard_service.get_composition(db_session)
    overview = home_service.get_overview(db_session)
    todos = home_service.get_todos(db_session)
    quick_links = home_service.get_quick_links(db_session)
    status = home_service.get_system_status(db_session)

    assert metrics["total_income"] == 50.0
    assert len(trends["dates"]) == 2
    assert composition["items"][0]["value"] == 1000.0
    assert overview["pending_tasks"] >= 1
    assert todos["counts"]["import"] == 1
    assert quick_links["links"]
    assert status["recent_actions"][0]["action"] == "backup_create"


def test_auth_service_default_user_login_token_and_password_change(db_session):
    user = auth_service.get_or_create_default_user(db_session)
    logged_in = auth_service.authenticate(db_session, "admin", "admin123")
    payload = auth_service.decode_token(logged_in["token"])
    changed, message = auth_service.change_password(db_session, user.id, "admin123", "new-password")

    assert logged_in["user"]["username"] == "admin"
    assert payload["username"] == "admin"
    assert changed is True
    assert message
    assert auth_service.authenticate(db_session, "admin", "new-password") is not None
    assert auth_service.get_user_by_id(db_session, user.id)["username"] == "admin"


def test_manual_scheme_service_validates_core_fields(db_session):
    _seed_manual_fields(db_session)
    scheme = manual_scheme_service.create_scheme(
        db_session,
        ManualSchemeCreate(
            scheme_code="manual_test",
            scheme_name="Manual Test",
            selected_fields=CORE_MANUAL_FIELDS,
            is_default=True,
        ),
    )
    updated = manual_scheme_service.update_scheme(
        db_session,
        scheme.id,
        ManualSchemeUpdate(scheme_name="Manual Test Updated", selected_fields=CORE_MANUAL_FIELDS + ["note_text"]),
    )

    assert len(manual_scheme_service.list_field_pool(db_session)) == len(CORE_MANUAL_FIELDS)
    assert manual_scheme_service.list_schemes(db_session)[0].scheme_code == "manual_test"
    assert manual_scheme_service.get_scheme_by_code(db_session, "manual_test").id == scheme.id
    assert updated.scheme_name == "Manual Test Updated"
    with pytest.raises(ValueError):
        manual_scheme_service.create_scheme(
            db_session,
            ManualSchemeCreate(
                scheme_code="manual_bad",
                scheme_name="Manual Bad",
                selected_fields=["business_date"],
            ),
        )


def test_report_template_crud_default_and_excel_parsing(db_session, tmp_path):
    first = report_template_service.create_template(db_session, {
        "template_name": "Daily Default",
        "report_type": "daily_report",
        "columns": [
            {"field_key": "entity_name", "header_name": "Entity", "width": 120, "align": "left", "visible": True, "sort_order": 1},
            {"field_key": "total_income", "header_name": "Income", "width": 120, "align": "right", "visible": True, "format": "money", "sort_order": 2},
        ],
        "is_default": True,
    })
    second = report_template_service.create_template(db_session, {
        "template_name": "Daily Alternative",
        "report_type": "daily_report",
        "columns": [{"field_key": "ending_balance", "header_name": "Ending", "sort_order": 1}],
    })
    updated = report_template_service.update_template(
        db_session,
        second["id"],
        {"template_name": "Daily Alternative Updated", "is_default": True, "layout": {"rows": []}},
    )
    report_template_service.set_default(db_session, first["id"])
    deleted = report_template_service.delete_template(db_session, second["id"])

    xlsx_path = tmp_path / "template.xlsx"
    xlsx_path.write_bytes(make_xlsx([
        ["Report Title"],
        ["Entity", "Income", "Expense"],
        ["{{entity_name}}", "{{income}}", "{{expense}}"],
    ]))
    headers = report_template_service.parse_excel_headers(str(xlsx_path), "daily_report")
    layout = report_template_service.parse_excel_layout(str(xlsx_path))

    assert first["template_code"] == "MB0001"
    assert updated["template_name"] == "Daily Alternative Updated"
    assert report_template_service.get_default_template(db_session, "daily_report")["id"] == first["id"]
    assert deleted is True
    assert report_template_service.get_template(db_session, second["id"])["status"] == "deleted"
    assert report_template_service.list_templates(db_session, report_type="daily_report")
    assert headers[0]["header_name"] == "Entity"
    assert layout["col_count"] == 3


def test_backup_service_lists_and_rejects_unsafe_paths(tmp_path, monkeypatch):
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    backup_file = backup_dir / "bk_20260424_001.zip"
    with zipfile.ZipFile(backup_file, "w") as zf:
        zf.writestr("meta.json", json.dumps({"ok": True}))
    monkeypatch.setattr(backup_service, "BACKUP_DIR", str(backup_dir))

    listed = backup_service.list_backups()

    assert listed["total"] == 1
    assert backup_service._validate_backup_filename("bk_20260424_001.zip") == "bk_20260424_001.zip"
    with pytest.raises(ValueError):
        backup_service._validate_backup_filename("../bk_20260424_001.zip")
    with zipfile.ZipFile(tmp_path / "bad.zip", "w") as zf:
        zf.writestr("../evil.txt", "bad")
    with zipfile.ZipFile(tmp_path / "bad.zip") as zf:
        with pytest.raises(ValueError):
            backup_service._safe_extract(zf, str(tmp_path / "restore"))


def test_master_data_batch_import_accounts_creates_master_records(db_session):
    file_data = make_xlsx([
        [f"h{i}" for i in range(20)],
        [
            "Batch Division",
            "Batch Entity Ltd",
            "BatchEntity",
            "E900",
            "Batch Bank",
            "6222000000001234",
            "Batch Account",
            "A900",
            "",
            "basic",
            "bank_deposit",
            "true",
            "manual",
            "CNY",
            "128.50",
            "2026-04-01",
            "true",
            "true",
            "enabled",
            "imported",
        ],
        [
            "Batch Division",
            "Batch Entity Ltd",
            "BatchEntity",
            "E900",
            "Batch Bank",
            "6222000000001234",
            "Batch Account",
            "A900",
            "",
            "basic",
            "bank_deposit",
            "true",
            "manual",
            "CNY",
            "128.50",
            "2026-04-01",
            "true",
            "true",
            "enabled",
            "duplicate",
        ],
    ])

    result = master_data_service.batch_import_accounts(db_session, file_data, "accounts.xlsx")

    assert result["total_rows"] == 2
    assert result["created_divisions"] == 1
    assert result["created_entities"] == 1
    assert result["created_accounts"] == 1
    assert result["error_count"] == 1
    assert master_data_service.list_accounts(db_session, keyword="Batch Account").total == 1


def test_manual_flow_excel_upload_commit_and_export_template(db_session, chart_of_accounts, tmp_path, monkeypatch):
    from datetime import date as date_type
    from unittest.mock import patch

    from db.tables import ParserArtifact

    _seed_manual_scheme(db_session)
    monkeypatch.setattr("services.manual_flow_service.DATA_DIR", str(tmp_path))

    artifact = ParserArtifact(
        name="Test Manual Parser",
        kind="manual",
        account_code=None,
        version=1,
        status="active",
        code="def parse(ws): return []",
        primitives_imports=[],
        sample_check_log={},
        confidence=0.9,
        created_by="test",
        created_at=datetime.now(),
    )
    db_session.add(artifact)
    db_session.commit()
    db_session.refresh(artifact)

    file_data = make_xlsx([
        CORE_MANUAL_FIELDS,
        ["E001", "A001", "2026-04-24", "excel receipt", "Customer", "33.00", ""],
    ])

    uploaded = manual_flow_service.upload_workbook(
        db_session,
        file_data,
        "manual.xlsx",
        "manual_multi_subject_basic",
    )

    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    canonical_rows = [
        {
            "business_date": date_type(2026, 4, 24),
            "entity_code": entity.entity_code,
            "entity_name": entity.short_name,
            "account_code": account.account_code,
            "account_name": account.account_alias,
            "summary": "excel receipt",
            "counterparty": "Customer",
            "amount_in": 33,
            "amount_out": 0,
            "rolling_balance": None,
            "state": "正常",
            "source": "手工录入",
        },
    ]

    with patch.object(manual_flow_service.artifact_runtime, "run_parser", return_value=iter(canonical_rows)):
        committed = manual_flow_service.commit_manual(
            db_session,
            uploaded["batch_code"],
            parser_artifact_id=artifact.id,
        )

    template_bytes = manual_flow_service.export_template(
        db_session,
        "manual_multi_subject_basic",
        include_example=True,
    )

    assert uploaded["row_count"] == 1
    assert committed["inserted_rows"] == 1
    assert committed["parser_artifact_id"] == artifact.id
    assert template_bytes.startswith(b"PK")


def test_export_service_generates_all_report_types(db_session, chart_of_accounts, tmp_path, monkeypatch):
    entity = chart_of_accounts["entity"]
    account = chart_of_accounts["account"]
    batch = add_import_batch(db_session, batch_code="EXPORT_BATCH")
    add_fund_event(db_session, entity, account, batch, amount_in=70, summary="receipt")
    add_fund_event(db_session, entity, account, batch, amount_out=25, summary="payment")
    base_kwargs = {
        "start_date": "2026-04-24",
        "end_date": "2026-04-24",
        "entity_id": entity.id,
    }
    monkeypatch.setattr(export_service, "EXPORT_DIR", str(tmp_path / "exports"))

    generated = []
    for export_type in [
        "base_data",
        "daily_report",
        "cash_journal",
        "account_balance",
        "income_list",
        "expense_list",
        "major_balance",
        "week_report",
    ]:
        generated.append(export_service.generate_export(db_session, export_type, **base_kwargs))
    generated.append(export_service.generate_export(
        db_session,
        "month_check",
        start_date="2026-04-24",
        end_date="2026-04-24",
        entity_id=entity.id,
        year=2026,
        month=4,
    ))
    generated.append(export_service.generate_export(
        db_session,
        "month_report",
        start_date="2026-04-24",
        end_date="2026-04-24",
        entity_id=entity.id,
        year=2026,
        month=4,
    ))
    generated.append(export_service.generate_export(
        db_session,
        "year_report",
        start_date="2026-04-24",
        end_date="2026-04-24",
        entity_id=entity.id,
        year=2026,
    ))

    assert len(generated) == 11
    assert all(path.endswith(".xlsx") for path in generated)
    with pytest.raises(ValueError):
        export_service.generate_export(db_session, "unknown", **base_kwargs)
