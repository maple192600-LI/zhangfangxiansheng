# 03 · 技术约束

> 配合 [00_project_constitution.md](00_project_constitution.md) 使用。
> 本文件是技术栈和工程约束的完整参考，任何技术选型决策必须以本文件为准。

---

## §1 · 技术栈锁定

**未经用户书面同意，不得更换以下任何主技术栈。**

### §1.1 · 后端

| 组件 | 技术 | 版本约束 | 用途 |
|------|------|----------|------|
| 语言 | Python | 3.11+ | 后端全部 |
| Web 框架 | FastAPI | 0.136+ | API 路由 + 生命周期 |
| ASGI 服务器 | Uvicorn | 0.44+ | 开发 + 生产运行 |
| ORM | SQLAlchemy | 2.0+ | 数据库访问（唯一 ORM） |
| 数据迁移 | Alembic | 1.18+ | Schema 版本管理 |
| 数据校验 | Pydantic | 2.x | 请求/响应模型 |
| 数据处理 | Polars | 1.x | 大表处理、聚合、清洗 |
| Excel 读写 | openpyxl | 3.1+ | .xlsx 模板生成和报表输出 |
| 旧格式 Excel | xlrd | 2.0+ | .xls 旧银行流水读取 |
| HTTP 客户端 | httpx | 0.28+ | AI Provider API 调用 |
| 认证 | PyJWT + bcrypt | — | 用户认证 + 密码哈希 |
| 文件监听 | watchfiles | 1.x | 开发热重载 |
| 配置 | PyYAML | 6.x | YAML 配置读取 |
| 测试 | pytest + coverage | — | 单元 + 集成测试 |

### §1.2 · 前端

| 组件 | 技术 | 版本约束 | 用途 |
|------|------|----------|------|
| 框架 | Vue 3 | 3.5+ | SPA（Composition API） |
| 构建工具 | Vite | 8.x | 开发服务器 + 生产构建 |
| UI 组件库 | Ant Design Vue | 4.x | 表格、表单、弹窗、布局 |
| 图表 | ECharts | 6.x | 看板图表 |
| 状态管理 | Pinia | 3.x | 全局状态 |
| 路由 | Vue Router | 4.x | SPA 路由 |
| HTTP | Axios | 1.x | API 请求 |

### §1.3 · 数据库

| 组件 | 技术 | 约束 |
|------|------|------|
| 数据库 | SQLite | 唯一数据库 |
| 模式 | WAL | 启用 write-ahead logging（database.py 自动配置） |
| 外键 | 启用 | 每次连接自动 `PRAGMA foreign_keys=ON` |
| 连接 | 单线程 | `check_same_thread=False`（FastAPI 异步场景） |

### §1.4 · 打包部署

| 约束 | 说明 |
|------|------|
| PyInstaller | 最终产物为单个可执行文件 |
| 前端静态挂载 | 后端自动挂载 `frontend/dist/`，无需独立前端服务器 |
| SPA 路由兜底 | 非 `/api` 路径一律返回 `index.html` |
| 双击启动 | `start.bat`（Windows），用户无需命令行 |
| 自动开浏览器 | 启动后自动打开默认浏览器 |

---

## §2 · 后端架构约束

### §2.1 · 分层架构

```
api/          ← 路由层：只做请求收发、参数校验、响应格式化
services/     ← 业务逻辑层：所有业务规则必须在这里
db/           ← 数据模型层：ORM 模型定义（tables.py + schemas.py）
core/         ← 通用引擎：导出、解析、Agent、安全、日志
agents/       ← Agent 运行时：通用 Agent + 工具注册 + 会话管理（旧 `agents/fund/` 已在 Phase 5 删除）
config.py     ← 全局配置
database.py   ← 数据库引擎与会话管理
main.py       ← FastAPI 入口 + 路由注册
```

**强制规则**：
- 路由层（`api/`）不承载业务逻辑，只做参数校验 + 调用 service + 返回结果
- 业务逻辑必须在 `services/` 中，不得散落在 `api/` 或 `core/`
- 数据库访问统一通过 SQLAlchemy ORM，禁止裸 SQL（Alembic 迁移脚本除外）
- `core/` 是跨模块通用能力，不接受业务特定逻辑

### §2.2 · API 规范

- 统一响应格式：`{ "code": 0, "message": "ok", "data": {} }`
- 端点上限 42 个（§C7）
- 全局异常兜底：未捕获异常统一返回 500 + 中文提示
- 认证中间件：SPA 路由兜底之后注册，拦截未认证请求
- CORS：本地部署场景，限制为固定域名列表

### §2.3 · 数据库访问

- ORM 模型集中定义在 `db/tables.py`
- 会话管理通过 `get_db()` 依赖注入
- Schema 变更必须走 Alembic 迁移
- 增量补列通过 `_patch_schema()` 幂等执行（用于开发阶段热补）
- 启动流程：Alembic upgrade → patch → 确保默认用户 → 注册全局技能

---

## §3 · 前端架构约束

### §3.1 · 页面组织

```
src/views/           ← 页面组件（按功能模块命名）
src/components/      ← 通用组件
src/api/             ← 接口请求统一收敛
src/stores/          ← Pinia 状态管理
src/router/          ← 路由配置
src/styles/          ← 全局样式
src/utils/           ← 工具函数
```

### §3.2 · 设计规范

- **表格为主战场** — 首页和工作页面以表格为核心交互方式
- **全中文 UI** — 所有界面文案、错误提示、日期格式均为中文
- **视觉风格** — 稳重复克制的暖色系（详细规范见 `references/style_and_interaction/`）
- **Ant Design Vue** — 主组件库，不引入第二套组件库

---

## §4 · Agent 架构约束

### §4.1 · 物理结构

```
backend/agents/
├── runtime.py         ← Agent 运行时核心循环
├── workspace.py       ← Agent 工作区管理
├── context.py         ← 上下文构建
├── prompt_builder.py  ← 提示词组装
├── permission.py      ← 工具权限控制
├── tool_registry.py   ← 工具注册表
├── skill_registry.py  ← 技能注册表
├── skill_creator.py   ← 技能创建器
├── skill_executor.py  ← 技能执行器
├── skill_scanner.py   ← 技能扫描
├── skill_loader.py    ← 技能加载
├── session_store.py   ← 会话存储
├── session_lock.py    ← 会话锁
├── memory_store.py    ← 记忆存储
├── memory_provider.py ← 记忆提供者
├── memory_manager.py  ← 记忆管理
├── curator.py         ← 上下文整理
├── provider.py        ← AI Provider 适配
├── sse_helper.py      ← SSE 流式输出
├── ~~fund/~~          ← 已删除（Phase 5）
│   └── (旧 harness/schemas/memory/skills 已删除)
└── tools/             ← Agent 可调用的工具集
    ├── db_ops.py      ← 数据库操作
    ├── fs.py          ← 文件系统操作
    ├── shell_ops.py   ← Shell 命令
    ├── openpyxl_ops.py← Excel 操作
    ├── memory.py      ← 记忆工具
    ├── ask_user.py    ← 询问用户
    ├── skill_ops.py   ← 技能操作
    └── file_parse.py  ← 文件解析（PDF/DOCX/Excel/CSV）
```

### §4.2 · Agent 工具系统

Agent 可调用的工具通过 `tool_registry.py` 注册，包含：
- 数据库操作（查询/写入，受权限控制）
- 文件系统操作（读/写/列表）
- 文件解析（PDF/DOCX/Excel/CSV 自动解析）
- Excel 操作（openpyxl 封装）
- Shell 命令（受限执行）
- 记忆读写（长期 + 短期）
- 技能操作（创建/注册/调用）
- 用户交互（询问确认）

### §4.3 · 确定性 Artifact 执行约束

- ParserArtifact / RuleArtifact 由通用 Agent 生成和维护，由 artifact service 管理和审核
- 产物必须通过 AST 扫描（基元库白名单 §C5）
- 执行由 artifact runtime 确定性完成，不由 Agent 运行期决策（§C8）
- 执行阶段禁止调 LLM（§C8）
- Artifact 审核必须由用户确认后通过 artifact service 完成
- 隐私三档：standard / strict / offline
- `backend/agents/fund/` 已在 Phase 5 删除；`backend/fund/` 是产物确定性执行基础设施，必须保留

---

## §5 · 数据处理约束

### §5.1 · 确定性优先原则

- 核心财务逻辑（导入、汇总、报表生成）必须由确定性代码完成
- Agent 生成脚本 → 脚本确定性执行 → 产出结果
- AI 不得在运行时自由决定账户归属、金额汇总正确性

### §5.2 · 文件解析能力

系统内置文件解析工具（`agents/tools/file_parse.py`），所有 Agent 默认可用：
- Excel（.xlsx / .xls）— openpyxl + xlrd
- CSV — Polars
- PDF — 自动提取文本和表格
- DOCX — 自动提取文本

### §5.3 · 编码与乱码

- 所有文件读取必须尝试多种编码（UTF-8 → GBK → GB18030 → Latin-1）
- 文件名上传后统一重命名为安全 ASCII + 时间戳格式
- 数据库存储一律 UTF-8
- 导出文件一律 UTF-8 + BOM（兼容 Excel 打开中文）

---

## §6 · 安全约束

### §6.1 · 认证

- JWT Token 认证，默认有效期 480 分钟
- 默认 admin 用户启动时自动创建
- 未设 `ZF_SECRET_KEY` 时基于数据库路径自动生成确定性密钥
- 生产环境必须设置 `ZF_SECRET_KEY` 环境变量

### §6.2 · Agent 安全

- Agent 工具权限通过 `permission.py` 控制
- Agent 代码产物必须通过 AST 白名单扫描
- Agent 不得访问外部网络（除配置的 AI Provider）
- Agent 不得执行 `subprocess`（沙箱内受限执行除外）

---

## §7 · 开发环境约束

### §7.1 · 目录结构

```
backend/            ← 后端代码
frontend/           ← 前端代码
docs/               ← 开发文档（最高优先级：governance → contracts → execution）
agents/             ← Agent 运行时数据（用户创建的 Agent 实例）
samples/            ← 银行流水/手工流水样本文件
templates/          ← 前端模板、手工模板
references/         ← 原始输入、截图、样式规范
tests/              ← pytest 测试
alembic/            ← 数据库迁移
```

### §7.2 · 端口与地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 后端 | http://127.0.0.1:8000 | FastAPI |
| 前端开发 | http://localhost:5180 | Vite dev server |

### §7.3 · 环境变量

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `ZF_DB_PATH` | `backend/data/zhangfang.db` | 数据库路径 |
| `ZF_SECRET_KEY` | 自动生成 | JWT 签名密钥 |
| `ZF_TOKEN_EXPIRE_MINUTES` | 480 | Token 有效期（分钟） |
| `ZF_CORS_ORIGINS` | localhost + 127.0.0.1 | CORS 允许域名 |

---

## §8 · 禁止事项

| 禁止 | 原因 |
|------|------|
| 更换 Python/Vue/SQLite 主栈 | 用户约束 + 打包要求 |
| 引入 Redis/PostgreSQL 等外部依赖 | 本地部署，不装额外服务 |
| 路由层写业务逻辑 | 分层架构约束 |
| 裸 SQL 写业务查询 | 必须走 ORM |
| 使用 pandas | 统一用 Polars |
| 运行时调 LLM 做核心计算 | §C8 Runtime 无 AI 原则 |
| 非中文错误信息 | 用户画像 |
| 暴露 JSON/正则/映射配置给用户 | §C9 零编程原则 |

---

**版本**
- v2.0 · 2026-05-02 · 基于 V1 现状全面重写（覆盖 v1 英文版）
- v1 · 原英文版归档见 F:\zhangfangxiansheng_archived\
