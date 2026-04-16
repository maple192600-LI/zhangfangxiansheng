# 12 Bank Import Execution

## 1. Module goal

Implement structured bank file upload, template matching, preview, and formal write-in.

## 2. Scope

Must build:

- multi-file upload
- read xlsx / xls / csv
- parser template skeleton
- template matching
- preview grid
- formal write-in to fund_events
- batch id generation
- raw row JSON retention

### Rule Agent 能力（V2 增强）

用户上传银行流水文件后，AI 自动分析文件结构并生成解析规则，而非要求用户手动配置 JSON 映射。

**Rule Agent 职责：**
1. 分析上传的银行文件表头和数据结构
2. 根据基础数据表的字段需求（business_date, income_amount, expense_amount, counterparty_name, summary_text 等）自动匹配
3. 生成 parser_template 的 mapping_json 和 sample_headers
4. 向用户展示识别结果并用自然语言描述（如"我检测到这是招商银行的交易明细，包含交易日期、收入金额、支出金额等字段"）
5. 用户确认后自动保存为银行流水规则

**收支规则字典：** Rule Agent 还负责生成收支分类规则，根据摘要/对方户名自动分类资金用途。

**凭证原始凭证规则：** 根据收支规则自动映射会计科目，为后续凭证生成做准备。

**注意：** V1 阶段先实现基础模板匹配（已有）。Rule Agent 的 AI 自动生成规则能力在后续迭代中实现，当前阶段需确保模板结构可被 Agent 读取和生成。

Must not build now:

- OCR parsing for bank files
- free-form AI auto-fix
- high-risk auto ownership decision without confirmation

## 3. Pages

### page
`frontend/src/views/BankImport.vue`

Required regions:

- upload area
- file status list
- preview grid
- template create / confirm dialog

## 4. Backend files

- `backend/api/bank_import.py`
- `backend/services/bank_import_service.py`
- `backend/core/parser_engine.py`
- `backend/core/ai_provider.py`

## 5. Workflow

1. user uploads files
2. system reads structure
3. system tries parser template match
4. if matched, parse preview
5. if not matched, enter first-time template confirmation
6. user confirms mapping
7. system saves parser template
8. system re-parses preview
9. user confirms write-in
10. system writes records with `batch_id` and `raw_data`

## 6. Preview required columns

- file name
- matched template
- candidate entity / account
- transaction date
- summary
- counterparty
- income
- expense
- balance
- parse status

## 7. Core rules

- no silent formal write without preview
- if ownership is not unique, force user confirmation
- every imported row must carry `batch_id`
- every imported row must carry `raw_data`

## 8. APIs

- `POST /api/bank-import/upload`
- `POST /api/bank-import/preview`
- `POST /api/bank-import/template-confirm`
- `POST /api/bank-import/commit`
- `GET /api/bank-import/batches/{batch_id}`

## 9. Done standard

Complete only if:

- at least 2 different bank formats can be previewed
- unmatched template can be saved then reused
- committed rows can be traced by batch id
