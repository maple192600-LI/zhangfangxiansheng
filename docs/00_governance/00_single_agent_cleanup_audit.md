# 单通用 Agent 架构清理审计报告 v3.2

> **本文档是清理审计基线，不是功能实现文档，不代表清理已完成。**
> 本文档记录仓库中与"单通用 Agent 架构原则"不一致的所有对象，按分类和 Phase 给出清理建议。实际清理需按 Phase 顺序执行，每 Phase 完成后验收再进入下一 Phase。

**审计日期：** 2026-05-10
**审计范围：** 仓库全部文件，聚焦"单通用 Agent 架构原则"一致性
**审计方法：** 只读审计，不修改任何文件

---

## 一、审计原则

| # | 原则 |
|---|------|
| 1 | 项目只有一个通用 Agent（`backend/agents/runtime.py`），不存在独立的 FundAgent、ReportAgent 等领域 Agent 类 |
| 2 | 所有 skill 由通用 Agent 统一调度，不绑定到任何领域专用调度器 |
| 3 | 在解析器、规则、报表模板等可复用规则类能力中，Agent 只负责生成和维护 Artifact，不直接写业务表。日常查询、解释、异常归纳、操作引导等能力仍可由通用 Agent 通过受控工具完成 |
| 4 | 确定性执行阶段由 artifact runtime 完成，不需要专用调度器（如 harness_strict） |
| 5 | `harness_strict` / FundAgent harness 是旧体系遗留，不应出现在生产路径 |
| 6 | `fund_skill_run` 等桥接工具绕过通用 Agent runtime，属于旧体系 |
| 7 | Artifact 的创建草稿可由通用 Agent 通过工具层发起；Artifact 的管理、版本、状态流转由 artifact service 负责；Artifact 的审核必须由用户确认后通过 artifact service 完成；Artifact 的执行由 artifact runtime 确定性完成，不需要专用调度器 |

---

## 二、分类判断标准

| 分类 | 含义 | 判定条件 |
|------|------|----------|
| A — 必须删除 | 旧体系残留，无复用价值 | 生产环境从未生效（死链路）且无迁移价值；空壳文件无实际逻辑；文档中与原则直接矛盾的"冻结"条款（冻结后应删除） |
| B — 必须迁移（后删除） | 含可复用逻辑，但当前位置/归属错误 | 逻辑正确但挂在 FundAgent 名下；被生产代码或测试实际引用；迁移后原位置删除 |
| C — 必须保留 | 符合新原则，或属于白名单基础设施 | §C5 白名单（primitives、artifacts 产物文件）；通用 Agent 基础设施；不含 FundAgent 概念的通用代码 |
| D — 待确认 | 需人工判断取舍 | 有旧体系特征但也有独立价值；测试引用不存在的文件但测试本身有价值 |

---

## 三、关键发现

### 3.1 生产死链路

`backend/api/fund_agent.py` 定义了 9 个 API 端点（`/api/fund/*`），但 `backend/main.py` 未注册该 router。这意味着：

- 生产环境中 `/api/fund/*` 的 9 个端点全部 404
- 前端 `fund.js` 的 9 个 API 调用全部不通
- 依赖这些端点的 `AgentReview.vue`、`ManualFlow.vue`、`ReportTemplate.vue` 功能不可用
- `tests/fund/test_phase6_api.py` 在测试中手动注册 router 才能通过，生产从未生效

这是最高优先级问题：旧体系声称有 5 个 fund skill 和完整的 API 端点，但生产从未跑通。

### 3.2 引用不存在的文件

| 文件 | 引用位置 | 状态 |
|------|----------|------|
| `agents/fund/skills/_shared.py` | `tests/fund/conftest.py:8`、`tests/fund/test_artifact_runtime.py:6` | 仓库中不存在 |
| `agents/fund/sandbox.py` | `tests/fund/test_sandbox.py:5` | 仓库中不存在 |

说明 `agents/fund/` 的实现不完整，旧体系未完成。

---

## 四、按对象类型审计

### 4.1 治理文档（最高优先级）

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `00_project_constitution.md` | D | §C4 冻结 5 个 fund skill；§C6 标记"Fund Agent 产物" | Phase 0 废弃注释 → Phase 1 重写 §C4：移除"5 个固定 fund skill 冻结"口径，改为"通用 Agent 初始技能与动态技能体系"，并明确不允许绑定领域专用调度器；§C6 改为"通用 Agent 产物" |
| `01_project_map.md` | D | 描述"三层架构"中 `fund/` 为"财务专用子系统"，`harness.py` 为 FundAgent 调度器 | Phase 1 重写相关段落，明确 `fund/` = 产物确定性执行基础设施 |
| `02_naming_glossary.md` | D | FundAgent 定义为"独立 Python 类" | Phase 1 标记为旧中间态，补充新定义 |
| `03_target_product_map.md` | D | 基本符合新原则，但未明确说明"Agent 均指唯一通用 Agent" | 建议补充"本文档中 Agent 均指唯一通用 Agent"的说明 |
| `04_roadmap_and_change_log.md` | D | Phase F 延续 FundAgent harness 概念 | Phase 1 重写 Phase F，改为"产物体系完成迁移" |
| `10_scope_and_order.md` | D | §1.1"Fund Agent：5 个 skill"，§1.2"禁止新增第 6 个 skill" | Phase 1 删除 §1.1-1.2 的旧 skill 清单，改为通用 Agent 技能体系 |
| `12_tech_constraints.md` | D | §2.1 并列 Fund Agent 与通用 Agent；§4.1 物理结构含 fund/ 目录；§4.3"Fund Agent 专用约束" | Phase 1 重写 §2.1 和 §4.3，消除 FundAgent 独立实体概念 |
| `18_anti_drift.md` | D | §3 Layer 1 含"§C4 Fund Agent 5 skill" | Phase 1 更新 Layer 1 清单，移除旧 skill 引用 |
| `19_ai_capability.md` | D | §5 整章"Fund Agent 专用约束"（含 harness_strict、5 skill 表、物理位置） | Phase 1 删除 §5 或重写为"产物体系 Agent 能力约束" |

### 4.2 执行文档

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `16_agent_system_execution.md` | D | §2.3 "Fund Agent 专用模块"，§6 双轨制声明 | Phase 1 重写 §2.3 和 §6 |
| `17_skill_system_design.md` | D | §4.3 code_entry 映射到 fund_skill_run | Phase 1 重写 §4.3，code_entry 应映射到通用 Agent 工具 |

### 4.3 产品设计文档

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `03_funds_workflow.md` | D | "已有解析器模板"延续旧概念，未提及 Agent 角色 | Phase 1 补充"解析器模板由通用 Agent 通过工具生成" |

### 4.4 API 契约

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `23_api_contracts.md` | D | #13-17 标记为"Fund Agent"，路径含 `/fund/` | Phase 2 建立新契约后，Phase 5 删除旧契约 |

### 4.5 后端代码 — 旧 Agent 体系

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `backend/agents/fund/__init__.py` | A | "Fund Agent 账房先生核心财务智能体" — 旧 Agent 声明 | Phase 5 删除 |
| `backend/agents/fund/harness.py` | B | `FundAgent` 类（第 35 行）、`ALLOWED_SKILLS`（第 20-26 行）— 旧调度器，但 `_stage_a_parse` / `_stage_b_map` 可复用 | Phase 3 提取可复用逻辑 → Phase 5 删除 |
| `backend/agents/fund/memory.py` | B | Artifact CRUD（第 13-148 行）和字段字典加载（第 151-199 行）可复用 | Phase 3 迁移 → Phase 5 删除 |
| `backend/agents/fund/schemas.py` | B | Pydantic Schema 全部可复用 | Phase 3 迁移 → Phase 5 删除 |
| `backend/agents/fund/skills/*.py` | A | 5 个空壳文件 | Phase 5 删除 |

### 4.6 后端代码 — 桥接工具

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `skill_ops.py` — `fund_skill_run`（第 248-276 行） | A | 直接调用 FundAgent 绕过 runtime。该函数本身必须删除，不迁移。不得将其调度结构迁移为新的通用 Agent 工具 | Phase 5 删除 |
| `skill_ops.py` — `_find_fund_skill_dir`（第 566-588 行） | A | 定位旧 skill 目录 | Phase 5 删除 |
| `skill_ops.py` — `_record_fund_skill_experience`（第 591-598 行） | B | 旧经验记录。仅其中的经验记录思路，如确认有价值，可迁移到通用技能经验系统 | Phase 3 评估并迁移 → Phase 5 删除旧函数 |

### 4.7 后端代码 — API 路由（死链路）

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `backend/api/fund_agent.py` 整体 | B（部分迁移后全部 A） | 9 个端点，main.py 未注册，生产死链路 | 见下方细分 |
| ↳ ParserArtifact / RuleArtifact / TemplateInferenceJob 的 CRUD、审核、查询端点 | B | 产物管理逻辑可复用 | Phase 3 迁移到新 artifact API |
| ↳ `/api/fund/agent/skills/*/invoke` 等 skill 调用端点 | A | 直接调用旧 FundAgent，属于旧调度体系。必须删除，不迁移，不得改名后保留 | Phase 5 删除 |
| `backend/main.py` | C | 无 fund_agent 注册，共 20 个路由模块 | Phase 2 注册新路由（通用 Agent 产物管理 API） |

### 4.8 后端代码 — 产物执行基础设施

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `backend/core/artifact_runtime.py` | C | 两个占位函数 `raise ValueError`，docstring 错误标注"deprecated" | Phase 2 修正 docstring，定义 `run_parser` / `run_rule` 的输入、输出、错误格式、沙箱边界和验收标准。是否实现完整执行逻辑应作为后续独立开发任务，不纳入本清理审计基线 |
| `backend/fund/primitives/`（7 个模块） | C | §C5 白名单，确定性基元函数 | 保留 |
| `backend/fund/artifacts/parsers/`（15 个 .py 产物文件） | C | §C5 白名单，确定性解析产物 | 保留 |
| `backend/fund/__init__.py` | C | primitives 和 artifacts 包入口 | 保留 |

重要区别：`backend/fund/`（产物确定性执行基础设施）≠ `backend/agents/fund/`（FundAgent 调度器）。前者保留，后者迁移后删除。

### 4.9 SKILL.md 技能文件

具体工具字段以实际文件为准，执行清理前需逐个确认 allowed-tools。

| 文件 | 分类 | 核心问题 | 处理建议 |
|------|------|----------|----------|
| `fund_parser_bank/SKILL.md` | B | 含 `code_entry` 绑定到 harness key；含 `db_insert_fund_event`（直接写业务表） | Phase 3 改为通用 Agent 技能：移除 code_entry，移除 db_insert_fund_event，保留解析逻辑描述 |
| `fund_parser_manual/SKILL.md` | A | 根本性问题：不是生成解析器，而是绕过 ParserArtifact 直接录入手工流水。违反原则 3 和 7 | Phase 5 删除旧 `fund_parser_manual/SKILL.md`，不得直接迁移。后续如需手工流水相关技能，应新建 `manual_parser` 或 `manual_entry_assistant`，并明确其职责：生成手工模板解析规则或辅助用户录入，不得直接写入 `fund_events`，不得绕过预览、确认和确定性服务层 |
| `fund_rule_template_fill/SKILL.md` | B | 含 `code_entry`；含 `db_insert_fund_event` | Phase 3 移除 code_entry 和 db_insert_fund_event，保留规则填充逻辑描述 |
| `fund_rule_maintain/SKILL.md` | B | 含 `code_entry` | Phase 3 移除 code_entry，保留规则维护逻辑描述 |
| `fund_template_inference/SKILL.md` | B | 含 `code_entry` | Phase 3 移除 code_entry，保留模板推断逻辑描述 |

### 4.10 前端代码

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `frontend/src/api/fund.js` | B | 9 个 API 调用，全部调不通（死链路） | Phase 4 替换为调用新通用 Agent 产物管理 API |
| `frontend/src/views/ManualFlow.vue` | D | 第 180 行调用 `invokeFundSkill('parser.manual')` | Phase 4 移除 `invokeFundSkill`。如新通用 Agent 任务入口已完成，则通过通用 Agent 任务/会话入口发起解析器生成；如未完成，则隐藏或禁用该入口，并给出明确状态说明 |
| `frontend/src/views/ReportTemplate.vue` | D | 调用 `fund.uploadFundTemplate` 等 | Phase 4 替换为新 API 调用 |
| `frontend/src/views/AgentReview.vue` | B | import fund.js，调用 `approveParserArtifact` 等，标题"Fund Agent 审核" | Phase 4 替换 API 调用，标题改为"产物审核" |
| `frontend/src/views/agent/*.vue`（6 个文件） | C | 通用 Agent 前端文件 | 保留 |

### 4.11 测试代码

| 文件 | 分类 | 问题 | 处理建议 |
|------|------|------|----------|
| `tests/fund/conftest.py` | A | 引用 `agents.fund.skills._shared`（不存在） | Phase 5 删除 |
| `tests/fund/test_phase6_api.py` | A | 手动注册 fund_agent router，测试旧体系端点 | Phase 5 删除（新端点在 Phase 2-3 后写新测试） |
| `tests/fund/test_artifact_runtime.py` | A | 引用 `_shared`（不存在） | Phase 5 删除 |
| `tests/fund/test_sandbox.py` | A | 引用 `agents.fund.sandbox`（不存在） | Phase 5 删除 |
| `tests/fund/test_phase7_privacy.py` | A | 直接实例化 FundAgent | Phase 5 删除 |
| `tests/fund/primitives/`（7 个文件） | C | 基元函数测试，不含 FundAgent 概念 | 保留 |
| `tests/e2e/test_full_flow.py` | D | 调用 `/api/fund/` 端点 | Phase 4 更新为新端点路径 |
| `tests/e2e/conftest.py` | D | 引用 fund_agent | Phase 4 更新引用 |

---

## 五、清理执行计划（Phase 0-5）

### Phase 0：冻结与标记（风险：零）

**目标：** 在不改变任何运行时行为的前提下，标记所有旧体系内容为"废弃"。

**允许的操作：**

- 在文档中添加 `[DEPRECATED]` 标记
- 在代码文件头部添加废弃注释（如 `# DEPRECATED: 本文件属于旧 FundAgent 体系，将在 Phase 5 删除`）
- 在 `00_project_constitution.md` §C4 添加注释说明 5 个 fund skill 冻结条款将在后续 Phase 重写

**不允许的操作：**

- 不修改函数行为、路由注册、业务逻辑、数据库结构或测试行为
- 不删除任何文件
- 不修改任何代码逻辑
- 不改变任何 import 或依赖关系

**产出：** 所有旧体系对象被明确标记，后续 Phase 可按标记追踪。

---

### Phase 1：文档修正（风险：低）

**目标：** 修正所有治理文档和执行文档，消除 FundAgent 独立实体概念。

**修改范围：**

| 文件 | 修改内容 |
|------|----------|
| `00_project_constitution.md` | 重写 §C4：移除"5 个固定 fund skill 冻结"口径，改为"通用 Agent 初始技能与动态技能体系"，并明确不允许绑定领域专用调度器；§C6 "Fund Agent 产物"改为"通用 Agent 产物" |
| `01_project_map.md` | 重写"财务专用子系统"描述，明确 `fund/` = 产物确定性执行基础设施 |
| `02_naming_glossary.md` | FundAgent 标记为旧中间态，补充通用 Agent 定义 |
| `03_target_product_map.md` | 补充"本文档中 Agent 均指唯一通用 Agent"说明 |
| `04_roadmap_and_change_log.md` | 重写 Phase F 为"产物体系完成迁移" |
| `10_scope_and_order.md` | 删除 §1.1-1.2 旧 skill 清单，改为通用 Agent 技能体系 |
| `12_tech_constraints.md` | 重写 §2.1 和 §4.3，消除 FundAgent 独立实体概念 |
| `18_anti_drift.md` | 更新 §3 Layer 1 清单 |
| `19_ai_capability.md` | 删除或重写 §5 "Fund Agent 专用约束" |
| `16_agent_system_execution.md` | 重写 §2.3 和 §6 |
| `17_skill_system_design.md` | 重写 §4.3 code_entry 映射 |
| `03_funds_workflow.md` | 补充 Agent 角色说明 |

**回滚方式：** git revert，纯文档变更无运行时影响。

---

### Phase 2：建立新契约（风险：中）

**目标：** 建立通用 Agent 产物管理的 API 契约和运行时契约，为旧能力迁移提供目标。

**允许的操作：**

- 以新增文件为主
- 仅允许最小修改 `artifact_runtime.py` 的契约说明（docstring、类型标注）
- 仅允许 `main.py` 的新路由注册（注册新契约路由，不修改已有路由）

**新增文件：**

- 新 API 契约文档（`23_api_contracts.md` 中新增章节，或独立文件）
- 通用 Agent 产物管理 service（如果需要新增）

**扩展 artifact_runtime.py：**

- 修正 docstring（去掉 "deprecated"）
- 定义 `run_parser` / `run_rule` 的输入、输出、错误格式、沙箱边界和验收标准
- 是否实现完整执行逻辑应作为后续独立开发任务，不纳入本清理审计基线

**不允许的操作：**

- 不删除任何旧文件
- 不修改旧路由或旧 service 的逻辑
- 不修改前端代码
- 不修改 `agents/fund/` 下的任何文件

**回滚方式：** 删除新增文件，revert `main.py` 和 `artifact_runtime.py` 的最小修改。

**验收标准：**

- 新增文件存在且通过 lint
- `main.py` 中可看到新路由注册
- 旧文件未被动
- `git diff --name-only` 显示只有新增文件 + `main.py` + `artifact_runtime.py`

---

### Phase 3：迁移能力（风险：高）

**目标：** 将 `agents/fund/` 中的可复用逻辑迁移到新位置。

**迁移清单（含明确目标位置）：**

| 源文件 | 可复用内容 | 目标位置 |
|--------|------------|----------|
| `agents/fund/harness.py` `_stage_a_parse` / `_stage_b_map` | 解析映射逻辑 | `backend/services/template_analysis.py` |
| `agents/fund/memory.py` 字段字典加载 | 字段映射逻辑 | `backend/services/field_dictionary_service.py` |
| `agents/fund/memory.py` artifact CRUD | 产物管理逻辑 | `backend/services/artifact_service.py` |
| `agents/fund/schemas.py` | Pydantic Schema | `backend/schemas/artifact_schemas.py` |
| `skill_ops.py` `_record_fund_skill_experience` | 经验记录思路（如确认有价值） | 通用技能经验系统 |
| `api/fund_agent.py` 中产物 CRUD / 审核 / 查询端点 | ParserArtifact / RuleArtifact / TemplateInferenceJob 管理 | 新 artifact API |
| 4 个 SKILL.md（不含 fund_parser_manual） | 移除 code_entry 和 db_insert_fund_event 后的逻辑描述 | 通用技能文件 |

**不迁移清单：**

| 源 | 原因 |
|----|------|
| `skill_ops.py` `fund_skill_run` | 该函数本身必须删除，不迁移。不得将其调度结构迁移为新的通用 Agent 工具 |
| `skill_ops.py` `_find_fund_skill_dir` | 旧 skill 目录定位逻辑，无迁移价值 |
| `api/fund_agent.py` `/api/fund/agent/skills/*/invoke` 等 skill 调用端点 | 直接调用旧 FundAgent，必须删除，不得改名后保留 |
| `fund_parser_manual/SKILL.md` | 根本性问题，不得直接迁移。后续如需应新建技能并明确职责 |

**关键原则：**

- 迁移 = 复制到新位置 + 适配新体系，不是移动文件
- 迁移后旧文件保留不动（Phase 5 统一删除）
- 每迁移一项，写对应的新测试

**关于前端：** Phase 3 不处理前端调用。前端旧调用当前仍是死链路，不得为了兼容而重新注册 `/api/fund/*`。Phase 4 统一替换前端调用路径或禁用无效入口。

**回滚方式：** 删除迁移目标文件，revert `main.py` 路由变更。

**验收标准：**

- 所有迁移内容在新位置有对应测试且通过
- 旧文件未删除、未修改运行时行为
- 旧文件保留但不作为生产路径，不得重新注册 `/api/fund/*`
- `git diff --name-only` 中不出现 `frontend/` 目录下的文件

---

### Phase 4：替换前端（风险：中）

**目标：** 将前端对旧 API 的调用替换为新 API。

| 文件 | 修改内容 |
|------|----------|
| `frontend/src/api/fund.js` | 9 个调用全部替换为新端点 |
| `frontend/src/views/ManualFlow.vue` | 移除 `invokeFundSkill`。如新通用 Agent 任务入口已完成，则通过通用 Agent 任务/会话入口发起解析器生成；如未完成，则隐藏或禁用该入口，并给出明确状态说明 |
| `frontend/src/views/ReportTemplate.vue` | 替换为新 API |
| `frontend/src/views/AgentReview.vue` | 替换 API 调用，标题改为"产物审核" |
| `tests/e2e/test_full_flow.py` | 更新端点路径 |
| `tests/e2e/conftest.py` | 更新引用 |

**回滚方式：** git revert 前端变更。

**验收标准：**

- 前端不再 import `fund.js` 旧函数（除非已改为调用新端点）
- 浏览器实际操作验证每个被替换的流程
- E2E 测试通过

---

### Phase 5：删除旧体系（风险：低，前置条件已满足）

**目标：** 删除所有被标记为 A 类的文件和已完成迁移的 B 类源文件。

**删除清单：**

| 文件/目录 | 原因 |
|-----------|------|
| `backend/agents/fund/` 整个目录 | 已迁移（Phase 3），空壳和旧调度器 |
| `backend/api/fund_agent.py` | 已迁移有价值的产物 CRUD/审核/查询端点；skill 调用端点本就不迁移 |
| `backend/agents/tools/skill_ops.py` 中旧函数 | `fund_skill_run`（不迁移）、`_find_fund_skill_dir`（不迁移）、`_record_fund_skill_experience`（已迁移） |
| `agents/system/skills/fund_parser_manual/SKILL.md` | 根本性问题，不得直接迁移。后续如需手工流水相关技能，应新建 `manual_parser` 或 `manual_entry_assistant`，明确其职责为生成手工模板解析规则或辅助用户录入，不得直接写入 `fund_events`，不得绕过预览、确认和确定性服务层 |
| `tests/fund/conftest.py` | 引用不存在的文件 |
| `tests/fund/test_phase6_api.py` | 测试旧端点 |
| `tests/fund/test_artifact_runtime.py` | 引用不存在的文件 |
| `tests/fund/test_sandbox.py` | 引用不存在的文件 |
| `tests/fund/test_phase7_privacy.py` | 实例化旧 FundAgent |
| Phase 0 添加的所有废弃注释 | 清理标记 |

**验收标准：**

- `grep -r "FundAgent\|fund_skill_run\|harness_strict" backend/` 无结果
- `grep -r "fund_agent" backend/main.py` 无结果
- 全部测试通过
- 前端功能正常

---

## 六、最容易误删的对象

以下对象有旧体系外观但**必须保留**：

| 对象 | 误删风险 | 保留原因 |
|------|----------|----------|
| `backend/fund/primitives/`（7 个模块） | 高 — 名称含 `fund/` | §C5 白名单，确定性基元函数，与 Agent 无关 |
| `backend/fund/artifacts/parsers/`（15 个 .py） | 高 — 名称含 `fund/` | §C5 白名单，ParserArtifact 确定性产物，不是 Agent 代码 |
| `backend/fund/__init__.py` | 中 — 同在 `fund/` 下 | 包入口，primitives 和 artifacts 的 import 依赖 |
| `backend/core/artifact_runtime.py` | 高 — docstring 含 "deprecated" | 产物执行的关键契约文件，需扩展契约定义而非删除 |
| `tests/fund/primitives/`（7 个文件） | 中 — 同在 `tests/fund/` 下 | 基元函数测试，不含 FundAgent 概念 |
| `frontend/src/views/agent/*.vue`（6 个文件） | 低 — 但需注意 | 通用 Agent 前端，保留 |

判断口诀：`backend/fund/` 保留，`backend/agents/fund/` 迁移后删除。前者是产物基础设施，后者是 Agent 调度器。

---

## 七、4 项核心区别（防止执行时混淆）

| # | 旧体系概念 | 新体系对应 | 混淆后果 |
|---|-----------|-----------|----------|
| 1 | FundAgent 类（`agents/fund/harness.py`） | 通用 Agent + 通用工具 | 误以为需要保留 FundAgent 类 |
| 2 | `harness_strict` 调度模式 | 通用 Agent 的标准工具调用流程 | 误以为 harness 有独特价值需保留 |
| 3 | `fund_skill_run` 桥接工具 | 通用 Agent 的标准工具注册 | 误以为桥接工具有独立存在的必要 |
| 4 | 5 个固定 fund skill | 通用 Agent 的动态技能集 | 误以为需要维持固定 skill 清单 |

---

**审计结论：** 仓库中 FundAgent 旧体系的代码在生产环境从未生效（main.py 未注册路由），文档层面的冲突是主要问题。清理应按 Phase 0-5 顺序执行，每个 Phase 有明确的回滚点和验收标准。`fund_skill_run` 和 skill 调用端点必须删除不得迁移；产物 CRUD/审核/查询端点可迁移到新 artifact API。最关键的交付物是 Phase 2（建立新契约）和 Phase 3（迁移可复用逻辑），Phase 5（删除）只是收尾。
