# 23 · API 契约

> 本文件定义 API 契约原则、统一响应格式、模块级端点分组、错误码表和变更规则。
> 宪法锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C7。

---

## §A0 · 统一响应格式（强制）

```json
{ "code": 0, "message": "ok", "data": {} }
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | integer | 0 = 成功；非零 = 错误码（见 §A99） |
| `message` | string | 中文提示（成功为 "ok"） |
| `data` | object / array / null | 实际返回数据 |

违反由契约和代码审查约束。后续可补 guard 自动检测。

---

## §A1 · API Inventory 事实源

- **来源**：`python tools/guards/check_api_inventory.py --list`
- **当前为** 166 effective endpoints，0 duplicate route identities
- 端点数量不是固定上限；guard 检测 effective path 重复，不检查数量预算
- effective path = `include_prefix + router_prefix + decorator_path`（归一化后）

本文件不保留历史端点数量预算。当前 API 事实源以 `check_api_inventory.py --list` 为准。

---

## §A2 · 模块级端点分组

以下按 `backend/main.py` 中的 `include_router` 和 `backend/api/` 模块列出 22 个业务 API 模块及其路由前缀和职责。

| # | 模块 | 路由前缀 | 职责 |
|---|------|----------|------|
| 1 | `health.py` | `/api` | 健康检查 |
| 2 | `auth.py` | `/api/auth` | 登录、改密、当前用户 |
| 3 | `home.py` | `/api/home` | 首页总控台：概览、待办、快捷方式、系统状态 |
| 4 | `master_data.py` | `/api` | 板块 / 法人 / 账户 CRUD + 批量导入 |
| 5 | `bank_master.py` | `/api/banks` | 银行主数据 CRUD |
| 6 | `bank_import.py` | `/api/bank-import` | 银行流水导入（upload → preview → commit） |
| 7 | `manual_flow.py` | `/api/manual-flow` | 手工流水：字段池、方案、快速录入、上传、预览、提交、AI 解析 |
| 8 | `base_data.py` | `/api/base-data` | 基础数据表：聚合查询、重建、批量删除 |
| 9 | `reports.py` | `/api/reports` | 日报、现金日记账、余额表、收支明细等报表 + 生成 + 下载 |
| 10 | `report_template.py` | `/api/report-templates` | 报表模板 CRUD + Excel 导入 + excel-html 预览 |
| 11 | `dashboard.py` | `/api/dashboard` | 看板指标、趋势、构成 |
| 12 | `export.py` | `/api/export` | 导出 Excel |
| 13 | `backup.py` | `/api/backups` | 备份创建、恢复、清理 |
| 14 | `batch.py` | `/api/batches` | 导入批次列表、回滚 |
| 15 | `logs.py` | `/api/logs` | 操作日志 |
| 16 | `ai_config.py` | `/api` | AI Provider 配置 CRUD + 连接测试 + 模型列表 + 调用日志 |
| 17 | `agent_config.py` | `/api` | Agent workspace 初始化 |
| 18 | `agent.py` | `/api/agent` | 通用 Agent：实例 / 会话 / 消息 / 文件 / 记忆 / 技能 / 权限管理 |
| 19 | `artifacts.py` | `/api/artifacts` | ParserArtifact / RuleArtifact / TemplateInferenceJob CRUD + 审批 |
| 20 | `events.py` | `/api/events` | 异常中心：待确认 / 异常列表、标记正常 / 作废 |
| 21 | `reset.py` | `/api/reset` | 数据库工厂重置 |
| 22 | `workflow.py` | `/api/workflow` | 工作流：定义 CRUD + graph patch + 版本 + 运行 + 暂停恢复 |

完整端点列表以 `check_api_inventory.py --list` 输出为准，不在此手写全量清单。

---

## §A3 · Agent / Artifact API

### 通用 Agent API（`/api/agent`）

路由前缀 `/api/agent`，由 `backend/api/agent.py` 提供。核心能力：

| 能力 | 端点示例 |
|------|----------|
| Agent 实例管理 | `GET/POST /api/agent/agents`、`GET/PUT/DELETE /api/agent/agents/{id}` |
| 会话管理 | `GET/POST /api/agent/agents/{id}/sessions` |
| 消息（SSE） | `POST /api/agent/sessions/{id}/messages` |
| 文件操作 | `GET/POST /api/agent/agents/{id}/files`、`GET/PUT/DELETE .../files/content` |
| 记忆管理 | `GET/POST /api/agent/agents/{id}/memories` |
| 技能管理 | `GET /api/agent/agents/{id}/skills`、`POST .../skill-run`、`POST .../skill-test` |
| 权限管理 | `GET/PUT /api/agent/agents/{id}/permissions` |
| 技能安装 | `GET /api/agent/skills/available`、`POST /api/agent/skills/install`、`DELETE /api/agent/skills/{code}` |
| 工具确认 | `POST /api/agent/sessions/{id}/tool-confirm` |

### Artifact API（`/api/artifacts`）

路由前缀 `/api/artifacts`，由 `backend/api/artifacts.py` 提供。

| 端点 | 职责 |
|------|------|
| `GET /api/artifacts/parsers` | ParserArtifact 列表（支持 status/kind/account_code 筛选） |
| `GET /api/artifacts/parsers/{id}` | ParserArtifact 详情（含 code） |
| `POST /api/artifacts/parsers/drafts` | 创建 ParserArtifact 草稿 |
| `POST /api/artifacts/parsers/{id}/approve` | 审批通过（draft → active） |
| `POST /api/artifacts/parsers/{id}/reject` | 拒绝（draft → retired） |
| `GET /api/artifacts/rules` | RuleArtifact 列表（支持 status/template_id 筛选） |
| `GET /api/artifacts/rules/{id}` | RuleArtifact 详情（含 placeholder_bindings） |
| `POST /api/artifacts/rules/drafts` | 创建 RuleArtifact 草稿 |
| `POST /api/artifacts/rules/{id}/approve` | 审批通过 |
| `POST /api/artifacts/rules/{id}/reject` | 拒绝 |
| `GET /api/artifacts/template-inference-jobs` | 模板推断任务列表 |
| `GET /api/artifacts/template-inference-jobs/{id}` | 模板推断任务详情 |

状态流转：`create → draft → active（approve）或 retired（reject）`。同账户同类型 active 的旧版本自动降级为 retired。

审核边界：
- `approve` / `reject` 由用户发起，Agent 不直接审批
- 执行阶段（`artifact_runtime.run_parser` / `run_rule`）不经过此 API
- 执行阶段禁止 LLM（§C8）

---

## §A4 · 禁止恢复的旧 API

以下路由模式已被删除，**禁止恢复**：

| 旧路由模式 | 删除原因 |
|-----------|----------|
| `/api/fund/agent/skills/*/invoke` | Fund Agent 体系已删除，统一走通用 Agent |
| `/api/fund/parsers/*` | 已迁移到 `/api/artifacts/parsers` |
| `/api/fund/rules/*` | 已迁移到 `/api/artifacts/rules` |
| `/api/bank-import/ai-parse` | 已删除，银行导入统一走 ParserArtifact 路线 |
| `/api/bank-import/commit-by-mapping` | 已删除 |
| `/api/bank-import/save-template` | 已删除 |

新能力必须走通用 Agent（`/api/agent`）+ Artifact API（`/api/artifacts`）。

---

## §A5 · 工作流 API

路由前缀 `/api/workflow`，由 `backend/api/workflow.py` 提供。

| 端点 | 职责 |
|------|------|
| `GET/POST /api/workflow/workflows` | 工作流定义列表 / 创建草稿 |
| `GET /api/workflow/nodes` | 可用节点类型 |
| `GET /api/workflow/runs` | 运行记录列表 |
| `GET /api/workflow/runs/{id}` | 运行详情（含节点执行记录） |
| `GET/PUT /api/workflow/workflows/{id}` | 工作流定义详情 / 更新元数据 |
| `PATCH /api/workflow/workflows/{id}/graph` | 统一 patch 入口（生成新版本） |
| `POST /api/workflow/workflows/{id}/validate` | 校验 graph（不保存、不创建版本） |
| `POST /api/workflow/workflows/{id}/activate` | 启用 |
| `POST /api/workflow/workflows/{id}/archive` | 归档 |
| `POST /api/workflow/workflows/{id}/runs` | 同步启动运行 |
| `GET /api/workflow/workflows/{id}/versions` | 版本历史列表 |
| `POST /api/workflow/runs/{id}/resume` | 恢复暂停的运行 |

validate 校验规则：INVALID_STRUCTURE / EMPTY_NODES / INVALID_NODE / MISSING_NODE_FIELD / DUPLICATE_NODE_ID / INVALID_EDGE / INVALID_EDGE_REF / UNKNOWN_NODE_TYPE / CYCLE_DETECTED / ORPHAN_NODE（error）；MISSING_START / MISSING_END / PAUSE_NO_SUCCESSOR（warning）。

---

## §A99 · 错误码表

| 码 | 消息（中文） | 典型场景 |
|---|---|---|
| `0` | `ok` | 成功 |
| `1001` | `参数缺失` | 必填字段空 |
| `1002` | `参数格式错误` | 日期 / 金额 / 编码格式 |
| `1003` | `权限不足` | — |
| `2001` | `账户不存在` | entity / account 未注册 |
| `2002` | `金额互斥冲突` | amount_in 和 amount_out 同时 > 0 |
| `2003` | `状态不允许` | 对已作废行做操作 |
| `2004` | `占位符未绑定` | 模板中有占位符未在 Rule 中覆盖 |
| `3001` | `Parser 生成失败` | Agent 返回非法产物 |
| `3002` | `SAMPLE_CHECK 未通过` | 样本回归失败 |
| `3003` | `基元库调用越界` | AST 扫描失败 |
| `3004` | `沙箱超时` | 单次执行 > 60s |
| `3005` | `Rule 占位符数量不符` | 不是 18 个 |
| `4001` | `AI Provider 连接失败` | — |
| `4002` | `AI Provider 返回非 JSON` | — |
| `5001` | `数据库错误` | — |
| `5002` | `文件 IO 错误` | — |
| `5999` | `未知错误` | 兜底 |

---

## §A-Route · 路由实现约束

| 约束 | 说明 |
|---|---|
| 路由层只做请求收发 | 业务逻辑**必须**在 `backend/services/` |
| 路由层不得调用 `ai_call` | AI 调用由通用 Agent runtime 封装 |
| 响应体必须走 `response.success()` / `response.error()` | 强制统一格式 |
| 端点新增必须更新相关 active docs | 运行 `check_api_inventory.py` 验证 |

---

## §ChangeFlow · API 变更规则

- 新增 / 删除 / 修改 API 必须更新相关 active docs 或本文件
- 结果报告必须包含 API 影响判断
- 运行 `python tools/guards/check_api_inventory.py` 验证无重复

---
**校准来源：** `backend/main.py`、`backend/api/`、`tools/guards/check_api_inventory.py --list`
**最后校准：** 2026-05-17
