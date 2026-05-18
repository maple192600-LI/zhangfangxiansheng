# 银行导入通用识别与主数据归属匹配

## 总原则

1. `FundEvent` 是最终事实表，不是导入匹配的唯一信息源
2. 银行导入必须读取主数据管理信息，把流水准确归属到法人单位和银行账户
3. Parser 只负责银行格式解析，不负责最终账户归属决策
4. 账户归属匹配是独立服务能力，与 Parser Runtime 解耦
5. 没有足够事实线索时，系统不能假装"智能自动识别"，不能默认第一个账户，不能猜

## 术语

| 术语 | 定义 | 实现状态 |
|------|------|----------|
| Parser Runtime | 底层确定性执行器，执行 active ParserArtifact 的 Python code | 已实现（`run_parser`） |
| Bank Format Parser | 银行格式级解析器。一个 parser 服务同银行同格式的所有账户 | 未实现（无真实 bank parser） |
| Bank Format Identification | 识别银行和导出格式（如"中国银行标准对账单 v1"） | 未实现 |
| Identity Hints Extraction | 从文件中提取账号、户名、单位名、银行名、开户行等线索 | 未实现 |
| Master Data Matching | 读取主数据进行匹配，确定流水归属 | 未实现 |
| Account Attribution | 确定流水归属哪个法人单位和银行账户 | 未实现 |
| Upload Preview | 异常编辑、重校验、最终提交的位置 | 已实现（`import_preview_service`） |

## 业务链路

```
银行流水上传
→ Bank Format Identification（识别银行和格式）
→ bank/format 级 ParserArtifact 匹配（选哪个格式 parser）
→ Parser Runtime 执行（解析流水字段）
→ Identity Hints Extraction（提取文件身份线索）
→ Master Data Matching（读取主数据进行匹配）
→ Account Attribution（确定账户/单位归属）
→ Upload Preview（异常处理、编辑、校验）
→ commit → FundEvent(state=正常)
```

当前已实现的环节：上传 → Parser Runtime → Upload Preview → commit
尚未实现的环节：Bank Format Identification → 身份线索提取 → 主数据匹配 → 账户归属

## 主数据匹配字段

账户归属匹配使用以下主数据字段：

| 表 | 字段 | 匹配用途 |
|----|------|----------|
| banks | bank_name, short_name | 银行识别 |
| accounts | bank_id | 银行约束 |
| accounts | bank_name, branch_name | 开户行匹配 |
| accounts | account_number | 账号精确匹配 |
| accounts | account_last_four | 后四位匹配 |
| accounts | account_alias | 别名匹配 |
| accounts | input_method | 区分网银/手工账户 |
| accounts | has_online_banking | 筛选网银账户 |
| entities | name, short_name, entity_code | 法人匹配 |
| account_aliases | alias_text | 别名库匹配 |

## 四类文件场景

| 场景 | 文件中可提取的信息 | 处理策略 |
|------|-------------------|----------|
| A | 账号和单位/户名都有 | 账号精确匹配，单位/户名做一致性校验；不一致进入异常 |
| B | 只有账号或后四位 | 账号/后四位 + 银行约束匹配账户；唯一候选可自动，多候选进入异常 |
| C | 只有单位/户名 | 先匹配实体，再找其启用的网银账户；唯一候选可自动，多候选进入异常 |
| D | 账号和单位/户名都没有 | 只能依赖用户上传时选择账户、历史绑定或文件名强线索；否则必须 unmatched |

**场景 D 的硬约束**：没有事实线索时，系统不能假装智能识别。不能默认第一个账户，不能猜。必须标记为 unmatched，由用户在上传结果预览页手动指定。

## ParserArtifact 粒度

- `kind="bank"` 的 ParserArtifact 目标是**银行/格式级**，不是账户级
- 一个中国银行标准格式 parser 服务所有中国银行同格式流水，不管哪个法人单位、哪个账户
- ParserArtifact **不得**硬编码 `account_code` / `entity_code` / 单位名称 / 账户名称
- `ParserArtifact.account_code` 对银行导入**不应作为主匹配键**，只能作为旧兼容字段或非银行场景字段
- 银行导入匹配 parser 应按 bank/format 级匹配，不按 account_code 匹配

### 当前架构状态

`bank_import_service` 已通过 09D 接入 bank/format 级 parser 匹配（`_match_bank_format_parser_artifact`），按 bank_id + format_key 四级优先匹配，不再按 account_code 匹配银行 parser。`import_preview_service` 已通过 09D2 使用 bank/format 匹配路径（`build_bank_import_context`），bank 批次 commit 不再重新 parser，不覆盖用户编辑结果。银行歧义在账户匹配中不再静默降级为"无银行过滤"。详见下方"已实现服务"章节。

## 已有的匹配能力

以下匹配能力已存在于手工流水路径（`manual_flow_service`）和基元库（`master_match`），可作为银行导入匹配的参考或复用基础：

| 能力 | 位置 | 匹配策略 |
|------|------|----------|
| 实体匹配 | `manual_flow_service._match_entity()` | entity_code → short_name → alias → name 包含 |
| 账户匹配 | `manual_flow_service._match_account()` | account_code → alias → account_alias |
| 基元实体匹配 | `fund.primitives.master_match.match_entity()` | alias_library → name/short_name 相似度 |
| 基元账户匹配 | `fund.primitives.master_match.match_account()` | alias_library → account_aliases → 后四位 → 名称相似度 |
| 编辑时实体解析 | `import_preview_service._resolve_entity_for_input()` | 简称/别名 → canonical entity_code |
| 编辑时账户解析 | `import_preview_service._resolve_account_for_input()` | 简称/别名 → canonical account_code |

银行导入需要的匹配能力范围更广：需要从文件中提取账号、户名、银行名等线索，然后按多维度综合匹配。这超出了现有能力的范围。

## 禁止事项

- 不允许 parser 硬编码 `DEFAULT_ACCOUNT_CODE`（非空）
- 不允许 parser 固定 `entity_code="E001"` 或 `account_code="A001"`
- 不允许 parser 名称或 match rule 绑定到具体账户作为唯一目标
- 不允许声称"银行导入智能识别已完成"或"所有银行流水已可通用解析"
- 不允许在无事实线索时自动选择账户

## 后续阶段

| 步骤 | 目标 |
|------|------|
| 09C | 银行文件识别 + 身份线索提取服务 |
| 09D | ParserArtifact bank/format 级匹配策略（替代 account_code 匹配） |
| 09E | 主数据账户/单位归属匹配服务 |
| 09F | parser 硬编码 guard |
| 09H | 多银行/多账户/多线索场景端到端验收 |

## 已实现服务（已接入导入流程）

| 服务 | 文件 | 职责 |
|------|------|------|
| 身份线索提取 | `backend/services/bank_statement_identity_service.py` | 从 xlsx 文件和文件名提取银行名（原始文本）、账号、户名、开户行等线索。不硬编码银行名，不归一化 |
| 账户归属匹配 | `backend/services/bank_account_match_service.py` | 根据身份线索匹配主数据（banks + entities + accounts + account_aliases），输出 matched / ambiguous / unmatched |
| SourceFile 记录 | `backend/services/source_file_service.py` | 每次上传创建 SourceFile 记录，跟踪文件状态（uploaded/parsed/ready/needs_rule/needs_account/failed） |
| 账户归属审计 | `backend/services/account_resolution_audit_service.py` | 记录每次账户归属判断的 attempt 和 evidence |

### 已完成（A1）

- SourceFile 文件处理记录（上传时创建，状态随 parser 结果更新）
- account_resolution_attempts / account_resolution_evidence（账户归属判断留痕）
- 单文件上传已接入 SourceFile 创建、状态更新、归属判断记录
- 结果预览阶段回写 SourceFile 状态（parser 成功 → parsed，失败 → failed + error_code）

### 尚未完成

- 批量上传 UI 未完成
- 规则中心已完成（12B 返工：ParserTrainingJob 持久化、job_code 驱动、用户选 Agent）
- 结果预览证据抽屉未完成（evidence 数据已存但前端未展示）
- 用户确认后沉淀 account_resolution_rules 未完成

| 服务 | 文件 | 职责 |
|------|------|------|
| 身份线索提取 | `backend/services/bank_statement_identity_service.py` | 从 xlsx 文件和文件名提取银行名（原始文本）、账号、户名、开户行等线索。不硬编码银行名，不归一化 |
| 账户归属匹配 | `backend/services/bank_account_match_service.py` | 根据身份线索匹配主数据（banks + entities + accounts + account_aliases），输出 matched / ambiguous / unmatched |

### 设计要点

- **银行文本候选收集**：身份线索提取服务输出 `bank_text_candidates` 列表（最多 80 条去重原始文本），来源包括 filename、单元格文本、headers、bank_name、branch_name。不做任何主数据判断
- **DB 驱动银行识别**：匹配服务通过 `_resolve_bank()` 从候选列表中识别银行。支持精确匹配（bank_name / short_name / bank_code）和双向包含匹配（候选包含银行字段或银行字段包含候选），仅唯一 Bank 才返回
- **AccountAlias**：匹配服务在实体名匹配路径中优先尝试 `account_aliases.alias_text` 精确匹配，可命中别名
- **完整账号不匹配**：当 `identity_hints.account_number` 存在但不匹配任何账户时，直接返回 `ACCOUNT_HINT_NOT_FOUND`，不 fallback 到实体名匹配
- **银行强过滤**：当银行 hint 可解析为唯一 Bank 但过滤后候选为空，返回 `BANK_ACCOUNT_CONFLICT`，不恢复原候选

这两个服务已通过测试验证，并已接入 `bank_import_service` 的上传流程（09D）和 `import_preview_service` 的预览/提交流程（09D2）。前端展示将在 09G 中完成。

---
**校准来源：** `ai_coordination/parser-runtime/09_bank_parser_generalization_revised_plan_v2.md`、`backend/services/bank_import_service.py`、`backend/services/import_preview_service.py`、`backend/services/manual_flow_service.py`、`backend/fund/primitives/master_match.py`、`backend/db/tables.py`
**最后校准：** 2026-05-19（09F parser 硬编码 guard 已实现，规则中心 MVP 已完成）
