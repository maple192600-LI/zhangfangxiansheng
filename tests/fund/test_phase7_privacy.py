from __future__ import annotations

import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from agents.fund.harness import FundAgent
from agents.fund import memory
from core.privacy_pipeline import OfflineModeError, mask_for_llm
from db.tables import AIConfig, AICallLog, Account, AccountAlias


def _session():
    import database

    return database.SessionLocal()


def _write_bank_sample(path: Path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "EntityName", "AccountNo", "Counterparty", "Income"])
    ws.append(["2026-04-24", "Example Tech Co Ltd", "6222000011112222", "Customer A", "12345.67"])
    wb.save(path)


def _clean_privacy_rows(engine):
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("DELETE FROM parser_artifacts"))
        conn.execute(text("DELETE FROM ai_call_logs"))
        conn.execute(text("DELETE FROM ai_configs"))
        conn.execute(text("DELETE FROM account_aliases"))


def test_field_dictionary_seed_has_ten_core_fields():
    data = memory.load_field_dictionary()
    assert set(data) == {
        "business_date",
        "entity_code",
        "entity_name",
        "account_code",
        "account_name",
        "summary",
        "counterparty",
        "amount_in",
        "amount_out",
        "rolling_balance",
    }
    assert all(len(item["aliases"]) >= 5 for item in data.values())


def test_list_aliases_merges_seed_and_db(primitives_db, tmp_path, monkeypatch):
    _clean_privacy_rows(primitives_db)
    seed = tmp_path / "alias_library.json"
    seed.write_text(json.dumps({"ICBC": ["工商银行", "ICBC"], "A001": ["种子别名"]}, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(memory, "ALIAS_LIBRARY_PATH", seed)

    with _session() as db:
        account = db.query(Account).filter(Account.account_code == "A001").first()
        db.add(AccountAlias(account_id=account.id, alias_text="DB别名", alias_type="自动"))
        db.commit()
        aliases = memory.list_aliases(db)

    assert aliases["ICBC"] == ["工商银行", "ICBC"]
    assert aliases["A001"] == ["种子别名", "DB别名"]


def test_mask_for_llm_privacy_modes():
    rows = {
        "headers": ["单位", "账号", "金额"],
        "rows": [{"单位": "示例科技有限公司", "账号": "6222000011112222", "金额": "12345.67"}],
    }

    standard = mask_for_llm(rows, "standard")
    assert standard["rows"][0]["单位"] == "示***"
    assert standard["rows"][0]["账号"] == "****************"
    assert standard["rows"][0]["金额"] == "12000"

    strict = mask_for_llm(rows, "strict")
    assert strict["headers"] == rows["headers"]
    assert strict["rows"] == []

    with pytest.raises(OfflineModeError, match="已设为离线模式"):
        mask_for_llm(rows, "offline")


def test_harness_privacy_mode_from_ai_config(primitives_db, tmp_path):
    _clean_privacy_rows(primitives_db)
    sample = tmp_path / "bank.xlsx"
    _write_bank_sample(sample)

    with _session() as db:
        db.add(AIConfig(
            provider="fund",
            display_name="strict config",
            api_key_local="",
            model_name="harness",
            is_default=True,
            privacy_mode="strict",
            status="active",
        ))
        db.commit()
        agent = FundAgent(db)
        preview = agent._privacy_preview("parser.bank", {"sample_file": str(sample)}, "strict")
        assert preview["headers"] == ["Date", "EntityName", "AccountNo", "Counterparty", "Income"]
        assert preview["rows"] == []
        draft = agent.run_skill("parser.bank", {
            "account_code": "A001",
            "sample_file": str(sample),
            "privacy_mode": "standard",
        })
        assert draft.payload["artifact_id"]

        db.query(AIConfig).delete()
        db.add(AIConfig(
            provider="fund",
            display_name="offline config",
            api_key_local="",
            model_name="harness",
            is_default=True,
            privacy_mode="offline",
            status="active",
        ))
        db.commit()

        with pytest.raises(ValueError, match="已设为离线模式"):
            agent.run_skill("parser.bank", {"account_code": "A001", "sample_file": str(sample)})

        blocked = db.query(AICallLog).filter(AICallLog.error_code == "PRIVACY_OFFLINE").first()
        assert blocked is not None
