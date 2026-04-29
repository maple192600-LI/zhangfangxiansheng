"""pytest 配置 · tests/db

把 backend/ 挂到 sys.path，使得：
    from database import Base
    from db.tables import ...
可以正确解析到 `backend/db/tables.py`，而不是被 pytest 的 test-root 收集路径 shadow。

注意：tests/db/ 下故意不放 __init__.py —— 有它时 pytest 会把 `tests/db/` 注册为顶层包 `db`，
从而把 `import db.tables` 劫持到测试目录，导致 ModuleNotFoundError。
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

# 让 config.py 在 warning 前找到一个确定的 SECRET_KEY，避免 UserWarning 污染 stderr
os.environ.setdefault("ZF_SECRET_KEY", "test-p0t2-secret-do-not-use-in-prod")
