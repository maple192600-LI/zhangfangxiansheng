"""账房先生 V1 — FastAPI 入口

启动方式：
  Windows: 双击 start.bat 或 venv\Scripts\python.exe main.py
  Linux/Mac: venv/bin/python main.py
"""
import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # noqa: F401 — kept for potential future use
from fastapi.responses import FileResponse

# 确保项目根目录在 sys.path 中
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BACKEND_DIR)
sys.path.insert(0, BACKEND_DIR)
sys.path.insert(0, PROJECT_ROOT)

from config import HOST, PORT, FRONTEND_DIST
from db import tables as _  # noqa: F401 — 注册 ORM 模型到 Base.metadata
from api.health import router as health_router
from api.master_data import router as master_router
from api.ai_config import router as ai_router
from api.agent_config import router as agent_config_router
from api.bank_import import router as bank_import_router
from api.parser_template import router as parser_template_router
from api.manual_flow import router as manual_flow_router
from api.base_data import router as base_data_router
from api.reports import router as reports_router
from api.home import router as home_router
from api.dashboard import router as dashboard_router
from api.export import router as export_router
from api.backup import router as backup_router
from api.batch import router as batch_router
from api.logs import router as logs_router
from api.auth import router as auth_router
from api.reset import router as reset_router
from api.bank_master import router as bank_master_router
from api.report_template import router as report_template_router
from api.events import router as events_router
from api.agent import router as agent_router


def _init_db():
    """初始化数据库结构和最小系统数据。"""
    _run_alembic_upgrade()
    _patch_schema()
    _ensure_default_user()
    _register_global_skills()


def _patch_schema():
    """增量补齐尚未通过 alembic 迁移的列（无害幂等）。"""
    from sqlalchemy import text as _t
    from database import engine

    _SCHEMA_PATCHES = [
        ("ALTER TABLE report_templates ADD COLUMN source_file_path VARCHAR(500)",
         "report_templates.source_file_path"),
        ("ALTER TABLE agents_v2 ADD COLUMN llm_timeout INTEGER NOT NULL DEFAULT 300",
         "agents_v2.llm_timeout"),
        ("ALTER TABLE agents_v2 ADD COLUMN llm_max_tokens INTEGER NOT NULL DEFAULT 4096",
         "agents_v2.llm_max_tokens"),
        ("ALTER TABLE agent_messages ADD COLUMN reasoning_content TEXT",
         "agent_messages.reasoning_content"),
        ("ALTER TABLE parser_templates ADD COLUMN account_code VARCHAR(30)",
         "parser_templates.account_code"),
    ]

    with engine.connect() as conn:
        for sql, col_name in _SCHEMA_PATCHES:
            try:
                conn.execute(_t(sql))
                conn.commit()
                print(f"[schema] 已补齐 {col_name}")
            except Exception as e:
                err = str(e).lower()
                if "duplicate column" in err or "already exists" in err:
                    pass
                else:
                    print(f"[schema] 补齐 {col_name} 失败: {e}")


def _run_alembic_upgrade():
    """运行 Alembic 迁移到 head。"""
    from alembic import command
    from alembic.config import Config

    cfg = Config(os.path.join(PROJECT_ROOT, "alembic.ini"))
    cfg.set_main_option("script_location", os.path.join(PROJECT_ROOT, "alembic"))
    command.upgrade(cfg, "head")


def _ensure_default_user():
    """确保默认 admin 用户存在"""
    from database import SessionLocal
    from services.auth_service import get_or_create_default_user
    with SessionLocal() as db:
        get_or_create_default_user(db)


_BROWSER_OPENED = False


def _open_browser(url: str):
    """服务启动后自动打开默认浏览器（仅首次启动，热重载不重复打开）"""
    global _BROWSER_OPENED
    import os
    import threading
    import webbrowser

    if os.environ.get("_BROWSER_OPENED") == "1" or _BROWSER_OPENED:
        return
    _BROWSER_OPENED = True
    os.environ["_BROWSER_OPENED"] = "1"

    def _do_open():
        import time
        time.sleep(1.5)
        webbrowser.open(url)

    threading.Thread(target=_do_open, daemon=True).start()


def _register_global_skills():
    """注册全局系统技能（owner_agent_id=None）"""
    import json
    import os
    from datetime import datetime
    from database import SessionLocal
    from db.tables import Skill
    from agents.skill_loader import load_manifest

    system_skills_dir = os.path.join(
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "agents", "system", "skills")
    )
    if not os.path.isdir(system_skills_dir):
        return

    db = SessionLocal()
    try:
        for skill_dir_name in os.listdir(system_skills_dir):
            skill_path = os.path.join(system_skills_dir, skill_dir_name)
            if not os.path.isdir(skill_path):
                continue

            manifest = load_manifest(skill_path)
            if not manifest:
                continue

            skill_code = manifest.get("skill_code", skill_dir_name)
            existing = db.query(Skill).filter(Skill.skill_code == skill_code).first()
            if existing:
                # 更新
                existing.display_name = manifest.get("display_name", skill_code)
                existing.description = manifest.get("description", "")
                existing.manifest_json = json.dumps(manifest, ensure_ascii=False)
                existing.source_path = skill_path
                existing.status = "verified"
                existing.updated_at = datetime.now()
            else:
                row = Skill(
                    skill_code=skill_code,
                    display_name=manifest.get("display_name", skill_code),
                    description=manifest.get("description", ""),
                    owner_agent_id=None,  # 全局
                    manifest_json=json.dumps(manifest, ensure_ascii=False),
                    source_path=skill_path,
                    status="verified",
                    created_at=datetime.now(),
                    updated_at=datetime.now(),
                )
                db.add(row)
        db.commit()
    except Exception as e:
        print(f"[skills] 全局技能注册失败: {e}")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理"""
    _init_db()
    from services.agent_init import init_agent_workspaces
    init_agent_workspaces()
    print(f"账房先生已启动 → http://{HOST}:{PORT}")
    _open_browser(f"http://{HOST}:{PORT}")
    yield


# ── 创建 FastAPI 实例 ──
app = FastAPI(title="账房先生", version="1.0.0", docs_url=None, redoc_url=None, lifespan=lifespan)


import logging as _logging
from fastapi.responses import JSONResponse as _JSONResponse

_logger = _logging.getLogger(__name__)


@app.exception_handler(Exception)
async def _global_exception_handler(request: Request, exc: Exception):
    import traceback
    traceback.print_exc()
    _logger.error("未捕获异常 %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return _JSONResponse(
        status_code=500,
        content={"code": 5000, "message": "服务内部错误，请查看操作日志", "data": None},
    )

# ── CORS（本地部署 + 开发用）──
_CORS_ORIGINS = os.environ.get(
    "ZF_CORS_ORIGINS",
    "http://localhost:5180,http://127.0.0.1:5180,http://localhost:8000",
).split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
app.include_router(health_router, prefix="/api")
app.include_router(master_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(agent_config_router, prefix="/api")
app.include_router(bank_import_router, prefix="/api")
app.include_router(parser_template_router, prefix="/api")
app.include_router(manual_flow_router, prefix="/api")
app.include_router(base_data_router, prefix="/api")
app.include_router(reports_router, prefix="/api")
app.include_router(home_router, prefix="/api")
app.include_router(dashboard_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(backup_router, prefix="/api")
app.include_router(batch_router, prefix="/api")
app.include_router(logs_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(reset_router, prefix="/api")
app.include_router(bank_master_router, prefix="/api")
app.include_router(report_template_router, prefix="/api")
app.include_router(events_router, prefix="/api")
app.include_router(agent_router, prefix="/api")


# ── SPA 路由兜底：非 /api 且非静态资源的路径，一律返回 index.html ──
frontend_dist = os.path.abspath(FRONTEND_DIST)
if os.path.isdir(frontend_dist):
    _dist_assets = os.path.join(frontend_dist, "assets")

    @app.middleware("http")
    async def spa_fallback(request: Request, call_next):
        path = request.url.path
        # /api 路径直接放行给路由层
        if path.startswith("/api"):
            return await call_next(request)
        # 静态资源（有扩展名且文件存在）直接返回文件 + 禁缓存
        if "." in os.path.basename(path):
            file_path = os.path.join(frontend_dist, path.lstrip("/"))
            if os.path.isfile(file_path):
                return FileResponse(file_path,
                                    headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        # 其余所有路径（/ /bank-import /account-manage 等）返回 index.html
        index_html = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_html):
            return FileResponse(index_html, media_type="text/html",
                                headers={"Cache-Control": "no-cache, no-store, must-revalidate"})
        return await call_next(request)

    # ── 认证中间件（在 spa_fallback 之后注册，先于 spa 执行） ──
    from core.auth_middleware import auth_middleware
    app.middleware("http")(auth_middleware)


if __name__ == "__main__":
    _base = os.path.dirname(os.path.abspath(__file__))
    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        reload=True,
        reload_dirs=[_base],
        reload_includes=["*.py"],
        reload_excludes=["data/**", "exports/**", "backups/**"],
    )
