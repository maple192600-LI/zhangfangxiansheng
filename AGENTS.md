# AGENTS.md

AI Coding 工具进入本项目的入口文件。

## MUST READ

先读 `docs/README.md`，它是唯一的文档入口。

技术栈真相源：
- `frontend/package.json` — 前端依赖和版本
- `backend/requirements.txt` — 后端依赖和版本

不要信任任何文档中的技术栈表述，以上述文件为准。

## AUTHORITY

本项目的代码和配置文件是唯一实现权威。文档描述的是意图，代码描述的是事实。

如果文档与代码冲突，以代码为准，然后修正文档。

## CURRENT BLOCKERS

Artifact runtime 状态：

- `backend/core/artifact_runtime.py::run_parser` — 已实现 ParserArtifact deterministic runtime
- `backend/core/artifact_runtime.py::run_rule` — NotImplementedError，Phase H1 待交付

ParserArtifact 可创建、审核、执行。RuleArtifact 可创建和审核，但无法通过 artifact runtime 执行。

银行格式识别和账户归属匹配尚未实现。`run_parser` 只是底层确定性执行器，不等于银行通用识别能力。

手工流水快速录入路径已可直接写入 FundEvent，不应被重建。

## HARD RULES

- 不在 `main` 分支直接开发，使用功能分支。
- 不创建同一能力的平行实现。
- 不创建平行替换文件来绕过缺陷。
- 不新增领域专用 Agent 类（如 FundAgent、ReportAgent、ParserAgent、RuleAgent）来绕过通用 Agent 架构。
- 不调用旧 `fund_skill_run`。
- 不新增 `/api/fund/agent/skills/*/invoke` 路由。
- 不在路由层写业务逻辑，业务逻辑放 `services/`。
- API 统一响应格式：`{ "code": 0, "message": "ok", "data": {} }`。
- 不把 `runtime/`、`.venv/`、`node_modules/`、下载文件、日志、临时输出提交进仓库。
- 不创建 docs archive 目录，不保留 legacy docs。旧文档污染源已物理删除。
- 用户可见的工作必须通过浏览器验证。
- 增强层（模板、主题、配置）缺失时降级到默认行为，不能阻断核心功能。
