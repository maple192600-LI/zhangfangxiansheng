"""Tests for generic artifact API contract.

Verifies:
- New artifacts router is registrable
- No dependency on legacy agents.fund
- Service layer CRUD lifecycle
- Error scenarios
"""
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Base
from db.schemas import ParserArtifactDraftCreate, RuleArtifactDraftCreate, ArtifactKind
from db.tables import ParserArtifact, RuleArtifact
from services import artifact_service


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


# ── Import isolation ──

def test_api_artifacts_does_not_import_agents_fund():
    """api.artifacts module must not transitively import agents.fund."""
    import api.artifacts
    module_names = set(sys.modules.keys())
    assert "agents.fund" not in module_names
    assert "agents.fund.memory" not in module_names
    assert "agents.fund.harness" not in module_names


def test_artifact_service_does_not_import_agents_fund():
    """artifact_service must not import agents.fund."""
    import services.artifact_service
    src = Path(services.artifact_service.__file__).read_text(encoding="utf-8")
    assert "agents.fund" not in src
    assert "fund_skill_run" not in src
    assert "FundAgent" not in src


# ── Router registration ──

def test_artifacts_router_has_correct_prefix():
    from api.artifacts import router
    assert router.prefix == "/artifacts"


def test_artifacts_router_does_not_expose_fund_skill_invoke():
    """No route should match /api/fund/agent/skills/*/invoke."""
    from api.artifacts import router
    for route in router.routes:
        path = getattr(route, "path", "")
        assert "/api/fund/agent/skills" not in path
        assert "fund_skill" not in path


def test_main_does_not_register_fund_agent():
    """main.py must not include fund_agent router."""
    import main as app_module
    src = Path(app_module.__file__).read_text(encoding="utf-8")
    lines = src.split("\n")
    for line in lines:
        if "fund_agent" in line and "include_router" in line:
            pytest.fail("main.py registers fund_agent router")


# ── ParserArtifact lifecycle ──

def test_create_parser_draft(db_session):
    data = ParserArtifactDraftCreate(
        name="TestParser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# test",
        primitives_imports=["fund.primitives.sheet_ops"],
        sample_check_log={"rows": 10},
        confidence=0.95,
    )
    result = artifact_service.create_parser_draft(db_session, data)
    assert result["id"] is not None
    assert result["status"] == "draft"
    assert result["version"] == 1
    assert result["kind"] == "bank"


def test_approve_parser_draft(db_session):
    data = ParserArtifactDraftCreate(
        name="TestParser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# test",
        primitives_imports=[],
        sample_check_log={},
    )
    draft = artifact_service.create_parser_draft(db_session, data)
    approved = artifact_service.approve_parser_artifact(db_session, draft["id"], "admin")
    assert approved["status"] == "active"
    assert approved["approved_by"] == "admin"
    assert approved["approved_at"] is not None


def test_reject_parser_draft(db_session):
    data = ParserArtifactDraftCreate(
        name="TestParser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# bad",
        primitives_imports=[],
        sample_check_log={},
    )
    draft = artifact_service.create_parser_draft(db_session, data)
    rejected = artifact_service.reject_parser_artifact(
        db_session, draft["id"], "代码质量不达标", "admin"
    )
    assert rejected["status"] == "retired"
    assert rejected["sample_check_log"]["__rejection"]["reason"] == "代码质量不达标"


def test_approve_nonexistent_parser_fails(db_session):
    with pytest.raises(ValueError, match="不存在"):
        artifact_service.approve_parser_artifact(db_session, 99999, "admin")


def test_approve_non_draft_parser_fails(db_session):
    data = ParserArtifactDraftCreate(
        name="TestParser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# test",
        primitives_imports=[],
        sample_check_log={},
    )
    draft = artifact_service.create_parser_draft(db_session, data)
    artifact_service.approve_parser_artifact(db_session, draft["id"], "admin")
    with pytest.raises(ValueError, match="只有 draft 可审批"):
        artifact_service.approve_parser_artifact(db_session, draft["id"], "admin")


def test_approve_parser_retires_previous_active(db_session):
    data_old = ParserArtifactDraftCreate(
        name="ICBC_Parser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# old",
        primitives_imports=[],
        sample_check_log={},
    )
    old_parser = artifact_service.create_parser_draft(db_session, data_old)
    artifact_service.approve_parser_artifact(db_session, old_parser["id"], "admin")

    data_current = ParserArtifactDraftCreate(
        name="ICBC_Parser",
        kind=ArtifactKind.bank,
        account_code="A001",
        code="# current",
        primitives_imports=[],
        sample_check_log={},
    )
    current_parser = artifact_service.create_parser_draft(db_session, data_current)
    assert current_parser["version"] == 2
    approved_current = artifact_service.approve_parser_artifact(db_session, current_parser["id"], "admin")
    assert approved_current["status"] == "active"

    old_row = db_session.query(ParserArtifact).filter(ParserArtifact.id == old_parser["id"]).first()
    assert old_row.status == "retired"


# ── RuleArtifact lifecycle ──

def test_create_rule_draft(db_session):
    data = RuleArtifactDraftCreate(
        name="TestRule",
        placeholder_bindings={"报表标题": "ICBC 日报"},
        primitives_imports=["fund.primitives.template_fill"],
    )
    result = artifact_service.create_rule_draft(db_session, data)
    assert result["status"] == "draft"
    assert result["version"] == 1


def test_approve_rule_draft(db_session):
    data = RuleArtifactDraftCreate(
        name="TestRule",
        placeholder_bindings={},
        primitives_imports=[],
    )
    draft = artifact_service.create_rule_draft(db_session, data)
    approved = artifact_service.approve_rule_artifact(db_session, draft["id"], "admin")
    assert approved["status"] == "active"
    assert approved["approved_by"] == "admin"


def test_reject_rule_draft(db_session):
    data = RuleArtifactDraftCreate(
        name="TestRule",
        placeholder_bindings={},
        primitives_imports=[],
    )
    draft = artifact_service.create_rule_draft(db_session, data)
    rejected = artifact_service.reject_rule_artifact(
        db_session, draft["id"], "绑定不完整", "admin"
    )
    assert rejected["status"] == "retired"
    assert rejected["sample_check_log"]["__rejection"]["reason"] == "绑定不完整"


def test_get_nonexistent_rule_returns_none(db_session):
    result = artifact_service.get_rule_artifact(db_session, 99999)
    assert result is None


# ── List filters ──

def test_list_parsers_filter_by_kind(db_session):
    bank_data = ParserArtifactDraftCreate(
        name="BankParser", kind=ArtifactKind.bank, account_code="A001",
        code="#", primitives_imports=[],
    )
    manual_data = ParserArtifactDraftCreate(
        name="ManualParser", kind=ArtifactKind.manual, account_code="A001",
        code="#", primitives_imports=[],
    )
    artifact_service.create_parser_draft(db_session, bank_data)
    artifact_service.create_parser_draft(db_session, manual_data)

    bank_only = artifact_service.list_parser_artifacts(db_session, kind="bank")
    assert len(bank_only) == 1
    assert bank_only[0]["kind"] == "bank"


# ── bank/format 元数据 ──

def test_create_parser_draft_with_bank_format(db_session):
    data = ParserArtifactDraftCreate(
        name="BOC_Standard",
        kind=ArtifactKind.bank,
        account_code=None,
        bank_id=1,
        format_key="fp_abc123",
        match_rules={"header_match": "exact"},
        code="# parser",
        primitives_imports=[],
    )
    result = artifact_service.create_parser_draft(db_session, data)
    assert result["bank_id"] == 1
    assert result["format_key"] == "fp_abc123"
    assert result["match_rules"] == {"header_match": "exact"}
    assert result["account_code"] is None


def test_approve_parser_retires_same_bank_format(db_session):
    d1 = ParserArtifactDraftCreate(
        name="BOC_Std", kind=ArtifactKind.bank,
        bank_id=1, format_key="fp_x",
        code="# old", primitives_imports=[],
    )
    old_parser = artifact_service.create_parser_draft(db_session, d1)
    artifact_service.approve_parser_artifact(db_session, old_parser["id"], "admin")

    d2 = ParserArtifactDraftCreate(
        name="BOC_Std", kind=ArtifactKind.bank,
        bank_id=1, format_key="fp_x",
        code="# current", primitives_imports=[],
    )
    current_parser = artifact_service.create_parser_draft(db_session, d2)
    artifact_service.approve_parser_artifact(db_session, current_parser["id"], "admin")

    old_row = db_session.query(ParserArtifact).filter(ParserArtifact.id == old_parser["id"]).first()
    assert old_row.status == "retired"


def test_approve_parser_different_bank_format_not_retired(db_session):
    d1 = ParserArtifactDraftCreate(
        name="BOC_Std", kind=ArtifactKind.bank,
        bank_id=1, format_key="fp_x",
        code="# boc", primitives_imports=[],
    )
    old_parser = artifact_service.create_parser_draft(db_session, d1)
    artifact_service.approve_parser_artifact(db_session, old_parser["id"], "admin")

    d2 = ParserArtifactDraftCreate(
        name="ICBC_Std", kind=ArtifactKind.bank,
        bank_id=2, format_key="fp_x",
        code="# icbc", primitives_imports=[],
    )
    current_parser = artifact_service.create_parser_draft(db_session, d2)
    artifact_service.approve_parser_artifact(db_session, current_parser["id"], "admin")

    old_row = db_session.query(ParserArtifact).filter(ParserArtifact.id == old_parser["id"]).first()
    assert old_row.status == "active"  # different bank_id, not retired
