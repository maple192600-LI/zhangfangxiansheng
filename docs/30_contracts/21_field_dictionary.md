# 21 Field Dictionary Contract

## 1. Purpose

This file defines the canonical field names used across backend, frontend, import, manual flow, preview, and reports.

No module may invent a new meaning for an existing field code.

## 2. Canonical fields

| field_code | cn_name | type | layer | notes |
|---|---|---|---|---|
| entity_match_key | 法人识别键 | text | input | code or alias for entity match |
| entity_name | 法人名称 | text | display | auto-filled when matched |
| entity_code | 法人编码 | text | display | auto-filled when matched |
| account_match_key | 账户识别键 | text | input | code or alias for account match |
| account_name | 账户名称 | text | display | auto-filled when matched |
| account_code | 账户编码 | text | display | auto-filled when matched |
| account_type | 账户类型 | text | display | auto-filled when matched |
| bank_name | 开户银行 | text | display | auto-filled when matched |
| branch_name | 开户行 | text | display | auto-filled when matched |
| account_number_masked | 账号信息 | text | display | masked |
| business_date | 业务日期 | date | core | required |
| business_time | 业务时间 | text | optional | |
| summary_text | 摘要 | text | core | required |
| counterparty_name | 对方名称 | text | core | required |
| income_amount | 收入 | number | core | |
| expense_amount | 支出 | number | core | |
| previous_balance_input | 上期余额 | number | optional check | |
| ending_balance_input | 期末余额 | number | optional check | not required |
| direction | 收支方向 | text | derived | can be inferred |
| group_name | 分组 | text | optional | from field pool |
| department_name | 所属部门 | text | optional | from field pool |
| income_expense_type | 收支类型 | text | optional | from field pool |
| handler_name | 经办人 | text | optional | from field pool |
| owner_name | 负责人 | text | optional | from field pool |
| note_text | 备注 | text | optional | from field pool |
| pending_recovery_flag | 待回补 | bool | optional | from field pool |
| voucher_no | 凭证号 | text | optional | from field pool |
| receipt_no | 回单编号 | text | optional | from field pool |

## 3. Rules

- `entity_match_key` and `account_match_key` are preferred manual input keys
- `entity_name`, `entity_code`, `account_name`, `account_code`, `bank_name`, `branch_name` may be auto-filled after match
- `business_date`, `summary_text`, `counterparty_name`, and at least one of `income_amount` / `expense_amount` are mandatory for a valid row
- `ending_balance_input` is optional and only for validation

## 4. Validation rules

### 核心字段验证

| field_code | 必填 | 验证规则 | 错误 abnormal_code |
|------------|------|---------|-------------------|
| entity_match_key | 是 | 非空，能在 account_aliases 或 entities 中匹配 | ENTITY_MATCH_FAILED |
| account_match_key | 是 | 非空，能在 account_aliases 或 accounts 中匹配 | ACCOUNT_MATCH_FAILED |
| business_date | 是 | 日期格式 YYYY-MM-DD 或 YYYY.MM.DD，不晚于今天 | DATE_INVALID |
| summary_text | 是 | 非空，最大 500 字符 | SUMMARY_MISSING |
| counterparty_name | 条件必填 | 正常交易必填，期初承接行可为空 | COUNTERPARTY_MISSING |
| income_amount | 至少一个 | 数字 >= 0，最多 2 位小数，income/expense 不能同时 > 0 | AMOUNT_INVALID |
| expense_amount | 至少一个 | 数字 >= 0，最多 2 位小数 | AMOUNT_INVALID |
| previous_balance_input | 否 | 数字 >= 0，用于辅助校验 | BALANCE_MISMATCH（警告） |
| ending_balance_input | 否 | 数字，用于与系统计算值对比 | BALANCE_MISMATCH |

### 可选字段验证

| field_code | 验证规则 | 默认值 |
|------------|---------|--------|
| business_time | 格式 HH:MM 或 HH:MM:SS，不校验 | null |
| group_name | 非空字符串，最大 50 字符 | null |
| department_name | 非空字符串，最大 50 字符 | null |
| income_expense_type | 非空字符串，最大 30 字符 | null |
| handler_name | 非空字符串，最大 30 字符 | null |
| owner_name | 非空字符串，最大 30 字符 | null |
| note_text | 字符串，最大 500 字符 | null |
| pending_recovery_flag | 布尔值 "是"/"否" 或 true/false | false |
| voucher_no | 字符串，最大 50 字符 | null |
| receipt_no | 字符串，最大 50 字符 | null |

### 匹配优先级

entity_match_key 匹配顺序：
1. entities.entity_code（精确匹配）
2. entities.short_name（精确匹配）
3. account_aliases.alias_text（精确匹配）
4. entities.name（模糊包含匹配，需用户确认）

account_match_key 匹配顺序：
1. accounts.account_code（精确匹配）
2. account_aliases.alias_text（精确匹配）
3. accounts.account_alias（精确匹配）

### 日期格式兼容

系统必须接受以下日期格式并统一转换为 YYYY-MM-DD 存储：
- `YYYY-MM-DD` → 直接使用
- `YYYY.MM.DD` → 替换 `.` 为 `-`
- `YYYY/MM/DD` → 替换 `/` 为 `-`
- `YYYYMMDD` → 插入分隔符

- `entity_match_key` and `account_match_key` are preferred manual input keys
- `entity_name`, `entity_code`, `account_name`, `account_code`, `bank_name`, `branch_name` may be auto-filled after match
- `business_date`, `summary_text`, `counterparty_name`, and at least one of `income_amount` / `expense_amount` are mandatory for a valid row
- `ending_balance_input` is optional and only for validation
