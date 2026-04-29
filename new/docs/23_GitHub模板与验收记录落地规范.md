# 23_GitHub模板与验收记录落地规范

## READ WHEN

创建 GitHub Issue 模板、PR 模板、浏览器验收记录模板、开发任务交接模板前读取。

## CANONICAL SOURCES

模板正文不得多处维护。以下文件是唯一来源：

| 模板 | 唯一来源 |
|---|---|
| 任务单 / Issue | `docs/12_任务单与PR模板规范.md` 的 `TASK CARD` |
| PR | `docs/12_任务单与PR模板规范.md` 的 `PR TEMPLATE` |
| 浏览器验收记录 | `docs/15_浏览器验收记录规范.md` 的 `RECORD TEMPLATE` |
| 项目护栏输出 | `docs/14_项目护栏检查脚本规格.md` 的 `OUTPUT FORMAT` |

## TARGET FILES

目标开发仓库允许创建：

```text
.github/ISSUE_TEMPLATE/task.md
.github/pull_request_template.md
dev/reports/browser_acceptance/.gitkeep
dev/reports/browser_acceptance/README.md
```

## GENERATION RULE

生成模板文件时，只允许从 CANONICAL SOURCES 提取对应模板。

不得在模板文件中另写一套字段、另改标题、另造验收口径。

如果需要改模板字段，先修改唯一来源，再重新生成目标文件。

## ISSUE TEMPLATE RULE

`.github/ISSUE_TEMPLATE/task.md` 只承载任务单字段。

字段以 `docs/12_任务单与PR模板规范.md` 的 `TASK CARD` 为准。

## PR TEMPLATE RULE

`.github/pull_request_template.md` 只承载 PR 字段。

字段以 `docs/12_任务单与PR模板规范.md` 的 `PR TEMPLATE` 为准。

## BROWSER ACCEPTANCE RULE

`dev/reports/browser_acceptance/README.md` 只说明记录存放、命名和结论要求。

每次验收记录使用：

```text
dev/reports/browser_acceptance/YYYYMMDD_HHMM_<task-name>.md
```

验收记录字段必须来自 `docs/15_浏览器验收记录规范.md`，不得另建格式。

## MUST

- 模板文件和唯一来源字段保持一致。
- 修改模板字段后同步检查 `.github/` 和 `dev/reports/browser_acceptance/README.md`。
- PR 中必须说明模板是否变更。
- 项目护栏脚本必须检查模板一致性。

## NEVER

- 不要把同一模板正文复制到多个规范文件。
- 不要让 Issue 模板、PR 模板、验收记录模板字段互相冲突。
- 不要为了某个任务临时删减模板字段。
- 不要把浏览器验收记录写进 PR 正文后不落文件。

## DONE

```text
Issue 模板路径：
PR 模板路径：
浏览器验收记录目录：
唯一来源检查：
字段一致性检查：
护栏检查项：
```

