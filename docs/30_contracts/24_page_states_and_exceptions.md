# 24 Page States And Exceptions

## 1. Purpose

This file defines required UI states and abnormal routing.

## 2. Home page states

### 工作总览
- empty: no work started
- running: batches pending
- blocked: abnormal rows block generation
- done: latest daily run completed

## 3. Bank import page states

- no file
- uploaded waiting parse
- template matched
- template unmatched
- preview ready
- commit success
- commit failed

## 4. Manual flow page states

- empty scheme selected
- editing rows
- saved to staging
- upload parsing
- preview ready
- abnormal exists
- commit success

## 5. Upload preview page states

- no batch selected
- preview loaded
- partially abnormal
- all valid
- all blocked
- committed

## 6. Base data table states

- no valid rows
- valid rows available
- filtered result empty
- rebuilding
- rebuild success

## 7. Report page states

- no date chosen
- no valid base rows
- generated
- export running
- print preview

## 8. Abnormal codes

| code | cn message | action |
|---|---|---|
| ENTITY_MATCH_FAILED | 法人识别失败 | user confirms entity |
| ACCOUNT_MATCH_FAILED | 账户识别失败 | user confirms account |
| CORE_FIELD_MISSING | 核心字段缺失 | user edits row |
| DUPLICATE_SUSPECTED | 疑似重复 | user chooses keep or drop |
| BALANCE_CHECK_FAILED | 余额校验失败 | user checks row group |
| TEMPLATE_PARSE_FAILED | 模板解析失败 | user reselects scheme or mapping |

## 9. Display rule

All abnormal rows must be visible in preview or maintenance page.
No abnormal row may silently enter formal valid base data.
