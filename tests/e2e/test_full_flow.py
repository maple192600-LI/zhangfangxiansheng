from __future__ import annotations

from datetime import date
from pathlib import Path

from db.tables import AICallLog, AIConfig, FundEvent, ParserArtifact

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "fund_samples"


def _post_xlsx(client, url: str, path: Path, data: dict | None = None):
    with path.open("rb") as f:
        return client.post(
            url,
            data=data or {},
            files={"file": (path.name, f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        ).json()


def _session(env):
    return env["SessionLocal"]()


def test_bank_import_e2e_and_repeat_uses_active_parser(e2e_client, e2e_env):
    first = _post_xlsx(e2e_client, "/api/bank-import/upload", FIXTURES / "bank_icbc_01.xlsx")
    assert first["code"] == 0

    draft = e2e_client.post("/api/fund/agent/skills/parser.bank/invoke", json={
        "account_code": "A001",
        "batch_code": first["data"]["batch_code"],
        "privacy_mode": "standard",
    }).json()
    assert draft["code"] == 0, draft
    parser_id = draft["data"]["artifact_id"]

    approved = e2e_client.post(f"/api/fund/parsers/{parser_id}/approve").json()
    assert approved["code"] == 0
    committed = e2e_client.post("/api/bank-import/commit", json={
        "batch_code": first["data"]["batch_code"],
        "parser_artifact_id": parser_id,
    }).json()
    assert committed["code"] == 0
    assert committed["data"]["inserted_rows"] == 2

    with _session(e2e_env) as db:
        before_ai_calls = db.query(AICallLog).count()
        assert db.query(FundEvent).filter(FundEvent.parser_artifact_id == parser_id).count() == 2
        assert db.query(ParserArtifact).filter(ParserArtifact.id == parser_id).first().status == "active"

    second = _post_xlsx(e2e_client, "/api/bank-import/upload", FIXTURES / "bank_icbc_02.xlsx")
    assert second["code"] == 0
    repeat_commit = e2e_client.post("/api/bank-import/commit", json={
        "batch_code": second["data"]["batch_code"],
        "parser_artifact_id": parser_id,
    }).json()
    assert repeat_commit["code"] == 0
    assert repeat_commit["data"]["inserted_rows"] == 2

    with _session(e2e_env) as db:
        assert db.query(AICallLog).count() == before_ai_calls
        total = sum(float(row.amount_in or 0) for row in db.query(FundEvent).all())
        assert total == 1000.0


def test_manual_excel_e2e(e2e_client, e2e_env):
    uploaded = _post_xlsx(
        e2e_client,
        "/api/manual-flow/upload",
        FIXTURES / "manual_multi_entity_01.xlsx",
        data={"scheme_code": "manual_multi_subject_basic"},
    )
    assert uploaded["code"] == 0

    draft = e2e_client.post("/api/fund/agent/skills/parser.manual/invoke", json={
        "batch_code": uploaded["data"]["batch_code"],
        "scheme_code": "manual_multi_subject_basic",
        "privacy_mode": "standard",
    }).json()
    assert draft["code"] == 0, draft
    parser_id = draft["data"]["artifact_id"]
    assert e2e_client.post(f"/api/fund/parsers/{parser_id}/approve").json()["code"] == 0

    committed = e2e_client.post("/api/manual-flow/commit", json={
        "batch_code": uploaded["data"]["batch_code"],
        "parser_artifact_id": parser_id,
    }).json()
    assert committed["code"] == 0
    assert committed["data"]["inserted_rows"] == 2

    with _session(e2e_env) as db:
        rows = db.query(FundEvent).filter(FundEvent.parser_artifact_id == parser_id).all()
        assert len(rows) == 2
        assert {row.source for row in rows} == {"手工录入"}


def test_template_report_e2e(e2e_client, e2e_env):
    uploaded = _post_xlsx(e2e_client, "/api/fund/templates/upload", FIXTURES / "cash_journal_blank.xlsx")
    assert uploaded["code"] == 0
    rule_id = uploaded["data"]["rule_draft_id"]
    assert e2e_client.post(f"/api/fund/rules/{rule_id}/approve").json()["code"] == 0

    with _session(e2e_env) as db:
        db.add(FundEvent(
            business_date=date(2026, 4, 24),
            entity_code="E001",
            entity_name="示例科技有限公司",
            account_code="A001",
            account_name="工行主账户",
            summary="回款",
            counterparty="示例客户",
            amount_in=300,
            amount_out=0,
            rolling_balance=100300,
            state="正常",
            source="网银导入",
        ))
        db.commit()

    generated = e2e_client.post("/api/reports/generate", json={
        "rule_id": rule_id,
        "account_code": "A001",
        "entity_code": "E001",
        "period_start": "2026-04-01",
        "period_end": "2026-04-30",
    }).json()
    assert generated["code"] == 0
    assert generated["data"]["placeholder_filled"] == 18

    download = e2e_client.get(generated["data"]["download_url"])
    assert download.status_code == 200
    assert download.content[:2] == b"PK"


def test_privacy_offline_blocks_skill_before_artifact(e2e_client, e2e_env):
    with _session(e2e_env) as db:
        cfg = db.query(AIConfig).filter(AIConfig.is_default == True).first()
        cfg.privacy_mode = "offline"
        db.commit()

    uploaded = _post_xlsx(e2e_client, "/api/bank-import/upload", FIXTURES / "bank_icbc_01.xlsx")
    response = e2e_client.post("/api/fund/agent/skills/parser.bank/invoke", json={
        "account_code": "A001",
        "batch_code": uploaded["data"]["batch_code"],
        "privacy_mode": "standard",
    }).json()

    assert response["code"] == 3001
    assert "离线模式" in response["message"]
    with _session(e2e_env) as db:
        assert db.query(ParserArtifact).count() == 0
        assert db.query(AICallLog).filter(AICallLog.error_code == "PRIVACY_OFFLINE").count() == 1
