# 31 End To End Acceptance

> E2E 验收场景覆盖主流程和关键异常路径。所有场景使用 samples/ 中的真实样本数据。

---

## Scenario A: 完整日报主流程（手工多主体样本）

### 前置条件
- 应用已启动，数据库为空
- 样本文件：`samples/manual/manual_sample_confirmed.xlsx`
- 期望结果：`samples/expected/manual_sample_confirmed.expected.json`

### 步骤

| # | 操作 | 验证点 |
|---|------|--------|
| 1 | 创建板块"养护板块" | 返回 code=0，id=1 |
| 2 | 创建 5 个法人实体（E001-E005） | 全部 code=0，entity_code 唯一 |
| 3 | 创建 6 个账户（A001, A101, A301, A302, A205, A402），设置对应期初余额 | 期初余额与样本一致 |
| 4 | 为每个账户添加别名（用于手工表匹配） | 别名可用 |
| 5 | POST /api/manual-flow/preview 上传 manual_sample_confirmed.xlsx，scheme_code="manual_multi_subject_basic" | 返回 parsed_rows=12, abnormal_count=0 |
| 6 | POST /api/manual-flow/commit 提交全部 12 行 | committed_count=12, batch_status='committed' |
| 7 | POST /api/base-data/rebuild | valid_rows=12, abnormal_rows=0 |
| 8 | GET /api/base-data 验证基础数据表行数 | items.length=12 |
| 9 | POST /api/reports/generate start_date=2026-03-01, end_date=2026-03-05 | report_code 非空，status='confirmed' |
| 10 | GET /api/reports/account-balance | 验证每个账户 ending_balance 与 expected.json 一致 |
| 11 | GET /api/reports/income-detail | 行数=5（与 samples/reports/manual_sample_confirmed__收入明细表.csv 一致） |
| 12 | GET /api/reports/expense-detail | 行数=5（与 samples/reports/manual_sample_confirmed__支出明细表.csv 一致） |
| 13 | POST /api/export/excel 导出账户余额表 | 文件可下载，大小 > 0 |
| 14 | POST /api/backup/create | 备份成功，list 可见 |

### 预期结果
- 所有 12 条有效行可按 batch_code 追溯
- 基础数据表 12 行，无异常行
- 账户余额表 6 行，期末余额精确匹配：
  - A001=424400, A101=13040, A301=860000, A302=65000, A205=64000, A402=220550
- 收入明细表 5 行，支出明细表 5 行
- Excel 导出可正常打开
- 备份文件含数据库

---

## Scenario B: 回滚后重新生成

### 前置条件
- Scenario A 已完成

### 步骤

| # | 操作 | 验证点 |
|---|------|--------|
| 1 | 记录当前 GET /api/reports/account-balance 结果 | 截图保存 |
| 2 | POST /api/batches/{manual_batch_code}/rollback | removed_row_count=12 |
| 3 | GET /api/base-data | items 为空（或仅剩非回滚数据） |
| 4 | GET /api/reports/account-balance | 返回空或余额=期初余额 |
| 5 | 重新上传 + commit 同一样本 | 新 batch 生成 |
| 6 | POST /api/base-data/rebuild | valid_rows=12 |
| 7 | POST /api/reports/generate 相同日期范围 | 重新生成成功 |
| 8 | GET /api/reports/account-balance | 余额与 Scenario A 一致 |
| 9 | GET /api/operation-logs | 含回滚记录和重新生成记录 |

### 预期结果
- 回滚后 fund_events.parse_status='rolled_back'（非物理删除）
- 重新上传后余额计算结果与首次一致
- 操作日志完整保留回滚和重新生成记录

---

## Scenario C: 异常数据处理

### 前置条件
- 主数据已创建（5 个实体、6 个账户）
- 准备一个含有错误数据的 Excel：实体名错误 1 行、金额为空 1 行、正常行 5 行

### 步骤

| # | 操作 | 验证点 |
|---|------|--------|
| 1 | POST /api/manual-flow/preview 上传异常样本 | abnormal_count=2, valid_count=5 |
| 2 | 检查异常行 abnormal_code | ENTITY_MATCH_FAILED 和 AMOUNT_MISSING |
| 3 | POST /api/manual-flow/commit 仅 confirm 正常行 | committed_count=5 |
| 4 | POST /api/manual-flow/commit 尝试 commit 异常行（不修复） | 应被拒绝或保持 abnormal |
| 5 | POST /api/manual-flow/commit 带 fixes 修复实体归属 | 修复后 commit 成功 |

### 预期结果
- 异常行可被识别且标记正确 abnormal_code
- 仅有效行可被 commit 到 fund_events
- 修复后可正常 commit

---

## Scenario D: 边界条件

### D.1 空数据

| 操作 | 预期 |
|------|------|
| GET /api/base-data（无数据时） | 返回 items=[], total=0 |
| GET /api/home/overview（无数据时） | pending_tasks.total=0, generation_status="未生成" |
| POST /api/reports/generate（无有效 fund_events） | 生成空报表 |

### D.2 重复数据

| 操作 | 预期 |
|------|------|
| 上传相同文件两次 | 第二次应触发重复拦截（abnormal_code='DUPLICATE_SUSPECTED'） |
| 强制 commit 重复行 | 系统允许但标记 duplicate_flag |

### D.3 日期边界

| 操作 | 预期 |
|------|------|
| 生成 start_date > end_date 的报表 | 返回 code=1002 参数错误 |
| 生成跨越多个已有报告区间的报表 | 正常重新计算，不依赖旧缓存 |
