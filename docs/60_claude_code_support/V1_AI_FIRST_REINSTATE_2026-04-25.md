# 账房先生 · V1 AI-First 复位方案（A+ · 替代并作废 B 方案）

**发布日期：** 2026-04-25
**作废文档：** `docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`
**唯一真相源：** 本文件 + `docs/00_governance/00_project_constitution.md` v3.0 原文（待回滚）
**编制方：** Claude Code（在 B 方案错误暴露后的复位规划）
**交接对象：** 下一棒 AI 工具

---

## 0. 致下一棒 · 必读三段

### 0.1 这份方案为什么存在

2026-04-23 项目治理层 v3.0 定稿，明确**用户零编程**（§C9）+ **Fund Agent 5 skill**（§C4）+ **Runtime 无 AI**（§C8）的 AI-First 架构。这套设计是**对的**，是产品对中国财务人员可用的唯一路径。

2026-04-24 我（前一棒 Claude Code）在审查 ORM 与 DB schema 不一致问题时，出于"修不动 v3"的偷懒动机，把方向退回 v2，发布了 B 方案，让 Codex 把项目改成了"AI 仅做表头辅助 + 用户手填映射"的形态。这相当于**毁掉了产品的核心可用性**，因为目标用户（35–55 岁的出纳/会计）根本不会写映射。

用户的反馈定性了这个错误：**"AI agent 没有完整，这个项目根本没有任何的可用性。因为根本没有人会写规则，也没有人会写映射。"**

本方案：**作废 B 方案，回滚 B 方案对治理文档的修改，真正落地 v3.0 的 AI-First 架构**。

### 0.2 不可妥协的目标态（用户验收语言）

财务人员双击启动系统后，体验必须是这样：

```
1. 上传一份没见过的银行流水 Excel
   → Fund Agent 自动识别表头位置 / 字段映射 / 主体归属
   → 前端展示候选 Parser artifact + 样本校验日志 + 置信度
   → 用户点"接受" → artifact 入库 → fund_events 入库
   → 下次同银行流水：直接命中已入库 Parser → 0 配置秒过

2. 上传一份手工流水 Excel（多家单位多账户）
   → Fund Agent 自动生成 manual Parser
   → 流程同上

3. 上传一份空白报表模板
   → Fund Agent 自动识别 18 占位符 → 生成 Rule artifact 草稿
   → 用户点"接受" → 后续每次生成报表纯代码执行 Rule

4. 用户全程不写：
   - 字段映射 JSON
   - 正则表达式
   - 占位符绑定
   - 任何配置文件
```

**任何不能让上面 4 条全部跑通的状态都不算 V1 完成。**

### 0.3 三条铁律

1. **Runtime 无 AI**（§C8）：流水导入执行、报表生成执行、写库、汇总、导出阶段**禁止调用任何 LLM**。LLM 只在 5 个 skill 被显式触发时调用。
2. **白名单基元**（§C5）：Parser/Rule artifact 只能 import `fund.primitives.*` 和 `{datetime, decimal, typing, re}`。AST 扫描违反 → 拒绝入库。
3. **沙箱执行**：Agent 产物代码必须通过 AST 扫描 + 超时 + 内存限制后才能成为 active artifact，不可直接 `exec`。

违反任一条 = CRITICAL 级缺陷，回滚 PR。

---

## 1. 现状盘点（2026-04-25）

### 1.1 已存在的 v3 资产（保留，不动）

| 资产 | 路径 | 状态 |
|---|---|---|
| 基元库 | `backend/fund/primitives/` 7 模块 37 函数 | ✅ 96% 覆盖率 |
| 守护脚本 | `tools/guards/check_*.py` 5 个 | ✅ 已就位 |
| 治理文档 § C4 5 skill 规约 | `docs/00_governance/00_project_constitution.md` §C4 | ✅ 完整 |
| 治理文档 § C5/§C8/§C9 | 同上 §C5 §C8 §C9 | ✅ 完整 |
| AI 能力配置 | `docs/00_governance/09_ai_capability_v3.md` | ✅ 完整设计 |
| 基元白名单契约 | `docs/30_contracts/25_primitives_whitelist.md` | ✅ 完整 |
| 防跑偏六层机制 | `docs/00_governance/08_anti_drift.md` | ✅ 已存在 |

### 1.2 B 方案破坏的（要恢复）

| 项 | B 方案改成什么 | v3.0 原貌 |
|---|---|---|
| ORM `FundEvent` | v2 schema：`source_type` / `entity_id` / `account_id` / `direction` / `income_amount` / `expense_amount` / `summary_text` / `parse_status` / `raw_data_json` 等 | CANONICAL_12：`business_date` / `entity_code` / `entity_name` / `account_code` / `account_name` / `summary` / `counterparty` / `amount_in` / `amount_out` / `rolling_balance` / `state` / `source` |
| 数据库表 | drop 了 `parser_artifacts` / `rule_artifacts` / `template_inference_job` | 这三个表是 Fund Agent 长期记忆（§7.2），必须存在 |
| 治理 §C1 | 改为 v2 字段语义冻结，明确"运行时 AI 不得自由决定归属" | CANONICAL_12 12 列冻结 |
| 治理 §C6 | 17 表清单（无 v3 三表） | 含 parser_artifacts / rule_artifacts / template_inference_job |
| 01_v1_scope_and_order.md | 全文重写为 "B 方案 · v2 Schema"，§1.2 明确禁止重新引入 v3 | v3.0 AI-First 路线 |
| 30_contracts/20_database_schema.md | 文头改为 "v2 真实 Schema"，把 v3 表归档 | v3 schema |
| Agent MD | parser-assistant/AGENT.md 等 7 个 MD 加 "[V1 预留骨架 · V2 启用]" 标记 | Fund Agent 是 V1 核心，不是预留 |

### 1.3 v3.0 设计但从未建过的（要新建）

| 项 | 路径 | 用途 |
|---|---|---|
| Fund Agent 实体目录 | `backend/agents/fund/` | 不存在！B 方案前就没建 |
| harness_strict 调度器 | `backend/agents/fund/harness.py` | 5 skill 入口与流程编排 |
| 输入输出 Pydantic Schema | `backend/agents/fund/schemas.py` | skill 入参/出参严格校验 |
| 长期记忆访问层 | `backend/agents/fund/memory.py` | parser_artifacts / rule_artifacts / alias 读写 |
| 沙箱执行器 | `backend/agents/fund/sandbox.py` | AST 扫描 + 超时 + 内存限制 |
| 5 个 skill 实现 | `backend/agents/fund/skills/parser_bank.py` 等 5 个 | §C4 冻结 |
| 字段字典种子 | `backend/seed/field_dictionary.json` | §4.1 |
| 别名库种子 | `backend/seed/alias_library.json` | §4.2 |
| Runtime 执行器 | `backend/core/artifact_runtime.py` | artifact 就绪后纯代码执行 |
| 隐私脱敏管线 | `backend/core/privacy_pipeline.py` | §5 三档：standard/strict/offline |
| Agent 调用 API | `backend/api/agent_skill.py` | 5 skill 的 HTTP 入口 |
| 前端 Agent 交互 | `frontend/src/views/AgentReview.vue` | 接受/修改/拒绝 artifact 草稿 |

### 1.4 旧业务服务的处置

| 服务 | 处置 | 说明 |
|---|---|---|
| `bank_import_service.py` | **拆分** | 上传/批次/预览/确认四个动作保留；模板匹配/AI 表头猜逻辑删除（由 Fund Agent 取代）；commit 改为执行 Parser artifact |
| `manual_flow_service.py` | **拆分** | 快速录入保留（用户直接填表）；多主体 Excel 上传逻辑改为触发 `parser.manual` skill |
| `report_service.py` | **重写** | 从 SQL 硬编码改为执行 Rule artifact |
| `bank_service.py` / `master_data_service.py` | 保留 | 主数据 CRUD，与 AI 无关 |
| 其它 service | 保留或微调 | 不直接受影响 |
| 前端 `BankImport.vue` | **大改** | 流程从 "上传 → 选模板 → 手填映射 → 提交" 改为 "上传 → 等 Agent → 审核草稿 → 接受 → 完成" |

### 1.5 数据库当前状态（需要迁移）

- 当前 `backend/data/zhangfang.db` 是 B 方案产物：v2 schema + 已删 v3 三表
- ORM 也是 v2（B 方案改的）
- alembic_version：B 方案后用户尚未确认是否已写入 baseline

**处置：**
- DB 重建（用户单机部署，目前无生产数据，可重建）
- 写一次性迁移：drop v2 fund_events → 按 CANONICAL_12 重建 → 重建 v3 三表 → alembic stamp 到 v3 baseline
- 已有的真实测试样本（如有）通过新流程重新导入

---

## 2. 治理文档回滚指令（Phase 0 必做）

### 2.1 待修订文件清单

| 文件 | 修订动作 |
|---|---|
| `docs/00_governance/00_project_constitution.md` §C1 | 回滚为 v3.0 CANONICAL_12 字段语义 |
| 同上 §C6 | 17 表清单恢复为 18 表（增 parser_artifacts / rule_artifacts / template_inference_job，删除"v2 活动表集合"措辞） |
| `docs/00_governance/01_v1_scope_and_order.md` | **整文件重写**为 v3.0 AI-First 路线，§0/§1/§2/§5 全部覆盖 |
| `docs/30_contracts/20_database_schema.md` 文头 + §T0 + fund_events 节 | 回滚为 v3 真实 schema，移除 "B 方案回滚" 措辞，把 v3 三表的 DDL 加回 |
| `docs/00_governance/03_tech_constraints.md` | 检查是否有 "v2 路线" 措辞，若有删除 |

### 2.2 §C1 v3 原貌（恢复目标）

```markdown
## §C1 · 基础数据表 · CANONICAL_12 列序冻结

`fund_events` 是本系统的事实表。其 12 列 canonical schema 列序、列名、枚举值冻结：

| # | 列名 | 类型 | NULL | 语义 |
|---|---|---|---|---|
| 1 | business_date    | DATE          | NO  | 业务日期 |
| 2 | entity_code      | VARCHAR(50)   | NO  | 法人/单位编码 |
| 3 | entity_name      | VARCHAR(200)  | NO  | 法人/单位名称 |
| 4 | account_code     | VARCHAR(50)   | NO  | 账户编码 |
| 5 | account_name     | VARCHAR(100)  | NO  | 账户名称 |
| 6 | summary          | VARCHAR(500)  | YES | 摘要 |
| 7 | counterparty     | VARCHAR(200)  | YES | 对方 |
| 8 | amount_in        | NUMERIC(18,2) | NO  | 收入（DEFAULT 0） |
| 9 | amount_out       | NUMERIC(18,2) | NO  | 支出（DEFAULT 0） |
| 10 | rolling_balance | NUMERIC(18,2) | YES | 滚动余额 |
| 11 | state           | VARCHAR(20)   | NO  | 状态枚举（默认"正常"） |
| 12 | source          | VARCHAR(20)   | NO  | 来源枚举 |

CHECK 约束：
- NOT (amount_in > 0 AND amount_out > 0) — 互斥
- amount_in >= 0 AND amount_out >= 0 — 非负
- state IN ('正常','待确认','异常','已作废')
- source IN ('网银导入','手工录入','现金录入','票据录入','财务公司单据')

不变量：
- 12 列列序 / 列名 / 枚举值冻结，新增字段一律走辅助列（batch_id / parser_artifact_id / created_at / updated_at）
- §C8 Runtime 无 AI 原则下，运行时填入 fund_events 的代码必须来自 Parser/Rule artifact，不得有其它路径
```

### 2.3 §C6 v3 原貌（恢复目标）

```markdown
## §C6 · 数据库 · v3 活动表集合

```
1. divisions
2. entities
3. banks
4. accounts
5. account_aliases
6. parser_templates                ← 仍在用作"已生效模板列表" UI 渲染（与 parser_artifacts 互补）
7. manual_field_pool
8. manual_template_schemes
9. import_batches
10. fund_events                    ← CANONICAL_12（§C1）
11. daily_report_runs
12. ai_configs
13. ai_call_logs
14. agent_configs
15. operation_logs
16. users
17. report_templates
18. parser_artifacts               ← Fund Agent 长期记忆（§7.2）
19. rule_artifacts                 ← 同上
20. template_inference_job         ← template.inference 三阶段流水线状态表
```

合计 20 表。完整 DDL 见 `docs/30_contracts/20_database_schema.md` §T1–§T6。
```

### 2.4 `01_v1_scope_and_order.md` 重写（v3 路线）

**§0 · 当前结论改为：**
```
V1 走 v3 AI-First Schema：CANONICAL_12 fund_events + parser_artifacts + rule_artifacts + template_inference_job + 5 个 skill 实体化的 Fund Agent。
```

**§1.1 包含改为（追加）：**
```
- Fund Agent 5 个 skill 完整实现（§C4）
- 字段字典 + 别名库 + 隐私三档
- artifact 沙箱执行（AST 扫描 + 超时 + 内存限制）
- 用户零编程交互：上传 → Agent 处理 → 审核 → 接受 → 入库
```

**§1.2 禁止改为：**
```
- 让用户在 UI 中直接编辑字段映射 / 正则 / JSON / 占位符绑定
- Runtime 阶段调用 LLM（§C8）
- Agent 产物代码绕过 AST 扫描入库
- 新增第 6 个 skill（§C4）
```

**§2 开发顺序改为：**
```
1. 治理文档回滚（Phase 0）
2. v3 Schema 落地（Phase 1）
3. Fund Agent 骨架（Phase 2）
4. 5 个 skill 实现（Phase 3）
5. 沙箱与守护（Phase 4）
6. Runtime 执行器（Phase 5）
7. API + 前端（Phase 6）
8. 字段字典 / 别名库 / 隐私三档（Phase 7）
9. 集成测试 + 真实样本回归（Phase 8）
```

---

## 3. Phase 实施清单

### 3.1 总览

| Phase | 名称 | 工期 | 阻塞下游 |
|---|---|---|---|
| 0 | 治理文档回滚 | 1d | Phase 1+ |
| 1 | v3 Schema 真正落地 | 2d | Phase 2+ |
| 2 | Fund Agent 骨架 | 3d | Phase 3+ |
| 3 | 5 个 Skill 实现 | 8d | Phase 4 部分 / Phase 6 |
| 4 | 沙箱与守护 | 2d | Phase 6 |
| 5 | Runtime 执行器 | 3d | Phase 6 |
| 6 | API + 前端 UX | 5d | Phase 8 |
| 7 | 字段字典 / 别名库 / 隐私三档 | 2d | Phase 3 部分依赖 |
| 8 | 集成测试 + 样本回归 | 4d | M3 |

**总工期：30 工作日**（净开发 28d + 缓冲 2d）

排序约束（不可乱）：
```
P0 → P1 → P2 ─┐
              ├─ P3 ─┐
            P7 ──────┤
                     ├─ P4 ─┬─ P6 ─ P8
                     ├─ P5 ─┘
```

### 3.2 Phase 0 · 治理文档回滚（1 天）

**目标：** 让宪法 / V1 范围 / 数据库契约三处文档**内部自洽**，回到 v3.0 AI-First 路线。

**红线：** Phase 0 **只动 `docs/`**，不修改 `backend/` 任何文件。任何要求改 ORM / alembic / 服务代码的行为都必须延后到 Phase 1+。

#### 3.2.A 守护脚本时序表（关键）

5 个守护脚本不是同一时间全部要求绿。每个脚本的扫描目标在不同 Phase 才被建立，强行在 Phase 0 跑全套会触发"扫描目标不存在 / 与红线冲突"的硬冲突。

| 守护脚本 | 扫描目标 | 必须绿的 Phase | Phase 0 期望状态 |
|---|---|---|---|
| `check_contract_hash.py` | 治理文档 SHA256 vs `contracts.lock` | **Phase 0 P0-7** | **必须绿（唯一硬性要求）** |
| `check_canonical_schema.py` | `backend/db/tables.py::FundEvent` ORM 列序 | **Phase 1 P1-2** | 红色可接受（ORM 在 Phase 1 才回滚） |
| `check_primitives_whitelist.py` | `parser_artifacts.code` AST 扫描 | Phase 3 起 | 跳过（artifact 表 Phase 1 才建，记录还没有） |
| `check_placeholder_binding.py` | `rule_artifacts.placeholder_bindings` | **Phase 3 P3-3** | 跳过（同上） |
| `check_api_inventory.py` | `backend/api/` vs `23_api_contracts.md` | Phase 6 | 仅记录当前状态，不要求绿 |

**判定原则：** Phase 0 的"全量回归"指**只跑 `check_contract_hash.py`**。其他脚本退出非零属于预期，由后续 Phase 转绿。

#### 3.2.B 任务卡

- [P0-1] 修订 `00_project_constitution.md` §C1 回滚为 CANONICAL_12（参考 §2.2）
- [P0-2] 修订同文件 §C6 增 v3 三表（参考 §2.3），更新表序号到 20
- [P0-3] **整文件重写** `01_v1_scope_and_order.md`（参考 §2.4），版本号升到 v3.1（v3.0 → v2.1 是 B 方案误改）
- [P0-4] 修订 `30_contracts/20_database_schema.md`：文头改为 "v3 真实 Schema"，§T0 列出 20 表，把 v3 三表 DDL 从 `docs/99_archived/v3_attempt/` 复制回来
- [P0-5] 检查 `03_tech_constraints.md` / `08_anti_drift.md` / `09_ai_capability_v3.md` 是否有"B 方案"残留措辞，统一清理
- [P0-6] 把 `docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md` 移到 `docs/99_archived/b_plan_repealed/`，文件头加 `> ⚠ 本方案已于 2026-04-25 作废，请改读 V1_AI_FIRST_REINSTATE_2026-04-25.md`
- [P0-7] 重算 `contracts.lock`（运行 `tools/guards/check_contract_hash.py --update`）

#### 3.2.C 验收（严格按时序表）

- [ ] **`tools/guards/check_contract_hash.py` 退出码 0**（唯一硬性要求）
- [ ] 在治理目录 grep `B 方案` / `v2 schema` 仅出现在 P0-6 归档文件中
- [ ] `00_project_constitution.md` §C1 / §C4 / §C6 / §C8 / §C9 内部不再矛盾
- [ ] `check_canonical_schema.py` 红色 → 记录到交班单，标注"由 Phase 1 P1-2 转绿"
- [ ] `check_primitives_whitelist.py` / `check_placeholder_binding.py` 跳过（artifact 表 Phase 1 才建）
- [ ] `check_api_inventory.py` 仅记录当前差异，不阻塞 Phase 0 完工

---

### 3.3 Phase 1 · v3 Schema 真正落地（2 天）

**目标：** 让 ORM、alembic、SQLite 三方对齐到 v3 CANONICAL_12 + 三表。

**任务卡：**
- [P1-1] 备份当前 DB → `backend/data/zhangfang.db.bak.b_plan.20260425`
- [P1-2] 改 `backend/db/tables.py::FundEvent` 回滚到 CANONICAL_12（参考 §2.2 列定义）
- [P1-3] 在 `backend/db/tables.py` 重新加入 `ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` 三个 ORM 类（DDL 见 §3.3.A 附录）
- [P1-4] 删除 B 方案添加的兼容字段（business_time / direction / counterparty_name / summary_text / income_amount / expense_amount / parse_status / abnormal_code / raw_data_json / previous_balance_input / ending_balance_input / source_type / entity_id / account_id），它们的语义已通过 CANONICAL_12 + state + raw_payload 表达
- [P1-5] 整理 `alembic/versions/`：保留 `001_v3_fund_events.py`（重新启用），新增 `002_add_v3_artifacts.py` 创建三个 v3 表
- [P1-6] 写一次性脚本 `scripts/reset_to_v3.py`：drop 当前 fund_events 与 v2 字段、按 alembic 重建、stamp 到 head
- [P1-7] 改 `backend/main.py::lifespan`：移除 `Base.metadata.create_all` + `_migrate_schema`，改用 `alembic upgrade head`（Python API 调用）
- [P1-8] 修复因 §C1 回滚导致的下游服务编译错误：
  - `bank_import_service.py::commit` 改为执行 Parser artifact，不再直接 INSERT（这部分由 Phase 5 完成；Phase 1 只让代码 import 通过即可，业务逻辑临时 raise NotImplementedError）
  - `manual_flow_service.py::commit` 同上
  - `report_service.py` 同上
  - 测试用例临时跳过

**验收：**
- [ ] `alembic current` 显示 v3 head
- [ ] `python -c "from db.tables import FundEvent; print([c.name for c in FundEvent.__table__.columns][:13])"` 输出 CANONICAL_12
- [ ] `python -c "from db.tables import ParserArtifact, RuleArtifact, TemplateInferenceJob"` 不报错
- [ ] `tools/guards/check_canonical_schema.py` 退出码 0

#### 3.3.A 附录 · v3 三表 DDL

```sql
CREATE TABLE parser_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100) NOT NULL,
  kind VARCHAR(20) NOT NULL,                    -- 'bank' / 'manual'
  account_code VARCHAR(50),                      -- 与某个账户绑定（可空表示通用）
  version INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',  -- 'draft' / 'active' / 'retired'
  code TEXT NOT NULL,                            -- Python 源码（必须通过 AST 扫描）
  primitives_imports JSON NOT NULL,             -- 引用的基元清单
  sample_check_log JSON NOT NULL,               -- 样本校验日志
  confidence DECIMAL(5,4),                      -- 0.0000 ~ 1.0000
  created_by VARCHAR(50) NOT NULL,              -- 'agent' / user_id
  approved_by VARCHAR(50),                      -- 用户接受时填写
  approved_at DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME
);
CREATE INDEX idx_parser_artifacts_account ON parser_artifacts(account_code, status);
CREATE INDEX idx_parser_artifacts_kind ON parser_artifacts(kind, status);

CREATE TABLE rule_artifacts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name VARCHAR(100) NOT NULL,
  template_id INTEGER REFERENCES report_templates(id),
  version INTEGER NOT NULL DEFAULT 1,
  status VARCHAR(20) NOT NULL DEFAULT 'draft',
  placeholder_bindings JSON NOT NULL,
  loop_config JSON,
  primitives_imports JSON NOT NULL,
  sample_check_log JSON NOT NULL,
  confidence DECIMAL(5,4),
  created_by VARCHAR(50) NOT NULL,
  approved_by VARCHAR(50),
  approved_at DATETIME,
  created_at DATETIME NOT NULL,
  updated_at DATETIME
);
CREATE INDEX idx_rule_artifacts_template ON rule_artifacts(template_id, status);

CREATE TABLE template_inference_job (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  template_file VARCHAR(255) NOT NULL,
  stage VARCHAR(20) NOT NULL,                   -- 'A_struct' / 'B_semantic' / 'C_review'
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  stage_a_output JSON,                          -- Stage A 结构解析产物（占位符列表 + 锚点）
  stage_b_output JSON,                          -- Stage B AI 语义映射产物（草稿 binding）
  stage_c_decision VARCHAR(20),                 -- 'accepted' / 'modified' / 'rejected'
  rule_artifact_id INTEGER REFERENCES rule_artifacts(id),
  error_message TEXT,
  created_at DATETIME NOT NULL,
  updated_at DATETIME
);
```

---

### 3.4 Phase 2 · Fund Agent 骨架（3 天）

**目标：** 创建 `backend/agents/fund/` 整套实体，让 5 个 skill 有承载体。

**任务卡：**
- [P2-1] 创建 `backend/agents/fund/` 目录结构
  ```
  backend/agents/fund/
  ├── __init__.py
  ├── AGENT.md           ← 主提示词（职责、边界、工具清单）
  ├── harness.py         ← harness_strict 模式调度器
  ├── schemas.py         ← skill 输入/输出 Pydantic Schema
  ├── memory.py          ← parser_artifacts / rule_artifacts / alias 访问层
  ├── sandbox.py         ← 在 Phase 4 实现，先放空文件
  └── skills/
      ├── __init__.py
      ├── parser_bank.py
      ├── parser_manual.py
      ├── rule_template_fill.py
      ├── rule_maintain.py
      └── template_inference.py
  ```
- [P2-2] 实现 `harness.py`：
  - `class FundAgent`：单例，初始化加载字段字典 + 别名库
  - `def run_skill(skill_name, payload) -> ArtifactDraft`：分派到对应 skill 模块
  - 强制：5 skill 名称在白名单 `{"parser.bank","parser.manual","rule.template_fill","rule.maintain","template.inference"}`
  - 强制：每次调用产生唯一 trace_id，落 ai_call_logs
- [P2-3] 实现 `schemas.py`：5 个 skill 各自的 InputSchema / OutputSchema（参考 09_ai_capability_v3.md §3）
- [P2-4] 实现 `memory.py`：
  - `def find_parser(kind, account_code) -> Optional[ParserArtifact]` — 命中已有 active artifact
  - `def save_parser_draft(...) -> int` — 写 draft，等待用户审核
  - `def approve_parser(artifact_id, user_id)` — 把 draft → active；同账户旧版 → retired
  - `def find_rule(template_id) -> Optional[RuleArtifact]` 同上
  - `def list_aliases() -> dict` — 把 account_aliases 表渲染成 alias_library
  - `def register_alias(code, alias, confidence, alias_type='自动')` — 写回
- [P2-5] 改写 5 个 skill 模块为**骨架占位**：
  ```python
  # parser_bank.py
  from agents.fund.schemas import ParserBankInput, ParserBankOutput
  def run(payload: ParserBankInput) -> ParserBankOutput:
      raise NotImplementedError("Phase 3 P3-1 实现")
  ```
- [P2-6] 改 `agents/parser-assistant/` 7 个 MD：
  - 不再标 "[V1 预留骨架]"
  - 内容指向 `backend/agents/fund/AGENT.md`，说明 v3 路线下 Fund Agent 是唯一活动 Agent
  - master/ 维持"协调"语义，但 V1 仅作为 Fund Agent 的 harness 调用入口（不做多 Agent 编排）
- [P2-7] 改 `services/agent_init.py`：bootstrap 时检测 `backend/agents/fund/` 不存在则跳过；存在则注册到 agent_configs 表（agent_code='fund'，agent_type='fund'，workspace_dir='backend/agents/fund'）

**验收：**
- [ ] `python -c "from agents.fund.harness import FundAgent; FundAgent()"` 不报错
- [ ] `python -c "from agents.fund.schemas import ParserBankInput; ParserBankInput(skill='parser.bank', account_code='X', sample_file='/tmp/x.xlsx')"` 通过验证
- [ ] DB `agent_configs` 表有 `agent_code='fund'` 一行
- [ ] 5 个 skill 模块都能 import 但调用时 raise NotImplementedError（提示 Phase 3）

---

### 3.5 Phase 3 · 5 个 Skill 实现（8 天）

**目标：** 让 5 个 skill 真正能产出 artifact 草稿。

按 09_ai_capability_v3.md §3 的规约实现。每个 skill 独立任务卡。

#### [P3-1] `parser.bank`（2 天）

**实现要点：**
1. 接收 `sample_file` 路径 → 用 `fund.primitives.sheet_ops.read_sheet` 加载（Agent 自己不开文件）
2. Stage A · 结构解析（无 AI）：
   - `detect_header_row` 找表头
   - `extract_headers` 取列字典
   - 用前 5 行采样（按 privacy_mode 脱敏）
3. Stage B · LLM 调用：
   - Prompt 模板：上下文（账户信息 + 字段字典 + 别名库片段）+ 任务（请生成 Parser 代码）
   - 强约束：output JSON Schema 严格匹配 `schemas.ParserBankOutput`
   - 必须生成 Python 代码块，仅 import `fund.primitives.*` + `{datetime, decimal, typing, re}`
   - 失败重试 1 次（错误提示 LLM 修正）
4. Stage C · 自检：
   - 把生成的 code 用 `sandbox.execute(code, sample_workbook, ctx)` 跑
   - 计算 `sample_check_log`：parsed_rows / canonical_violations / amount_sum_in / amount_sum_out
   - `canonical_violations > 0` → 返回错误，让用户重试或人工介入（不入库）
5. 写 `parser_artifacts` 为 `status='draft'`，返回 artifact_id + 自检日志 + 置信度

**验收：**
- [ ] 给一份"工行流水样本.xlsx"，调用 skill → 返回 draft 且 sample_check_log.canonical_violations == 0
- [ ] 生成的 code 通过 `tools/guards/check_primitives_whitelist.py`
- [ ] 同账户重复调用 → 返回新版本（version+1）

#### [P3-2] `parser.manual`（2 天）

实现思路同 [P3-1]，差异：
- 输入是手工流水 Excel（多家单位多账户）
- 必须支持"一行一条"和"一行多科目"两种布局识别
- 必须识别 6 核心字段（单位/账户/金额/摘要/对方/日期）
- 不能匹配的字段 → `state='待确认'`，不丢数据

**验收：**
- [ ] 给一份"多主体手工流水.xlsx"（含 3 家单位 5 账户），生成的 Parser 能产出 ≥95% 行有完整 12 列

#### [P3-3] `rule.template_fill`（1.5 天）

**实现要点：**
1. 输入是 `template_inference_job` 的 Stage A 产物（占位符列表 + 锚点）
2. LLM 调用 → 为每个占位符建议 primitive + params
3. 强校验：18 个占位符 = `placeholder_bindings.keys() ∪ loop.columns.keys()`，少一个或多一个 → 拒绝
4. 写 `rule_artifacts` 为 draft

**验收：**
- [ ] 给一份"现金日记账空白模板.xlsx"（已经过 template.inference Stage A），返回 18 个 binding 全部生成
- [ ] `tools/guards/check_placeholder_binding.py` 退出码 0

#### [P3-4] `rule.maintain`（1 天）

**实现要点：**
1. 输入是已有 rule_id + change_request 自然语言
2. LLM 调用 → 在原 binding 上做最小修改，生成新版
3. 旧版保留为 `status='active'`（暂时），新版为 `draft`；用户审核接受后旧版 → `retired`

**验收：**
- [ ] 修改"日期格式改成 MM月DD日" → 新版 binding 与旧版差异仅在该字段

#### [P3-5] `template.inference`（1.5 天）

**三阶段：**
- Stage A · 纯代码（无 AI）：扫描 .xlsx，找 `${xxx}` / `{{xxx}}` / 中文占位符 → 写 `template_inference_job.stage_a_output`
- Stage B · 调 `rule.template_fill`：拿 Stage A 的占位符列表当输入 → 拿到草稿 → 写 `stage_b_output`
- Stage C · 等待前端用户决策（accepted/modified/rejected） → 写 `stage_c_decision`

**置信度规则（§3.5 v3.0）：**
- 全部 ≥ 0.85 → 默认可用
- 任一 < 0.70 → 红色，强制人工
- 0.70–0.85 → 黄色，鼓励确认

**验收：**
- [ ] 给一份"农民工工资表空白.xlsx"，三阶段全部走通

---

### 3.6 Phase 4 · 沙箱与守护（2 天）

**目标：** 让 Agent 产出的代码绝对不能逃出白名单。

**任务卡：**
- [P4-1] 实现 `backend/agents/fund/sandbox.py`：
  - `def execute(code: str, workbook, ctx, timeout=30, mem_limit_mb=256) -> Iterator[CanonicalRow]`
  - 实现：
    - 在执行前调 `tools/guards/check_primitives_whitelist.py` 做 AST 扫描
    - 用 `multiprocessing.Process` 起子进程执行（超时 kill）
    - 子进程内 `resource.setrlimit(RLIMIT_AS, mem_limit)`（Linux 才支持，Windows 退化为只做超时）
    - exec 时仅暴露 `fund.primitives.*` + 标准白名单子集到 globals
    - 任何异常 → 杀进程 → 返回错误结构
- [P4-2] 加强 `tools/guards/check_primitives_whitelist.py`：
  - 当前已扫 import；加扫 `Call(Name='open'/'eval'/'exec'/'compile'/'__import__')` 和 `Attribute('__class__'/'__subclasses__'/'__globals__')`
- [P4-3] 写沙箱测试：
  - 提交合法 code → 通过
  - 提交 `import os` → 拒绝
  - 提交 `eval("...")` → 拒绝
  - 提交死循环 → 30s 超时被 kill
  - 提交 `[1] * 10**9` 内存炸弹 → mem_limit 触发（Linux）/ 30s 超时兜底（Windows）

**验收：**
- [ ] 上述 5 个测试用例全部通过
- [ ] sandbox.execute 的 timeout/mem 配置可从 `ai_configs` 读取

---

### 3.7 Phase 5 · Runtime 执行器（3 天）

**目标：** artifact 就绪后，**纯代码执行**写入 fund_events，禁止 LLM 调用（§C8）。

**任务卡：**
- [P5-1] 实现 `backend/core/artifact_runtime.py`：
  - `def run_parser(artifact_id, file_path, ctx) -> Iterator[CanonicalRow]`
    - load `parser_artifacts.code`（status='active'）
    - 用 sandbox 执行
    - yield 12 列 dict
  - `def run_rule(artifact_id, ctx) -> Workbook`
    - load `rule_artifacts.placeholder_bindings + loop_config`
    - 解析 binding，对每个 primitive 调用对应函数
    - 把结果填入模板，返回 Workbook
- [P5-2] 改写 `backend/services/bank_import_service.py`：
  - `commit(batch_code, parser_artifact_id)` ← 注意签名变化
  - 调 `artifact_runtime.run_parser` 拿 CanonicalRow 流
  - 逐行 `db.add(FundEvent(**row))`，落 batch_id 与 parser_artifact_id 外键
- [P5-3] 改写 `backend/services/manual_flow_service.py` 同上（multi_entity_excel 流程）
  - 快速录入路径保留：用户表单 → 直接构造 CanonicalRow → state='正常' → 入库（这条路径无 Parser 介入是合规的，因为是用户直接给结构化数据）
- [P5-4] 改写 `backend/services/report_service.py`：
  - `generate_report(rule_artifact_id, ctx)` 调 `artifact_runtime.run_rule`
  - 返回 Workbook 流给下载端点
- [P5-5] Runtime 守护：在 `artifact_runtime.py` 顶部 import `core.runtime_guard`，启动时检查 `os.environ['ZF_RUNTIME_NO_AI'] == '1'`（CI 设置）→ monkey-patch `requests.post` / `urllib.request.urlopen` 在 runtime 阶段调用时抛异常

**验收：**
- [ ] 用 P3-1 产出的 Parser 跑 commit → fund_events 出现 N 行
- [ ] 同流程，跑 1000 行 → 不调 LLM（grep ai_call_logs）
- [ ] Rule artifact 跑 generate_report → Excel 文件 18 个占位符全部填充

---

### 3.8 Phase 6 · API + 前端 UX（5 天）

**目标：** 让用户在浏览器里只点 4 个按钮就能完成全流程。

#### 后端 API（2 天）

新增端点（注意 §C7 总数上限 42，要在 23_api_contracts.md 检查并更新）：

```
POST /api/agent/skill/{skill_name}      ← 触发 5 个 skill 之一
GET  /api/parser-artifacts              ← 列出，支持 status / kind / account_code 筛选
GET  /api/parser-artifacts/{id}         ← 详情（含 code / sample_check_log）
POST /api/parser-artifacts/{id}/approve ← 用户审核接受 → status='active'
POST /api/parser-artifacts/{id}/reject  ← 用户拒绝 → status='retired'
POST /api/parser-artifacts/{id}/modify  ← 用户修改 binding（仅 rule，不允许改 parser code）
GET  /api/rule-artifacts                ← 同上
GET  /api/rule-artifacts/{id}
POST /api/rule-artifacts/{id}/approve
POST /api/rule-artifacts/{id}/reject
POST /api/rule-artifacts/{id}/modify
GET  /api/template-inference/{job_id}   ← 拉 Stage A/B 进展
```

#### 前端组件（3 天）

新增页面：
- `frontend/src/views/AgentReview.vue`：通用 artifact 审核页
  - 路由：`/agent/review/parser/:id` 和 `/agent/review/rule/:id`
  - 内容：
    - 顶部：banner 显示置信度颜色（绿 ≥0.85 / 黄 0.70-0.85 / 红 <0.70）
    - 中部：sample_check_log 可视化（解析行数 / 12 列违规行 / 收入支出小计）
    - 下部：code/binding 高亮展示（只读，不让用户改）
    - 底部三按钮：[接受] / [拒绝] / [修改]（修改仅对 rule 可用，弹层让用户调 binding 的 primitive 名而不是写代码）

改造现有页面：
- `BankImport.vue`：上传后 → 触发 `parser.bank` skill → 跳转 AgentReview
- `ManualFlow.vue`：多主体 Excel 上传后 → 触发 `parser.manual` skill → 跳转 AgentReview
- `Report.vue`：选模板 → 如无 active rule_artifact → 触发 `template.inference` → 跳转 AgentReview

**验收：**
- [ ] 上传 → 自动跳转审核页 → 接受 → 列表回写 → fund_events 入库，全部 UI 流程
- [ ] 用户全程未输入 JSON / 正则 / 字段映射

---

### 3.9 Phase 7 · 字段字典 / 别名库 / 隐私三档（2 天）

**任务卡：**
- [P7-1] 创建 `backend/seed/field_dictionary.json`（参考 09_ai_capability_v3.md §4.1，10 个核心字段 + 别名）
- [P7-2] 创建 `backend/seed/alias_library.json`（初始为空 dict）
- [P7-3] 改 `agents/fund/memory.py::list_aliases` 把种子文件 + DB account_aliases 合并
- [P7-4] 实现 `backend/core/privacy_pipeline.py`：
  - `def mask_for_llm(rows, mode) -> rows_masked`
  - mode=standard：金额脱敏到千位，单位首字母 + 占位
  - mode=strict：去掉所有数据行，仅保留列头
  - mode=offline：抛异常（不允许 LLM 调用）
- [P7-5] 在 `harness.run_skill` 入口校验 `ai_configs.privacy_mode`，按档位调用 mask_for_llm

**验收：**
- [ ] privacy_mode='strict' 时 prompt 中无任何数据行
- [ ] privacy_mode='offline' 时 skill 调用直接报错"已设为离线模式"

---

### 3.10 Phase 8 · 集成测试 + 真实样本回归（4 天）

**任务卡：**
- [P8-1] 准备样本（脱敏后入库 `tests/fixtures/`）：
  - 工商银行流水 1 份
  - 建设银行流水 1 份
  - 招商银行流水 1 份
  - 多主体手工流水 1 份
  - 现金日记账空白模板 1 份
- [P8-2] E2E 测试用 Playwright：
  - test_bank_import_e2e — 上传 工行 → 等 Agent → 接受 → 看 fund_events
  - test_bank_import_repeat — 第二次上传同银行 → 直接命中已有 active Parser
  - test_manual_flow_e2e — 多主体 Excel
  - test_report_e2e — 模板上传 → template.inference → 接受 → 生成 Excel
- [P8-3] 跨银行回归：用同一 Parser 跑另一份工行流水（不同月份）→ 错误率 ≤ 1%
- [P8-4] 隐私回归：strict 模式下跑全流程 → ai_call_logs 中 prompt 字段不含金额 / 户名
- [P8-5] 沙箱回归：注入恶意 code（os/eval/death loop）→ 全部被拦
- [P8-6] CI 接入：GitHub Actions / 本地脚本，pytest + tools/guards/check_*.py 全绿才允许 commit

**验收：**
- [ ] 上述 5 项全绿
- [ ] backend 服务覆盖率 ≥ 75%
- [ ] 前端关键流程用 Playwright 录屏归档

---

## 4. 红线（不可逾越）

按 §C8 + §C9 + §C5：

1. ❌ Runtime 阶段（commit / generate_report / 导出）调用 LLM = CRITICAL
2. ❌ artifact 代码绕过 AST 扫描入库 = CRITICAL
3. ❌ artifact 代码 import 非白名单模块 = CRITICAL
4. ❌ 让用户在 UI 中编辑字段映射 / 正则 / JSON / 占位符 binding = HIGH
5. ❌ 把用户原始文件直接发给 LLM（必须先脱敏） = HIGH
6. ❌ 新增第 6 个 skill = 违反 §C4 走 ChangeFlow
7. ❌ 修改宪法 / V1 范围 / 数据库契约 文档而不走 ChangeFlow = 违反 §C0
8. ❌ Parser/Rule artifact 代码以外的位置写入 fund_events（除"快速录入"用户直接录入路径） = HIGH

---

## 5. 与已存在资产的接口

### 5.1 必须保留不动

| 资产 | 原因 |
|---|---|
| `backend/fund/primitives/` 7 模块 37 函数 | 96% 覆盖率，是 Parser/Rule artifact 唯一可调用对象 |
| `tools/guards/check_*.py` 5 个 | 守护脚本，contract.lock 依赖 |
| `docs/00_governance/00_project_constitution.md` §C2/§C3/§C4/§C5/§C7/§C8/§C9 | v3.0 原貌不动 |
| `docs/00_governance/09_ai_capability_v3.md` 全文 | Fund Agent 设计的真相源 |
| `docs/30_contracts/25_primitives_whitelist.md` 全文 | 基元规约 |
| `backend/services/master_data_service.py` / `bank_service.py` / 其它主数据 CRUD | 与 AI 无关 |

### 5.2 可放心修改

| 资产 | 修改原因 |
|---|---|
| `backend/db/tables.py::FundEvent` 等 | Phase 1 回滚 |
| `backend/services/bank_import_service.py` | Phase 5 重写 commit |
| `backend/services/manual_flow_service.py` | 同上 |
| `backend/services/report_service.py` | Phase 5 重写 |
| `backend/main.py` | Phase 1 用 alembic 替换手写迁移 |
| `frontend/src/views/BankImport.vue` / `ManualFlow.vue` / `Report.vue` | Phase 6 改造 |
| 治理文档中"B 方案"措辞 | Phase 0 全部清理 |

### 5.3 必须重建（B 方案删了的）

| 资产 | 操作 |
|---|---|
| `parser_artifacts` 表 | Phase 1 P1-3 |
| `rule_artifacts` 表 | 同上 |
| `template_inference_job` 表 | 同上 |

---

## 6. 给下一棒 AI 的开工手册

### 6.1 必读顺序

1. 本文件全部
2. `docs/00_governance/00_project_constitution.md`（重点 §C1 §C4 §C5 §C8 §C9）
3. `docs/00_governance/09_ai_capability_v3.md`（Fund Agent 完整设计）
4. `docs/30_contracts/25_primitives_whitelist.md`（37 基元规约）
5. `docs/00_governance/08_anti_drift.md`（防跑偏六层机制）
6. `docs/60_claude_code_support/12_claude_code_collaboration_protocol.md`（协作协议）
7. **不要读** `docs/99_archived/b_plan_repealed/B_PLAN_COMPLETE_2026-04-24.md`（已作废，仅作为反面教材）

### 6.2 环境准备

```bash
cd F:/zhangfangxiansheng

# 备份当前 DB
cp backend/data/zhangfang.db backend/data/zhangfang.db.bak.b_plan.20260425

# Python 环境
cd backend
python -m venv venv
venv/Scripts/activate
pip install -r requirements.txt

# 前端
cd ../frontend
npm install

# 守护脚本试跑（Phase 0 完成后应该全绿）
cd ..
python tools/guards/check_contract_hash.py
python tools/guards/check_canonical_schema.py
python tools/guards/check_primitives_whitelist.py
python tools/guards/check_placeholder_binding.py
python tools/guards/check_api_inventory.py
```

### 6.3 每 Phase 完成后必交付

```markdown
## Phase {N} 完成报告

### 新增文件
- ...

### 修改文件
- ...

### 删除文件
- ...

### 守护脚本结果
- check_contract_hash.py: ✅
- check_canonical_schema.py: ✅
- check_primitives_whitelist.py: ✅
- check_placeholder_binding.py: ✅
- check_api_inventory.py: ✅

### 验收证据
- 命令输出 / 截图路径 / 测试通过列表

### 已知风险
- ...

### 是否达到下一 Phase 进入条件
- YES / NO + 理由
```

### 6.4 用户回归里程碑

| 里程碑 | Phase 完成 | 用户验收 |
|---|---|---|
| **M0** | P0 | 治理文档自洽（让用户读 §C1/§C4/§C9 三处确认不再矛盾） |
| **M1** | P1+P2 | DB 重建 + Fund Agent 骨架启动；用户在 AI 配置页能看到 fund agent |
| **M2** | P3 | 5 个 skill 在 dev 环境可调通（用样本 Excel 试一遍） |
| **M3** | P4+P5 | Runtime 跑通 1000 行流水，零 LLM 调用 |
| **M4** | P6 | 用户在浏览器里上传文件 → 审核 → 接受全 UI 流程 |
| **M5** | P7+P8 | 隐私三档可切换；3 家银行真实样本全部 ≤1% 错误率 |

每个 M 都需要用户**亲自试用**并给"通过"才能进下一段。

### 6.5 当方向再次出现"是否要简化/降级"诱惑时

**停下，写问题报告，等用户决定。** 不要自己拍板退化路线。

具体红线：
- 看到 v3 schema 与 DB 不一致 → 修 DB，**不要**回 v2
- 看到 5 个 skill 难做 → 拆分子任务多花时间，**不要**砍 skill
- 看到沙箱难写 → 看看是否能用现成库（RestrictedPython / pyston subset），**不要**让 artifact 直接 exec
- 看到前端 UX 复杂 → 简化到必须的 4 步（上传/审核/接受/查看），**不要**回到"让用户写 mapping"
- 看到 LLM 调用慢/不稳 → 优化 prompt + 重试 + Ollama 本地兜底，**不要**改成"AI 仅做提示"

---

## 7. 工期与资源

### 7.1 总工期

**30 工作日**（Phase 0–8 净开发 28 天 + 缓冲 2 天）

### 7.2 关键路径

```
P0(1d) → P1(2d) → P2(3d) → P3(8d) → P5(3d) → P6(5d) → P8(4d)  =  26d
                          ↘ P4(2d) ↗
                          ↘ P7(2d) (与 P3 部分并行)
```

### 7.3 风险点 + 处置

| 风险 | 影响 | 处置 |
|---|---|---|
| LLM 生成的 Parser 代码经常失败重试 | P3 工期 ×1.5 | 在 prompt 里附 §P9 示例骨架 + few-shot；预计真实工期 P3=10d 而非 8d |
| Windows 沙箱内存限制不可用 | P4 退化为只做超时 | 接受退化；在 macOS/Linux 部署时再加 RLIMIT |
| 前端 AgentReview 设计复杂 | P6 工期 ×1.3 | 先简版（接受/拒绝），修改功能延后 V1.1 |
| 用户提供真实样本不脱敏 | P8 阻塞 | 提供脱敏脚本 `scripts/desensitize_sample.py` |
| 已删 v3 表的 DB 迁移失败 | P1 阻塞 | 已备份 → 实在不行重建空 DB（用户单机无生产数据） |

### 7.4 与 V1 总开发顺序的对应

V1 总顺序（治理文档 §2 v3.1 版）：

```
1. 项目骨架与可运行环境              ← 已完成（B 方案残留可用）
2. 数据库与基础表                    ← Phase 1
3. 主数据中心                        ← 已完成
4. AI 配置与 Agent 骨架              ← Phase 2 + 改造已有
5. 银行流水导入与模板识别            ← Phase 3 P3-1 + Phase 5 + Phase 6
6. 手工流水双轨                      ← Phase 3 P3-2 + Phase 5 + Phase 6
7. 基础数据表与区间日报              ← Phase 3 P3-3/P3-4/P3-5 + Phase 5 + Phase 6
8. 首页总控台、导出、打印、看板      ← 部分已完成，Phase 5/6 顺带补
9. 集成测试与真实样本回归            ← Phase 8
```

---

## 8. 结语

### 8.1 我之前犯的错（备忘）

- 看到 ORM/DB 不一致就喊"v3 修不动"
- 没读 §C4/§C9 整套 AI-First 设计就推翻 §C1
- 把 B 方案当"务实"，实际是把核心可用性砍了
- 没识别契约自相矛盾的契约歧义点（§C9 vs §0/§1），按协作协议本应停下报告

### 8.2 这份方案的边界

- 我**只**写了实施计划。不修代码、不改文档。
- 治理文档的回滚动作（Phase 0）必须由下一棒 AI 拿到用户授权后再做（按 §ChangeFlow）
- v3.0 原文需要从 git history 恢复，本文件 §2 给的只是**目标态摘要**，不是完整文本

### 8.3 给用户的说明

1. **B 方案被作废**了。`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md` 在 P0-6 后会移到归档。
2. **治理文档需要回滚**，这是 §ChangeFlow 受控修改，**需要你书面同意**才能执行。请在确认本方案后，授权下一棒 AI 进行 Phase 0 的修订。
3. **DB 会被重建**。当前 `zhangfang.db` 自动备份后会按 v3 重建。如有真实数据已录入，请在 Phase 1 前导出。
4. **总工期 30 个工作日**。比之前 B 方案的 15 天多一倍，但这次是真正能交付到财务人员手上的。
5. 中间有 5 个用户回归点（M0–M5），每个点你都会亲自试一遍才能进下一段。

— 编制完毕 · 2026-04-25 · Claude Code Opus 4.7
