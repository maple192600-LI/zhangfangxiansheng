# 13 Manual Flow Execution

## 1. Module goal

Build the confirmed dual-track manual flow mechanism.

Track A:
- in-system quick entry

Track B:
- Excel multi-subject workbook upload

Both tracks must end in the same preview -> maintenance -> base data pipeline.

## 2. Key product rule

Manual flow must be faster than old Excel practice.

The system must support one workbook containing many entities and many manual fund carriers.

The system must not force one account per file.

## 3. Frontend pages

- `frontend/src/views/ManualFlow.vue`
- `frontend/src/views/ManualMaintenance.vue`
- `frontend/src/views/UploadPreview.vue`

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

- `GET /api/manual-flow/schemes`
- `POST /api/manual-flow/schemes`
- `PUT /api/manual-flow/schemes/{id}`
- `POST /api/manual-flow/quick-entry/save`
- `POST /api/manual-flow/upload`
- `POST /api/manual-flow/preview`
- `POST /api/manual-flow/commit`
- `POST /api/manual-flow/export-template`

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
