"""pytest 配置 · tests/fund/

与 tests/db/conftest.py 同策略：
  - 把 backend/ 挂到 sys.path
  - 故意不放 __init__.py 防止 pytest 把 tests/fund/ 注册为顶层包 `fund`，
    否则会 shadow 掉 backend/fund/
  - 提供 `primitives_db` session 级 fixture：
      1. 在 tmp dir 创建干净 sqlite
      2. rebind database.engine / SessionLocal
      3. rebind 已 import 的 primitives 模块里的 SessionLocal 变量引用
      4. 先 Base.metadata.create_all（建 v2 辅助表）
      5. DROP v3 表 → alembic upgrade head（获得 server_default + CHECK 的真 DDL）
      6. 播种 divisions / entities / accounts / batch 等父行
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

os.environ.setdefault("ZF_SECRET_KEY", "test-p0t3-secret-do-not-use-in-prod")

# ── fixture 延迟 import，避免顶层解析 database 时就绑定旧 DB_PATH ──
import pytest  # noqa: E402


@pytest.fixture(scope="session")
def tmp_db_path(tmp_path_factory):
    """整场会话共享的 tmp DB 路径。"""
    d = tmp_path_factory.mktemp("zf_primitives_db")
    return d / "zf.db"


@pytest.fixture(scope="session")
def primitives_db(tmp_db_path):
    """建 schema、rebind SessionLocal、播种父行。"""
    from sqlalchemy import create_engine, event, text
    from sqlalchemy.orm import sessionmaker

    db_url = f"sqlite:///{tmp_db_path}"

    import config as _cfg
    _cfg.DB_PATH = str(tmp_db_path)

    new_engine = create_engine(
        db_url,
        echo=False,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(new_engine, "connect")
    def _pragma(dbapi_connection, _):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    new_sess = sessionmaker(
        autocommit=False, autoflush=False, bind=new_engine
    )

    # 1) rebind database 模块全局
    import database as _db
    _db.engine = new_engine
    _db.SessionLocal = new_sess

    # 2) rebind 已 import 的 primitives 模块里的变量引用
    from fund.primitives import master_match as _mm
    from fund.primitives import base_queries as _bq
    from fund.primitives import aggregations as _ag
    _mm.SessionLocal = new_sess
    _bq.SessionLocal = new_sess
    _ag.SessionLocal = new_sess

    from agents.fund.skills import _shared as _skill_shared
    from agents.fund.skills import rule_maintain as _rule_maintain
    from agents.fund.skills import template_inference as _template_inference
    _skill_shared.SessionLocal = new_sess
    _rule_maintain.SessionLocal = new_sess
    _template_inference.SessionLocal = new_sess

    # 3) 建 v2 辅助表（create_all）
    from database import Base  # noqa: F401
    import db.tables  # noqa: F401
    Base.metadata.create_all(new_engine)

    # 4) DROP v3，走 alembic 取得 CHECK + server_default
    v3_tables = [
        "template_inference_job",
        "rule_artifacts",
        "parser_artifacts",
        "fund_events",
    ]
    with new_engine.begin() as conn:
        for t in v3_tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {t}"))

    from alembic import command
    from alembic.config import Config as AlembicConfig

    cfg = AlembicConfig(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")

    # 5) 播种父行（用 ORM；created_at/updated_at 等 Python 级默认值会自动填）
    from datetime import date
    from db.tables import Account, Division, Entity, ImportBatch
    with new_sess() as s:
        div1 = Division(division_code="D1", name="总部板块", status="enabled")
        div2 = Division(division_code="D2", name="南方板块", status="enabled")
        s.add_all([div1, div2])
        s.flush()

        ent1 = Entity(
            division_id=div1.id, entity_code="E001",
            name="示例科技有限公司", short_name="示例", status="enabled",
        )
        ent2 = Entity(
            division_id=div2.id, entity_code="E002",
            name="示例贸易有限公司", short_name="示贸", status="enabled",
        )
        s.add_all([ent1, ent2])
        s.flush()

        today = date(2026, 4, 1)
        accounts_seed = [
            ("A001", "工行主户", ent1.id, 100000, "1234"),
            ("A002", "建行副户", ent1.id, 50000, "5678"),
            ("A003", "招行户", ent2.id, 20000, "9012"),
        ]
        for (code, alias, ent_id, balance, last4) in accounts_seed:
            s.add(Account(
                entity_id=ent_id,
                account_code=code,
                account_alias=alias,
                account_type="结算户",
                instrument_type="网银",
                input_method="online_bank",
                currency="CNY",
                initial_balance=balance,
                balance_date=today,
                status="enabled",
                bank_name="工商银行",
                account_last_four=last4,
                has_online_banking=True,
                include_in_daily_report=True,
                allow_manual_entry=True,
            ))

        s.add(ImportBatch(batch_code="B001", source_type="bank_import", status="uploaded"))
        s.commit()

    yield new_engine
    new_engine.dispose()


@pytest.fixture
def seed_events(primitives_db):
    """每个测试函数级：清空 fund_events 再插干净事件；返回 helper 函数。"""
    from sqlalchemy import text

    engine = primitives_db
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM fund_events"))

    def _insert(
        account_code: str,
        business_date,
        amount_in,
        amount_out,
        *,
        entity_code: str = "E001",
        entity_name: str = "示例科技有限公司",
        account_name: str = "工行主户",
        state: str = "正常",
        source: str = "网银导入",
        summary: str = "",
        counterparty: str = "",
        rolling_balance=None,
    ):
        with engine.begin() as conn:
            sql = (
                "INSERT INTO fund_events ("
                "business_date, entity_code, entity_name, account_code, account_name, "
                "summary, counterparty, amount_in, amount_out, rolling_balance, state, source) "
                "VALUES (:business_date, :entity_code, :entity_name, :account_code, :account_name, "
                ":summary, :counterparty, :amount_in, :amount_out, :rolling_balance, :state, :source)"
            )
            conn.execute(
                text(sql),
                dict(
                    business_date=business_date,
                    entity_code=entity_code,
                    entity_name=entity_name,
                    account_code=account_code,
                    account_name=account_name,
                    summary=summary,
                    counterparty=counterparty,
                    amount_in=float(amount_in),
                    amount_out=float(amount_out),
                    rolling_balance=float(rolling_balance) if rolling_balance is not None else None,
                    state=state,
                    source=source,
                ),
            )

    return _insert
