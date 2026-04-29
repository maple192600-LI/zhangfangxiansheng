# Phase 6 交班单：API + 前端 UX

## 执行口径

- 按用户确认的“契约口径”执行 P6。
- API 以 `docs/30_contracts/23_api_contracts.md` 为准。
- `check_api_inventory.py` 只记录当前状态，不作为 P6 阻断项。

## 完成范围

- P6-1：新增 Fund Agent 契约 API
  - `POST /api/fund/agent/skills/{skill_name}/invoke`
  - `GET /api/fund/parsers`
  - `GET /api/fund/parsers/{id}`
  - `POST /api/fund/parsers/{id}/approve`
  - `GET /api/fund/rules`
  - `GET /api/fund/rules/{id}`
  - `POST /api/fund/rules/{id}/approve`
  - `POST /api/fund/templates/upload`
  - `GET /api/fund/templates/jobs/{id}`
  - `POST /api/fund/templates/jobs/{id}/confirm`
- P6-2：新增报表生成与下载契约 API
  - `POST /api/reports/generate`
  - `GET /api/reports/download/{id}`
- P6-3：前端接入“上传 -> 审核 -> 接受 -> 查看”闭环
  - 银行流水上传后自动生成 Parser 草稿并进入审核页。
  - 手工流水 Excel 上传后自动生成 Parser 草稿并进入审核页。
  - 报表模板上传后自动生成 Rule 草稿并进入审核页。
  - 审核页只提供契约内的“接受”动作，不引入 reject/modify 额外端点。
- P6-4：新增 P6 API 回归测试，覆盖 Parser 审核、Rule 审核、报表生成下载。

## 新增文件

- `backend/api/fund_agent.py`
- `frontend/src/api/fund.js`
- `frontend/src/views/AgentReview.vue`
- `tests/fund/test_phase6_api.py`
- `docs/60_claude_code_support/HANDOFF/PHASE6_HANDOFF_2026-04-26.md`

## 修改文件

- `backend/main.py`
- `backend/api/reports.py`
- `frontend/src/router/index.js`
- `frontend/src/views/BankImport.vue`
- `frontend/src/views/ManualFlow.vue`
- `frontend/src/views/ReportTemplate.vue`
- `tests/fund/conftest.py`

## 验收证据

```powershell
pytest tests\fund -q
221 passed, 1 warning in 6.63s
```

```powershell
python -m compileall backend\api\fund_agent.py backend\api\reports.py backend\main.py -q
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
[OK] 基元库白名单扫描通过（11 个文件）
```

```powershell
python tools\guards\check_placeholder_binding.py
[OK] 占位符绑定校验通过（9 个 Rule 各自覆盖 18/18）
```

```powershell
python tools\guards\check_api_inventory.py
[FAIL] API 端点 107 > 上限 42（§C7 冻结为 42）
```

## 已知风险

- API inventory 当前为 107/42，属于 P6 前已存在的端点扩张债务叠加本轮契约端点接入；本轮按方案只记录，不处理。
- 报表生成响应中的 `rows_written` 目前返回 0，P6 回归已验证文件可下载且占位符填充数量正确；多行写入统计可在后续报表体验阶段补齐。
- 审核页按契约只支持“接受”，未实现方案文档中未进入 `23_api_contracts.md` 的 reject/modify 流程。
- 浏览器真实样本流仍需人工用本地页面跑一次 M4：银行流水、手工流水、模板上传三条入口各走一遍。

## 是否达到下一 Phase 进入条件

- YES。
- 理由：契约 API 已接入，前端三条入口已形成上传到审核的用户闭环，Parser/Rule 接受动作能落到 runtime 与报表下载；fund 全量测试、前端构建、核心治理守护均通过。API inventory 红项按 P6 口径记录到交班单。
