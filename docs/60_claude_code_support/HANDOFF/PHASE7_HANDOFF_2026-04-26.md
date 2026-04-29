# Phase 7 交班单：字段字典 / 别名库 / 隐私三档

## 完成范围

- P7-1：新增 `backend/seed/field_dictionary.json`
  - 覆盖 10 个核心字段：`business_date` / `entity_code` / `entity_name` / `account_code` / `account_name` / `summary` / `counterparty` / `amount_in` / `amount_out` / `rolling_balance`
  - 每个字段提供中文名、类型和 5 个以上别名。
- P7-2：新增 `backend/seed/alias_library.json`
  - 初始为空 dict，运行期别名仍由 `account_aliases` 增长。
- P7-3：改造 `agents/fund/memory.py::list_aliases`
  - 合并 seed alias 与 DB `account_aliases`。
  - 新增 `load_field_dictionary()` / `load_seed_aliases()`。
- P7-4：新增 `backend/core/privacy_pipeline.py`
  - `standard`：保留列头与脱敏样本；金额脱敏到千位，长账号/编号数字掩码，名称保留首字。
  - `strict`：只保留列头，数据行为空。
  - `offline`：抛出“已设为离线模式，不允许调用 Fund Agent skill”。
- P7-5：在 `agents/fund/harness.py` 入口统一执行隐私模式
  - 优先读取默认 active `ai_configs.privacy_mode`。
  - 无配置时回退 payload 中的 `privacy_mode`，再回退 `standard`。
  - `offline` 在 skill 执行前阻断并写 `ai_call_logs.error_code='PRIVACY_OFFLINE'`。
- UI 补齐
  - `AIConfig.vue` 增加“隐私档位”列和编辑下拉框。
  - 后端 AI 配置 create/update/list 支持 `privacy_mode`。
- DB 迁移
  - 新增 Alembic `003_add_ai_privacy_mode.py`。
  - `alembic upgrade head` 已执行，当前 `backend/data/zhangfang.db.ai_configs` 已包含 `privacy_mode` 列。

## 新增文件

- `backend/seed/field_dictionary.json`
- `backend/seed/alias_library.json`
- `backend/core/privacy_pipeline.py`
- `alembic/versions/003_add_ai_privacy_mode.py`
- `tests/fund/test_phase7_privacy.py`
- `docs/60_claude_code_support/HANDOFF/PHASE7_HANDOFF_2026-04-26.md`

## 修改文件

- `alembic/versions/001_v3_fund_events.py`
- `backend/agents/fund/memory.py`
- `backend/agents/fund/harness.py`
- `backend/db/tables.py`
- `backend/db/schemas.py`
- `backend/api/ai_config.py`
- `backend/services/ai_config_service.py`
- `frontend/src/views/AIConfig.vue`

## 验收证据

```powershell
pytest tests\fund\test_phase7_privacy.py -q
4 passed, 1 warning
```

```powershell
pytest tests\fund -q
225 passed, 1 warning in 6.87s
```

```powershell
python -m compileall backend\core\privacy_pipeline.py backend\agents\fund\memory.py backend\agents\fund\harness.py backend\db\tables.py backend\api\ai_config.py backend\services\ai_config_service.py -q
# exit code 0
```

```powershell
alembic upgrade head
# exit code 0
```

```powershell
npm run build
✓ built
# Vite chunk-size warning remains, build exit code 0
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
python tools\guards\check_primitives_whitelist.py
[OK] 基元库白名单扫描通过（12 个文件）
```

```powershell
python tools\guards\check_placeholder_binding.py
[OK] 占位符绑定校验通过（12 个 Rule 各自覆盖 18/18）
```

```powershell
python tools\guards\check_api_inventory.py
[FAIL] API 端点 107 > 上限 42（§C7 冻结为 42）
```

## 已知风险

- `check_api_inventory.py` 仍为 107/42，延续 P6 已记录的端点扩张债务；P7 未新增 API 路由。
- 当前 5 个 skill 多为确定性本地实现，尚未真正构造 LLM prompt；P7 已把可发给 LLM 的脱敏快照放在 harness 入口，后续若接入真实 LLM 必须只使用该快照。
- `strict` 验收已覆盖“隐私预览 rows 为空”；真实 provider prompt 内容需在 P8 隐私回归中继续验证。
- `offline` 会阻断新 skill 调用；已有 active artifact 的纯 runtime 执行不受影响，符合 §C8 Runtime 禁 AI 原则。

## 是否达到下一 Phase 进入条件

- YES。
- 理由：字段字典、别名库、隐私三档、AI 配置持久化与 UI 切换均已接入；`strict` / `offline` 行为有单测覆盖；fund 全量测试、前端构建、核心守护均通过。API inventory 红项按既定口径记录，不阻断进入 P8。
