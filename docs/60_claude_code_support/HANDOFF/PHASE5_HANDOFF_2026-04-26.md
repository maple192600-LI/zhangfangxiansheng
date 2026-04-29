# Phase 5 交班单：Runtime 执行器

## 完成范围

- P5-1：新增 `backend/core/artifact_runtime.py`
  - `run_parser(db, artifact_id, file_path, ctx)`：只加载 `status='active'` 的 `ParserArtifact`
  - 通过 `agents.fund.sandbox.execute()` 执行 artifact code
  - 输出严格走 CANONICAL_12 字典
  - `run_rule(db, artifact_id, ctx)`：只加载 `status='active'` 的 `RuleArtifact`
  - 解析 `placeholder_bindings` 与 `loop_config`，调用白名单 primitives 填充 Excel 模板并返回 Workbook
- P5-2：改造 `backend/services/bank_import_service.py`
  - `commit(batch_code, parser_artifact_id)` 改为调用 `artifact_runtime.run_parser`
  - 写入 `fund_events`，同时记录 `batch_id` 与 `parser_artifact_id`
- P5-3：改造 `backend/services/manual_flow_service.py`
  - 多主体 Excel commit 改为调用 Parser artifact runtime
  - 快速录入路径保持确定性结构化写入，不调用 AI
- P5-4：改造 `backend/services/report_service.py`
  - 新增 `generate_report(db, rule_artifact_id, ctx)`，调用 `artifact_runtime.run_rule`
- P5-5：新增 `backend/core/runtime_guard.py`
  - Runtime 阶段临时阻断 `requests.post`、`urllib.request.urlopen`
  - 兼容阻断已加载的 `core.ai_call.urlopen/chat`
  - `ZF_RUNTIME_NO_AI=1` 时可持久激活阻断
- 补强 P4 sandbox
  - 修复大结果集时父进程先 `join` 后读 `Queue` 导致 1000 行 payload 卡住的问题
  - 父进程改为在 timeout 窗口内持续读取结果队列，再 join 子进程

## 新增文件

- `backend/core/artifact_runtime.py`
- `backend/core/runtime_guard.py`
- `tests/fund/test_artifact_runtime.py`
- `docs/60_claude_code_support/HANDOFF/PHASE5_HANDOFF_2026-04-26.md`

## 修改文件

- `backend/agents/fund/sandbox.py`
- `backend/services/bank_import_service.py`
- `backend/services/manual_flow_service.py`
- `backend/services/report_service.py`
- `backend/api/bank_import.py`
- `backend/api/manual_flow.py`
- `backend/db/schemas.py`

## 验收证据

```powershell
pytest tests\fund\test_artifact_runtime.py -q
3 passed, 1 warning
```

```powershell
pytest tests\fund\test_artifact_runtime.py tests\fund\test_sandbox.py -q
9 passed, 1 warning
```

```powershell
pytest tests\fund -q
219 passed, 1 warning
```

```powershell
python tools\guards\check_primitives_whitelist.py
[OK] 基元库白名单扫描通过（8 个文件）
```

```powershell
python tools\guards\check_placeholder_binding.py
[OK] 占位符绑定校验通过（7 个 Rule 各自覆盖 18/18）
```

```powershell
python tools\guards\check_contract_hash.py
[OK] contracts.lock 校验通过（1 个契约文件）
```

```powershell
python tools\guards\check_canonical_schema.py
[OK] fund_events 12 列按 §C1 契约序连续出现（+5 元数据列：['id', 'batch_id', 'parser_artifact_id', 'created_at', 'updated_at']）
```

```powershell
python -m compileall backend\core\artifact_runtime.py backend\core\runtime_guard.py backend\agents\fund\sandbox.py backend\services\bank_import_service.py backend\services\manual_flow_service.py backend\services\report_service.py backend\api\bank_import.py backend\api\manual_flow.py backend\db\schemas.py tests\fund\test_artifact_runtime.py -q
# exit code 0
```

## 已知风险

- `report_service.generate_report()` 当前返回 Workbook，下载端点可在 Phase 6 接入 StreamingResponse。
- Runtime rule 的 loop 当前按 P5 最小闭环取首条事件填充行级占位符；多行展开能力留到模板下载端点/报表 UI 联调阶段继续完善。
- 快速录入路径会按现有 `_process_row/_validate_row` 结果写入 CANONICAL_12；若主数据匹配失败，仍可能因 v3 外键约束要求前端先补齐主数据或在后续 Phase 增加待确认暂存策略。

## 是否达到下一 Phase 进入条件

- YES。
- 理由：Parser artifact 已能执行 commit 并写入 `fund_events`；1000 行导入不会产生 `ai_call_logs`；Rule artifact 可执行并替换现金日记账 18 个占位符；白名单、占位符、contract hash、canonical schema 与 fund 全量测试均为绿色。
