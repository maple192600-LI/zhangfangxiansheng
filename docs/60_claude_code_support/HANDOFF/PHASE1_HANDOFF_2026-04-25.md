# Phase 1 交班单 · 2026-04-25

## 完成范围

- P1-1：已备份当前 DB 到 `backend/data/zhangfang.db.bak.b_plan.20260425`。
- P1-2 / P1-4：`backend/db/tables.py::FundEvent` 已回滚到 CANONICAL_12，删除旧兼容字段。
- P1-3：已恢复 `ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` ORM。
- P1-5：已整理 Alembic v3 链路，当前 head 为 `002_add_v3_artifacts`。
- P1-6：已新增并执行 `scripts/reset_to_v3.py`，当前 SQLite 已重建到 v3 head。
- P1-7：启动逻辑保留 Alembic upgrade head，移除清理 v3 残余表的旧逻辑。
- P1-8：下游旧写入路径已显式挂起，避免继续按旧 schema 写入 `fund_events`。

## 当前 DB 状态

- `alembic_version`: `002_add_v3_artifacts`
- 活动业务表：20 张
- `fund_events` 列：`id` + CANONICAL_12 + `batch_id` / `parser_artifact_id` / `created_at` / `updated_at`

## 已挂起的运行时能力

- `bank_import_service.commit`：等待 Parser artifact + Runtime 接管。
- `manual_flow_service.quick_entry_save` / `preview_manual` / `commit_manual`：等待 `parser.manual` artifact + Runtime 接管。
- 手工流水模板字段池仍需 Phase 7 重新整理为字段字典 / 别名库 / 隐私三档的一部分。

## 验收命令

- `backend\venv\Scripts\python.exe -m alembic current` → `002_add_v3_artifacts (head)`
- `python tools/guards/check_canonical_schema.py` → OK
- `backend\venv\Scripts\python.exe -m pytest tests\db\test_v3_tables.py -q` → 12 passed
- `backend\venv\Scripts\python.exe -m pytest tests\fund -q` → 210 passed
- `backend\venv\Scripts\python.exe -m compileall backend\api backend\services backend\db backend\core scripts -q` → exit 0

## Phase 2 接手点

1. 创建 `backend/agents/fund/` 实体目录。
2. 建立 harness、schemas、memory 骨架。
3. 对接本 Phase 已恢复的三张 artifact 表，但不实现 5 skill 细节。

## 是否达到 Phase 2 进入条件

YES。ORM、Alembic、SQLite 已对齐到 v3 CANONICAL_12 + 三张 artifact 表；`check_canonical_schema.py` 已转绿。
