from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

os.environ.setdefault("ZF_SECRET_KEY", "test-p8-secret-do-not-use-in-prod")


@pytest.fixture
def e2e_env(tmp_path, monkeypatch):
    db_path = tmp_path / "p8.db"
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    import config as _cfg
    _cfg.DB_PATH = str(db_path)
    _cfg.DATA_DIR = str(data_dir)

    engine = create_engine(
        f"sqlite:///{db_path}",
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    import database as _db
    _db.engine = engine
    _db.SessionLocal = SessionLocal

    from fund.primitives import aggregations as _ag
    from fund.primitives import base_queries as _bq
    from fund.primitives import master_match as _mm
    _ag.SessionLocal = SessionLocal
    _bq.SessionLocal = SessionLocal
    _mm.SessionLocal = SessionLocal

    from agents.fund.skills import _shared as _skill_shared
    from agents.fund.skills import rule_maintain as _rule_maintain
    from agents.fund.skills import template_inference as _template_inference
    _skill_shared.SessionLocal = SessionLocal
    _rule_maintain.SessionLocal = SessionLocal
    _template_inference.SessionLocal = SessionLocal

    from database import Base
    import db.tables  # noqa: F401
    Base.metadata.create_all(engine)

    with engine.begin() as conn:
        for table in ["template_inference_job", "rule_artifacts", "parser_artifacts", "fund_events"]:
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

    from alembic import command
    from alembic.config import Config
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")

    from services import bank_import_service, manual_flow_service
    from api import fund_agent, reports
    monkeypatch.setattr(bank_import_service, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(manual_flow_service, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(fund_agent, "DATA_DIR", str(data_dir))
    monkeypatch.setattr(reports, "DATA_DIR", str(data_dir))

    _seed_master_data(SessionLocal)
    yield {"engine": engine, "SessionLocal": SessionLocal, "data_dir": data_dir}
    engine.dispose()


def _seed_master_data(SessionLocal):
    from datetime import date
    from db.tables import AIConfig, Account, Bank, Division, Entity

    with SessionLocal() as db:
        div = Division(division_code="D1", name="总部板块", status="enabled")
        db.add(div)
        db.flush()
        ent = Entity(
            division_id=div.id,
            entity_code="E001",
            name="示例科技有限公司",
            short_name="示例科技",
            status="enabled",
        )
        db.add(ent)
        db.flush()
        bank = Bank(bank_code="ICBC", bank_name="工商银行", short_name="工行", status="enabled")
        db.add(bank)
        db.flush()
        db.add(Account(
            entity_id=ent.id,
            bank_id=bank.id,
            account_code="A001",
            account_alias="工行主账户",
            bank_name="工商银行",
            account_last_four="1234",
            account_type="结算户",
            instrument_type="网银",
            input_method="online_bank",
            has_online_banking=True,
            include_in_daily_report=True,
            allow_manual_entry=True,
            currency="CNY",
            initial_balance=100000,
            balance_date=date(2026, 4, 1),
            status="enabled",
        ))
        db.add(AIConfig(
            provider="fund",
            display_name="默认隐私配置",
            api_key_local="",
            model_name="harness",
            is_default=True,
            privacy_mode="standard",
            status="active",
        ))
        db.commit()


@pytest.fixture
def e2e_client(e2e_env):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from api.bank_import import router as bank_router
    from api.fund_agent import router as fund_router
    from api.manual_flow import router as manual_router
    from api.reports import router as reports_router
    from api.events import router as events_router
    from database import get_db

    app = FastAPI()
    app.include_router(bank_router, prefix="/api")
    app.include_router(manual_router, prefix="/api")
    app.include_router(fund_router, prefix="/api")
    app.include_router(reports_router, prefix="/api")
    app.include_router(events_router, prefix="/api")

    def override_db():
        with e2e_env["SessionLocal"]() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    return TestClient(app)
