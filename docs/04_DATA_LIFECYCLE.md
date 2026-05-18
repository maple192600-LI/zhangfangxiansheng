# 数据生命周期

## 核心事实表：FundEvent

FundEvent 是本系统的核心事实表，所有资金流水最终收敛于此。

`state` 字段隔离不同状态的数据：
- `正常` — 已确认的正常流水
- `待确认` — 等待用户确认
- `异常` — 检测到异常需处理
- `已作废` — 标记为作废

`FundEvent` 同时承载两类行：

| 行类型 | 状态 | 核心字段要求 | 是否进入基础数据 |
|--------|------|--------------|------------------|
| 上传结果预览行 | `待确认` / `异常` | `business_date`、`entity_code`、`account_code` 可暂缺，供用户在预览页修正 | 否 |
| 正式基础数据行 | `正常` | `business_date`、`entity_code`、`account_code` 必须完整 | 是 |

因此，导入阶段不能用空字符串假装匹配成功；无法匹配的单位/账户编码应保持为空并在上传结果预览中标记异常。提交前必须重新校验，只有全部核心字段完整的行才能从 `待确认` 改为 `正常`。

## 数据流入路径

### 银行流水导入

```
上传 Excel
→ bank_import_service.upload_file()
→ ImportBatch(status=uploaded)
→ Bank Format Identification（识别银行和格式）
→ bank/format 级 ParserArtifact 匹配
→ Parser Runtime 解析流水字段
→ Identity Hints Extraction（提取文件身份线索）
→ Master Data Matching（读取主数据进行匹配）
→ Account Attribution（确定账户/单位归属）
→ import_preview_service 统一预览/编辑/校验
→ commit → FundEvent(state=正常)
```

- 完整链路参见 [`14_BANK_IMPORT_GENERALIZATION.md`](14_BANK_IMPORT_GENERALIZATION.md)
- 网银导入上传后**不直接跳转**上传结果预览；必须先在网银导入页完成 Parser 识别和解析预览，用户确认后才进入上传结果预览
- 无 parser 或 runtime 不可用时停留在网银导入页，显示可读提示，不跳转、不入库
- 最终提交只在上传结果预览页完成，通过 `import_preview_service.commit()` 统一入口
- `artifact_runtime.run_parser` 已实现（底层执行器），ParserArtifact 可真实解析 xlsx。但银行格式识别、身份线索提取、主数据匹配、账户归属均尚未实现，仍需后续交付

### 手工流水 — 快速录入

```
用户填写表单 → manual_flow_service.quick_entry_save() → FundEvent(state=待确认) → import_preview_service 统一预览/编辑/提交 → FundEvent(state=正常)
```

- 快速录入生成批次和待确认 FundEvent，跳转统一上传结果预览页
- 校验通过后通过 `import_preview_service.commit()` 提交为正式数据
- 如果单位、账户或日期无法识别，仍应进入上传结果预览，不应因数据库约束导致整批失败

### 手工流水 — Excel 上传

```
上传 Excel → manual_flow_service.upload_workbook() → ImportBatch → import_preview_service 统一预览/编辑/提交 → FundEvent(state=正常)
```

- source_type 为 `manual_excel`
- 文件以 batch_code 前缀保存，保证稳定查找
- 预览时自动解析文件并创建待确认 FundEvent
- 手工 Excel 不再通过 `manual-flow/commit` 公开入口提交；最终提交统一走上传结果预览页
- 无法匹配的单位/账户和坏日期应作为预览页异常行展示，用户修正后再提交

## 数据流出路径

### 日报/报表生成

```
report_service → 查询 FundEvent + ReportTemplate → 生成报表数据/Excel
```

- `report_service` 使用硬编码逻辑生成各类报表
- `run_rule` 为 NotImplementedError，RuleArtifact 驱动的报表填充路径阻断
- 报表模板支持 Excel 布局渲染（`source_file_path` 指向上传的 Excel）

### 导出

```
export_service → 查询 FundEvent → 生成 Excel
```

## FundEvent 与 Artifact 的关系

```
FundEvent.parser_artifact_id → ParserArtifact.id（创建、审核、执行可用）
RuleArtifact.template_id → ReportTemplate.id（创建和审核可用，执行阻断）
```

## 不要做的事

- 不要提出新暂存表作为既定方案，除非代码事实证明必须
- 不要重建手工流水快速录入路径（Track A 已可用）
- 不要声称银行通用识别已完成（`run_parser` 只是底层执行器，不等于银行格式识别或账户归属匹配）
- 不要声称 `run_rule` 已实现

---
**校准来源：** `backend/db/tables.py`、`backend/services/bank_import_service.py`、`backend/services/manual_flow_service.py`、`backend/services/base_data_service.py`、`backend/api/batch.py`、`backend/core/artifact_runtime.py`
**最后校准：** 2026-05-18
