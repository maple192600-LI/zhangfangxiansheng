# 04 · 编码与命名规范

本文件定义当前项目的工程写法。冻结契约仍以 `00_project_constitution.md` 为准；普通开发不得直接修改冻结契约。

## 命名原则

使用稳定业务概念，不引入版本化分裂命名。

允许使用：

- Agent
- Skill
- Memory
- Parser
- Rule
- Artifact

不要新增带版本后缀的 Agent/Skill/Memory 命名，不要新增 `new_*`、`legacy_*` 这类为同一能力临时创建的平行替代名。

历史遗留命名必须通过迁移任务逐步收敛，不得在新代码、新文档、新 UI 文案中继续扩散。

## 后端规范

```text
api/      -> 参数校验、调用 service、返回响应
services/ -> 业务流程和事务编排
db/       -> ORM 模型和数据结构
agents/   -> Agent、Skill、Memory、工具、规则创建流程
fund/     -> Parser/Rule 确定性执行所需的基元和 artifact
```

要求：

- 路由层不写业务逻辑。
- Service 层不直接操作 FastAPI request/response。
- 确定性执行阶段不得调用 LLM。
- 所有 API 响应走 `core.response.success/error`。
- 用户可见错误信息使用中文。
- Parser/Rule artifact 只能调用白名单基元。

## 前端规范

```text
views/       -> 页面
components/  -> 可复用组件
api/         -> 接口封装
stores/      -> 全局状态
router/      -> 路由
styles/      -> 全局样式
```

要求：

- 页面组件不直接写底层请求细节，统一从 `src/api/` 调用。
- 工作流页面必须围绕“上传、匹配/创建规则、预览、确认、结果”组织。
- 不向用户暴露 JSON、正则、SQL 或字段映射编辑器。
- Agent、Skill、Memory、Parser、Rule 在 UI 中使用同一套中文表达。

## 单一实现规则

同一能力只能有一个当前实现入口。

如果发现旧实现仍被调用：

1. 标记旧入口。
2. 找出所有调用方。
3. 迁移到当前入口。
4. 删除或归档旧入口。
5. 增加回归测试。

不得通过新增平行文件绕过缺陷。

## 提交与验证

每个任务结束必须提供：

- 文件清单。
- 运行的测试或构建命令。
- 守卫脚本结果。
- 用户可见变更的浏览器验证结果。
- 未完成项或冻结契约阻塞项。

## Git 提交规范

本项目使用 GitHub Flow 和 Conventional Commits。

分支规则：

- `main` 只接收通过 PR 合并的代码。
- 每个任务从最新 `main` 创建短分支。
- 分支名使用小写短横线，格式建议为 `type/topic`。
- 常用类型：`feat`、`fix`、`docs`、`test`、`refactor`、`chore`、`ci`。
- 一个分支只做一个明确目标，避免把文档治理、功能开发、格式化和重构混在一起。

提交规则：

```text
<type>(<scope>): <summary>
```

示例：

```text
docs(governance): add GitHub Flow rules
fix(bank-import): route preview through parser artifacts
test(reports): cover rule-based report generation
chore(guards): freeze API inventory baseline
```

提交要求：

- 摘要用英文类型和简短说明。
- 正文说明为什么改，不只说明改了什么。
- 不提交 `WIP`、`update`、`fix stuff` 这类无信息提交。
- 不把无关文件塞进同一个提交。
- 已推送到共享分支后，不随意 rebase 或强推；确需强推只能用 `--force-with-lease`。

PR 要求：

- PR 标题使用 Conventional Commit 风格。
- PR 描述必须包含变更摘要、验证命令、guard 结果、浏览器验证结果、风险和未完成项。
- 检查失败不得合并。
- review 意见必须处理或明确解释。
- 小而聚焦的 PR 优先使用 squash merge。
