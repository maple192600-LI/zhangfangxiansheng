"""Drop v3 residue tables from the current v2 runtime database."""
import json
import os
import sys
from datetime import datetime
from typing import Iterable

from sqlalchemy import Engine, create_engine, text

RESIDUE_TABLES = ("parser_artifacts", "rule_artifacts", "template_inference_job")


def cleanup_v3_residue(engine: Engine, tables: Iterable[str] = RESIDUE_TABLES) -> list[str]:
    """Drop known v3 residue tables and write one operation log when anything changed."""
    table_names = list(tables)
    dropped: list[str] = []

    with engine.connect() as conn:
        conn.exec_driver_sql("PRAGMA foreign_keys=OFF")
        existing = {
            row[0]
            for row in conn.execute(text(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )).fetchall()
        }

        for table in table_names:
            if table not in existing:
                continue
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))
            dropped.append(table)

        if dropped and "operation_logs" in existing:
            conn.execute(text(
                "INSERT INTO operation_logs "
                "(action, module, batch_id, detail_json, created_at) "
                "VALUES (:action, :module, NULL, :detail_json, :created_at)"
            ), {
                "action": "cleanup_v3_residue",
                "module": "database",
                "detail_json": json.dumps({"dropped_tables": dropped}, ensure_ascii=False),
                "created_at": datetime.now(),
            })

        conn.commit()
        conn.exec_driver_sql("PRAGMA foreign_keys=ON")

    return dropped


def main() -> int:
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.join(project_root, "backend")
    sys.path.insert(0, backend_dir)

    from config import DB_PATH

    engine = create_engine(f"sqlite:///{DB_PATH}")
    dropped = cleanup_v3_residue(engine)
    print("dropped:", ", ".join(dropped) if dropped else "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
