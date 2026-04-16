# 20 Database Schema Contract

## 1. Purpose

This file is the database execution contract for V1.

All table creation and migrations must follow this file.

## 2. Tables

### divisions
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| name | varchar(100) | yes | unique within active scope |
| sort_order | integer | no | default 0 |
| status | varchar(20) | yes | enabled / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### entities
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| division_id | integer fk divisions.id | no | |
| entity_code | varchar(50) | yes | unique |
| name | varchar(200) | yes | |
| short_name | varchar(100) | yes | |
| status | varchar(20) | yes | enabled / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### accounts
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| entity_id | integer fk entities.id | yes | |
| account_code | varchar(50) | yes | unique |
| account_alias | varchar(100) | yes | |
| bank_name | varchar(100) | no | |
| branch_name | varchar(200) | no | |
| account_number | varchar(100) | no | |
| account_type | varchar(50) | yes | |
| instrument_type | varchar(50) | yes | |
| input_method | varchar(50) | yes | bank_import / manual |
| currency | varchar(20) | yes | CNY default |
| initial_balance | numeric(18,2) | yes | |
| balance_date | date | yes | |
| status | varchar(20) | yes | enabled / disabled / closed |
| notes | text | no | |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### account_aliases
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| account_id | integer fk accounts.id | yes | |
| alias_text | varchar(100) | yes | used for fast match |
| alias_type | varchar(50) | yes | code / short_name / display_name |
| created_at | datetime | yes | |

### parser_templates
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| template_name | varchar(100) | yes | |
| template_type | varchar(30) | yes | bank / manual |
| file_format | varchar(20) | yes | xlsx/xls/csv |
| header_row | integer | yes | |
| skip_rows | integer | yes | default 0 |
| sample_headers | text | yes | json array |
| mapping_json | text | yes | json object |
| created_by | varchar(30) | yes | ai / manual / system |
| status | varchar(20) | yes | active / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### manual_field_pool
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| field_code | varchar(50) | yes | unique |
| field_name_cn | varchar(100) | yes | |
| data_type | varchar(30) | yes | text/number/date/bool/select |
| is_core | boolean | yes | |
| is_default_visible | boolean | yes | |
| is_disable_allowed | boolean | yes | |
| is_parse_key | boolean | yes | |
| is_validation_key | boolean | yes | |
| is_batch_inheritable | boolean | yes | |
| options_json | text | no | |
| status | varchar(20) | yes | active / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### manual_template_schemes
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| scheme_code | varchar(50) | yes | unique |
| scheme_name | varchar(100) | yes | |
| description | text | no | |
| selected_fields_json | text | yes | ordered field list |
| is_default | boolean | yes | |
| status | varchar(20) | yes | active / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### import_batches
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| batch_code | varchar(50) | yes | unique |
| source_type | varchar(30) | yes | bank / manual_quick / manual_excel |
| source_name | varchar(200) | no | file name or scheme name |
| status | varchar(30) | yes | uploaded / previewed / committed / rolled_back |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### fund_events
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| batch_id | integer fk import_batches.id | yes | |
| source_type | varchar(30) | yes | |
| business_date | date | yes | |
| business_time | varchar(20) | no | |
| entity_id | integer fk entities.id | no | nullable until confirmed |
| account_id | integer fk accounts.id | no | nullable until confirmed |
| direction | varchar(20) | no | income / expense / derived |
| income_amount | numeric(18,2) | no | |
| expense_amount | numeric(18,2) | no | |
| counterparty_name | varchar(200) | no | |
| summary_text | varchar(500) | yes | |
| previous_balance_input | numeric(18,2) | no | |
| ending_balance_input | numeric(18,2) | no | optional check value |
| rolling_balance | numeric(18,2) | no | system generated |
| parse_status | varchar(30) | yes | pending / valid / abnormal |
| abnormal_code | varchar(50) | no | |
| raw_data_json | text | yes | |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

### daily_report_runs
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| report_code | varchar(50) | yes | unique |
| report_name | varchar(200) | yes | |
| start_date | date | yes | |
| end_date | date | yes | |
| status | varchar(30) | yes | draft / confirmed |
| notes | text | no | |
| created_at | datetime | yes | |

### ai_configs
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| provider | varchar(50) | yes | |
| display_name | varchar(100) | yes | |
| api_key_encrypted | text | yes | |
| base_url | varchar(255) | no | |
| model_name | varchar(100) | no | |
| is_default | boolean | yes | |
| status | varchar(20) | yes | active / disabled |
| created_at | datetime | yes | |

### operation_logs
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| action | varchar(50) | yes | |
| module | varchar(50) | yes | |
| batch_id | integer fk import_batches.id | no | |
| detail_json | text | yes | |
| created_at | datetime | yes | |

### agent_configs
| field | type | required | notes |
|---|---|---:|---|
| id | integer pk | yes | |
| agent_code | varchar(50) | yes | unique |
| agent_name | varchar(100) | yes | |
| agent_type | varchar(30) | yes | shared / master / parser_assistant |
| workspace_dir | varchar(200) | yes | relative path under agents/ |
| ai_config_id | integer fk ai_configs.id | no | nullable = no AI binding |
| description | text | no | |
| status | varchar(20) | yes | active / disabled |
| created_at | datetime | yes | |
| updated_at | datetime | yes | |

## 3. Indexes

以下索引为 V1 必建索引，在建表 SQL 中一并创建。

```sql
-- 主数据查询
CREATE INDEX idx_entities_division ON entities(division_id);
CREATE INDEX idx_accounts_entity ON accounts(entity_id);
CREATE INDEX idx_account_aliases_account ON account_aliases(account_id);
CREATE INDEX idx_account_aliases_text ON account_aliases(alias_text);

-- 资金事件查询
CREATE INDEX idx_fund_events_batch ON fund_events(batch_id);
CREATE INDEX idx_fund_events_date ON fund_events(business_date);
CREATE INDEX idx_fund_events_entity ON fund_events(entity_id);
CREATE INDEX idx_fund_events_account ON fund_events(account_id);
CREATE INDEX idx_fund_events_status ON fund_events(parse_status);
CREATE INDEX idx_fund_events_date_account ON fund_events(business_date, account_id);

-- 导入批次
CREATE INDEX idx_import_batches_status ON import_batches(status);
CREATE INDEX idx_import_batches_source ON import_batches(source_type);

-- 日报
CREATE INDEX idx_daily_report_runs_dates ON daily_report_runs(start_date, end_date);

-- 解析模板
CREATE INDEX idx_parser_templates_type ON parser_templates(template_type, status);

-- 操作日志
CREATE INDEX idx_operation_logs_module ON operation_logs(module, created_at);
CREATE INDEX idx_operation_logs_batch ON operation_logs(batch_id);

-- Agent
CREATE INDEX idx_agent_configs_type ON agent_configs(agent_type, status);
```

## 4. Foreign Key Constraints

SQLite 默认不强制外键，需在每次连接时执行 `PRAGMA foreign_keys = ON`。

| 子表 | 外键字段 | 父表 | 父字段 | 级联 |
|------|---------|------|--------|------|
| entities | division_id | divisions | id | SET NULL |
| accounts | entity_id | entities | id | RESTRICT |
| account_aliases | account_id | accounts | id | CASCADE |
| fund_events | batch_id | import_batches | id | RESTRICT |
| fund_events | entity_id | entities | id | SET NULL |
| fund_events | account_id | accounts | id | SET NULL |
| operation_logs | batch_id | import_batches | id | SET NULL |
| agent_configs | ai_config_id | ai_configs | id | SET NULL |

## 5. Table Name Convention

> **V1 统一表名为 `fund_events`**，代表"标准资金事件"。
> 部分历史文档中出现的 `transactions` 为旧称，已全部统一。
> 所有执行文档、API、代码中一律使用 `fund_events`。

## 6. General rules

- no physical delete for business master tables
- code fields must be unique
- json fields stored as text in V1 SQLite
- all datetime fields use backend local standard
