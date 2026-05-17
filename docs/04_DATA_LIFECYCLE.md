# 数据生命周期

## 核心事实表：FundEvent

FundEvent 是本系统的核心事实表，所有资金流水最终收敛于此。

`state` 字段隔离不同状态的数据：
- `正常` — 已确认的正常流水
- `待确认` — 等待用户确认
- `异常` — 检测到异常需处理
- `已作废` — 标记为作废

## 数据流入路径

### 银行流水导入

```
上传 Excel → bank_import_service.preview() → 预览 → bank_import_service.commit() → FundEvent
```

- `bank_import_service` 调用 `artifact_runtime.run_parser`，但因 NotImplementedError，当前走硬编码解析路径
- `parser_engine.py` 提供格式检测、表头识别、数据读取等基础能力
- commit 时批量写入 FundEvent，关联 ImportBatch

### 手工流水 — Track A 快速录入

```
用户填写表单 → manual_flow_service.quick_entry_save() → FundEvent
```

- **已有独立路径**，直接写入 FundEvent，不应被重建
- 无需经过 preview/commit

### 手工流水 — Track B Excel 上传

```
上传 Excel → AI 解析映射 → preview() → commit() → FundEvent
```

- `manual_flow_service` 中 Excel 上传路径走 `core.ai_parse_utils` 做 AI 映射
- `ManualCommitBody.parser_artifact_id` 为 Optional，当前可不指定 parser artifact
- commit 时关联 ImportBatch

### 手工流水 Excel 当前注意事项

- `parser_artifact_id` 在 `ManualCommitBody` 中是 Optional，不强制关联 parser
- AI 解析通过 `core.ai_parse_utils` 完成，不经过 `artifact_runtime.run_parser`

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
FundEvent.parser_artifact_id → ParserArtifact.id（创建和审核可用，执行阻断）
RuleArtifact.template_id → ReportTemplate.id（创建和审核可用，执行阻断）
```

## 不要做的事

- 不要提出新暂存表作为既定方案，除非代码事实证明必须
- 不要重建手工流水快速录入路径（Track A 已可用）
- 不要声称 `run_parser` / `run_rule` 已实现

---
**校准来源：** `backend/db/tables.py`、`backend/services/bank_import_service.py`、`backend/services/manual_flow_service.py`、`backend/services/base_data_service.py`、`backend/api/batch.py`、`backend/core/artifact_runtime.py`
**最后校准：** 2026-05-17
