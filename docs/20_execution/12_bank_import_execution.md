# 12 Bank Import Execution

## 1. Module goal

Implement structured bank file upload, ParserArtifact matching, deterministic parsing preview, and formal write-in.

## 2. Scope

Must build:

- multi-file upload
- read xlsx / xls / csv
- ParserArtifact matching（active status parser 自动匹配）
- deterministic parsing via ParserArtifact code execution
- preview grid
- formal write-in to fund_events
- batch id generation

Must not build now:

- OCR parsing for bank files
- free-form AI auto-fix
- high-risk auto ownership decision without confirmation

## 3. Pages

### page
`frontend/src/views/BankImport.vue`

Required regions:

- upload area（拖拽或点击上传）
- upload result panel（批次号、文件名、格式、数据行）
- parser match panel（匹配到的 ParserArtifact 信息）
- preview grid（解析预览表格）
- commit confirmation

## 4. Backend files

- `backend/api/bank_import.py`
- `backend/services/bank_import_service.py`
- `backend/core/parser_engine.py`
- `backend/core/artifact_runtime.py`

## 5. Workflow

1. user uploads bank file
2. system reads structure, detects format and header row
3. system matches active ParserArtifact（kind="bank", status="active"）
4. if matched: display parser info, proceed to preview
5. if not matched: show hint to create parser via AI Agent
6. user clicks preview
7. system runs ParserArtifact code via artifact_runtime.run_parser
8. display parsed rows（valid + abnormal counts）
9. user confirms write-in
10. system writes records with batch_id and parser_artifact_id

## 6. Preview required columns

- file name
- matched parser artifact
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
- every imported row must carry `parser_artifact_id`
- parsing uses deterministic ParserArtifact code, no LLM calls during execution（§C8）

## 8. APIs

- `POST /api/bank-import/upload` — 上传文件，返回 batch + parser_match
- `POST /api/bank-import/preview` — 预览解析（参数：batch_code + parser_artifact_id）
- `POST /api/bank-import/commit` — 确认入库（参数：batch_code + parser_artifact_id）

## 9. Done standard

Complete only if:

- at least 1 bank format with active ParserArtifact can be previewed
- committed rows can be traced by batch id
- committed rows carry parser_artifact_id
- parsing is fully deterministic（no LLM call during execution）
