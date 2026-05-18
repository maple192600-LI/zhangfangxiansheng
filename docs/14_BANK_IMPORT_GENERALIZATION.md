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

### 当前架构问题

`bank_import_service._match_active_parser_artifact()` 当前按 `account_code` 优先匹配 bank parser。这是架构级设计问题，将在 09D 中通过引入 bank/format 级匹配策略解决。

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
| 09G | 前端展示银行识别和账户归属匹配结果 |
| 09H | 多银行/多账户/多线索场景端到端验收 |

## 已实现服务（尚未接入导入流程）

| 服务 | 文件 | 职责 |
|------|------|------|
| 身份线索提取 | `backend/services/bank_statement_identity_service.py` | 从 xlsx 文件和文件名提取银行名、账号、户名、开户行等线索 |
| 账户归属匹配 | `backend/services/bank_account_match_service.py` | 根据身份线索匹配主数据，输出 matched / ambiguous / unmatched |

这两个服务已通过测试验证，但尚未接入 `bank_import_service` 的导入流程，也未接入前端和 ParserArtifact bank/format 匹配。接入工作将在 09D 和 09G 中完成。

---
**校准来源：** `ai_coordination/parser-runtime/09_bank_parser_generalization_revised_plan_v2.md`、`backend/services/bank_import_service.py`、`backend/services/import_preview_service.py`、`backend/services/manual_flow_service.py`、`backend/fund/primitives/master_match.py`、`backend/db/tables.py`
**最后校准：** 2026-05-18
