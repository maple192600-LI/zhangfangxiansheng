"""Alembic 运行环境 · 账房先生 current baseline

- 从 backend/config.py 读 DB_PATH
- 从 backend/db/tables.py 读 metadata（用于 autogenerate 对照）
- 启用 SQLite 的 render_as_batch，避免 DDL 变更时重建表失败

契约锚点：
    docs/00_governance/00_project_constitution.md §C1 / §C6
    docs/30_contracts/20_database_schema.md
"""
from __future__ import annotations

import sys
from logging.config import fileConfig
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine, pool

# 把 backend/ 挂到 sys.path（alembic.ini 的 prepend_sys_path 在某些运行方式下不生效）
REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from config import DB_PATH  # noqa: E402  · after sys.path
from database import Base  # noqa: E402
import db.tables  # noqa: E402,F401  · 触发 ORM 类注册到 Base.metadata

config = context.config

# 日志
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# 运行期覆盖 sqlalchemy.url —— 不在 alembic.ini 里写死绝对路径
RUNTIME_URL = f"sqlite:///{DB_PATH}"
config.set_main_option("sqlalchemy.url", RUNTIME_URL)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """离线模式：生成 SQL 但不连接 DB。"""
    context.configure(
        url=RUNTIME_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """在线模式：打开 DB 连接，逐步执行迁移。"""
    connectable = create_engine(
        RUNTIME_URL,
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            render_as_batch=True,  # SQLite 友好：DDL 变更走 batch table recreate
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
