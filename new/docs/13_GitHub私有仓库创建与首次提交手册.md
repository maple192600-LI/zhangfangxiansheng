# 13_GitHub私有仓库创建与首次提交手册

## READ WHEN

创建 GitHub 私有仓库、初始化目标开发目录、复制已确认文档、首次提交、首次 PR 前必须读取。

## PURPOSE

让非编程用户也能按固定步骤启动项目开发。

AI Coding 工具负责执行技术步骤；用户只负责账号授权、确认仓库名称、查看页面验收结果和确认 PR。

## USER CONFIRMATION POINTS

以下步骤需要用户确认：

```text
GitHub 账号登录
仓库名称
仓库是否 Private
授权 Claude Code / Codex / GitHub App
目标开发目录位置
是否允许 AI 创建仓库或推送代码
PR 是否可以合并
```

AI 不得绕过用户授权。

## AI CAN DO

授权完成后，AI 可以代办：

```text
创建本地目标目录
初始化 Git 仓库
连接 GitHub 私有仓库
创建目录结构
复制已确认文档
创建 .gitignore
提交 initial docs
创建任务分支
创建 PR
删除失败任务分支
生成验收说明
```

## AI MUST NOT DO

AI 不得：

```text
创建 Public 仓库
把运行数据推送到 GitHub
把依赖目录推送到 GitHub
把当前工作区整包复制到目标仓库
跳过 .gitignore
跳过项目护栏检查
直接在 main 开发产品功能
未得到确认就合并 PR
```

## TARGET REPOSITORY FIRST CONTENT

首次提交只允许包含：

```text
AGENTS.md
README.md
.gitignore
app/.gitkeep
skills/skill-creator/SKILL.md
skills/index.json
docs/
dev/fixtures/.gitkeep
dev/scripts/.gitkeep
dev/reports/.gitkeep
workspaces/default/skills/index.json
data/.gitkeep
```

`data/` 目录可以保留空目录占位，但目录内运行产物不得提交。

## README MINIMUM

目标仓库 `README.md` 至少说明：

```text
产品名称
项目目标
本地开发为主
GitHub Private 仓库仅用于版本记录和同步
用户可见功能必须浏览器验收
开发前先读 AGENTS.md
```

## FIRST .GITIGNORE

`.gitignore` 至少包含：

```text
.venv/
node_modules/
data/**
!data/.gitkeep
*.log
*.tmp
*.cache
*.sqlite
*.db
test-results/
playwright-report/
dist/
build/
coverage/
```

## FIRST PR

首次 PR 只做初始化，不做产品功能。

PR 必须包含：

```markdown
## 目标
初始化目标开发仓库。

## 修改范围
- 文档目录
- 开发辅助目录
- 应用源码占位目录
- .gitignore
- README

## 不做范围
- 不实现产品功能
- 不安装依赖
- 不创建运行数据库
- 不创建业务 Skill
- 只预置产品内置全局 `skill-creator`
- `skill-creator` 来源为 Anthropic skills 仓库或当前 AI Coding 工具内置来源
- 不创建多余 Skill 目录层级

## 项目护栏检查
首次 PR 可说明护栏脚本将在下一任务实现。

## 用户检查路径
1. 打开 GitHub 私有仓库。
2. 确认仓库是 Private。
3. 确认目录结构正确。
4. 确认没有运行数据、依赖目录、临时文件。
```

## SECOND TASK

首次 PR 合并后，第二个任务必须实现：

```text
dev/scripts/check_project_guard
```

实现规格见：

```text
docs/14_项目护栏检查脚本规格.md
```

护栏脚本完成前，不得开始产品功能开发。

## DONE

完成初始化必须满足：

- 仓库是 Private。
- 本地目录由用户确认。
- 首次提交不包含运行产物。
- `.gitignore` 存在。
- `skills/skill-creator/SKILL.md` 已存在，且保持 `SKILL.md` 兼容结构。
- `AGENTS.md` 指向正式文档位置。
- 第一个 PR 只包含初始化内容。
- 用户知道如何在 GitHub 页面查看 PR。

