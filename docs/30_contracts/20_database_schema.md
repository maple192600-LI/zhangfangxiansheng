# 20 · 数据库契约（当前 Schema）

> 本文件定义当前 `backend/db/tables.py` 中 31 张业务 ORM 表的完整 DDL。
> 契约锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C1 与 §C6。

---

## §T0 · 表清单

当前 31 张业务 ORM 表（按 `backend/db/tables.py` 中 `__tablename__` 定义）：

```text
── 主数据模块（6 张）──
1.  divisions                板块
2.  entities                 法人/单位
3.  banks                    银行
4.  accounts                 账户
5.  account_aliases          账户别名
6.  users                    本地单用户认证

── 手工流水配置（2 张）──
7.  manual_field_pool        手工流水字段池
8.  manual_template_schemes  手工模板方案

── 流水事实（5 张）──
9.  import_batches           导入批次
10. fund_events              CANONICAL_12 资金流水事实表（§C1）
11. source_files             上传文件处理记录（每次上传创建一条）
12. account_resolution_attempts  账户归属判断记录
13. account_resolution_evidence  账户归属判断证据（结果预览证据抽屉数据来源）

── Agent 产物（3 张）──
14. parser_artifacts         ParserArtifact 银行/手工解析器
15. rule_artifacts           RuleArtifact 报表填充规则
16. template_inference_job   template.inference 三阶段流水线状态

── 报表（2 张）──
17. report_templates         报表模板配置
18. daily_report_runs        日报生成记录

── AI / 日志（3 张）──
19. ai_configs               AI Provider 配置
20. ai_call_logs             AI 调用审计日志
21. operation_logs           操作日志

── Agent 系统（6 张）──
22. agents_v2                Agent 实例
23. skills_v2                技能注册表
24. agent_sessions           Agent 会话
25. agent_messages           Agent 消息
26. agent_runs               Agent 运行记录
27. agent_memories           Agent 记忆存储

── 工作流编排（4 张）──
28. workflows                工作流主表
29. workflow_versions        工作流版本
30. workflow_runs            工作流运行记录
31. workflow_run_steps       工作流节点执行记录
```

已移除：
- `parser_templates` — Alembic `005_drop_parser_templates` 中移除，禁止恢复。

---

## §T1 · 主数据表

### §T1.1 · `divisions`

```sql
CREATE TABLE divisions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  division_code VARCHAR(50) UNIQUE,
  name VARCHAR(100) NOT NULL UNIQUE,
  sort_order INTEGER DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'enabled',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

### §T1.2 · `entities`

```sql
CREATE TABLE entities (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  division_id INTEGER REFERENCES divisions(id) ON DELETE SET NULL,
  entity_code VARCHAR(50) NOT NULL UNIQUE,
  name VARCHAR(200) NOT NULL,
  short_name VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'enabled',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_entities_division ON entities(division_id);
```

### §T1.3 · `banks`

```sql
CREATE TABLE banks (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  bank_code VARCHAR(50) NOT NULL UNIQUE,
  bank_name VARCHAR(100) NOT NULL UNIQUE,
  short_name VARCHAR(50),
  cnaps_code VARCHAR(20),
  contact_phone VARCHAR(30),
  website VARCHAR(200),
  notes TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'enabled',
  sort_order INTEGER DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_banks_status ON banks(status);
```

### §T1.4 · `accounts`

```sql
CREATE TABLE accounts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_id INTEGER NOT NULL REFERENCES entities(id) ON DELETE RESTRICT,
  bank_id INTEGER REFERENCES banks(id) ON DELETE SET NULL,
  account_code VARCHAR(50) NOT NULL UNIQUE,
  account_alias VARCHAR(100) NOT NULL,
  bank_name VARCHAR(100),
  branch_name VARCHAR(200),
  account_number VARCHAR(100),
  account_last_four VARCHAR(10),
  account_type VARCHAR(50) NOT NULL,
  instrument_type VARCHAR(50) NOT NULL,
  input_method VARCHAR(50) NOT NULL DEFAULT 'manual',
  has_online_banking BOOLEAN NOT NULL DEFAULT 0,
  include_in_daily_report BOOLEAN NOT NULL DEFAULT 1,
  allow_manual_entry BOOLEAN NOT NULL DEFAULT 1,
  currency VARCHAR(20) NOT NULL DEFAULT 'CNY',
  initial_balance NUMERIC(18,2) NOT NULL DEFAULT 0,
  balance_date DATE NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'enabled',
  notes TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_accounts_entity ON accounts(entity_id);
```

### §T1.5 · `account_aliases`

```sql
CREATE TABLE account_aliases (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  account_id INTEGER NOT NULL REFERENCES accounts(id) ON DELETE CASCADE,
  alias_text VARCHAR(100) NOT NULL,
  alias_type VARCHAR(50) NOT NULL,
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_account_aliases_account ON account_aliases(account_id);
CREATE INDEX idx_account_aliases_text ON account_aliases(alias_text);
```

---

## §T2 · 导入与流水表

### §T2.1 · `parser_templates`（已移除，禁止恢复）

`parser_templates` 表已在 Alembic 迁移 `005_drop_parser_templates` 中移除。代码零残留。银行流水解析规则当前以 `parser_artifacts`（§T4.1）为准。**禁止恢复此表。**

### §T2.2 · `manual_field_pool`

```sql
CREATE TABLE manual_field_pool (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  field_code VARCHAR(50) NOT NULL UNIQUE,
  field_name_cn VARCHAR(100) NOT NULL,
  data_type VARCHAR(30) NOT NULL,
  is_core BOOLEAN NOT NULL DEFAULT 0,
  is_default_visible BOOLEAN NOT NULL DEFAULT 1,
  is_disable_allowed BOOLEAN NOT NULL DEFAULT 1,
  is_parse_key BOOLEAN NOT NULL DEFAULT 0,
  is_validation_key BOOLEAN NOT NULL DEFAULT 0,
  is_batch_inheritable BOOLEAN NOT NULL DEFAULT 0,
  options_json TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

### §T2.3 · `manual_template_schemes`

```sql
CREATE TABLE manual_template_schemes (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  scheme_code VARCHAR(50) NOT NULL UNIQUE,
  scheme_name VARCHAR(100) NOT NULL,
  description TEXT,
  selected_fields_json TEXT NOT NULL,
  is_default BOOLEAN NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

### §T2.4 · `import_batches`

```sql
CREATE TABLE import_batches (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_code VARCHAR(50) NOT NULL UNIQUE,
  source_type VARCHAR(30) NOT NULL,
  source_name VARCHAR(200),
  status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_import_batches_status ON import_batches(status);
CREATE INDEX idx_import_batches_source ON import_batches(source_type);
```

### §T2.5 · `fund_events`

`fund_events` 是报表和基础数据表的唯一流水事实表。其 12 列 canonical schema 列序、列名、枚举值由 §C1 冻结。

```sql
CREATE TABLE fund_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_date DATE,
  entity_code VARCHAR(50),
  entity_name VARCHAR(200) NOT NULL,
  account_code VARCHAR(50),
  account_name VARCHAR(100) NOT NULL,
  summary VARCHAR(500),
  counterparty VARCHAR(200),
  amount_in NUMERIC(18,2) NOT NULL DEFAULT 0,
  amount_out NUMERIC(18,2) NOT NULL DEFAULT 0,
  rolling_balance NUMERIC(18,2),
  state VARCHAR(20) NOT NULL DEFAULT '正常',
  source VARCHAR(20) NOT NULL,
  batch_id INTEGER,
  parser_artifact_id INTEGER,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  CHECK (NOT (amount_in > 0 AND amount_out > 0)),
  CHECK (amount_in >= 0 AND amount_out >= 0),
  CHECK (state IN ('正常','待确认','异常','已作废')),
  CHECK (source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')),
  CHECK (
    state != '正常'
    OR (
      business_date IS NOT NULL
      AND entity_code IS NOT NULL
      AND entity_code != ''
      AND account_code IS NOT NULL
      AND account_code != ''
    )
  ),
  FOREIGN KEY (entity_code) REFERENCES entities(entity_code),
  FOREIGN KEY (account_code) REFERENCES accounts(account_code),
  FOREIGN KEY (batch_id) REFERENCES import_batches(id),
  FOREIGN KEY (parser_artifact_id) REFERENCES parser_artifacts(id)
);
CREATE INDEX idx_fund_events_date_account ON fund_events(business_date, account_code);
CREATE INDEX idx_fund_events_state ON fund_events(state);
CREATE INDEX idx_fund_events_batch ON fund_events(batch_id);
```

#### §T2.5.1 · CANONICAL_12 不变量

- 12 列必须按 §C1 契约序连续出现。
- 元数据列只允许 `id`、`batch_id`、`parser_artifact_id`、`created_at`、`updated_at`。
- 收支金额非负，且同一行不得同时出现正收入与正支出。
- `state` 与 `source` 枚举值不得绕过 §ChangeFlow 修改。
- `待确认` / `异常` 行属于上传结果预览阶段，允许 `business_date`、`entity_code`、`account_code` 暂缺，以便用户在预览页修正。
- `正常` 行属于正式基础数据，必须满足 `business_date`、`entity_code`、`account_code` 非空且编码不为空字符串。
- 查询基础数据、报表、导出时必须过滤 `state = '正常'`。

### §T2.6 · `source_files`

`source_files` 记录每次上传文件的处理状态。不是固定模板，而是每次上传都会创建的动态记录。

```sql
CREATE TABLE source_files (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  batch_id INTEGER NOT NULL REFERENCES import_batches(id),
  original_filename VARCHAR(300) NOT NULL,
  storage_path VARCHAR(500) NOT NULL,
  file_hash VARCHAR(64) NOT NULL,
  file_size INTEGER NOT NULL,
  sheet_name VARCHAR(100),
  format_fingerprint VARCHAR(100),
  parser_artifact_id INTEGER REFERENCES parser_artifacts(id),
  status VARCHAR(30) NOT NULL DEFAULT 'uploaded',
  error_code VARCHAR(50),
  error_message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  CHECK (status IN ('uploaded','parsed','needs_rule','needs_account','failed','ready'))
);
CREATE INDEX idx_source_files_batch ON source_files(batch_id);
CREATE INDEX idx_source_files_hash ON source_files(file_hash);
CREATE INDEX idx_source_files_parser ON source_files(parser_artifact_id);
CREATE INDEX idx_source_files_status ON source_files(status);
```

`source_files` 与 `FundEvent` 的关系：`source_files` 记录文件级状态（parser 是否匹配、解析是否成功），`FundEvent` 记录行级流水数据。行级预览仍由 `ImportBatch + FundEvent.state` 完成，不新增 `import_batch_rows`。

### §T2.7 · `account_resolution_attempts`

每次账户归属判断的记录。

```sql
CREATE TABLE account_resolution_attempts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_file_id INTEGER NOT NULL REFERENCES source_files(id),
  status VARCHAR(30) NOT NULL,
  recommended_entity_code VARCHAR(50),
  recommended_account_code VARCHAR(50),
  confidence NUMERIC(5,4),
  match_reason TEXT,
  error_code VARCHAR(50),
  raw_hints JSON,
  candidates JSON,
  bank_resolution JSON,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  CHECK (status IN ('matched','ambiguous','unmatched','conflict'))
);
CREATE INDEX idx_account_resolution_attempts_file ON account_resolution_attempts(source_file_id);
```

### §T2.8 · `account_resolution_evidence`

账户归属判断的证据记录，用于结果预览证据抽屉展示。

```sql
CREATE TABLE account_resolution_evidence (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  attempt_id INTEGER NOT NULL REFERENCES account_resolution_attempts(id),
  evidence_type VARCHAR(50) NOT NULL,
  evidence_value TEXT,
  matched_entity_code VARCHAR(50),
  matched_account_code VARCHAR(50),
  weight NUMERIC(5,4),
  message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (evidence_type IN (
    'account_number','account_last_four','account_name',
    'bank','filename','alias','history','balance_chain',
    'parser_hint','entity_name'
  ))
);
CREATE INDEX idx_account_resolution_evidence_attempt ON account_resolution_evidence(attempt_id);
```

---

## §T3 · 报表与配置表

### §T3.1 · `daily_report_runs`

```sql
CREATE TABLE daily_report_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_code VARCHAR(50) NOT NULL UNIQUE,
  report_name VARCHAR(200) NOT NULL,
  start_date DATE NOT NULL,
  end_date DATE NOT NULL,
  status VARCHAR(30) NOT NULL DEFAULT 'draft',
  notes TEXT,
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_daily_report_runs_dates ON daily_report_runs(start_date, end_date);
```

### §T3.2 · `report_templates`

```sql
CREATE TABLE report_templates (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_code VARCHAR(50) NOT NULL UNIQUE,
  template_name VARCHAR(100) NOT NULL,
  report_type VARCHAR(30) NOT NULL,
  columns_json TEXT NOT NULL,
  layout_json TEXT,
  group_by VARCHAR(50),
  is_default BOOLEAN NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_by VARCHAR(30) NOT NULL DEFAULT 'admin',
  remark TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_report_templates_type ON report_templates(report_type, status);
CREATE INDEX idx_report_templates_default ON report_templates(report_type, is_default);
```

### §T3.3 · `ai_configs`

```sql
CREATE TABLE ai_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider VARCHAR(50) NOT NULL,
  display_name VARCHAR(100) NOT NULL,
  api_key_local TEXT NOT NULL,
  base_url VARCHAR(255),
  model_name VARCHAR(100),
  is_default BOOLEAN NOT NULL DEFAULT 0,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL
);
```

`api_key_local` 是本地明文保存字段。不要将真实 `zhangfang.db` 发送给无关人员。

### §T3.4 · `ai_call_logs`

```sql
CREATE TABLE ai_call_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  provider VARCHAR(50) NOT NULL,
  model VARCHAR(100),
  endpoint VARCHAR(255),
  status VARCHAR(20) NOT NULL,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  request_size INTEGER NOT NULL DEFAULT 0,
  response_size INTEGER NOT NULL DEFAULT 0,
  error_code VARCHAR(50),
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_ai_call_logs_created ON ai_call_logs(created_at);
```

### §T3.5 · 已移除的旧 Agent 配置表

旧 Agent 配置表无对应 ORM 类，配置能力已合并入 `agents_v2`（§T7.1）。**禁止恢复此表。**

### §T3.6 · `operation_logs`

```sql
CREATE TABLE operation_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  action VARCHAR(50) NOT NULL,
  module VARCHAR(50) NOT NULL,
  batch_id INTEGER REFERENCES import_batches(id) ON DELETE SET NULL,
  detail_json TEXT NOT NULL,
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_operation_logs_module ON operation_logs(module, created_at);
CREATE INDEX idx_operation_logs_batch ON operation_logs(batch_id);
```

### §T3.7 · `users`

```sql
CREATE TABLE users (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  username VARCHAR(50) NOT NULL UNIQUE,
  password_hash VARCHAR(128) NOT NULL,
  must_change_password BOOLEAN NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
```

---

## §T4 · Agent 产物表

### §T4.1 · `parser_artifacts`

```sql
CREATE TABLE parser_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100) NOT NULL,
  kind VARCHAR(20) NOT NULL,
  account_code VARCHAR(50),
  bank_id INTEGER REFERENCES banks(id) ON DELETE SET NULL,
  format_key VARCHAR(100),
  match_rules JSON NOT NULL DEFAULT '{}',
  version INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  code TEXT NOT NULL,
  primitives_imports JSON NOT NULL,
  sample_check_log JSON NOT NULL DEFAULT '{}',
  confidence DECIMAL(5,4),
  created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
  approved_by VARCHAR(50),
  approved_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  UNIQUE(name, version),
  CHECK (kind IN ('bank','manual')),
  CHECK (status IN ('draft','active','retired'))
);
CREATE INDEX idx_parser_artifacts_account ON parser_artifacts(account_code, status);
CREATE INDEX idx_parser_artifacts_kind ON parser_artifacts(kind, status);
CREATE INDEX idx_parser_artifacts_bank_format ON parser_artifacts(kind, bank_id, format_key, status);
```

`account_code` 字段说明：对银行导入场景，此字段不应作为主匹配键。银行导入应按 bank/format 级匹配 parser（09D 已交付），不按 account_code 匹配。此字段保留作为旧兼容或非银行场景字段。

`bank_id` + `format_key`：银行导入 parser 的匹配键。bank/format 级 parser 服务同银行同格式的所有账户。

```sql
CREATE TABLE rule_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100) NOT NULL,
  template_id INTEGER REFERENCES report_templates(id),
  version INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  placeholder_bindings JSON NOT NULL,
  loop_spec JSON,
  loop_config JSON,
  primitives_imports JSON NOT NULL,
  sample_check_log JSON NOT NULL DEFAULT '{}',
  confidence DECIMAL(5,4),
  created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
  approved_by VARCHAR(50),
  approved_at DATETIME,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  CHECK (status IN ('draft','active','retired'))
);
CREATE INDEX idx_rule_artifacts_template ON rule_artifacts(template_id, status);
```

### §T4.3 · `template_inference_job`

```sql
CREATE TABLE template_inference_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_file VARCHAR(255),
  original_filename VARCHAR(300),
  file_path VARCHAR(500),
  stage VARCHAR(20),
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  stage_a_output JSON,
  stage_b_output JSON,
  stage_c_decision VARCHAR(20),
  rule_artifact_id INTEGER REFERENCES rule_artifacts(id),
  error_message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME,
  CHECK (status IN ('pending','reviewed','approved','rejected'))
);
```

`loop_spec`、`original_filename`、`file_path` 为兼容列，用于保留既有测试与早期 artifact 草稿的读写能力；新流程优先使用 `loop_config`、`template_file` 与三阶段输出字段。

---

---

## §T7 · Agent 系统扩展表

### §T7.1 · `agents_v2` — Agent 实例

```sql
CREATE TABLE agents_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_code VARCHAR(50) NOT NULL UNIQUE,
  display_name VARCHAR(100) NOT NULL,
  role_prompt TEXT NOT NULL DEFAULT '',
  ai_config_id INTEGER REFERENCES ai_configs(id) ON DELETE SET NULL,
  workspace_path VARCHAR(500) NOT NULL,
  llm_timeout INTEGER NOT NULL DEFAULT 300,
  llm_max_tokens INTEGER NOT NULL DEFAULT 16384,
  permission_json TEXT NOT NULL DEFAULT '{}',
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_by VARCHAR(50),
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_agents_v2_status ON agents_v2(status);
```

### §T7.2 · `skills_v2` — 技能注册

```sql
CREATE TABLE skills_v2 (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_code VARCHAR(80) NOT NULL UNIQUE,
  display_name VARCHAR(150) NOT NULL,
  description TEXT,
  owner_agent_id INTEGER REFERENCES agents_v2(id) ON DELETE SET NULL,
  manifest_json TEXT NOT NULL DEFAULT '{}',
  source_path VARCHAR(500) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  verified_at DATETIME,
  test_pass_count INTEGER NOT NULL DEFAULT 0,
  test_fail_count INTEGER NOT NULL DEFAULT 0,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_skills_v2_status ON skills_v2(status);
```

### §T7.3 · `agent_sessions` — Agent 会话

```sql
CREATE TABLE agent_sessions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id INTEGER NOT NULL REFERENCES agents_v2(id) ON DELETE CASCADE,
  title VARCHAR(200),
  context_summary TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  last_active_at DATETIME NOT NULL
);
CREATE INDEX idx_agent_sessions_agent ON agent_sessions(agent_id);
```

### §T7.4 · `agent_messages` — Agent 消息

```sql
CREATE TABLE agent_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  session_id INTEGER NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
  role VARCHAR(20) NOT NULL,
  content TEXT,
  reasoning_content TEXT,
  tool_call_json TEXT,
  tool_result_json TEXT,
  duration_ms INTEGER,
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_agent_messages_session ON agent_messages(session_id);
```

### §T7.5 · `agent_runs` — Agent 运行记录

```sql
CREATE TABLE agent_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  skill_id INTEGER REFERENCES skills_v2(id) ON DELETE SET NULL,
  agent_id INTEGER REFERENCES agents_v2(id) ON DELETE SET NULL,
  session_id INTEGER REFERENCES agent_sessions(id) ON DELETE SET NULL,
  inputs_json TEXT,
  outputs_json TEXT,
  logs TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  duration_ms INTEGER,
  created_at DATETIME NOT NULL
);
CREATE INDEX idx_agent_runs_agent ON agent_runs(agent_id);
```

### §T7.6 · `agent_memories` — Agent 记忆

```sql
CREATE TABLE agent_memories (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_id INTEGER NOT NULL REFERENCES agents_v2(id) ON DELETE CASCADE,
  key VARCHAR(200) NOT NULL,
  content TEXT NOT NULL,
  scope VARCHAR(30) NOT NULL DEFAULT 'agent',
  confidence NUMERIC(5,4) NOT NULL DEFAULT 1.0,
  source VARCHAR(50),
  created_at DATETIME NOT NULL,
  last_used_at DATETIME NOT NULL
);
CREATE INDEX idx_agent_memories_agent ON agent_memories(agent_id);
CREATE INDEX idx_agent_memories_key ON agent_memories(agent_id, key);
```

---

## §T8 · 工作流编排表

### §T8.1 · `workflows` — 工作流主表

```sql
CREATE TABLE workflows (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_code VARCHAR(80) NOT NULL UNIQUE,
  name VARCHAR(150) NOT NULL,
  description TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  current_version INTEGER NOT NULL DEFAULT 1,
  created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (status IN ('draft','active','archived'))
);
CREATE INDEX idx_workflows_status ON workflows(status);
```

### §T8.2 · `workflow_versions` — 工作流版本

```sql
CREATE TABLE workflow_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  version INTEGER NOT NULL,
  graph_json TEXT NOT NULL,
  change_summary TEXT,
  created_by VARCHAR(50) NOT NULL DEFAULT 'agent',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_workflow_versions_workflow ON workflow_versions(workflow_id);
CREATE UNIQUE INDEX ux_workflow_versions_workflow_version ON workflow_versions(workflow_id, version);
```

### §T8.3 · `workflow_runs` — 工作流运行记录
```sql
CREATE TABLE workflow_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  workflow_id INTEGER NOT NULL REFERENCES workflows(id) ON DELETE CASCADE,
  workflow_version_id INTEGER REFERENCES workflow_versions(id) ON DELETE SET NULL,
  workflow_code VARCHAR(80) NOT NULL,
  workflow_version INTEGER NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT,
  error_message TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  started_at DATETIME,
  finished_at DATETIME,
  CHECK (status IN ('pending','running','completed','failed','paused','cancelled'))
);
CREATE INDEX idx_workflow_runs_workflow ON workflow_runs(workflow_id);
CREATE INDEX idx_workflow_runs_version ON workflow_runs(workflow_version_id);
CREATE INDEX idx_workflow_runs_status ON workflow_runs(status);
```

### §T8.4 · `workflow_run_steps` — 工作流节点执行记录

```sql
CREATE TABLE workflow_run_steps (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id INTEGER NOT NULL REFERENCES workflow_runs(id) ON DELETE CASCADE,
  node_id VARCHAR(80) NOT NULL,
  node_type VARCHAR(100) NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  input_json TEXT NOT NULL DEFAULT '{}',
  output_json TEXT,
  error_message TEXT,
  started_at DATETIME,
  finished_at DATETIME,
  CHECK (status IN ('pending','running','completed','failed','skipped','paused'))
);
CREATE INDEX idx_workflow_run_steps_run ON workflow_run_steps(run_id);
CREATE INDEX idx_workflow_run_steps_node ON workflow_run_steps(run_id, node_id);
```

---

**校准来源：** `backend/db/tables.py`、`tools/guards/check_canonical_schema.py`
**最后校准：** 2026-05-18
