# 20 · 数据库契约（v3 真实 Schema）

> 本文件定义 V1 AI-First 路线的活动数据库契约。契约锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C1 与 §C6。
> Phase 0 仅修订文档；ORM、Alembic、SQLite 实库将在 Phase 1 按本文档落地。

---

## §T0 · 表清单

当前 V1 活动 schema：

```text
1. divisions                板块
2. entities                 法人/单位
3. banks                    银行
4. accounts                 账户
5. account_aliases          账户别名
6. parser_templates         [已移除] 银行流水解析规则已迁移到 parser_artifacts
7. manual_field_pool        手工流水字段池
8. manual_template_schemes  手工模板方案
9. import_batches           导入批次
10. fund_events             CANONICAL_12 资金流水事实表（§C1）
11. daily_report_runs       日报生成记录
12. ai_configs              AI Provider 配置
13. ai_call_logs            AI 调用审计日志
14. agent_configs           Agent 配置与 AI 绑定
15. operation_logs          操作日志
16. users                   本地单用户认证
17. report_templates        报表模板配置
18. parser_artifacts        Fund Agent Parser 产物
19. rule_artifacts          Fund Agent Rule 产物
20. template_inference_job  template.inference 三阶段流水线状态
```

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

### §T2.1 · `parser_templates`（已移除）

`parser_templates` 表已在 Alembic 迁移 `005_drop_parser_templates` 中移除。银行流水解析规则当前以 `parser_artifacts`（§T4.1）为准。

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

`fund_events` 是 V1 报表和基础数据表的唯一流水事实表。其 12 列 canonical schema 列序、列名、枚举值由 §C1 冻结。

```sql
CREATE TABLE fund_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  business_date DATE NOT NULL,
  entity_code VARCHAR(50) NOT NULL,
  entity_name VARCHAR(200) NOT NULL,
  account_code VARCHAR(50) NOT NULL,
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

### §T3.5 · `agent_configs`

```sql
CREATE TABLE agent_configs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  agent_code VARCHAR(50) NOT NULL UNIQUE,
  agent_name VARCHAR(100) NOT NULL,
  agent_type VARCHAR(30) NOT NULL,
  workspace_dir VARCHAR(200) NOT NULL,
  ai_config_id INTEGER REFERENCES ai_configs(id) ON DELETE SET NULL,
  description TEXT,
  status VARCHAR(20) NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL
);
CREATE INDEX idx_agent_configs_type ON agent_configs(agent_type, status);
```

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

## §T4 · Fund Agent 产物表

### §T4.1 · `parser_artifacts`

```sql
CREATE TABLE parser_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100) NOT NULL,
  kind VARCHAR(20) NOT NULL,
  account_code VARCHAR(50),
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
```

### §T4.2 · `rule_artifacts`

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

`loop_spec`、`original_filename`、`file_path` 为 v3 attempt 兼容列，用于保留既有测试与早期 artifact 草稿的读写能力；新流程优先使用 `loop_config`、`template_file` 与三阶段输出字段。

---

## §T5 · Phase 1 落地迁移

| 任务 | 动作 |
|---|---|
| P1-1 | 备份当前 `backend/data/zhangfang.db` |
| P1-2 | 将 `backend/db/tables.py::FundEvent` 改回 CANONICAL_12 |
| P1-3 | 重新加入 `ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` ORM |
| P1-4 | 删除当前 ORM 中不属于 §C1 的兼容字段 |
| P1-5 | 整理 Alembic 版本，建立 v3 baseline |
| P1-6 | 编写一次性 reset 脚本重建 SQLite |
| P1-7 | 启动时改用 Alembic upgrade head |
| P1-8 | 下游服务先保证 import 通过，业务写入改由后续 Runtime 承接 |

---

## §T6 · 守护脚本时序

| 守护脚本 | 必须转绿 Phase | Phase 0 状态 |
|---|---|---|
| `check_contract_hash.py` | Phase 0 P0-7 | 必须转绿 |
| `check_canonical_schema.py` | Phase 1 P1-2 | 红色可接受，交班到 Phase 1 |
| `check_primitives_whitelist.py` | Phase 3 | 跳过 |
| `check_placeholder_binding.py` | Phase 3 P3-3 | 跳过 |
| `check_api_inventory.py` | Phase 6 | 记录差异，不阻塞 Phase 0 |

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

**版本**
- v4.1 · 2026-05-10 · 移除 parser_templates 表（§T2.1），银行流水解析规则统一使用 parser_artifacts
- v4.0 · 2026-05-02 · 新增 §T7 Agent 系统扩展表（6 张表 DDL）
- v3.1 · 2026-04-25 · Phase 0 文档复位为 v3 真实 Schema，20 表清单与三张 artifact 表恢复。
- v3.0 · 2026-04-23 · AI-First artifact schema。
