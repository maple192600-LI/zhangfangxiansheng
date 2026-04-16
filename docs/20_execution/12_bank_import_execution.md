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
