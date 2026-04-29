import json
import sys
from pathlib import Path

from sqlalchemy import create_engine, text

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from scripts.cleanup_v3_residue import cleanup_v3_residue


def _make_engine(tmp_path):
    db_path = tmp_path / "cleanup.db"
    return create_engine(f"sqlite:///{db_path}")


def test_cleanup_drops_v3_residue_tables_and_writes_log(tmp_path):
    engine = _make_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(text("PRAGMA foreign_keys=ON"))
        conn.execute(text("CREATE TABLE parser_artifacts (id INTEGER PRIMARY KEY)"))
        conn.execute(text(
            "CREATE TABLE rule_artifacts ("
            "id INTEGER PRIMARY KEY, "
            "parser_id INTEGER REFERENCES parser_artifacts(id))"
        ))
        conn.execute(text(
            "CREATE TABLE template_inference_job ("
            "id INTEGER PRIMARY KEY, "
            "rule_draft_id INTEGER REFERENCES rule_artifacts(id))"
        ))
        conn.execute(text("INSERT INTO parser_artifacts (id) VALUES (1)"))
        conn.execute(text("INSERT INTO rule_artifacts (id, parser_id) VALUES (1, 1)"))
        conn.execute(text(
            "INSERT INTO template_inference_job (id, rule_draft_id) VALUES (1, 1)"
        ))
        conn.execute(text(
            "CREATE TABLE operation_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "action VARCHAR(50) NOT NULL, "
            "module VARCHAR(50) NOT NULL, "
            "batch_id INTEGER, "
            "detail_json TEXT NOT NULL, "
            "created_at DATETIME NOT NULL)"
        ))

    dropped = cleanup_v3_residue(engine)

    assert dropped == ["parser_artifacts", "rule_artifacts", "template_inference_job"]
    with engine.connect() as conn:
        remaining = conn.execute(text(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name IN "
            "('parser_artifacts','rule_artifacts','template_inference_job')"
        )).fetchall()
        log = conn.execute(text(
            "SELECT action, module, detail_json FROM operation_logs"
        )).one()

    assert remaining == []
    assert log.action == "cleanup_v3_residue"
    assert log.module == "database"
    assert json.loads(log.detail_json) == {
        "dropped_tables": ["parser_artifacts", "rule_artifacts", "template_inference_job"]
    }


def test_cleanup_is_noop_when_residue_tables_absent(tmp_path):
    engine = _make_engine(tmp_path)
    with engine.begin() as conn:
        conn.execute(text(
            "CREATE TABLE operation_logs ("
            "id INTEGER PRIMARY KEY AUTOINCREMENT, "
            "action VARCHAR(50) NOT NULL, "
            "module VARCHAR(50) NOT NULL, "
            "batch_id INTEGER, "
            "detail_json TEXT NOT NULL, "
            "created_at DATETIME NOT NULL)"
        ))

    dropped = cleanup_v3_residue(engine)

    assert dropped == []
    with engine.connect() as conn:
        log_count = conn.execute(text("SELECT COUNT(*) FROM operation_logs")).scalar_one()
    assert log_count == 0
