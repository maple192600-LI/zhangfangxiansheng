# 00 · V3 执行顺序与任务卡（v3）

> 本文件是 v3 阶段**唯一的任务执行清单**。所有 Codex / Claude / 人类开发者按本文件从上到下执行。
> 跳步 = 违反 §C9 阶段化约束。每步完成必须满足 `../00_governance/08_anti_drift.md` §5 的 DoD 4 项交付。
>
> 相关文档：
> - [../00_governance/01_v1_scope_and_order.md](../00_governance/01_v1_scope_and_order.md) · 三阶段总视图
> - [../00_governance/08_anti_drift.md](../00_governance/08_anti_drift.md) · 防跑偏
> - [../30_contracts/25_primitives_whitelist.md](../30_contracts/25_primitives_whitelist.md) · 基元清单

---

## §E0 · 总览

```
Phase 0 · AI 基础设施    P0-T1 ~ P0-T7    ~16 人日
    ↓ Gate G0
Phase 1 · 业务 AI 化     P1-T1 ~ P1-T7    ~18 人日
    ↓ Gate G1
Phase 2 · 收尾验收       P2-T1 ~ P2-T4    ~7  人日
    ↓ Gate G2 · 交付
```

每张"任务卡"都包含：
- 任务 ID / 标题
- 前置依赖
- 交付物
- 验证清单（可勾选）
- 禁止事项

---

## §E1 · Phase 0 · AI 基础设施（~16 人日）

### P0-T1 · pre-commit guards 上线（2 人日）

**前置**：无

**交付物**：
- `tools/guards/check_canonical_schema.py`
- `tools/guards/check_primitives_whitelist.py`
- `tools/guards/check_placeholder_binding.py`
- `tools/guards/check_api_inventory.py`
- `tools/guards/check_contract_hash.py`
- `contracts.lock`（基于 `00_project_constitution.md` 生成的 SHA256）
- `.pre-commit-config.yaml` 挂载上述 5 个脚本

**验证清单**：
- [ ] 5 个脚本在本地 pre-commit 触发
- [ ] 故意改宪法 → check_contract_hash.py 拒绝
- [ ] 故意 `import pandas` 加到某 artifact → check_primitives_whitelist.py 拒绝
- [ ] 故意把 fund_events 加第 13 列 → check_canonical_schema.py 拒绝
- [ ] 故意让 Rule 少绑占位符 → check_placeholder_binding.py 拒绝
- [ ] 故意让 `backend/api/` 超出 42 端点 → check_api_inventory.py 拒绝
- [ ] `docs/60_claude_code_support/HANDOFF/handoff_P0-T1.md` 已写

**禁止**：guards 脚本中不得有 TODO 留白；不得 `exit 0` 兜底。

---

### P0-T2 · 3 张新表 DDL + 迁移（1 人日）

**前置**：P0-T1

**交付物**：
- `backend/db/tables.py` 新增 `fund_events / parser_artifacts / rule_artifacts / template_inference_job` ORM 类
- `backend/db/tables.py` 中 `parser_templates` 类加 `# DEPRECATED v3` 注释（但不删）
- Alembic 迁移 `alembic/versions/001_v3_fund_events.py` 等 4 个迁移文件
- 单元测试：`tests/db/test_v3_tables.py` 验证 CHECK 约束

**验证清单**：
- [ ] `alembic upgrade head` 成功
- [ ] 插入 `amount_in=10, amount_out=10` → CHECK 拒绝
- [ ] 插入 `state='随便'` → CHECK 拒绝
- [ ] `tools/guards/check_canonical_schema.py` 通过
- [ ] Handoff 文档已写

**禁止**：不得更改 12 列的列序列名；`parser_templates` 不得删表（历史数据可读）。

---

### P0-T3 · 基元库 37 函数实现（4 人日）

**前置**：P0-T2

**交付物**：
- `backend/fund/primitives/{sheet_ops,value_parsers,canonical,master_match,base_queries,aggregations,template_fill}.py`
- `tests/fund/primitives/test_{...}.py` 各对应 1 个
- 覆盖率 ≥ 90%

**验证清单**：
- [ ] 37 个函数签名与 `25_primitives_whitelist.md` 完全一致
- [ ] `pytest tests/fund/primitives/` 全部通过
- [ ] `coverage report` ≥ 90%
- [ ] `parse_date` 支持至少 5 种中文日期格式
- [ ] `parse_amount` 支持千分位 / 括号负数 / 中文大写
- [ ] `emit_row` 在少列时抛清晰错误
- [ ] Handoff 文档已写

**禁止**：不得新增第 38 个基元（走 ChangeFlow）；不得依赖 pandas/numpy。

---

### P0-T4 · Artifact 服务 + 沙箱（3 人日）

**前置**：P0-T3

**交付物**：
- `backend/fund/artifact_service.py`（注册 / 版本化 / 查询 / 审批）
- `backend/fund/sandbox.py`（AST 扫描 + subprocess 隔离 + 超时 + RLIMIT）
- `tests/fund/test_artifact_service.py`
- `tests/fund/test_sandbox.py`

**验证清单**：
- [ ] Artifact 入库前强制调用 `check_primitives_whitelist.scan()`
- [ ] 沙箱执行 `import os` 代码 → 拒绝
- [ ] 沙箱执行超时 > 60s 代码 → kill
- [ ] 同名 Parser 提交第二次 → 自动 version+1
- [ ] `status` 从 draft → approved 记录 `approved_by / approved_at`
- [ ] Handoff 文档已写

---

### P0-T5 · Fund Agent 重建（5 人日）

**前置**：P0-T4

**交付物**：
- `backend/agents/fund/AGENT.md`（Agent 主提示词）
- `backend/agents/fund/harness.py`（harness_strict 调度器）
- `backend/agents/fund/schemas.py`（5 个 skill 的 Pydantic I/O schema）
- `backend/agents/fund/memory.py`（字段字典 / 别名库访问）
- `backend/agents/fund/skills/{parser_bank,parser_manual,rule_template_fill,rule_maintain,template_inference}.py`
- `backend/agents/master/DEPRECATED.md` + `backend/agents/parser-assistant/DEPRECATED.md`（标记作废，不删）

**验证清单**：
- [ ] `parser.bank` 在 `fixtures/bank/icbc_sample.xlsx` 上生成 Parser，SAMPLE_CHECK 通过
- [ ] 生成的代码通过 `check_primitives_whitelist.py`
- [ ] `template.inference` 在 `fixtures/template/cash_journal_blank.xlsx` 上识别 ≥ 15/18 占位符
- [ ] 5 个 skill 都有对应 Schema 校验
- [ ] `privacy_mode=strict` 时，Agent 不得收到样本数据行
- [ ] Handoff 文档已写

---

### P0-T6 · 字段字典种子（0.5 人日）

**前置**：P0-T3

**交付物**：
- `seed/field_dictionary.json`（12 核心字段 + 每字段 5+ 别名）
- `seed/alias_library.json`（空 JSON，运行时增长）
- `backend/services/master_data_service.py` 添加 `load_seed_dict()`

**验证清单**：
- [ ] 启动时加载种子，UI 显示字段字典可读
- [ ] Handoff 文档已写

---

### P0-T7 · few-shot 样本（0.5 人日）

**前置**：无（与 T3/T5 并行）

**交付物**：
- `fixtures/bank/icbc_sample_01..03.xlsx`（至少 3 条真实或脱敏样本）
- `fixtures/bank/abc_sample_01..03.xlsx`
- `fixtures/bank/ccb_sample_01..03.xlsx`
- `fixtures/bank/boc_sample_01..03.xlsx`
- `fixtures/bank/cmbc_sample_01..03.xlsx`
- `fixtures/manual/multi_entity_sample_01.xlsx`
- `fixtures/manual/cash_box_sample_01.xlsx`
- `fixtures/template/cash_journal_blank.xlsx`

**验证清单**：
- [ ] 每个样本加脱敏注释头（时间/单位/金额均已改）
- [ ] Handoff 文档已写

---

### 🚦 Gate G0 · 进入 Phase 1 的条件

- [ ] P0-T1 ~ P0-T7 全部完成
- [ ] 5 guards 在 CI 全绿
- [ ] 基元库覆盖率 ≥ 90%
- [ ] `parser.bank` 能在 fixtures 上生成通过校验的 Parser
- [ ] `docs/60_claude_code_support/HANDOFF/phase0_complete.md` 已写
- [ ] 宪法 SHA256 在 `contracts.lock` 中

**未满足 → 停工，不得启动 P1。**

---

## §E2 · Phase 1 · 业务 AI 化（~18 人日）

### P1-T1 · 银行导入切到 Parser artifact（3 人日）

**前置**：Gate G0

**交付物**：
- `backend/services/bank_import_service.py` 重写
- 老逻辑 `match_template()` 改名 `_legacy_match_template()` 并加 DEPRECATED
- `tests/services/test_bank_import_v3.py`

**核心流程**：
```
1. 用户上传流水 Excel → 得 account_code + sample_file
2. 查 parser_artifacts WHERE account_code=X AND status='approved' → 若有，直接用
3. 若无 → 触发 agents/fund/skills/parser_bank.invoke() → 生成 draft
4. 前端显示 draft + SAMPLE_CHECK 结果 → 用户点"批准" → status='approved'
5. sandbox.run(parser.code, ...) → yield CanonicalRow
6. 批量 insert fund_events
7. 返回 batch_id + 统计
```

**验证清单**：
- [ ] 端到端：上传 icbc 样本 → Parser 自动生成 → 批准 → 流水入库
- [ ] `state='待确认'` 的行数 ≤ 5%
- [ ] Runtime 零 LLM 调用
- [ ] Handoff 文档已写

---

### P1-T2 · 手工流水 artifact 化（3 人日）

**前置**：P1-T1

**交付物**：
- `backend/services/manual_flow_service.py` 重写
- 快速录入单条 → 仍保留（不经 Agent）
- Excel 多主体上传 → 走 `parser.manual` skill

**验证清单**：
- [ ] "多主体 Excel" 上传触发 `parser.manual` 生成 Parser
- [ ] 一行多科目布局支持
- [ ] 对未匹配的字段落入 `state='待确认'`
- [ ] Handoff 文档已写

---

### P1-T3 · 报表模板管理（4 人日）

**前置**：P1-T1

**交付物**：
- 后端：`backend/api/fund_templates.py`（端点 29/30/31）
- 前端：`frontend/src/views/template_manage/`（上传 / 识别结果预览 / 占位符校对 / 确认）
- 数据流：上传 → Stage A 结构解析 → Stage B `template.inference` → 用户确认 → 生成 Rule

**验证清单**：
- [ ] 上传 `cash_journal_blank.xlsx` → 识别出 ≥ 15/18 占位符
- [ ] 置信度 < 0.7 的占位符红色标注
- [ ] 用户可修改绑定 → 确认 → Rule artifact 入库
- [ ] Handoff 文档已写

---

### P1-T4 · `template.inference` skill 对接（2 人日）

**前置**：P1-T3 + P0-T5

**交付物**：
- `backend/agents/fund/skills/template_inference.py` 完整实现
- 三阶段流水线（Stage A 无 AI、Stage B AI、Stage C 用户）

**验证清单**：
- [ ] Stage A 能识别 `${xxx}` `{{xxx}}` 两种占位符语法
- [ ] Stage B 返回占位符 → primitive 建议 + 置信度
- [ ] Stage C 用户确认后生成 Rule draft
- [ ] Handoff 文档已写

---

### P1-T5 · 前端预览/批准页（3 人日）

**前置**：P1-T1 + P1-T3

**交付物**：
- `frontend/src/views/artifact_review/`：Parser 代码 diff 视图 + SAMPLE_CHECK 结果展示 + 批准按钮
- `frontend/src/views/rule_review/`：Rule bindings 表格 + 模板预览 + 批准按钮
- `frontend/src/views/exception_center/`：待确认 / 异常行处理（与 P2-T1 重叠，可合并）

**验证清单**：
- [ ] 用户看到"ICBC_网银_v1 · 样本 50/50 通过 · 零 canonical 违反"
- [ ] 用户可拒绝 → Agent 重试（带反馈）
- [ ] Handoff 文档已写

---

### P1-T6 · Rule Runtime（2 人日）

**前置**：P1-T4

**交付物**：
- `backend/fund/rule_runtime.py`
- `backend/services/report_service.py` 重写

**核心逻辑**：
```python
def execute(rule_id, ctx):
    rule = artifact_service.get(rule_id)
    wb = template_fill.load_template(rule.template_file)
    for ph, binding in rule.placeholder_bindings.items():
        value = call_primitive(binding, ctx)
        template_fill.fill(wb, ph, value)
    for row_ctx in call_primitive(rule.loop, ctx):
        write_row(wb, rule.loop.columns, row_ctx)
    return save(wb)
```

**验证清单**：
- [ ] 18 个占位符全部填充
- [ ] 金额格式、日期格式符合模板
- [ ] Runtime 零 LLM 调用（guard 验证）
- [ ] Handoff 文档已写

---

### P1-T7 · E2E 联调（1 人日）

**前置**：P1-T1 ~ P1-T6

**交付物**：
- `tests/e2e/test_full_flow.py`（上传流水 + 模板 → 生成现金日记账）

**验证清单**：
- [ ] 7 家银行样本 × 现金日记账模板 → 生成 Excel
- [ ] 金额与样本底账对账误差 = 0
- [ ] 单次流程 ≤ 30 秒
- [ ] Handoff 文档已写

---

### 🚦 Gate G1 · 进入 Phase 2 的条件

- [ ] P1-T1 ~ P1-T7 全部完成
- [ ] E2E 在多家银行样本上通过
- [ ] 金额准确率 ≥ 99.5%
- [ ] Runtime 链路零 LLM（guard 通过）
- [ ] `docs/60_claude_code_support/HANDOFF/phase1_complete.md` 已写

---

## §E3 · Phase 2 · 收尾（~7 人日）

### P2-T1 · 异常中心独立页（2 人日）

**交付物**：
- `frontend/src/views/exception_center/index.vue`
- 端点 35/36/37 完整实现
- 操作记录到 `operation_logs`

#### 完成报告（2026-04-26）

- 新增 `backend/api/events.py` 与 `backend/services/exception_center_service.py`，补齐 `GET /api/events/pending`、`PUT /api/events/{event_id}/resolve`、`PUT /api/events/{event_id}/void`。
- 新增 `frontend/src/views/ExceptionCenter.vue` 与 `frontend/src/api/events.js`，并将系统设置 > 异常中心两个占位路由接入独立页。
- 处理动作：`待确认/异常` 可修正后标记 `正常`；异常流水可标记 `已作废`。
- 审计动作：resolve / void 均写入 `operation_logs`，module=`exception_center`。
- 验收：`pytest tests\e2e\test_exception_center.py -q` 2 passed；`pytest tests\e2e -q` 7 passed；`pytest tests\fund -q` 225 passed；`npm run build` 通过；阻断型 guards 通过。
- 已知红项：`check_api_inventory.py` 变为 110/42，按 P6/P7/P8 已确认口径继续记录为端点治理债务。

---

### P2-T2 · 隐私三档（1 人日）

**交付物**：
- `ai_configs.privacy_mode` 字段生效
- UI 切换界面 + 即时生效
- 样本脱敏器：standard=千分位 + 首字母，strict=仅列头

#### 完成报告（2026-04-26）

- 本任务卡与 Phase 7 隐私三档交付物重叠，本轮按收尾阶段口径完成复核并补交班记录。
- `ai_configs.privacy_mode` 已在 ORM、schema、API 入参、AI 配置服务中生效，非法档位由 `core/privacy_pipeline.py::validate_privacy_mode` 拒绝。
- `AIConfig.vue` 已提供隐私档位显示与编辑，支持 `standard` / `strict` / `offline`。
- `FundAgent.run_skill` 每次调用都会读取当前 active/default AI 配置的隐私档位，满足“即时生效”。
- `standard` / `strict` / `offline` 行为由 `tests/fund/test_phase7_privacy.py` 覆盖；offline E2E 由 `tests/e2e/test_full_flow.py::test_privacy_offline_blocks_skill_before_artifact` 覆盖。
- 验收：`pytest tests\fund\test_phase7_privacy.py -q` 4 passed；`pytest tests\e2e\test_full_flow.py::test_privacy_offline_blocks_skill_before_artifact -q` 1 passed；`npm run build` 通过。

---

### P2-T3 · 集成测试（3 人日）

**交付物**：
- `tests/e2e/test_multi_bank.py`（多家银行 × 多模板）
- `tests/e2e/test_artifact_version.py`（artifact 版本迭代）
- `tests/e2e/test_privacy_modes.py`
- CI 配置 `.github/workflows/e2e.yml`

**验证**：金额准确率 ≥ 99.9%。

---

### P2-T4 · 文档收尾（1 人日）

**交付物**：
- `README.md` 更新启动步骤
- `docs/60_claude_code_support/HANDOFF/final_delivery.md`
- 删除 / 归档 v2 原版 `_原版.md` 文件
- 确认所有 v3 文档交叉链接正确

---

### 🚦 Gate G2 · 交付

- [ ] 全量自动化测试通过
- [ ] 金额准确率 ≥ 99.9%
- [ ] 所有 guards 在 pre-commit + CI 启用
- [ ] `final_delivery.md` 已写
- [ ] 用户能独立走完"6 步验收清单"（见 `../00_governance/01_v1_scope_and_order.md` §8）

---

## §E4 · Do Not Do（全局禁止清单）

| # | 禁止 | 理由 |
|---|---|---|
| 1 | 跳过 Gate 进入下一阶段 | 违反阶段化 |
| 2 | 在 services 里写"如果是工行就这样"的 if-else | 违反 artifact 原则 |
| 3 | 给用户加"手动配字段映射"入口 | 违反 §C9 |
| 4 | 擅自增加第 6 个 skill | 违反 §C4 |
| 5 | 擅自增加第 38 个基元 | 违反 §C5 |
| 6 | 擅自扩展 fund_events 列 | 违反 §C1 |
| 7 | 在 Runtime 里直接调 LLM | 违反 §C8 |
| 8 | 动态生成 SQL（用字符串拼接） | 安全 + 审计 |
| 9 | 把用户样本原始数据发给 LLM provider | 违反隐私三档 |
| 10 | 在 Handoff 文档里用"基本完成"、"大体 OK"等模糊语 | 违反目标硬化 |

---

**版本**
- v3.0 · 2026-04-23 · 首次发布
