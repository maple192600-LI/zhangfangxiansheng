# 32 Real Sample Regression

## 1. Purpose

Use de-sensitized real samples to prevent false success on mock-only data. Every regression run must pass all items below before merge.

## 2. Required sample groups

| 样本组 | 样本文件 | 状态 | 说明 |
|--------|---------|------|------|
| 手工多主体总表 | `samples/manual/manual_sample_confirmed.xlsx` | 已就绪 | 12 行，5 法人，6 账户，无异常 |
| 手工样本期望结果 | `samples/expected/manual_sample_confirmed.expected.json` | 已就绪 | 完整期望输出定义 |
| 手工报表基准 | `samples/reports/manual_sample_confirmed__*.csv` | 已就绪 | 4 份 CSV 基准 |
| 银行流水（格式 A） | `samples/bank/` | 待补充 | 至少 1 种银行格式 |
| 银行流水（格式 B） | `samples/bank/` | 待补充 | 与格式 A 不同的银行 |
| 异常样本 | 待创建 | 待补充 | 含实体匹配失败、金额为空 |
| 重复疑似样本 | 待创建 | 待补充 | 含重复行 |

## 3. Regression checklist

每次代码变更后，必须逐项验证：

### 3.1 解析器回归

| # | 检查项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| R-1 | 已保存的模板仍能命中同格式文件 | 上传与模板匹配的银行文件 | template_match.matched=true |
| R-2 | 手工工作簿仍能正确拆分 | 上传 manual_sample_confirmed.xlsx | parsed_rows=12, abnormal=0 |
| R-3 | 字段方案仍能导出正确列 | 导出空模板 | 表头与 scheme selected_fields 一致 |

### 3.2 异常路由回归

| # | 检查项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| R-4 | 实体匹配失败仍正确标记 | 上传含错误实体名的文件 | abnormal_code='ENTITY_MATCH_FAILED' |
| R-5 | 金额为空仍正确标记 | 上传含空金额的文件 | abnormal_code='AMOUNT_MISSING' |
| R-6 | 重复拦截仍触发 | 上传已 commit 的相同文件 | abnormal_code='DUPLICATE_SUSPECTED' |

### 3.3 报表计算回归

| # | 检查项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| R-7 | 基础数据表行数 | GET /api/base-data | 与 expected_counts.accepted_rows 一致 |
| R-8 | 账户余额表 | GET /api/reports/account-balance | 每个账户 ending_balance 与 expected_accounts 一致 |
| R-9 | 收入明细行数 | GET /api/reports/income-detail | 与 expected_counts.income_rows 一致 |
| R-10 | 支出明细行数 | GET /api/reports/expense-detail | 与 expected_counts.expense_rows 一致 |
| R-11 | 滚动余额 | 查询某账户的 rolling_balance 序列 | 逐行验证：上一行 rolling_balance + income - expense = 当前行 rolling_balance |
| R-12 | 总收入/总支出 | 汇总 fund_events | 与 expected_totals 一致 |

### 3.4 导出回归

| # | 检查项 | 验证方法 | 通过标准 |
|---|--------|---------|---------|
| R-13 | Excel 导出可正常打开 | 导出后用 openpyxl 读取 | 无异常，行数正确 |
| R-14 | CSV 基准对比 | 导出 CSV 与 samples/reports/ 中的基准对比 | 字段值完全一致 |

## 4. 自动化策略

- **运行频率**：每次合并到 main 分支前必须运行
- **运行方式**：`pytest tests/` 覆盖全部回归项
- **样本管理**：脱敏样本提交到仓库，不包含真实账户信息
- **失败处理**：任一回归项失败则阻止合并，必须修复后重新运行

## 5. Pass/Fail 标准

- **PASS**：全部 14 项回归检查通过
- **FAIL**：任一检查项失败
- 失败时必须记录：失败项编号、实际值、期望值、相关代码变更
