# 20 · 数据库契约（v3 · 14 张表）

> 本文件取代 v2 版。定义 V1 阶段冻结的 14 张表完整 DDL。
> 契约锚点见 [../00_governance/00_project_constitution.md](../00_governance/00_project_constitution.md) §C6。

---

## §T0 · 表清单

```
1. divisions                 ← 板块
2. entities                  ← 法人
3. accounts                  ← 账户（20 列 § C3）
4. account_aliases           ← 账户别名
5. fund_events               ← ★ 12 列基础数据表（§C1）
6. manual_field_pool         ← 手工字段池
7. manual_template_schemes   ← 手工模板方案
8. import_batches            ← 导入批次
9. parser_artifacts          ← ★ Parser 可执行代码 + 版本
10. rule_artifacts           ← ★ Rule 代码 + 版本
11. template_inference_job   ← ★ 模板识别任务中间态
12. ai_configs               ← AI Provider 配置
13. agent_configs            ← Agent-to-Provider 绑定
14. operation_logs           ← 操作日志
```

辅助表（`users`、`backups`）结构相对稳定，但不列入 FROZEN。

---

## §T1 · 基础表（4 张，保留自 v2）

### §T1.1 · `divisions` · 板块

```sql
CREATE TABLE divisions (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  code        VARCHAR(20) NOT NULL UNIQUE,
  name        VARCHAR(100) NOT NULL,
  sort_order  INTEGER DEFAULT 0,
  created_at  DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### §T1.2 · `entities` · 法人/单位

```sql
CREATE TABLE entities (
  id              INTEGER PRIMARY KEY AUTOINCREMENT,
  entity_code     VARCHAR(50)  NOT NULL UNIQUE,   -- 格式 DW####
  entity_name     VARCHAR(200) NOT NULL,
  short_name      VARCHAR(100),
  division_code   VARCHAR(20)  NOT NULL,
  org_segment     VARCHAR(100),
  status          VARCHAR(20)  DEFAULT '启用',
  notes           TEXT,
  created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at      DATETIME,
  FOREIGN KEY (division_code) REFERENCES divisions(code)
);
CREATE INDEX idx_entities_division ON entities(division_code);
```

### §T1.3 · `accounts` · 账户主数据（§C3 · 20 列）

```sql
CREATE TABLE accounts (
  id                      INTEGER PRIMARY KEY AUTOINCREMENT,
  account_code            VARCHAR(50)  NOT NULL UNIQUE,    -- 格式 ZH####
  account_name            VARCHAR(100) NOT NULL,
  account_last_four       VARCHAR(10),
  account_number          VARCHAR(100),
  bank_name               VARCHAR(200),
  entity_code             VARCHAR(50)  NOT NULL,
  account_type            VARCHAR(30)  NOT NULL,           -- §C3.1
  instrument_type         VARCHAR(30)  NOT NULL,           -- §C3.2
  has_online_banking      BOOLEAN      DEFAULT 0,
  input_method            VARCHAR(20)  NOT NULL,           -- §C3.3
  currency                VARCHAR(10)  DEFAULT 'CNY',
  initial_balance         NUMERIC(18,2) DEFAULT 0,
  balance_date            DATE,
  include_in_daily_report BOOLEAN      DEFAULT 1,
  allow_manual_entry      BOOLEAN      DEFAULT 0,
  status                  VARCHAR(20)  DEFAULT '启用',
  notes                   TEXT,
  created_at              DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at              DATETIME,
  CHECK (account_type    IN ('基本户','一般户','临时户','现金账户','农民工工资专用账户')),
  CHECK (instrument_type IN ('银行存款','现金','票据','信用证','保证金')),
  CHECK (input_method    IN ('网银','手工','现金','票据','财务公司')),
  FOREIGN KEY (entity_code) REFERENCES entities(entity_code)
);
CREATE INDEX idx_accounts_entity ON accounts(entity_code);
```

### §T1.4 · `account_aliases` · 账户别名

```sql
CREATE TABLE account_aliases (
  id             INTEGER PRIMARY KEY AUTOINCREMENT,
  account_code   VARCHAR(50)  NOT NULL,
  alias          VARCHAR(200) NOT NULL,
  alias_type     VARCHAR(20)  DEFAULT '自动',    -- 自动/手工
  confidence     NUMERIC(4,3),
  created_at     DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (account_code) REFERENCES accounts(account_code),
  UNIQUE(account_code, alias)
);
```

---

## §T2 · 基础数据表（1 张，新增 · §C1）

### §T2.1 · `fund_events` · 12 列基础数据表

```sql
CREATE TABLE fund_events (
  id                   INTEGER PRIMARY KEY AUTOINCREMENT,
  -- 12 列 CANONICAL_12 ↓
  business_date        DATE         NOT NULL,
  entity_code          VARCHAR(50)  NOT NULL,
  entity_name          VARCHAR(200) NOT NULL,
  account_code         VARCHAR(50)  NOT NULL,
  account_name         VARCHAR(100) NOT NULL,
  summary              VARCHAR(500),
  counterparty         VARCHAR(200),
  amount_in            NUMERIC(18,2) NOT NULL DEFAULT 0,
  amount_out           NUMERIC(18,2) NOT NULL DEFAULT 0,
  rolling_balance      NUMERIC(18,2),
  state                VARCHAR(20)   NOT NULL DEFAULT '正常',
  source               VARCHAR(20)   NOT NULL,
  -- 12 列 CANONICAL_12 ↑
  batch_id             INTEGER,
  parser_artifact_id   INTEGER,
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  updated_at           DATETIME,
  CHECK (NOT (amount_in > 0 AND amount_out > 0)),
  CHECK (state  IN ('正常','待确认','异常','已作废')),
  CHECK (source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')),
  CHECK (amount_in  >= 0 AND amount_out >= 0),
  FOREIGN KEY (entity_code)        REFERENCES entities(entity_code),
  FOREIGN KEY (account_code)       REFERENCES accounts(account_code),
  FOREIGN KEY (batch_id)           REFERENCES import_batches(id),
  FOREIGN KEY (parser_artifact_id) REFERENCES parser_artifacts(id)
);
CREATE INDEX idx_fund_events_date_account ON fund_events(business_date, account_code);
CREATE INDEX idx_fund_events_state         ON fund_events(state);
CREATE INDEX idx_fund_events_batch         ON fund_events(batch_id);
```

**不变量**：12 列的列序、列名、枚举值与 §C1 完全一致。`tools/guards/check_canonical_schema.py` 校对 DDL。

---

## §T3 · AI 产物表（3 张，新增）

### §T3.1 · `parser_artifacts` · Parser 代码版本

```sql
CREATE TABLE parser_artifacts (
  id                  INTEGER      PRIMARY KEY AUTOINCREMENT,
  name                VARCHAR(100) NOT NULL,           -- 如 "ICBC_网银_v1"
  kind                VARCHAR(20)  NOT NULL,           -- bank / manual
  account_code        VARCHAR(50),                     -- 绑定账户（可空：通用解析器）
  version             INTEGER      NOT NULL DEFAULT 1,
  code                TEXT         NOT NULL,           -- Python 代码（仅调基元库）
  primitives_imports  TEXT         NOT NULL,           -- JSON 数组
  sample_check_log    TEXT,                            -- SAMPLE_CHECK 结果 JSON
  created_by          VARCHAR(20)  DEFAULT 'fund.agent',
  approved_by         VARCHAR(50),
  approved_at         DATETIME,
  status              VARCHAR(20)  NOT NULL DEFAULT 'draft',  -- draft/approved/retired
  created_at          DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (kind   IN ('bank','manual')),
  CHECK (status IN ('draft','approved','retired')),
  UNIQUE(name, version)
);
CREATE INDEX idx_parser_artifacts_name    ON parser_artifacts(name);
CREATE INDEX idx_parser_artifacts_account ON parser_artifacts(account_code);
```

### §T3.2 · `rule_artifacts` · Rule 代码版本

```sql
CREATE TABLE rule_artifacts (
  id                   INTEGER      PRIMARY KEY AUTOINCREMENT,
  name                 VARCHAR(100) NOT NULL,           -- 如 "现金日记账_月账_v1"
  template_id          INTEGER      NOT NULL,
  version              INTEGER      NOT NULL DEFAULT 1,
  placeholder_bindings TEXT         NOT NULL,           -- JSON
  loop_spec            TEXT         NOT NULL,           -- JSON
  primitives_imports   TEXT         NOT NULL,
  sample_check_log     TEXT,
  created_by           VARCHAR(20)  DEFAULT 'fund.agent',
  approved_by          VARCHAR(50),
  approved_at          DATETIME,
  status               VARCHAR(20)  NOT NULL DEFAULT 'draft',
  created_at           DATETIME DEFAULT CURRENT_TIMESTAMP,
  CHECK (status IN ('draft','approved','retired')),
  UNIQUE(name, version)
);
```

### §T3.3 · `template_inference_job` · 模板识别任务

```sql
CREATE TABLE template_inference_job (
  id                    INTEGER      PRIMARY KEY AUTOINCREMENT,
  original_filename     VARCHAR(300) NOT NULL,
  file_path             VARCHAR(500) NOT NULL,
  detected_placeholders TEXT,                           -- JSON 数组
  confidence            NUMERIC(4,3),
  rule_draft_id         INTEGER,
  status                VARCHAR(20)  NOT NULL DEFAULT 'pending',
  created_at            DATETIME DEFAULT CURRENT_TIMESTAMP,
  reviewed_at           DATETIME,
  CHECK (status IN ('pending','reviewed','approved','rejected')),
  FOREIGN KEY (rule_draft_id) REFERENCES rule_artifacts(id)
);
```

---

## §T4 · 辅助表（6 张，保留自 v2）

以下 6 张表 DDL 沿用 v2（不在此重复），仅列字段要点：

### §T4.1 · `manual_field_pool`
用于"多主体 Excel"手工模板的字段池（字段名 / 数据类型 / 是否必填 / 映射到 canonical 的哪一列）。

### §T4.2 · `manual_template_schemes`
手工模板方案（布局、列位、字段池的组合）。

### §T4.3 · `import_batches`
导入批次表，记录单次上传的文件名、时间、触发的 parser_artifact_id、统计（成功 / 待确认 / 异常）。

### §T4.4 · `ai_configs`
AI Provider 配置：provider_name / api_key（加密）/ base_url / model / privacy_mode / enabled。

### §T4.5 · `agent_configs`
Agent → Provider 绑定：`fund.agent` 当前绑的哪个 provider，可切换。

### §T4.6 · `operation_logs`
操作日志：actor / action / object_type / object_id / payload / result / created_at。

---

## §T5 · 迁移清单（v2 → v3）

| 旧 | 新 | 动作 |
|---|---|---|
| `parser_templates` 表 | 作废 | 数据不迁移；保留为历史只读 |
| 无 `fund_events` | 新增 | Alembic 迁移 001 |
| 无 `parser_artifacts` | 新增 | Alembic 迁移 002 |
| 无 `rule_artifacts` | 新增 | Alembic 迁移 003 |
| 无 `template_inference_job` | 新增 | Alembic 迁移 004 |

---

**版本**
- v3.0 · 2026-04-23 · 重写为 14 表
- v2 · 原版见 git 历史
