"""账房先生 V1 — FastAPI 入口

启动方式：
  Windows: 双击 start.bat 或 venv\Scripts\python.exe main.py
  Linux/Mac: venv/bin/python main.py
"""
import os
import sys
import webbrowser
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# 确保项目根目录在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import HOST, PORT, FRONTEND_DIST, DATA_DIR
from database import engine, Base
from db import tables as _  # noqa: F401 — 注册 ORM 模型到 Base.metadata
from api.health import router as health_router
from api.master_data import router as master_router
from api.ai_config import router as ai_router
from api.agent_config import router as agent_router


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
        # 静态资源（有扩展名且文件存在）直接放行给 StaticFiles
        if "." in os.path.basename(path):
            file_path = os.path.join(frontend_dist, path.lstrip("/"))
            if os.path.isfile(file_path):
                return await call_next(request)
        # 其余所有路径（/bank-import、/account-manage 等）返回 index.html
        index_html = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(index_html):
            return FileResponse(index_html, media_type="text/html")
        return await call_next(request)

    # 静态资源挂载（仅用于 /assets/ 等有扩展名的文件）
    app.mount("/", StaticFiles(directory=frontend_dist), name="frontend")


if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
