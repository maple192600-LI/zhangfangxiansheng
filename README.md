# 账房先生 ZhangFang V1

面向中国财务人员的本地部署 Agent 驱动财务工作台。

Agent 生成和维护解析器、规则、模板等可审核产物（Artifact）；用户负责上传、查看、确认和审核；确定性执行由 artifact runtime 完成。

## 技术栈

> 以下信息来自 `frontend/package.json` 和 `backend/requirements.txt`，以代码为准。

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.11+ / FastAPI / SQLAlchemy / Alembic / SQLite |
| 数据处理 | openpyxl / xlrd / Polars |
| 前端 | Vue 3 / Vite / naive-ui / ECharts / Pinia |
| 表格组件 | Tabulator Tables / naive-ui Data Table |
| 工作流画布 | Vue Flow |
| 本地分析引擎 | DuckDB WASM |

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

默认后端地址：`http://127.0.0.1:8000`

前端开发：

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

一键启动：

```powershell
.\start.bat
```

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

## 环境变量

复制 `.env.example` 为 `.env` 后按需调整：

```text
ZF_SECRET_KEY=set_a_long_random_string_here
ZF_DB_PATH=backend/data/zhangfang.db
ZF_LOG_LEVEL=INFO
```

## 重要目录

| 目录 | 用途 |
|------|------|
| `backend/` | FastAPI 后端：API 路由（22 模块）、服务层（25 模块）、ORM 表（28 张）、Agent 运行时 |
| `frontend/` | Vue 3 前端：42 个视图组件 |
| `alembic/` | SQLite schema 迁移 |
| `tests/` | 后端测试、端到端测试、样本测试 |
| `docs/` | 开发文档（入口见 `docs/README.md`） |
| `backend/data/` | SQLite 数据 + 上传/导出/备份数据目录 |
| `agents/` | Agent 运行时数据（用户创建的实例） |
| `tools/guards/` | 契约守卫脚本 |

## 当前开发状态

- **Agent 系统**：已存在。通用 Agent 支持会话、工具调用、记忆、技能管理。
- **Artifact runtime**：`run_parser` 已实现（ParserArtifact deterministic runtime）；`run_rule` 仍为 `NotImplementedError`（Phase H1 待交付）。ParserArtifact 可创建、审核、执行。RuleArtifact 可创建和审核，但无法通过 artifact runtime 执行。
- **手工流水快速录入**：已有独立路径可直接写入 FundEvent，不应被重建。
- **文档体系**：docs 已完成重建和旧文档物理清理。14 个 active docs + 4 个受保护契约文件。
- **API 端点**：当前为 166 effective endpoints，0 duplicate route identities。来源：`python tools/guards/check_api_inventory.py --list`。

## 文档入口

所有开发文档入口：[`docs/README.md`](docs/README.md)

## V1 范围

**包含：** 主数据中心、银行导入、手工流水双轨、日报生成、导出打印、基础看板、备份回滚、日志、Agent 系统

**禁止：** 发票 OCR 正式流程、费用审批、合同管理、多人协作、集中部署
