"""账房先生 V1 — FastAPI 入口

启动方式：
  Windows: 双击 start.bat 或 venv\Scripts\python.exe main.py
  Linux/Mac: venv/bin/python main.py
"""
import os
import sys
import webbrowser
from contextlib import asynccontextmanager
from sqlalchemy import text as sql_text

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles  # noqa: F401 — kept for potential future use
from fastapi.responses import FileResponse, Response

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOST, PORT, FRONTEND_DIST, DATA_DIR
from database import engine, Base
from db import tables as _  # noqa: F401 — 注册 ORM 模型到 Base.metadata
from api.health import router as health_router
from api.master_data import router as master_router
from api.ai_config import router as ai_router
from api.agent_config import router as agent_router
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


def _init_db():
    """建表 + 种子数据"""
    from sqlalchemy import text, inspect

    Base.metadata.create_all(bind=engine)

    insp = inspect(engine)
    if not insp.get_table_names():
        return

    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM divisions"))
        if result.scalar() > 0:
            # 增量：补充手工字段池可选字段（如果只有7个核心字段）
            field_count = conn.execute(text("SELECT COUNT(*) FROM manual_field_pool")).scalar()
            if field_count <= 7:
                print("补充手工字段池可选字段...")
                _run_seed_increment(conn, DATA_DIR)
            return

        seed_path = os.path.join(DATA_DIR, "seed.sql")
        if not os.path.exists(seed_path):
            print("警告：未找到种子数据文件 data/seed.sql")
            return

        with open(seed_path, "r", encoding="utf-8") as f:
            seed_sql = f.read()

        lines = seed_sql.splitlines()
        clean_lines = [line for line in lines if not line.strip().startswith("--")]
        clean_sql = "\n".join(clean_lines)

        for stmt in clean_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt))
        conn.commit()
        print("种子数据已写入。")


def _run_seed_increment(conn, data_dir: str):
    """增量种子：追加手工字段池可选字段 + 附加方案"""
    from datetime import datetime
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    optional_fields = [
        (8, 'previous_balance_input', '上期余额', 'number', 0, 0, 1, 0, 1, 0),
        (9, 'ending_balance_input', '期末余额', 'number', 0, 0, 1, 0, 1, 0),
        (10, 'business_time', '业务时间', 'text', 0, 0, 1, 0, 0, 0),
        (11, 'group_name', '分组', 'text', 0, 0, 1, 0, 0, 0),
        (12, 'department_name', '所属部门', 'text', 0, 0, 1, 0, 0, 0),
        (13, 'income_expense_type', '收支类型', 'text', 0, 0, 1, 0, 0, 0),
        (14, 'handler_name', '经办人', 'text', 0, 0, 1, 0, 0, 0),
        (15, 'owner_name', '负责人', 'text', 0, 0, 1, 0, 0, 0),
        (16, 'note_text', '备注', 'text', 0, 1, 1, 0, 0, 0),
        (17, 'pending_recovery_flag', '待回补', 'bool', 0, 0, 1, 0, 0, 0),
        (18, 'voucher_no', '凭证号', 'text', 0, 0, 1, 0, 0, 0),
        (19, 'receipt_no', '回单编号', 'text', 0, 0, 1, 0, 0, 0),
    ]
    for f in optional_fields:
        conn.execute(sql_text(
            "INSERT OR IGNORE INTO manual_field_pool "
            "(id, field_code, field_name_cn, data_type, is_core, is_default_visible, "
            "is_disable_allowed, is_parse_key, is_validation_key, is_batch_inheritable, status, created_at, updated_at) "
            "VALUES (:id, :fc, :cn, :dt, 0, :dv, :da, 0, :vk, 0, 'active', :now, :now)"
        ), {"id": f[0], "fc": f[1], "cn": f[2], "dt": f[3], "dv": f[5], "da": f[6], "vk": f[8], "now": now})

    extra_schemes = [
        (2, 'manual_simple_cash', '现金简版', '现金类快速录入',
         '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","note_text"]', 0),
        (3, 'manual_bank_manual_account', '手工银行账户简版', '无网银账户',
         '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","previous_balance_input","ending_balance_input","voucher_no","receipt_no"]', 0),
        (4, 'manual_multi_subject_with_people', '多主体总表（含人员）', '带经办人负责人',
         '["entity_match_key","account_match_key","business_date","summary_text","counterparty_name","income_amount","expense_amount","department_name","handler_name","owner_name","note_text"]', 0),
    ]
    for s in extra_schemes:
        conn.execute(sql_text(
            "INSERT OR IGNORE INTO manual_template_schemes "
            "(id, scheme_code, scheme_name, description, selected_fields_json, is_default, status, created_at, updated_at) "
            "VALUES (:id, :sc, :sn, :desc, :sf, :def, 'active', :now, :now)"
        ), {"id": s[0], "sc": s[1], "sn": s[2], "desc": s[3], "sf": s[4], "def": s[5], "now": now})

    conn.commit()
    print(f"增量种子已写入：{len(optional_fields)} 个可选字段 + {len(extra_schemes)} 个方案")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期：启动时初始化，关闭时清理"""
    _init_db()
    from services.agent_init import init_agent_workspaces
    init_agent_workspaces()
    url = f"http://{HOST}:{PORT}"
    print(f"账房先生已启动 → {url}")
    webbrowser.open(url)
    yield


# ── 创建 FastAPI 实例 ──
app = FastAPI(title="账房先生", version="1.0.0", docs_url=None, redoc_url=None, lifespan=lifespan)

# ── CORS（开发用）──
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── 注册路由 ──
app.include_router(health_router, prefix="/api")
app.include_router(master_router, prefix="/api")
app.include_router(ai_router, prefix="/api")
app.include_router(agent_router, prefix="/api")
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


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
