# 30 Module Test Cases

> 每个测试用例包含：前置条件、步骤、预期结果、断言。

---

## 1. Master Data

### TC-1.1 创建板块

| 项目 | 内容 |
|------|------|
| 前置条件 | 数据库为空或已有板块数据 |
| 步骤 | 1. POST /api/divisions `{ "name": "养护板块", "sort_order": 0 }` |
| 预期结果 | 返回 code=0，data 含 id、name、status="enabled" |
| 断言 | GET /api/divisions 返回列表含新板块 |

### TC-1.2 创建法人实体

| 项目 | 内容 |
|------|------|
| 前置条件 | 板块已创建 |
| 步骤 | 1. POST /api/entities `{ "division_id": 1, "entity_code": "E001", "name": "山西喜跃发实业发展有限公司", "short_name": "实业公司" }` |
| 预期结果 | 返回 code=0，entity_code 唯一 |
| 断言 | GET /api/entities?division_id=1 返回含该实体 |

### TC-1.3 创建账户并设期初余额

| 项目 | 内容 |
|------|------|
| 前置条件 | 法人实体已存在 |
| 步骤 | 1. POST /api/accounts `{ "entity_id": 1, "account_code": "A001", "account_alias": "中行手工户", "account_type": "银行账户", "instrument_type": "银行存款", "input_method": "manual", "initial_balance": 200000, "balance_date": "2026-03-01" }` |
| 预期结果 | 账户创建成功，initial_balance=200000 |
| 断言 | GET /api/accounts/1 返回 initial_balance=200000, balance_date=2026-03-01 |

### TC-1.4 禁用账户

| 项目 | 内容 |
|------|------|
| 前置条件 | 账户已创建且 status=enabled |
| 步骤 | 1. PUT /api/accounts/1 `{ "status": "disabled" }` |
| 预期结果 | 状态变为 disabled |
| 断言 | GET /api/accounts?status=disabled 返回含该账户；GET /api/accounts?status=enabled 不含 |

### TC-1.5 添加别名

| 项目 | 内容 |
|------|------|
| 前置条件 | 账户已创建 |
| 步骤 | 1. POST /api/accounts/1/aliases `{ "alias_text": "中行户", "alias_type": "short_name" }` |
| 预期结果 | 别名添加成功 |
| 断言 | GET /api/accounts/1/aliases 返回含 alias_text="中行户" |

### TC-1.6 按状态查询

| 项目 | 内容 |
|------|------|
| 前置条件 | 至少有 2 个不同状态的账户 |
| 步骤 | 1. GET /api/accounts?status=enabled |
| 预期结果 | 仅返回 status=enabled 的账户 |
| 断言 | 返回列表中所有账户 status 均为 "enabled" |

---

## 2. Bank Import

### TC-2.1 导入已匹配模板的银行文件

| 项目 | 内容 |
|------|------|
| 前置条件 | parser_templates 中已存在对应模板 |
| 步骤 | 1. POST /api/bank-import/upload 上传 xlsx 文件<br>2. POST /api/bank-import/preview `{ "batch_code": "...", "template_id": 1 }`<br>3. POST /api/bank-import/commit `{ "batch_code": "...", "confirm_rows": [全部行] }` |
| 预期结果 | 上传返回 batch_code 和模板命中；预览返回解析行；commit 后 fund_events 写入成功 |
| 断言 | fund_events 表中存在对应 batch_id 的记录，parse_status='valid' |

### TC-2.2 导入未匹配模板的文件

| 项目 | 内容 |
|------|------|
| 前置条件 | 无匹配模板 |
| 步骤 | 1. POST /api/bank-import/upload 上传未知格式文件 |
| 预期结果 | 返回 template_match.matched=false，提示需要手动选模板或创建模板 |
| 断言 | batch_status='uploaded'，无 fund_events 写入 |

### TC-2.3 保存模板后重新导入

| 项目 | 内容 |
|------|------|
| 前置条件 | TC-2.2 已上传但未命中 |
| 步骤 | 1. POST /api/parser-templates 创建新模板<br>2. POST /api/bank-import/preview 使用新模板 ID<br>3. POST /api/bank-import/commit |
| 预期结果 | 新模板可成功解析同格式文件 |
| 断言 | fund_events 正确写入，字段映射正确 |

### TC-2.4 验证批次 ID 和原始数据保留

| 项目 | 内容 |
|------|------|
| 前置条件 | TC-2.1 已完成 |
| 步骤 | 1. 查询 import_batches 表<br>2. 查询 fund_events 表中 batch_id 对应记录的 raw_data_json |
| 预期结果 | batch 记录存在且 status='committed'；每条 fund_event 的 raw_data_json 非空 |
| 断言 | raw_data_json 包含原始行数据 |

---

## 3. Manual Flow

### TC-3.1 快速录入（基础方案）

| 项目 | 内容 |
|------|------|
| 前置条件 | 手工方案"多主体总表标准版"已存在，账户和实体已创建 |
| 步骤 | 1. POST /api/manual-flow/quick-entry/save 提交 3 行数据<br>2. POST /api/manual-flow/commit |
| 预期结果 | 3 条记录写入 fund_events |
| 断言 | fund_events 中 source_type='manual_quick'，行数=3 |

### TC-3.2 上传多主体 Excel 工作簿

| 项目 | 内容 |
|------|------|
| 前置条件 | 手工方案已存在，使用 samples/manual/manual_sample_confirmed.xlsx |
| 步骤 | 1. POST /api/manual-flow/preview 上传文件 + scheme_code<br>2. 验证返回 12 行解析结果 |
| 预期结果 | 12 行全部 parse_status='valid'，无异常行 |
| 断言 | expected_counts 与 samples/expected/manual_sample_confirmed.expected.json 一致 |

### TC-3.3 预览异常行

| 项目 | 内容 |
|------|------|
| 前置条件 | 上传含错误数据的 Excel（实体名不存在、金额为空等） |
| 步骤 | 1. POST /api/manual-flow/preview |
| 预期结果 | 异常行 parse_status='abnormal'，abnormal_code 非空 |
| 断言 | 返回的 abnormal_rows 不为空 |

### TC-3.4 确认有效行

| 项目 | 内容 |
|------|------|
| 前置条件 | TC-3.2 预览完成 |
| 步骤 | 1. POST /api/manual-flow/commit `{ "batch_code": "...", "confirm_rows": [1..12], "fixes": [] }` |
| 预期结果 | 12 行全部写入 fund_events，batch_status='committed' |
| 断言 | fund_events 中 batch_id 对应 12 条记录，parse_status='valid' |

---

## 4. Base Data and Reports

### TC-4.1 重建基础数据

| 项目 | 内容 |
|------|------|
| 前置条件 | 至少有 1 个 committed batch |
| 步骤 | 1. POST /api/base-data/rebuild `{ "confirm": true }` |
| 预期结果 | 返回 valid_rows 和 abnormal_rows 计数 |
| 断言 | GET /api/base-data 返回与 fund_events(valid) 一致的行数 |

### TC-4.2 按单日生成

| 项目 | 内容 |
|------|------|
| 前置条件 | 基础数据已存在 |
| 步骤 | 1. POST /api/reports/generate `{ "start_date": "2026-03-02", "end_date": "2026-03-02", "report_name": "日报_0302" }` |
| 预期结果 | 生成成功，返回 report_code |
| 断言 | GET /api/reports/daily?start_date=2026-03-02&end_date=2026-03-02 返回当日数据 |

### TC-4.3 按自定义区间生成

| 项目 | 内容 |
|------|------|
| 前置条件 | 基础数据覆盖 2026-03-01 至 2026-03-05 |
| 步骤 | 1. POST /api/reports/generate `{ "start_date": "2026-03-01", "end_date": "2026-03-05", "report_name": "日报_3月上旬" }` |
| 预期结果 | 区间内所有有效 fund_events 被包含 |
| 断言 | 账户余额表的 ending_balance 与 samples/reports/manual_sample_confirmed__账户余额表.csv 一致 |

### TC-4.4 验证滚动余额

| 项目 | 内容 |
|------|------|
| 前置条件 | TC-4.3 已完成，使用 samples/manual 样本数据 |
| 步骤 | 1. GET /api/reports/account-balance?start_date=2026-03-01&end_date=2026-03-05<br>2. 验证每个账户的期末余额 |
| 预期结果 | 余额与 expected.json 中 expected_accounts 的期末余额完全一致 |
| 断言 | A001=424400, A101=13040, A301=860000, A302=65000, A205=64000, A402=220550 |

---

## 5. Ops

### TC-5.1 导出报表

| 项目 | 内容 |
|------|------|
| 前置条件 | 日报已生成 |
| 步骤 | 1. POST /api/export/excel `{ "export_type": "account_balance", "start_date": "2026-03-01", "end_date": "2026-03-05", "format": "xlsx" }` |
| 预期结果 | 返回 xlsx 二进制文件，可正常打开 |
| 断言 | 文件大小 > 0，表头中文不乱码，金额有千分位 |

### TC-5.2 打印预览

| 项目 | 内容 |
|------|------|
| 前置条件 | 在日报页面 |
| 步骤 | 1. 点击打印按钮<br>2. 触发 window.print() |
| 预期结果 | 打印预览中侧栏、按钮、筛选器隐藏；仅表格区域可见 |
| 断言 | @media print CSS 生效，无空白页 |

### TC-5.3 创建备份

| 项目 | 内容 |
|------|------|
| 前置条件 | 数据库有数据 |
| 步骤 | 1. POST /api/backup/create `{ "backup_name": "手动备份", "description": "测试" }` |
| 预期结果 | ZIP 文件生成在 backups/ 目录 |
| 断言 | GET /api/backup/list 返回含新备份；ZIP 内含 db/zhangfang.db 和 meta.json |

### TC-5.4 恢复备份

| 项目 | 内容 |
|------|------|
| 前置条件 | TC-5.3 已创建备份；之后数据库有变更 |
| 步骤 | 1. POST /api/backup/restore `{ "backup_id": "bk_xxx" }` |
| 预期结果 | 数据库恢复到备份时状态 |
| 断言 | 查询数据与备份前一致 |

### TC-5.5 回滚批次

| 项目 | 内容 |
|------|------|
| 前置条件 | 有一个 committed batch |
| 步骤 | 1. POST /api/batches/{batch_code}/rollback `{ "confirm": true }` |
| 预期结果 | 该 batch 的 fund_events 状态改为 rolled_back；提示重新生成 |
| 断言 | fund_events 中该 batch_id 的记录 parse_status='rolled_back'；operation_logs 有回滚记录 |
