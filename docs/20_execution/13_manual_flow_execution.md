# 13 Manual Flow Execution

## 1. Module goal

Build the confirmed dual-track manual flow mechanism.

Track A:
- in-system quick entry

Track B:
- Excel multi-subject workbook upload
- **AI 智能解析列映射（通过用户选择的 Agent 智能体）**

Both tracks must end in the same preview -> maintenance -> base data pipeline.

## 2. Key product rule

Manual flow must be faster than old Excel practice.

The system must support one workbook containing many entities and many manual fund carriers.

The system must not force one account per file.

## 3. Frontend pages

- `frontend/src/views/ManualFlow.vue`
- `frontend/src/views/ManualMaintenance.vue`
- `frontend/src/views/UploadPreview.vue`

### 智能体调用（Round 11 增强）

手工流水页面的工具栏增加「调用智能体」下拉框，用于 Excel 上传时的 AI 智能列映射。用户可选择任意已创建的 Agent 智能体来解析手工流水表头。

**Excel 上传两种模式：**
1. **上传预览** — 需要活跃的 ParserArtifact，由通用 Agent 生成（旧 FundAgent `parser.manual` 已删除）
2. **AI 智能解析** — 使用选定的 Agent 智能体，基于当前方案的 field_pool 进行列映射分析

## 4. Track A: quick entry

### UI requirements

- one large editable table
- user may select template scheme before entry
- user may paste multiple rows
- common context fields may be inherited by batch
- no repeated pop-up form per row

### save targets

Quick-entry rows first enter manual batch staging, not final report directly.

## 5. Track B: Excel multi-subject upload

### workbook rule

One workbook may include:

- multiple entities
- multiple manual bank accounts
- multiple cash accounts
- multiple other manual fund carriers

### required parsing principle

A row must be converted to one standard fund event after:

- entity/account matching
- field mapping
- validation
- abnormal routing if needed

### AI 智能解析流程

1. 用户选择智能体 + 选择方案
2. 上传 Excel 文件
3. 系统检测表头
4. 调用 `POST /api/manual-flow/ai-parse`（传入 `agent_id`, `scheme_code`, `headers`）
5. AI 返回 `{Excel列名: field_code}` 映射和置信度
6. 用户确认映射 → 提交入库

### forbidden assumption

Do not rely on merged-cell visual blocks as the only ownership marker.

## 6. Field scheme support

The manual page must support field scheme selection:

- choose preset
- choose enabled optional fields
- order columns
- save as scheme
- export empty Excel template from the same scheme

## 7. Backend files

- `backend/api/manual_flow.py`
- `backend/services/manual_flow_service.py`
- `backend/services/manual_scheme_service.py`

## 8. APIs

- `GET /api/manual-flow/field-pool` — 字段池
- `GET /api/manual-flow/schemes`
- `POST /api/manual-flow/schemes`
- `PUT /api/manual-flow/schemes/{id}`
- `POST /api/manual-flow/quick-entry/save`
- `POST /api/manual-flow/upload`
- `POST /api/manual-flow/preview`
- `POST /api/manual-flow/commit`
- `POST /api/manual-flow/export-template`
- **`POST /api/manual-flow/ai-parse`** — AI 智能解析（参数：`headers`, `sample_rows`, `agent_id`, `scheme_code`）

## 9. Validation rules

- core recognition fields cannot be disabled
- if entity/account cannot be matched, row must go abnormal
- end balance must not be a mandatory input field
- user-entered ending balance may exist only as optional check value
- one uploaded workbook can contain many accounts

## 10. Done standard

This module is complete only if:

- user can enter rows in-system without repetitive drawers
- user can upload one workbook containing many manual subjects
- all rows enter preview before formal inclusion
- invalid rows route to manual maintenance
- **Excel 上传支持通过选定智能体进行 AI 智能列映射**
