# 12 Bank Import Execution

## 1. Module goal

Implement structured bank file upload, template matching, AI-assisted column mapping, preview, and formal write-in.

## 2. Scope

Must build:

- multi-file upload
- read xlsx / xls / csv
- parser template skeleton
- template matching
- **AI 智能解析列映射（通过用户选择的 AgentV2 智能体）**
- preview grid
- formal write-in to fund_events
- batch id generation
- raw row JSON retention
- **提交后自动保存解析规则到规则中心（银行流水规则），以识别的银行名称命名模板**

### 智能体调用能力（Round 11 增强）

用户上传银行流水文件后，可选择调用哪个 AI 智能体进行列映射解析。

**核心流程：**
1. 用户在"网银导入"页面选择「调用智能体」下拉框，选择要使用的 AgentV2 智能体
2. 上传银行流水文件后，系统将表头和样本数据发送给选定的智能体
3. 智能体使用其 `role_prompt`（出纳知识）和 `ai_config`（AI 模型配置）进行列映射分析
4. 返回标准字段映射结果（`{银行列名: 标准字段code}`）和置信度
5. 用户确认映射 → 预览 → 提交入库
6. 提交成功后自动将映射保存为规则模板到规则中心，模板名称使用 AI 识别的银行名称（如"招商银行流水解析规则"）

**标准字段列表（供 AI 映射）：**

| 字段 code | 中文名 |
|---|---|
| `business_date` | 交易日期 |
| `income_amount` | 收入金额 |
| `expense_amount` | 支出金额 |
| `counterparty_name` | 对方户名/对方名称 |
| `summary_text` | 摘要/用途 |
| `balance` | 余额 |
| `business_time` | 交易时间 |
| `counterpart_account` | 对方账号 |
| `counterpart_bank` | 对方开户行 |
| `voucher_no` | 凭证号 |
| `transaction_type` | 交易类型 |

**规则自动保存：** `_auto_save_template()` 在 `commit_by_mapping` 时自动触发，将 AI 解析确认后的映射保存到 `ParserTemplate`（template_type='bank'）。同名模板自动更新，新模板自动创建。

Must not build now:

- OCR parsing for bank files
- free-form AI auto-fix
- high-risk auto ownership decision without confirmation

## 3. Pages

### page
`frontend/src/views/BankImport.vue`

Required regions:

- **导入账户选择器** — 选择要导入的银行账户
- **调用智能体选择器** — 选择用于 AI 解析的 AgentV2 智能体
- upload area
- AI parse result display (mapping table)
- preview grid
- template create / confirm dialog

## 4. Backend files

- `backend/api/bank_import.py`
- `backend/services/bank_import_service.py`
- `backend/core/parser_engine.py`
- `backend/core/ai_provider.py`

## 5. Workflow

1. user selects target account
2. user selects AI agent for parsing
3. user uploads files
4. system reads structure
5. system calls selected agent for AI column mapping (`POST /api/bank-import/ai-parse` with `agent_id`)
6. system displays AI mapping result with confidence
7. user reviews mapping, clicks preview
8. system applies mapping and shows parsed preview
9. user confirms write-in
10. system writes records with `batch_id`
11. **system auto-saves mapping as rule template** (named by bank name)

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
- **AI 解析必须通过用户选择的 AgentV2 智能体，不允许使用独立 AI 配置**
- **确认后的解析规则必须自动保存到规则中心**

## 8. APIs

- `POST /api/bank-import/upload` — 上传文件
- `POST /api/bank-import/preview` — 预览解析
- `POST /api/bank-import/commit` — 提交（通过 parser artifact）
- `POST /api/bank-import/commit-by-mapping` — 基于映射提交（含 `template_name`, `sample_headers` 自动保存规则）
- `POST /api/bank-import/ai-parse` — AI 智能解析（参数：`headers`, `sample_rows`, `agent_id`）
- `POST /api/bank-import/save-template` — 手动保存为规则模板
- `GET /api/agent_v2/agents` — 获取可用智能体列表

## 9. Done standard

Complete only if:

- at least 2 different bank formats can be previewed
- unmatched template can be saved then reused
- committed rows can be traced by batch id
- **AI 解析使用用户选择的智能体，映射结果可预览确认**
- **确认后的解析规则自动保存到规则中心的银行流水规则下**
