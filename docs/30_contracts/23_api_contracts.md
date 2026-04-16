# 23 API Contracts

## 1. Response Wrapper

All APIs return unified envelope:

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

Failure:

```json
{
  "code": 4001,
  "message": "账户识别失败",
  "data": {
    "abnormal_code": "ACCOUNT_MATCH_FAILED"
  }
}
```

### Error Code Table

| code | 含义 | 场景 |
|------|------|------|
| 0 | 成功 | — |
| 1001 | 参数缺失 | 必填字段为空 |
| 1002 | 参数格式错误 | 日期/数字/JSON 格式不合法 |
| 1003 | 唯一约束冲突 | code/name 重复 |
| 2001 | 记录不存在 | 查询 ID 无对应记录 |
| 2002 | 状态不允许操作 | 已禁用/已回滚的记录 |
| 3001 | 文件读取失败 | 上传文件损坏或格式不支持 |
| 3002 | 模板匹配失败 | 无命中模板且无 AI 建议 |
| 4001 | 账户匹配失败 | 实体/账户归属无法识别 |
| 4002 | 余额校验失败 | 期末余额与计算值不一致 |
| 4003 | 重复拦截 | 疑似重复记录 |
| 5001 | AI 连接失败 | API Key 无效或网络不通 |
| 5002 | AI 超时 | 请求超过 30s |
| 9001 | 系统内部错误 | 未预期异常 |

### Pagination

分页接口统一使用以下参数和响应格式：

Request params:
- `page` (int, default 1)
- `page_size` (int, default 50, max 200)

Response:
```json
{
  "code": 0,
  "message": "ok",
  "data": {
    "items": [],
    "total": 100,
    "page": 1,
    "page_size": 50,
    "total_pages": 2
  }
}
```

---

## 2. Master Data — Divisions

### GET /api/divisions
Query params:
- `status` (string, optional): enabled / disabled

Response:
```json
{
  "code": 0,
  "data": [
    { "id": 1, "name": "养护板块", "sort_order": 0, "status": "enabled", "created_at": "2026-01-01T00:00:00" }
  ]
}
```

### POST /api/divisions
Request:
```json
{ "name": "养护板块", "sort_order": 0 }
```

### PUT /api/divisions/{id}
Request:
```json
{ "name": "养护板块", "sort_order": 1, "status": "enabled" }
```

---

## 3. Master Data — Entities

### GET /api/entities
Query params:
- `division_id` (int, optional)
- `status` (string, optional)
- `keyword` (string, optional): search name / entity_code

Response:
```json
{
  "code": 0,
  "data": {
    "items": [
      { "id": 1, "division_id": 1, "entity_code": "E001", "name": "山西喜跃发实业发展有限公司", "short_name": "实业公司", "status": "enabled", "created_at": "..." }
    ],
    "total": 5, "page": 1, "page_size": 50, "total_pages": 1
  }
}
```

### POST /api/entities
Request:
```json
{ "division_id": 1, "entity_code": "E001", "name": "山西喜跃发实业发展有限公司", "short_name": "实业公司" }
```

### PUT /api/entities/{id}
Request: same fields as POST, plus `status`.

---

## 4. Master Data — Accounts

### GET /api/accounts
Query params:
- `entity_id` (int, optional)
- `status` (string, optional)
- `keyword` (string, optional)
- `account_type` (string, optional)
- `instrument_type` (string, optional)

Response:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 1, "entity_id": 1, "account_code": "A001",
        "account_alias": "中行手工户", "bank_name": "中国银行",
        "account_type": "银行账户", "instrument_type": "银行存款",
        "input_method": "manual", "currency": "CNY",
        "initial_balance": 200000.00, "balance_date": "2026-03-01",
        "status": "enabled", "entity_name": "实业公司"
      }
    ],
    "total": 6, "page": 1, "page_size": 50, "total_pages": 1
  }
}
```

### GET /api/accounts/tree
Response: accounts grouped by entity, with alias list per account.
```json
{
  "code": 0,
  "data": [
    {
      "entity_id": 1, "entity_name": "实业公司",
      "accounts": [
        { "id": 1, "account_code": "A001", "account_alias": "中行手工户", "account_type": "银行账户", "status": "enabled" }
      ]
    }
  ]
}
```

### POST /api/accounts
Request:
```json
{
  "entity_id": 1,
  "account_code": "A001",
  "account_alias": "中行手工户",
  "bank_name": "中国银行",
  "branch_name": "太原分行",
  "account_number": "621700xxxxx",
  "account_type": "银行账户",
  "instrument_type": "银行存款",
  "input_method": "manual",
  "currency": "CNY",
  "initial_balance": 200000.00,
  "balance_date": "2026-03-01",
  "notes": ""
}
```

### PUT /api/accounts/{id}
Same fields as POST.

### POST /api/accounts/{id}/initial-balance
Set or update initial balance (only if no fund_events exist for this account).
```json
{ "initial_balance": 200000.00, "balance_date": "2026-03-01" }
```

### GET /api/accounts/{id}/aliases
Response:
```json
{ "code": 0, "data": [{ "id": 1, "alias_text": "中行户", "alias_type": "short_name" }] }
```

### POST /api/accounts/{id}/aliases
```json
{ "alias_text": "中行户", "alias_type": "short_name" }
```

### DELETE /api/accounts/{id}/aliases/{alias_id}
Soft delete (sets status=disabled).

---

## 5. Home Dashboard

### GET /api/home/overview
Returns today's dashboard summary.
```json
{
  "code": 0,
  "data": {
    "date": "2026-04-10",
    "pending_tasks": { "total": 7, "unimported": 2, "unconfirmed": 3, "ungenerated": 2 },
    "alerts": { "total": 4, "payment_exceptions": 2, "rule_missed": 2 },
    "generation_status": "incomplete",
    "generation_status_detail": "基础数据表未生成，日报未更新",
    "key_account_changes": 3,
    "last_report_time": "2026-04-09T18:36:00",
    "last_backup_time": "2026-04-10T08:10:00"
  }
}
```

### GET /api/home/tasks
Returns pending task list.
```json
{
  "code": 0,
  "data": [
    { "task_type": "待导入网银流水", "count": 2, "status": "未完成", "suggested_action": "进入工作台 / 网银导入" },
    { "task_type": "待确认手工流水", "count": 3, "status": "未完成", "suggested_action": "进入工作台 / 手动维护" }
  ]
}
```

### GET /api/home/quick-links
Returns configured quick links.
```json
{
  "code": 0,
  "data": [
    { "label": "网银导入", "description": "上传银行流水，进入待处理池", "route": "/fund/workbench/bank-import" },
    { "label": "手工流水", "description": "录入临时发生额和补录数据", "route": "/fund/workbench/manual-flow" }
  ]
}
```

### GET /api/home/system-status
```json
{
  "code": 0,
  "data": {
    "last_base_data_generation": { "status": "未生成", "time": null },
    "last_report_generation": { "status": "成功", "time": "2026-04-09T18:36:00" },
    "last_backup": { "status": "成功", "time": "2026-04-10T08:10:00" },
    "ocr_status": "正常",
    "recent_actions": [
      { "time": "08:12", "description": "出纳上传了中行流水文件 1 份。" }
    ]
  }
}
```

---

## 6. Parser Templates

### GET /api/parser-templates
Query params:
- `template_type` (string, optional): bank / manual
- `status` (string, optional)

Response:
```json
{
  "code": 0,
  "data": [
    { "id": 1, "template_name": "中国银行标准流水", "template_type": "bank", "file_format": "xls", "status": "active", "created_by": "manual", "created_at": "..." }
  ]
}
```

### POST /api/parser-templates
Create or update parser template.
```json
{
  "template_name": "中国银行标准流水",
  "template_type": "bank",
  "file_format": "xls",
  "header_row": 5,
  "skip_rows": 4,
  "sample_headers": ["交易日期", "摘要", "收入", "支出", "余额"],
  "mapping_json": {
    "交易日期": "business_date",
    "摘要": "summary_text",
    "收入": "income_amount",
    "支出": "expense_amount",
    "余额": "previous_balance_input"
  },
  "created_by": "manual"
}
```

---

## 7. Bank Import

### POST /api/bank-import/upload
Multipart upload.
- `file` (binary): xlsx/xls/csv file

Response:
```json
{
  "code": 0,
  "data": {
    "batch_code": "BANK_20260410_0001",
    "file_name": "中行流水.xls",
    "detected_format": "xls",
    "row_count": 36,
    "template_match": {
      "matched": true,
      "template_id": 1,
      "template_name": "中国银行标准流水",
      "confidence": "high"
    }
  }
}
```

### POST /api/bank-import/preview
Trigger parsing with template.
```json
{
  "batch_code": "BANK_20260410_0001",
  "template_id": 1
}
```
Response: parsed rows, abnormal rows, match suggestions.

### POST /api/bank-import/commit
Commit confirmed rows to fund_events.
```json
{
  "batch_code": "BANK_20260410_0001",
  "confirm_rows": [1, 2, 3],
  "fixes": [
    { "row_no": 5, "account_id": 3, "entity_id": 2 }
  ]
}
```
Response:
```json
{ "code": 0, "data": { "committed_count": 34, "abnormal_count": 2, "batch_status": "committed" } }
```

---

## 8. Manual Field Pool

### GET /api/manual-field-pool
Returns all field pool entries.
```json
{
  "code": 0,
  "data": [
    {
      "id": 1, "field_code": "business_date", "field_name_cn": "业务日期",
      "data_type": "date", "is_core": true, "is_default_visible": true,
      "is_disable_allowed": false, "is_parse_key": true, "is_validation_key": true,
      "is_batch_inheritable": false, "status": "active"
    }
  ]
}
```

---

## 9. Manual Flow — Schemes

### GET /api/manual-flow/schemes
```json
{
  "code": 0,
  "data": [
    {
      "id": 1, "scheme_code": "manual_multi_subject_basic",
      "scheme_name": "多主体总表标准版", "description": "默认多主体手工总表",
      "selected_fields": ["entity_match_key", "account_match_key", "business_date", "summary_text", "counterparty_name", "income_amount", "expense_amount"],
      "is_default": true, "status": "active"
    }
  ]
}
```

### POST /api/manual-flow/schemes
```json
{
  "scheme_code": "custom_001",
  "scheme_name": "自定义方案",
  "description": "含部门和收支类型",
  "selected_fields": ["entity_match_key", "account_match_key", "business_date", "summary_text", "counterparty_name", "income_amount", "expense_amount", "department", "income_expense_type"],
  "is_default": false
}
```

### PUT /api/manual-flow/schemes/{id}
Same fields as POST.

---

## 10. Manual Flow — Quick Entry

### POST /api/manual-flow/quick-entry/save
Save rows to a new batch with status=previewed.
```json
{
  "scheme_code": "manual_multi_subject_basic",
  "rows": [
    {
      "entity_match_key": "养护公司",
      "account_match_key": "农商行手工户",
      "business_date": "2026-03-02",
      "summary_text": "支付零星采购",
      "counterparty_name": "某文具店",
      "income_amount": null,
      "expense_amount": 320,
      "note_text": "现金付款"
    }
  ]
}
```
Response:
```json
{
  "code": 0,
  "data": {
    "batch_code": "MANUAL_20260302_0001",
    "saved_count": 1,
    "abnormal_count": 0
  }
}
```

---

## 11. Manual Flow — Excel Upload

### POST /api/manual-flow/preview
Multipart:
- `file` (binary): Excel multi-subject workbook
- `scheme_code` (string)

Response:
```json
{
  "code": 0,
  "data": {
    "batch_code": "MANUAL_20260302_0002",
    "parsed_rows": [
      { "row_no": 1, "entity_match_key": "实业公司", "account_match_key": "中行手工户", "business_date": "2026-03-01", "summary_text": "期初承接", "income_amount": 0, "expense_amount": 0, "parse_status": "valid" }
    ],
    "abnormal_rows": [],
    "match_suggestions": [],
    "total_count": 12,
    "valid_count": 12,
    "abnormal_count": 0
  }
}
```

### POST /api/manual-flow/commit
```json
{
  "batch_code": "MANUAL_20260302_0002",
  "confirm_rows": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
  "fixes": []
}
```
Response:
```json
{ "code": 0, "data": { "committed_count": 12, "abnormal_count": 0, "batch_status": "committed" } }
```

### POST /api/manual-flow/export-template
Export empty Excel template based on scheme.
```json
{ "scheme_code": "manual_multi_subject_basic", "include_example_rows": true }
```
Response: binary xlsx file download.

---

## 12. Base Data Table

### GET /api/base-data
Query params:
- `start_date` / `end_date` (date, optional)
- `entity_id` (int, optional)
- `account_id` (int, optional)
- `keyword` (string, optional)
- `page` / `page_size`

Response:
```json
{
  "code": 0,
  "data": {
    "items": [
      {
        "id": 1, "batch_id": 1, "source_type": "manual_excel",
        "business_date": "2026-03-02", "entity_id": 1, "entity_name": "实业公司",
        "account_id": 1, "account_name": "中行手工户",
        "direction": "income", "income_amount": 350000, "expense_amount": 0,
        "summary_text": "收到工程款", "counterparty_name": "某工程建设单位",
        "previous_balance_input": 200000, "rolling_balance": 550000,
        "parse_status": "valid", "abnormal_code": null
      }
    ],
    "total": 49, "page": 1, "page_size": 50, "total_pages": 1
  }
}
```

### POST /api/base-data/rebuild
Rebuild base data from all committed batches (clears and regenerates).
```json
{ "confirm": true }
```
Response:
```json
{ "code": 0, "data": { "total_rows": 49, "valid_rows": 44, "abnormal_rows": 5, "rebuild_time": "2026-04-10T10:00:00" } }
```

---

## 13. Reports — Generate & Query

### POST /api/reports/generate
Generate report for a date range.
```json
{
  "start_date": "2026-03-01",
  "end_date": "2026-03-05",
  "report_name": "资金日报_2026年3月上旬"
}
```
Response:
```json
{
  "code": 0,
  "data": {
    "report_code": "RPT_20260301_0001",
    "start_date": "2026-03-01",
    "end_date": "2026-03-05",
    "status": "confirmed",
    "total_fund_events": 12,
    "generated_at": "2026-04-10T10:05:00"
  }
}
```

### GET /api/reports/daily
Query fund_events as daily report view.
Query params:
- `start_date` / `end_date` (required)
- `entity_id` / `account_id` (optional)
- `keyword` (optional)
- `page` / `page_size`

Response: same as `/api/base-data` but with rolling_balance guaranteed populated.

### GET /api/reports/account-balance
Account balance summary for a date range.
Query params:
- `start_date` / `end_date` (required)
- `entity_id` (optional)

Response:
```json
{
  "code": 0,
  "data": [
    { "entity_code": "E001", "entity_name": "实业公司", "account_code": "A001", "account_name": "中行手工户", "account_type": "银行账户", "opening_balance": 200000, "total_income": 350000, "total_expense": 125600, "ending_balance": 424400 }
  ]
}
```

### GET /api/reports/income-detail
Income entries within date range.
Query params: same as `/api/reports/daily`.
Response: filtered fund_events where `income_amount > 0`.

### GET /api/reports/expense-detail
Expense entries within date range.
Query params: same as `/api/reports/daily`.
Response: filtered fund_events where `expense_amount > 0`.

---

## 14. Export & Print

### POST /api/export/excel
Export specified data to Excel.
```json
{
  "export_type": "base_data | account_balance | income_detail | expense_detail | full_report",
  "start_date": "2026-03-01",
  "end_date": "2026-03-05",
  "entity_id": null,
  "account_id": null,
  "format": "xlsx"
}
```
Response: binary xlsx file download.

### GET /api/export/print-data
Returns print-formatted data (no binary, just JSON for frontend print view).
Query params: same as report query.
Response: paginated data with print-friendly field names.

---

## 15. Dashboard

### GET /api/dashboard/metrics
```json
{
  "code": 0,
  "data": {
    "today_income": 180000,
    "today_expense": 125650,
    "total_balance": 1646990,
    "account_count": 6,
    "entity_count": 5
  }
}
```

### GET /api/dashboard/trends
Query params:
- `period` (string): 7d / 30d / 90d
- `entity_id` (int, optional)

Response:
```json
{
  "code": 0,
  "data": {
    "dates": ["2026-03-01", "2026-03-02", "..."],
    "income": [0, 350500, "..."],
    "expense": [0, 125920, "..."],
    "balance": [200000, 424580, "..."]
  }
}
```

---

## 16. AI Configuration

### GET /api/ai-configs
```json
{
  "code": 0,
  "data": [
    { "id": 1, "provider": "zhipu", "display_name": "智谱 GLM-4", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model_name": "glm-4-flash", "is_default": true, "status": "active" }
  ]
}
```
Note: `api_key_encrypted` is never returned in GET responses.

### POST /api/ai-configs
```json
{ "provider": "zhipu", "display_name": "智谱 GLM-4", "api_key": "sk-xxx", "base_url": "https://open.bigmodel.cn/api/paas/v4", "model_name": "glm-4-flash", "is_default": true }
```

### PUT /api/ai-configs/{id}
Same fields as POST. `api_key` is optional — omit to keep existing.

### POST /api/ai-configs/{id}/test
Test AI connection.
```json
{ "code": 0, "data": { "connected": true, "latency_ms": 230, "model_info": "glm-4-flash" } }
```

---

## 17. Agent Configuration

### GET /api/agent-configs
```json
{
  "code": 0,
  "data": [
    { "id": 1, "agent_code": "shared", "agent_name": "共享能力区", "agent_type": "shared", "workspace_dir": "agents/shared", "ai_config_id": 1, "description": "所有 agent 共享的通用能力", "status": "active" }
  ]
}
```

### PUT /api/agent-configs/{id}
```json
{ "agent_name": "共享能力区", "ai_config_id": 1, "description": "更新描述" }
```

---

## 18. Backup & Restore

### POST /api/backup/create
```json
{ "backup_name": "手动备份_20260410", "description": "日报生成前备份" }
```
Response:
```json
{ "code": 0, "data": { "backup_id": "bk_20260410_001", "file_name": "bk_20260410_001.zip", "file_size_mb": 12.3, "created_at": "2026-04-10T10:00:00" } }
```

### GET /api/backup/list
```json
{
  "code": 0,
  "data": [
    { "backup_id": "bk_20260410_001", "file_name": "bk_20260410_001.zip", "file_size_mb": 12.3, "description": "日报生成前备份", "created_at": "2026-04-10T10:00:00" }
  ]
}
```

### POST /api/backup/restore
```json
{ "backup_id": "bk_20260409_001" }
```
Response:
```json
{ "code": 0, "data": { "restored": true, "backup_time": "2026-04-09T18:00:00" } }
```

---

## 19. Batch Rollback

### POST /api/batches/{batch_code}/rollback
```json
{ "confirm": true }
```
Response:
```json
{
  "code": 0,
  "data": {
    "removed_row_count": 36,
    "affected_report_hint": "1 份已生成的日报可能受影响，建议重新生成",
    "batch_status": "rolled_back"
  }
}
```

---

## 20. Operation Logs

### GET /api/operation-logs
Query params:
- `module` (string, optional): import / manual / report / backup / system
- `batch_id` (int, optional)
- `start_date` / `end_date` (optional)
- `page` / `page_size`

Response:
```json
{
  "code": 0,
  "data": {
    "items": [
      { "id": 1, "action": "batch_commit", "module": "import", "batch_id": 1, "detail_json": { "batch_code": "BANK_20260410_0001", "row_count": 36 }, "created_at": "2026-04-10T08:24:00" }
    ],
    "total": 100, "page": 1, "page_size": 50, "total_pages": 2
  }
}
```
