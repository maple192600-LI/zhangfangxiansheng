# 账房先生 ZhangFang V1

面向中国财务人员的本地部署通用 Agent 驱动财务工作台。Agent 负责生成和维护解析器、规则、模板等可审核产物；用户负责上传、查看、确认和审核；确定性执行由 artifact runtime 完成。

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / SQLite / Alembic |
| 数据处理 | openpyxl / Polars |
| 前端 | Vue 3 / Vite / Ant Design Vue / ECharts |
| 打包 | 前端静态编译 + 后端挂载 + PyInstaller |

## 本地开发启动

首次准备环境：

```powershell
.\setup.bat
```

手工安装后端依赖：

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

默认后端地址：

```text
http://127.0.0.1:8000
```

## 前端开发

```powershell
cd frontend
npm install
npm run dev
```

前端生产构建：

```powershell
cd frontend
npm run build
```

构建完成后，后端会挂载 `frontend/dist`，可通过后端地址访问单页应用。

## 一键启动

完成 `setup.bat` 后：

```powershell
.\start.bat
```

`start.bat` 会清理端口 8000 上的旧进程、清理 Python 缓存，并启动后端服务。

## 环境变量

复制 `.env.example` 为 `.env` 后按需调整：

```text
ZF_SECRET_KEY=set_a_long_random_string_here
ZF_DB_PATH=backend/data/zhangfang.db
ZF_LOG_LEVEL=INFO
```

当前代码会读取 `ZF_SECRET_KEY` 和 `ZF_DB_PATH`。未设置 `ZF_SECRET_KEY` 时会基于数据库路径生成本地密钥，仅适合单机开发环境。

## 测试

后端测试：

```powershell
backend\venv\Scripts\pytest.exe tests\backend
```

服务层覆盖率门槛：

```powershell
backend\venv\Scripts\pytest.exe tests\backend --cov=backend/services --cov-report=term-missing --cov-fail-under=70
```

端到端业务闭环脚本：

```powershell
backend\venv\Scripts\pytest.exe tests\e2e\test_full_flow.py
```

## 打包成 exe

先构建前端：

```powershell
cd frontend
npm run build
cd ..
```

安装 PyInstaller 并打包后端入口：

```powershell
backend\venv\Scripts\pip.exe install pyinstaller
backend\venv\Scripts\pyinstaller.exe --onefile --name zhangfang --paths backend backend\main.py
```

打包产物位于 `dist/zhangfang.exe`。正式交付前需补充静态资源、数据库初始文件、Alembic 迁移文件和启动脚本的完整打包校验。

## 重要目录

| 目录 | 用途 |
| --- | --- |
| `backend/` | FastAPI 后端、服务层、数据库模型、Agent 运行时 |
| `frontend/` | Vue 前端 |
| `alembic/` | SQLite schema 迁移 |
| `tests/` | 后端、端到端、样本测试 |
| `docs/` | 治理、契约、执行与交付文档 |
| `backend/data/` | 本地 SQLite 数据与上传/导出/备份数据目录 |

## 当前边界

- V1 只交付本地单机财务工作台，不包含多人协作和集中部署。
- AI 辅助识别、规则生成与配置建议，不决定账户归属和汇总正确性。核心数据操作由通用 Agent 通过工具完成，不直接写业务表。
- `backend/data/zhangfang.db` 是本地业务数据核心文件，发送或备份前需要确认是否包含真实财务数据与本地明文 API Key。
