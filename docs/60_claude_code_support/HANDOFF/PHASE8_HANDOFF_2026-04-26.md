# Phase 8 交班单：集成测试与真实样本回归

## 完成范围

- P8-1：新增脱敏回归样本
  - `tests/fixtures/fund_samples/bank_icbc_01.xlsx`
  - `tests/fixtures/fund_samples/bank_icbc_02.xlsx`
  - `tests/fixtures/fund_samples/manual_multi_entity_01.xlsx`
  - `tests/fixtures/fund_samples/cash_journal_blank.xlsx`
  - 样本使用示例主体、账户、往来方与金额，不含真实财务明细。
- P8-2：新增 v3 E2E 测试基座
  - `tests/e2e/conftest.py` 使用临时 SQLite DB，执行 Alembic 到 head，并重绑定导入、Agent、报表模块的数据目录。
  - 每个用例隔离数据库与上传目录，避免污染本地 `backend/data/zhangfang.db`。
- P8-3：覆盖 V1 最小闭环 E2E
  - 银行流水上传 -> parser.bank -> 审核 ParserArtifact -> 提交 FundEvent。
  - 第二份同银行样本复用 active Parser，验证不新增 AI 调用日志。
  - 手工多主体 Excel 上传 -> parser.manual -> 审核 -> 提交 FundEvent。
  - 现金日记账模板上传 -> rule.generator -> 审核 RuleArtifact -> 生成并下载 xlsx。
- P8-4：隐私与沙箱回归
  - `offline` 隐私模式在 skill 执行前阻断，记录 `PRIVACY_OFFLINE`，且不生成 ParserArtifact。
  - 沙箱拒绝 `import os`、拒绝 `eval`、超时终止死循环。
- P8-5：修复 P8 暴露的手工流水样本定位问题
  - `backend/api/fund_agent.py` 的 manual skill payload 解析支持通过 `batch_code` 回查 `ImportBatch.source_name`。
  - 修复后 `parser.manual` 可从手工上传批次定位原始 Excel 文件。
- P8-6：更新 CI
  - `.github/workflows/backend-tests.yml` 改为执行 v3 当前门禁：核心/DB/脚本测试、Fund Agent 回归、P8 E2E、四个阻断型守护。
  - `check_api_inventory.py` 保留为记录项，`continue-on-error: true`，延续 P6/P7 已确认口径。

## 新增文件

- `tests/e2e/conftest.py`
- `tests/e2e/test_security_regression.py`
- `tests/fixtures/fund_samples/README.md`
- `tests/fixtures/fund_samples/bank_icbc_01.xlsx`
- `tests/fixtures/fund_samples/bank_icbc_02.xlsx`
- `tests/fixtures/fund_samples/manual_multi_entity_01.xlsx`
- `tests/fixtures/fund_samples/cash_journal_blank.xlsx`
- `docs/60_claude_code_support/HANDOFF/PHASE8_HANDOFF_2026-04-26.md`

## 修改文件

- `tests/e2e/test_full_flow.py`
- `tests/conftest.py`
- `backend/api/fund_agent.py`
- `.github/workflows/backend-tests.yml`

## 验收证据

```powershell
pytest tests\e2e -q
5 passed, 1 warning in 4.96s
```

```powershell
pytest tests\fund -q
225 passed, 1 warning in 7.36s
```

```powershell
pytest tests\backend\core tests\db tests\scripts -q
23 passed, 1 warning in 4.20s
```

```powershell
python -m compileall backend\api\fund_agent.py tests\e2e\conftest.py tests\e2e\test_full_flow.py tests\e2e\test_security_regression.py -q
# exit code 0
```

```powershell
npm run build
✓ built in 601ms
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
[OK] 基元库白名单扫描通过（13 个文件）
```

```powershell
python tools\guards\check_placeholder_binding.py
[OK] 占位符绑定校验通过（12 个 Rule 各自覆盖 18/18）
```

```powershell
python tools\guards\check_api_inventory.py
[FAIL] API 端点 107 > 上限 42（§C7 冻结为 42）
# 按 P6/P7 已确认口径：记录为既有端点治理债务，不阻断 P8。
```

## 已知风险

- Playwright / `@playwright/test` 当前未安装，P8 未新增浏览器自动化录屏；M5 如需浏览器录像，需要先确认是否允许引入前端 E2E 依赖。
- `pytest tests\backend -q` 仍会触发旧 v2 `tests/backend/services` 断言失败；这些测试仍按旧 `FundEvent` 字段与旧服务接口编写，未纳入本次 P8 v3 门禁。
- API inventory 仍为 107/42，延续 P6 记录的端点扩张债务；未在 P8 自由裁剪 API。
- 本次样本为脱敏代表性样本，不等同真实客户生产流水；真实样本回归仍建议在 M5 用户验收时用用户授权样本补测。

## 是否达到 M5 验收准备条件

YES。

理由：P8 已覆盖银行导入、手工 Excel、模板报表、重复 Parser 命中、隐私 offline 阻断、运行时沙箱阻断与 CI 门禁；阻断型守护均通过。剩余红项均为已记录的非 P8 阻断债务或需要用户授权的人工验收事项。
