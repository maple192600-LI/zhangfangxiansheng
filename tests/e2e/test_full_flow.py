"""E2E tests for full flow.

These tests depend on artifact runtime (run_parser / run_rule) being
fully implemented. Until Phase E/H delivers the runtime, they are skipped.
After runtime is ready, remove the pytest.mark.skip annotations.
"""
from __future__ import annotations

import pytest
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


@pytest.mark.skip(reason="Requires artifact runtime (Phase E). Re-enable after run_parser is implemented.")
def test_bank_import_e2e_and_repeat_uses_active_parser(e2e_client, e2e_env):
    first = _post_xlsx(e2e_client, "/api/bank-import/upload", FIXTURES / "bank_icbc_01.xlsx")
    assert first["code"] == 0

    draft = e2e_client.post("/api/artifacts/parsers/drafts", json={
        "name": "ICBC_test",
        "kind": "bank",
        "account_code": "A001",
        "code": "# parser code",
        "primitives_imports": [],
        "sample_check_log": {},
        "confidence": 0.9,
    }).json()
    assert draft["code"] == 0, draft
    parser_id = draft["data"]["id"]

    approved = e2e_client.post(f"/api/artifacts/parsers/{parser_id}/approve", json={
        "reviewer": "admin",
    }).json()
    assert approved["code"] == 0


@pytest.mark.skip(reason="Requires artifact runtime (Phase E). Re-enable after run_parser is implemented.")
def test_manual_excel_e2e(e2e_client, e2e_env):
    uploaded = _post_xlsx(
        e2e_client,
        "/api/manual-flow/upload",
        FIXTURES / "manual_multi_entity_01.xlsx",
        data={"scheme_code": "manual_multi_subject_basic"},
    )
    assert uploaded["code"] == 0


@pytest.mark.skip(reason="Requires artifact runtime (Phase H). Re-enable after run_rule is implemented.")
def test_template_report_e2e(e2e_client, e2e_env):
    pass


@pytest.mark.skip(reason="Requires legacy FundAgent skill invoke path. Deprecated in Phase 2.")
def test_privacy_offline_blocks_skill_before_artifact(e2e_client, e2e_env):
    pass
