# Agent 产物生命周期映射

> 描述 ParserArtifact 和 RuleArtifact 从创建到退役的完整生命周期。

---

## 通用生命周期

```
Agent 生成代码 → draft（草稿）→ 用户审批 → active（激活）→ 退役 → retired（退役）
```

三个状态存储在各自的 `status` 字段中，由数据库 CHECK 约束保障。

---

## ParserArtifact 生命周期

### 创建阶段

1. 用户在 AI 智能体中上传银行流水样本文件
2. Agent 分析样本，生成 Python 解析代码
3. 写入 `parser_artifacts` 表，`status='draft'`，`created_by='agent'`

**相关代码：**
- Agent 工具：`backend/agents/tools/skill_ops.py` → `fund_parser_bank` skill
- 数据存储：`backend/api/artifacts.py` → `POST /api/artifacts/parsers/drafts`
- 数据表：`parser_artifacts`（kind='bank' 或 'manual'）

### 审批阶段

1. 用户在「Agent 审核」页面（`AgentReview.vue`）查看生成的解析器
2. 可以看到：解析器名称、代码内容、置信度、样本校验日志
3. 审批通过：`status` 从 `draft` → `active`，记录 `approved_by` 和 `approved_at`

**相关代码：**
- 审批接口：`backend/api/artifacts.py` → `POST /api/artifacts/parsers/:id/approve`
- 审批页面：`frontend/src/views/AgentReview.vue`
- 数据表更新：`parser_artifacts.status`, `approved_by`, `approved_at`

### 使用阶段（执行）

1. 银行导入时，`bank_import_service._match_active_parser_artifact` 自动匹配 active 解析器
2. 匹配优先级：指定 account_code 的 > 通用的；版本号高的优先
3. 匹配后调用 `artifact_runtime.run_parser(db, artifact_id, file_path, ctx)`
4. `run_parser` 执行解析代码，输出 CANONICAL_12 行

**当前状态：** ⚠️ `run_parser` 是 `raise NotImplementedError` 的占位函数。Phase E1 将实现真正的执行器。

**执行约束：**
- 只执行 `status='active'` 的解析器
- 代码必须通过 AST 白名单校验（`artifact_ast_guard.validate_artifact_code`）
- 执行超时限制 60 秒
- 执行过程中禁止调用 LLM（§C8）

### 退役阶段

1. 当同一 kind + account_code 有更新的 active 解析器时，旧的可退役
2. `status` 从 `active` → `retired`
3. 退役的解析器不再被匹配

**相关代码：**
- 退役接口：`backend/api/artifacts.py` → `POST /api/artifacts/parsers/:id/retire`

---

## RuleArtifact 生命周期

### 创建阶段

1. 用户在「报表模板管理」上传 Excel 模板
2. 系统自动识别占位符（Stage A）：扫描模板中的 `{{xxx}}` 格式文本
3. Agent 分析占位符与数据字段的对应关系（Stage B）
4. 生成 `placeholder_bindings`（JSON），写入 `rule_artifacts` 表，`status='draft'`

**相关代码：**
- Stage A：`report_template_service.parse_excel_headers` + `parse_excel_layout`
- Stage B：`template_inference_job` 表记录推断过程
- 数据存储：`backend/api/artifacts.py` → `POST /api/artifacts/rules/drafts`

### 审批阶段

同 ParserArtifact，在 AgentReview 页面审批。

### 使用阶段（执行）

1. 报表生成时，`report_service.generate_report` 调用 `artifact_runtime.run_rule`
2. `run_rule` 读取模板文件，执行规则代码，用数据填充占位符
3. 返回填充后的 openpyxl Workbook

**当前状态：** ⚠️ `run_rule` 是 `raise NotImplementedError` 的占位函数。Phase H1 将实现。

### 退役阶段

同 ParserArtifact。

---

## 产物与流水的关联

```
ParserArtifact (parser_artifacts)
  └── FundEvent.parser_artifact_id ← 记录每条流水是由哪个解析器产出的

RuleArtifact (rule_artifacts)
  └── TemplateInferenceJob.rule_artifact_id ← 记录推断任务对应的规则
  └── ReportTemplate ← 规则绑定的报表模板
```

---

## 确定性执行基础设施

`backend/fund/` 目录（含 `primitives/` 和 `artifacts/`）是产物确定性执行的底层支持：
- `primitives/` — 白名单模块（openpyxl、datetime 等），解析器代码只能导入这些
- `artifacts/parsers/` — 解析器的运行时支持
- AST guard — 校验产物代码不导入非法模块

**重要区分：** `backend/fund/` ≠ 已删除的 `backend/agents/fund/`。前者是确定性执行基础设施，必须保留；后者是旧 FundAgent 的调度器，已删除。

---

## 禁止事项

- 禁止恢复旧 `backend/agents/fund/` 目录
- 禁止新增 `fund_skill_run` 工具
- 禁止新增独立的领域 Agent（如 FundAgent、ParserAgent）
- 禁止在 `run_parser` / `run_rule` 执行过程中调用 LLM
