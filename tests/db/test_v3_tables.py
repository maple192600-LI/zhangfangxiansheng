"""P0-T2 · v3 新表 DDL + CHECK 约束测试

覆盖：
    - fund_events §C1 12 列存在且 CANONICAL_12 按契约序
    - fund_events 4 条 CHECK：amount_mutex / state_enum / source_enum / amount_nonneg
    - parser_artifacts CHECK：kind 枚举 / status 枚举 / (name, version) 唯一
    - rule_artifacts  CHECK：status 枚举
    - template_inference_job CHECK：status 枚举
    - alembic 迁移链 001→002→003→004 可 upgrade head 且无报错

契约锚点：
    docs/30_contracts/20_database_schema.md §T2.1 / §T3.1-§T3.3
    docs/00_governance/00_project_constitution.md §C1

注：本测试在临时 SQLite 文件上运行，使用 alembic 迁移链搭建 schema。
    不污染 backend/data/zhangfang.db。
"""
from __future__ import annotations

import os
import sys
import subprocess
import tempfile
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, text
from sqlalchemy.exc import IntegrityError

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


# ─────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def tmp_db_path():
    """临时 SQLite 文件，session 作用域。"""
    with tempfile.TemporaryDirectory() as tmp:
        yield Path(tmp) / "test_v3.db"


@pytest.fixture(scope="module")
def migrated_engine(tmp_db_path):
    """通过 alembic upgrade head + Base.metadata.create_all 混合建表。

    策略：
        1. 先用 Base.metadata.create_all() 建出 v2 辅助表（entities / accounts / import_batches
           / report_templates 等 alembic 未覆盖的），否则迁移 001 的 FK 引用 entities 会爆炸。
        2. 再让 alembic 跑 4 个 v3 迁移，真正落 fund_events / parser_artifacts /
           rule_artifacts / template_inference_job 的契约级 DDL（含 server_default / CHECK）。

    好处：raw SQL INSERT 不写 status 也能落 draft 默认值；CHECK 约束与契约严格一致。
    """
    import config as _cfg
    from database import Base
    import db.tables  # noqa: F401  · 触发注册

    # 1) 把 config.DB_PATH 指到本次 tmp_db_path，alembic env.py 会据此组装 URL
    _cfg.DB_PATH = str(tmp_db_path)
    url = f"sqlite:///{tmp_db_path}"

    engine = create_engine(url)

    @event.listens_for(engine, "connect")
    def _enable_fk(dbapi_connection, connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    # 2) 先建所有 ORM 表（含 v2 遗留辅助表 + v3 新表）。随后 alembic 遇到 existing table
    #    会用 batch_alter_table 重建成契约级 DDL。
    Base.metadata.create_all(engine)

    # 3) 用 alembic 重建 4 张 v3 表，以拿到 server_default 与 CHECK
    # 由于 create_all 已经创建了这些表，我们先 drop 再跑迁移
    v3_tables = [
        "template_inference_job",
        "rule_artifacts",
        "parser_artifacts",
        "fund_events",
    ]
    with engine.begin() as conn:
        for t in v3_tables:
            conn.execute(text(f"DROP TABLE IF EXISTS {t}"))

    from alembic.config import Config
    from alembic import command

    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")

    # 4) 种子父表行：为 fund_events / rule_artifacts 提供合法的 FK 目标
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO divisions (name, status, created_at, updated_at) "
                "VALUES ('D1', 'enabled', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        conn.execute(
            text(
                "INSERT INTO entities (entity_code, name, short_name, status, created_at, updated_at) "
                "VALUES ('E001', 'E名称', 'E', 'enabled', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        eid = conn.execute(text("SELECT id FROM entities WHERE entity_code='E001'")).scalar()
        conn.execute(
            text(
                "INSERT INTO accounts ("
                "entity_id, account_code, account_alias, account_type, instrument_type, "
                "input_method, has_online_banking, include_in_daily_report, allow_manual_entry, "
                "currency, initial_balance, balance_date, status, created_at, updated_at"
                ") VALUES ("
                ":eid, 'A001', 'A别名', '基本户', '银行存款', 'manual', 0, 1, 1, "
                "'CNY', 0, '2026-01-01', 'enabled', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP"
                ")"
            ),
            dict(eid=eid),
        )

    yield engine
    engine.dispose()


# ─────────────────────────────────────────────────────
# §C1 · fund_events CANONICAL_12 列序
# ─────────────────────────────────────────────────────


def test_fund_events_has_canonical_12_columns(migrated_engine):
    with migrated_engine.connect() as conn:
        rows = conn.execute(text("PRAGMA table_info('fund_events')")).fetchall()
    names = [r[1] for r in rows]

    canonical = [
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
        "state",
        "source",
    ]
    # CANONICAL_12 必须以契约序作为连续子序列出现
    assert any(
        names[i : i + 12] == canonical for i in range(len(names) - 11)
    ), f"CANONICAL_12 未连续出现。实际列序: {names}"


# ─────────────────────────────────────────────────────
# §C1 · fund_events CHECK 约束
# ─────────────────────────────────────────────────────


def _insert_fund_event(
    conn, *, amount_in="0", amount_out="0", state="正常", source="手工录入"
):
    """构造合法/故意违规的插入语句（直接 SQL，绕过 ORM 默认值）。"""
    return conn.execute(
        text(
            "INSERT INTO fund_events "
            "(business_date, entity_code, entity_name, account_code, account_name, "
            " summary, counterparty, amount_in, amount_out, rolling_balance, state, source) "
            "VALUES "
            "(:d, 'E001', 'E名称', 'A001', 'A名称', '摘要', '对方', "
            " :ai, :ao, NULL, :st, :src)"
        ),
        dict(d="2026-04-01", ai=amount_in, ao=amount_out, st=state, src=source),
    )


def test_fund_events_amount_mutex_rejects_both_positive(migrated_engine):
    """§C1 CHECK: amount_in>0 AND amount_out>0 应被拒绝。"""
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError) as exc:
            _insert_fund_event(conn, amount_in="10", amount_out="10")
        assert "amount_mutex" in str(exc.value).lower() or "check" in str(exc.value).lower()


def test_fund_events_amount_nonneg_rejects_negative(migrated_engine):
    """§C1 CHECK: amount_in < 0 应被拒绝。"""
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            _insert_fund_event(conn, amount_in="-1", amount_out="0")


def test_fund_events_state_enum_rejects_invalid(migrated_engine):
    """§C1 CHECK: state='随便' 应被拒绝。"""
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            _insert_fund_event(conn, state="随便")


def test_fund_events_source_enum_rejects_invalid(migrated_engine):
    """§C1 CHECK: source='非契约值' 应被拒绝。"""
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            _insert_fund_event(conn, source="未知来源")


def test_fund_events_legal_insert_succeeds(migrated_engine):
    """合法插入：amount_in=10, amount_out=0, state='正常', source='手工录入'。"""
    with migrated_engine.begin() as conn:
        result = _insert_fund_event(
            conn, amount_in="10", amount_out="0", state="正常", source="手工录入"
        )
        assert result.rowcount == 1


# ─────────────────────────────────────────────────────
# §T3.1 · parser_artifacts
# ─────────────────────────────────────────────────────


def test_parser_artifacts_kind_enum(migrated_engine):
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO parser_artifacts (name, kind, version, code, primitives_imports) "
                    "VALUES ('X', 'invalid_kind', 1, 'pass', '[]')"
                )
            )


def test_parser_artifacts_status_enum(migrated_engine):
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO parser_artifacts (name, kind, version, code, primitives_imports, status) "
                    "VALUES ('X', 'bank', 1, 'pass', '[]', 'weird')"
                )
            )


def test_parser_artifacts_unique_name_version(migrated_engine):
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO parser_artifacts (name, kind, version, code, primitives_imports) "
                "VALUES ('ICBC_v1', 'bank', 1, 'pass', '[]')"
            )
        )
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO parser_artifacts (name, kind, version, code, primitives_imports) "
                    "VALUES ('ICBC_v1', 'bank', 1, 'pass', '[]')"
                )
            )


# ─────────────────────────────────────────────────────
# §T3.2 · rule_artifacts
# ─────────────────────────────────────────────────────


def test_rule_artifacts_status_enum(migrated_engine):
    # 先建一个 report_templates 以满足 FK（v2 ORM 的 is_default/status 为 NOT NULL，
    # ORM-level default 不会转成 SQL server_default，raw INSERT 需显式给值）
    with migrated_engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO report_templates "
                "(template_code, template_name, report_type, columns_json, is_default, status, created_by, created_at, updated_at) "
                "VALUES ('T1', '模板1', 'daily', '[]', 0, 'active', 'admin', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )
        tid = conn.execute(text("SELECT id FROM report_templates WHERE template_code='T1'")).scalar()

    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO rule_artifacts "
                    "(name, template_id, version, placeholder_bindings, loop_spec, primitives_imports, status) "
                    "VALUES ('R1', :t, 1, '{}', '{}', '[]', 'weird')"
                ),
                dict(t=tid),
            )


# ─────────────────────────────────────────────────────
# §T3.3 · template_inference_job
# ─────────────────────────────────────────────────────


def test_template_inference_job_status_enum(migrated_engine):
    with migrated_engine.begin() as conn:
        with pytest.raises(IntegrityError):
            conn.execute(
                text(
                    "INSERT INTO template_inference_job (original_filename, file_path, status) "
                    "VALUES ('a.xlsx', '/tmp/a.xlsx', 'weird')"
                )
            )


# ─────────────────────────────────────────────────────
# Alembic 迁移链：独立验证 `alembic upgrade head`
# ─────────────────────────────────────────────────────


def test_alembic_upgrade_head_on_clean_db(tmp_path):
    """独立跑 alembic upgrade head，确认 4 个迁移按序建表成功。"""
    db_file = tmp_path / "alembic_test.db"

    env = os.environ.copy()
    # 通过覆盖 config.DB_PATH 导入路径：env.py 从 config.DB_PATH 读 URL
    # 简单做法：复制 config.py 模式，直接 monkey-patch 环境
    env["ZF_DB_PATH_OVERRIDE"] = str(db_file)
    env["PYTHONIOENCODING"] = "utf-8"

    # 我们通过 python -c 的方式直接调用 alembic 命令（Python API 更稳健于 Windows）
    script = (
        "import sys, pathlib; "
        f"sys.path.insert(0, r'{BACKEND_DIR}'); "
        "import config; "
        f"config.DB_PATH = r'{db_file}'; "
        "from alembic.config import Config; "
        "from alembic import command; "
        f"cfg = Config(r'{REPO_ROOT / 'alembic.ini'}'); "
        f"cfg.set_main_option('script_location', r'{REPO_ROOT / 'alembic'}'); "
        "command.upgrade(cfg, 'head'); "
        "print('ALEMBIC_OK')"
    )

    result = subprocess.run(
        [sys.executable, "-c", script],
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    assert "ALEMBIC_OK" in (result.stdout or ""), (
        f"alembic upgrade head 失败\nstdout={result.stdout}\nstderr={result.stderr}"
    )

    # 验证 4 张新表都在
    engine = create_engine(f"sqlite:///{db_file}")
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        ).fetchall()
    table_names = {r[0] for r in rows}
    for required in ("fund_events", "parser_artifacts", "rule_artifacts", "template_inference_job"):
        assert required in table_names, f"迁移未创建 {required}；已存在 {table_names}"
    engine.dispose()
