# 提交治理清理 PR 计划

## 目标

把“旧阶段编号表达清理、Agent 定位说明、解析器/规则分工、后续开发计划文档、GitHub 误导项关闭”整理成一个可审查、可回滚的独立提交和 PR。

## 背景与当前事实

当前工作基于 `feature/bank-rule-sample-upload-flow`，该分支已有 PR #65。治理清理不应直接混进 PR #65 的功能描述，因此本次使用新分支 `codex/governance-cleanup-readiness`，并把 PR 目标分支设为 `feature/bank-rule-sample-upload-flow`。

当前已完成的事实：

1. 本地 active docs、测试、样本、脚本、协作任务目录中的旧阶段编号表达已清理。
2. 新增 `docs/15_AGENT_IMPORT_DEVELOPMENT_PLAN.md` 和 `docs/15_AGENT_IMPORT_DEVELOPMENT_PLAN.html`。
3. GitHub Issue #10 已关闭并标记为不再执行。
4. GitHub PR #1 已关闭并标记为过期。
5. GitHub Issue #3 已改写为历史测试债，不再包含旧阶段编号表达。

## 必读文件

1. `AGENTS.md`
2. `docs/README.md`
3. `docs/11_AI_CODING_WORKFLOW.md`
4. `docs/15_AGENT_IMPORT_DEVELOPMENT_PLAN.md`
5. `docs/15_AGENT_IMPORT_DEVELOPMENT_PLAN.html`

## 影响范围

1. 文档入口和项目治理口径。
2. 测试、脚本、样本文件名和文字说明。
3. GitHub 开放 issue / PR 的当前开发依据。
4. 不改变业务运行逻辑，不新增银行导入功能，不修改外部模型供应商地址。

## 允许修改范围

1. 根目录说明文件：`README.md`、`CLAUDE.md`。
2. `docs/` 下 active docs 和新增计划文档。
3. 测试、脚本、模板、样本的中性命名改造。
4. `references/original_input/` 中历史原稿的误导性阶段编号清理。
5. `.github/workflows/backend-tests.yml` 的测试文件名更新。
6. `frontend/README.md` 的模板说明替换。
7. `agents/ag_kbdpch/workspace/` 中被跟踪的样例解析器文件名清理。

## 禁止修改范围

1. 不提交 `agents/ag_kbdpch/.curator_state`。
2. 不提交 `frontend/dist/`、`.claude/`、`runtime/`、`node_modules/`、`__pycache__/`。
3. 不改外部 API 地址，例如供应商真实的版本化接口地址。
4. 不改模型商品名中的官方版本号。
5. 不改 Alembic 历史迁移文件名和数据库物理表名。
6. 不把这次治理 PR 写成新功能 PR。

## 实施步骤

1. 创建新分支 `codex/governance-cleanup-readiness`。
2. 写入本计划文件。
3. 检查 `git status --short`，确认 `agents/ag_kbdpch/.curator_state` 不进入暂存区。
4. 运行搜索：排除外部供应商地址、模型名、锁文件、SVG、构建产物后，确认无旧阶段编号表达。
5. 运行文件名搜索：确认仅剩 Alembic 历史迁移文件名。
6. 运行测试：
   - `pytest tests/db tests/scripts -q`
   - `pytest tests/test_artifact_api_contract.py tests/test_template_analysis_service.py tests/backend/api/test_workflow_api.py tests/backend/services/test_workflow_service.py tests/backend/services/test_bank_account_match_service.py -q`
   - `python tools/guards/check_parser_hardcoding.py`
   - `npm run build`（工作目录 `frontend/`）
7. 暂存允许范围内的文件，排除运行态和本地状态文件。
8. 提交：`chore: clean governance wording and add agent plan`
9. 推送分支。
10. 创建目标为 `feature/bank-rule-sample-upload-flow` 的 GitHub PR。

## 数据/接口/页面影响

1. 不改变 API 契约。
2. 不改变数据库迁移链。
3. 不改变用户页面业务行为。
4. `frontend/src/composables/useAdvancedTablePreferences.js` 的本地存储 key 后缀改为中性名称，可能导致用户本机高级表格偏好重新初始化一次。

## 文档影响

1. `docs/README.md` 增加后续计划入口。
2. 新增 `docs/15_AGENT_IMPORT_DEVELOPMENT_PLAN.md` 作为长期项目口径。
3. 新增同规格 HTML 阅读版。
4. 历史原稿只做去误导化，不把它们恢复成 active docs。

## 测试方式

见“实施步骤”第 6 步。测试通过后才能提交。

## 验收标准

1. PR 中没有 `agents/ag_kbdpch/.curator_state`。
2. 排除允许的外部技术真名后，全仓搜索不到旧阶段编号表达。
3. 文件名搜索只剩 Alembic 历史迁移文件。
4. 后端相关测试通过。
5. parser hardcoding guard 通过。
6. 前端构建通过。
7. GitHub open issue / open PR 搜索旧阶段编号表达结果为空。

## 回滚方案

1. 回滚本次提交即可恢复所有本地文本、测试名、脚本名、样本文档名。
2. GitHub Issue #10 和 PR #1 已关闭但未删除；如需恢复，可重新打开，不过当前不建议。
3. 如果本地表格偏好 key 变更引起用户不适，可单独回退 `frontend/src/composables/useAdvancedTablePreferences.js`。

## 结果报告路径

本次结果直接写在 Codex 最终回复中，并附 PR 地址、提交 SHA、验证命令结果。
