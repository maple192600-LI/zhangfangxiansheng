# 23 · API 契约（v4）

> 本文件定义所有 API 端点 + 统一响应格式 + 错误码表。
> 原始设计 42 端点上限（§A1），V1.1 因 Agent 系统扩展追加至 59 个（§A1-ext）。
> 契约锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C7。

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

违反 = `tools/guards/check_api_response_shape.py`（推荐）拒绝。

---

## §A1 · 端点总览（历史设计 42 上限已失效）

> **口径说明**：原始设计上限为 42 端点。V1.1 阶段因 Agent 系统扩展已追加至 59 个端点。实际代码中注册了更多路由。当前端点口径待重新统计，以下 42 端点清单保留作历史参考。新增和变更的端点见 §A99。

| # | 模块 | 方法 | 路径 | 职责 |
|---|---|---|---|---|
| 1 | 主数据 | GET | `/api/divisions` | 板块列表 |
| 2 | 主数据 | POST/PUT/DELETE | `/api/divisions/:code` | 板块 CUD |
| 3 | 主数据 | GET | `/api/entities` | 单位列表（分页） |
| 4 | 主数据 | POST/PUT/DELETE | `/api/entities/:code` | 单位 CUD |
| 5 | 主数据 | GET | `/api/accounts` | 账户列表 |
| 6 | 主数据 | POST/PUT/DELETE | `/api/accounts/:code` | 账户 CUD |
| 7 | 主数据 | POST | `/api/accounts/import` | Excel 批量导入 |
| 8 | AI 配置 | GET | `/api/ai/configs` | Provider 列表 |
| 9 | AI 配置 | POST/PUT/DELETE | `/api/ai/configs/:id` | Provider CUD |
| 10 | AI 配置 | POST | `/api/ai/configs/:id/test` | 连接测试 |
| 11 | AI 配置 | GET | `/api/agents` | Agent 配置 |
| 12 | AI 配置 | PUT | `/api/agents/:name/binding` | 绑定 Provider |
| 13 | Fund Agent | POST | `/api/fund/agent/skills/parser.bank/invoke` | 生成银行 Parser |
| 14 | Fund Agent | POST | `/api/fund/agent/skills/parser.manual/invoke` | 生成手工 Parser |
| 15 | Fund Agent | POST | `/api/fund/agent/skills/rule.template_fill/invoke` | 生成 Rule |
| 16 | Fund Agent | POST | `/api/fund/agent/skills/rule.maintain/invoke` | 维护 Rule |
| 17 | Fund Agent | POST | `/api/fund/agent/skills/template.inference/invoke` | 模板识别 |
| 18 | Artifacts | GET | `/api/fund/parsers` | Parser artifact 列表 |
| 19 | Artifacts | GET | `/api/fund/parsers/:id` | 详情 + 代码 |
| 20 | Artifacts | POST | `/api/fund/parsers/:id/approve` | 审批 draft → approved |
| 21 | Artifacts | GET | `/api/fund/rules` | Rule artifact 列表 |
| 22 | Artifacts | GET | `/api/fund/rules/:id` | 详情 + bindings |
| 23 | Artifacts | POST | `/api/fund/rules/:id/approve` | 审批 |
| 24 | 流水导入 | POST | `/api/bank/import` | 上传银行流水（触发 Parser） |
| 25 | 流水导入 | GET | `/api/bank/batches` | 批次列表 |
| 26 | 流水导入 | GET | `/api/bank/batches/:id` | 批次详情 |
| 27 | 流水导入 | POST | `/api/manual/flow` | 快速录入单条 |
| 28 | 流水导入 | POST | `/api/manual/flow/upload` | Excel 多主体上传 |
| 29 | 模板识别 | POST | `/api/fund/templates/upload` | 上传空白模板 |
| 30 | 模板识别 | GET | `/api/fund/templates/jobs/:id` | 识别任务状态 |
| 31 | 模板识别 | POST | `/api/fund/templates/jobs/:id/confirm` | 用户确认 → 生成 Rule |
| 32 | 报表 | POST | `/api/reports/generate` | 生成报表（走 Rule artifact） |
| 33 | 报表 | GET | `/api/reports/download/:id` | 下载 Excel |
| 34 | 报表 | GET | `/api/reports/history` | 历史报表 |
| 35 | 异常中心 | GET | `/api/events/pending` | 待确认/异常 列表 |
| 36 | 异常中心 | PUT | `/api/events/:id/resolve` | 标记正常 |
| 37 | 异常中心 | PUT | `/api/events/:id/void` | 作废 |
| 38 | 系统 | POST | `/api/auth/login` | 登录 |
| 39 | 系统 | POST | `/api/auth/logout` | 登出 |
| 40 | 系统 | GET | `/api/system/health` | 健康检查 |
| 41 | 系统 | GET | `/api/system/backup` | 备份下载 |
| 42 | 系统 | POST | `/api/system/backup/restore` | 恢复 |

**历史设计**：42 端点上限为原始设计约束，现已失效。端点数量以本文档 §A99 当前版本为准。新增必须走 §ChangeFlow，并更新 `23_api_contracts.md`。`tools/guards/check_api_inventory.py` 的 42 上限已过时，不得作为阻断条件。

---

## §A2 · 关键端点详细 Schema

### §A2.1 · `POST /api/fund/agent/skills/parser.bank/invoke`

**请求体**：
```json
{
  "account_code": "ZH0001",
  "sample_file_id": "upload-abc-123",
  "privacy_mode": "standard"
}
```

**成功响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "artifact_id": 17,
    "name": "ICBC_网银_v1",
    "version": 1,
    "status": "draft",
    "confidence": 0.94,
    "sample_check_log": {
      "sample_rows": 50,
      "parsed_rows": 50,
      "canonical_violations": 0
    }
  }
}
```

**错误响应**（样本校验未过）：
```json
{
  "code": 3002,
  "message": "样本校验未通过：50 行中 3 行金额互斥违反",
  "data": {
    "violations": [
      {"row": 12, "reason": "amount_in 和 amount_out 同时 > 0"}
    ]
  }
}
```

### §A2.2 · `POST /api/fund/templates/upload`

**请求**（multipart/form-data）：
- `file`: 空白 .xlsx 模板
- `kind`: "cash_journal" / "custom"

**成功响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "job_id": 42,
    "detected_placeholders": ["报表标题", "月初余额", "..."],
    "confidence": 0.87,
    "rule_draft_id": 100,
    "status": "pending"
  }
}
```

### §A2.3 · `POST /api/reports/generate`

**请求体**：
```json
{
  "rule_id": 100,
  "account_code": "ZH0001",
  "period_start": "2026-04-01",
  "period_end": "2026-04-30"
}
```

**成功响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "report_id": "rpt-20260423-001",
    "download_url": "/api/reports/download/rpt-20260423-001",
    "placeholder_filled": 18,
    "rows_written": 125,
    "runtime_ms": 4230
  }
}
```

### §A2.4 · `POST /api/bank/import`

**请求**（multipart/form-data）：
- `file`: 银行流水 Excel
- `account_code`: （可选）账户编码
- `parser_artifact_id`: （可选）指定 Parser 版本

**成功响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "batch_id": 88,
    "parser_artifact_id": 17,
    "total_rows": 200,
    "succeeded": 195,
    "pending": 3,
    "failed": 2,
    "detail_url": "/api/bank/batches/88"
  }
}
```

---

## §A99 · 错误码表

> 注意：42 端点上限为 V3 设计约束，已失效。Agent V2 系统（`/api/agent_v2/*`）和手工流水 AI 解析端点（`/api/manual-flow/ai-parse`）为 Round 10-11 新增，基于 Agent V2 智能体系统，不占用 Fund Agent 端点配额。银行导入旧端点（`/api/bank/import` 单文件上传、`/api/bank-import/ai-parse`、`/api/bank-import/commit-by-mapping`、`/api/bank-import/save-template`）已移除，**禁止恢复**。银行导入统一使用 ParserArtifact 路线（upload → preview → commit）。

### Round 10-11 新增端点

| # | 模块 | 方法 | 路径 | 职责 |
|---|---|---|---|---|
| N1 | Agent V2 | GET | `/api/agent_v2/agents` | 智能体列表 |
| N2 | Agent V2 | POST | `/api/agent_v2/agents` | 创建智能体 |
| N3 | Agent V2 | GET | `/api/agent_v2/agents/:id` | 智能体详情 |
| N4 | Agent V2 | PUT | `/api/agent_v2/agents/:id` | 更新智能体 |
| N5 | Agent V2 | DELETE | `/api/agent_v2/agents/:id` | 删除智能体 |
| N6 | Agent V2 | GET | `/api/agent_v2/agents/:id/sessions` | 会话列表 |
| N7 | Agent V2 | POST | `/api/agent_v2/agents/:id/sessions` | 创建会话 |
| N8 | Agent V2 | POST | `/api/agent_v2/sessions/:id/messages` | 发送消息（SSE） |
| N9 | Agent V2 | GET | `/api/agent_v2/sessions/:id/messages` | 消息历史 |
| N10 | Agent V2 | GET | `/api/agent_v2/ai-configs` | AI 配置列表 |
| N11 | Agent V2 | GET | `/api/agent_v2/agents/:id/skills` | 技能列表 |
| N12 | Agent V2 | GET | `/api/agent_v2/agents/:id/files` | 工作区文件 |
| N13 | Agent V2 | POST | `/api/agent_v2/agents/:id/files/upload` | 上传文件 |
| N14 | 手工流水 | POST | `/api/manual-flow/ai-parse` | AI 智能解析手工流水列映射 |
| N15 | 银行导入 | POST | `/api/bank-import/upload` | 上传银行流水（返回 batch + parser_match） |
| N16 | 银行导入 | POST | `/api/bank-import/preview` | 预览解析（参数：batch_code + parser_artifact_id） |
| N17 | 银行导入 | POST | `/api/bank-import/commit` | 确认入库（参数：batch_code + parser_artifact_id） |

### `POST /api/manual-flow/ai-parse` 请求/响应

**请求体**：
```json
{
  "headers": ["日期", "摘要", "收入", "支出", "对方"],
  "sample_rows": [],
  "agent_id": 1,
  "scheme_code": "manual_multi_subject_basic"
}
```

**成功响应**：
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "ok": true,
    "mapping": {"日期": "business_date", "摘要": "summary_text", "收入": "income_amount", "支出": "expense_amount", "对方": "counterparty_name"},
    "confidence": "high",
    "matched_count": 5,
    "total_columns": 5
  }
}
```

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
| 路由层不得调用 `ai_call` | AI 调用由 `backend/agents/fund/` 封装 |
| 每个端点必须有对应 pytest 用例 | 放在 `tests/api/test_*.py` |
| 响应体必须走 `response.success()` / `response.error()` | 强制统一格式 |
| 端点新增必须更新本文件 + guards 白名单 | pre-commit 拦截 |

---

**版本**
- v4.2 · 2026-05-10 · §A1 标记 42 上限已失效；§A99 标记旧端点禁止恢复；口径待重新统计
- v4.1 · 2026-05-10 · 移除银行导入旧端点（ai-parse / commit-by-mapping / save-template），N14-N17 改为 ParserArtifact 路线
- v4.0 · 2026-05-02 · 承认端点数从 42 扩展至 59，更新标题和说明
- v3.2 · 2026-04-28 · Round 11：新增 Agent V2 + AI 解析端点（§A99 扩展）
- v3.1 · 2026-04-27 · Round 10：登录认证 + 字段统一 + 模板修复
- v3.0 · 2026-04-23 · 重写为 42 端点清单
- v2 · 原版归档见 git 历史
