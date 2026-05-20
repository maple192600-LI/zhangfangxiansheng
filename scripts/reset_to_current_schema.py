"""Reset the local SQLite database to the current AI-First schema.

One-shot local reset script:
- keep a dated backup of the current database;
- drop the current schema, including legacy fund_events columns;
- run Alembic to rebuild the current schema and stamp the head revision.
"""
from __future__ import annotations

import shutil
import sqlite3
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import DB_PATH  # noqa: E402

DB_FILE = Path(DB_PATH)
BACKUP_FILE = DB_FILE.with_name("zhangfang.db.bak.b_plan.20260425")


def backup_db() -> None:
    if not DB_FILE.exists():
        return
    if not BACKUP_FILE.exists():
        shutil.copy2(DB_FILE, BACKUP_FILE)


def drop_current_schema() -> None:
    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    try:
        conn.execute("PRAGMA foreign_keys=OFF")
        rows = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()
        for (name,) in rows:
            conn.execute(f'DROP TABLE IF EXISTS "{name}"')
        conn.commit()
    finally:
        conn.close()


def upgrade_to_head() -> None:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    command.upgrade(cfg, "head")


def main() -> int:
    backup_db()
    drop_current_schema()
    upgrade_to_head()
    print(f"[OK] SQLite 已重建到 current head: {DB_FILE}")
    print(f"[OK] 备份文件: {BACKUP_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
