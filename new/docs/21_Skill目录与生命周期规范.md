# 21_Skill目录与生命周期规范

## READ WHEN

设计或实现 Skill 加载、创建、导入、安装、测试、启用、停用、绑定 Agent、注册工作流节点时必须读取。

## CORE RULE

账房先生有自己的 Skill 加载与治理机制。

Skill 文件格式兼容 Claude Code / Agent Skills 的 `SKILL.md` 结构，但 Skill 存放位置、启用、权限、绑定和审计由账房先生管理。

目录必须简单、直观、容易记忆。

## REFERENCE BASIS

| 参考项目 | 借鉴点 | 本产品实现方式 |
|---|---|---|
| Claude Code Agent Skills | `SKILL.md`、frontmatter、scripts、references、assets、渐进加载 | 兼容 `SKILL.md`，按 description 触发完整加载 |
| pi-mono | 多来源 Skill、按需加载、包和扩展思路 | 全局 Skill、工作区 Skill、Skill 摘要进入上下文 |
| OpenClaw | workspace Skill、安全扫描、依赖检查、运行记录 | 工作区 Skill、依赖声明、测试记录、启用确认 |
| Hermes Agent | 从反复操作和失败中沉淀技能 | 候选 Skill 草稿、样本试跑、用户确认 |

不采用：

```text
不把任何外部工具的 Skill 目录作为产品主目录
不要求用户理解多层 Skill 目录
不把 Skill 草稿自动启用
```

## STORAGE

只保留两类 Skill 目录：

```text
skills/
  skill-creator/
    SKILL.md
  <skill-name>/
    SKILL.md
  index.json

workspaces/
  <workspace_id>/
    skills/
      <skill-name>/
        SKILL.md
      index.json
```

含义：

- `skills/`：全局 Skill，所有工作区和 Agent 默认可见。
- `workspaces/<workspace_id>/skills/`：工作区 Skill，仅当前工作区可见。
- `skills/skill-creator/`：预置的创建 Skill 的全局 Skill。
- `index.json`：记录启用状态、来源、权限、绑定 Agent、测试记录、版本、hash。

不得增加中间层目录、系统目录、按 Agent 单独拆分的根级 Skill 目录，或把 Skill 放入 `data/`。

## SCOPE

只有两种作用域：

```text
global       全局 Skill，放在 skills/
workspace    工作区 Skill，放在 workspaces/<workspace_id>/skills/
```

如果某个 Skill 只允许部分 Agent 使用，不新增物理目录，用 `index.json` 里的 `allowed_agents` 控制。

## COMPATIBILITY INPUTS

产品必须能导入或引用以下来源的 Skill：

```text
Claude Code 用户 Skill 目录
Claude Code 项目 Skill 目录
Codex / Agent Skills 兼容目录
pi / pi-mono 全局、项目、settings、package、CLI Skill 来源
OpenClaw 共享 Skill 与 workspace Skill
普通本地文件夹
GitHub / Gitee / npm / pip 项目转换结果
```

兼容导入不等于把这些路径变成产品主目录。

导入时用户只需要选择：

```text
安装到全局 skills/
安装到当前工作区 workspaces/<workspace_id>/skills/
```

## DIRECTORY STRUCTURE

每个 Skill 目录只强制要求：

```text
skill-name/
  SKILL.md
```

可选资源：

```text
scripts/
references/
assets/
examples/
nodes/
templates/
```

不得要求合法 Skill 必须带：

```text
manifest.json
README.md
CHANGELOG.md
permissions.json
```

产品自己的登记信息写入 `index.json`，不改写导入 Skill 包内部文件。

## IMPLEMENTATION METHOD

Skill 管理至少拆成：

```text
SkillScanner
SkillIndexStore
SkillLoader
SkillInstaller
SkillTester
SkillPermissionGuard
SkillInvocationPlanner
```

加载流程必须可测试：

```text
1. SkillScanner 扫描 skills/ 和 workspaces/<workspace_id>/skills/
2. 读取 SKILL.md frontmatter
3. 读取 index.json
4. 合并状态、权限、依赖、绑定 Agent
5. 过滤不可用 Skill
6. 只把 name、description、scope、location 注入上下文
7. 命中任务后 SkillLoader 读取完整 SKILL.md
8. 需要脚本时交给工具层执行，不由模型直接运行
9. 执行和测试结果写入记录
```

核心接口：

```python
def scan_skills(workspace_id: str) -> list[SkillSummary]:
    ...

def load_skill(skill_name: str, workspace_id: str | None) -> SkillPackage:
    ...

def install_skill(source: SkillSource, target_scope: str, workspace_id: str | None) -> SkillInstallResult:
    ...

def test_skill(skill_name: str, fixture_id: str) -> SkillTestResult:
    ...

def enable_skill(skill_name: str, confirmed_by: str) -> SkillIndexEntry:
    ...
```

## SKILL.md ABI

`SKILL.md` 必须支持：

```markdown
---
name: skill-name
description: What this skill does and when to use it.
---

Instructions...
```

最低要求：

```text
name
description
```

兼容字段：

```text
license
compatibility
metadata
allowed-tools
disable-model-invocation
user-invocable
```

未知字段不得导致崩溃。能理解则利用，不能理解则保留并在详情页展示。

## INDEX

`skills/index.json` 和 `workspaces/<workspace_id>/skills/index.json` 至少记录：

```json
{
  "skills": [
    {
      "name": "skill-creator",
      "scope": "global",
      "path": "skills/skill-creator/SKILL.md",
      "enabled": true,
      "status": "enabled",
      "source_kind": "bundled",
      "source_ref": "",
      "version": "",
      "hash": "",
      "allowed_agents": [],
      "permissions": [],
      "dependencies": [],
      "workflow_nodes": [],
      "fixtures": [],
      "test_report_ids": [],
      "created_at": "",
      "updated_at": ""
    }
  ]
}
```

`allowed_agents` 为空表示当前作用域内所有 Agent 可用。

## DEPENDENCIES

Skill 可以声明额外依赖，但不得偷偷依赖本机全局环境。

依赖记录写入 `index.json.dependencies`：

```json
{
  "dependencies": [
    {
      "type": "python",
      "name": "pandas",
      "version": "",
      "reason": "该 Skill 复用的第三方解析项目依赖 pandas",
      "install_policy": "requires_user_confirm"
    }
  ]
}
```

允许声明：

```text
python 包
node 包
本地可执行文件路径
用户配置的外部工具路径
```

高风险或重依赖必须用户确认：

```text
安装新 Python 包
安装新 Node 包
调用 LibreOffice
调用外部系统 CLI
运行高权限脚本
```

安装位置：

```text
Python 包安装到项目 .venv
Node 包安装到对应 Skill 或前端允许目录
外部工具只保存用户确认的路径
```

Skill 启用前必须完成：

```text
依赖声明
安装或路径检查
样本测试
错误场景测试
权限确认
测试记录
```

不得因为某个 Skill 需要 pandas、xlsxwriter、LibreOffice，就把它们变成所有用户的默认强依赖。

## LOADING

某个 Agent 启动任务时，只加载两处：

```text
skills/
workspaces/<workspace_id>/skills/
```

加载流程：

```text
1. 扫描两处 Skill 目录
2. 识别 SKILL.md
3. 读取 index.json
4. 解析 frontmatter
5. 过滤 disabled、draft、failed、权限不匹配、Agent 不在 allowed_agents 的 Skill
6. 生成 available_skills 摘要
7. 注入 Agent 上下文
8. Agent 需要时再读取完整 SKILL.md
9. Skill 内引用的相对路径按 Skill 根目录解析
```

上下文注入只能放摘要：

```xml
<available_skills>
  <skill>
    <name>...</name>
    <description>...</description>
    <scope>global | workspace</scope>
    <location>...</location>
  </skill>
</available_skills>
```

完整 `SKILL.md` 只在触发后加载。

## PRECEDENCE AND COLLISION

加载顺序：

```text
skills/
workspaces/<workspace_id>/skills/
explicit_task
```

同名 Skill 不得静默覆盖。

发现同名冲突时：

- 标记冲突。
- 暂停自动调用。
- 在 Skill 管理界面展示冲突来源。
- 允许用户改名、停用或指定本次使用哪一个。

## SKILL CREATION

`skill-creator` 必须从 Anthropic skills 仓库或当前 AI Coding 工具内置来源获取，并预置为全局 Skill：

```text
skills/skill-creator/SKILL.md
```

要求：

- 所有工作区和 Agent 默认可见。
- 创建出的 Skill 仍必须符合本规范的 `SKILL.md` ABI。
- 创建 Skill 时用户只需要选择“全局”或“当前工作区”。
- 草稿仍放在目标目录中，通过 `index.json.status = draft` 控制，不新增草稿目录。
- 草稿必须经过样本测试和用户确认后才能启用。

Agent 创建 Skill 的最小流程：

```text
1. 理解用户要解决的重复工作
2. 判断是否已有可复用 Skill
3. 没有则调用 skill-creator
4. 用户选择全局或当前工作区
5. 生成 Skill 草稿
6. 生成样本和测试计划
7. 试跑
8. 展示风险与权限
9. 用户确认
10. 更新 index.json
```

## INVOCATION

Skill 触发方式：

```text
用户显式调用
Agent 根据 description 自动匹配
页面上下文触发
工作流节点调用
其他 Skill 请求调用
```

显式调用示例：

```text
/skill:skill-creator 创建一个用于解析某类预算表的 Skill
/skill:excel-template-fill 使用这个模板和填表说明生成绑定草稿
```

自动匹配必须可解释：

```text
命中的 Skill：
命中原因：
是否加载完整 SKILL.md：
调用了哪些脚本或工具：
结果：
```

## LIFECYCLE

```text
draft
testing
waiting_user_confirm
enabled
disabled
archived
failed
conflict
```

只有 `enabled` Skill 可被正式工作流调用。

## PERMISSIONS

产品权限必须显式声明：

```text
read_file
preview_file
parse_file
query_data
draft_rule
draft_workflow
export_file
call_connector
run_sandbox_script
```

以下权限需要用户确认或管理员授权：

```text
write_staged_data
commit_confirmed_data
enable_workflow
enable_rule
call_external_api
run_high_privilege_script
install_dependency
write_external_system
```

`allowed-tools` 只表示 Skill 作者建议的工具预授权提示，不等于产品正式权限。

产品正式权限以 `index.json`、Agent 权限、工作流节点权限共同决定。

## WORKFLOW NODE REGISTRATION

Skill 可以注册工作流节点，但节点定义必须由 `index.json` 或节点注册文件管理，不强制写入 `SKILL.md`。

节点必须定义：

```yaml
node_type:
label:
input_schema:
output_schema:
params:
permissions:
error_codes:
sample_fixture:
```

## TESTING

Skill 启用前必须测试：

```text
SKILL.md frontmatter 校验
index.json 校验
依赖声明校验
依赖安装或路径检查
权限校验
样本运行
错误场景
浏览器路径
工作流节点注册
上下文 token 影响
```

测试记录写入：

```text
dev/reports/skill_tests/
```

## BROWSER CHECK

Skill 功能必须验证：

- 全局 Skill 可查看。
- 工作区 Skill 可查看。
- `skill-creator` 在全局 Skill 中可见。
- Agent 创建 Skill 草稿可操作。
- 外部 Skill 包导入可操作。
- `SKILL.md` frontmatter 可查看。
- `index.json` 登记信息可查看。
- 权限可查看。
- 测试记录可查看。
- 同名冲突可提示。
- 用户确认后才能启用。
- 启用后可绑定 Agent 或工作流节点。
- 停用后正式工作流不再调用。

## NEVER

- 不要增加全局 Skill 的中间层目录。
- 不要按 Agent 单独创建 Skill 目录。
- 不要把任何外部工具的 Skill 目录固定为产品主 Skill 目录。
- 不要让 Skill 草稿自动启用。
- 不要让 Skill 绕过权限直接写正式数据。
- 不要把外部项目整包塞进产品目录。
- 不要无测试启用 Skill。
- 不要把 Skill 写死成固定业务模块。
- 不要让业务页面直接管理 Skill 草稿。
- 不要让 Skill 依赖未声明的本机全局环境。
- 不要让 Skill 偷偷安装依赖。
- 不要把某个 Skill 的依赖提升为产品全局强依赖。
- 不要要求合法 Skill 必须带 `manifest.json`。
- 不要把产品权限塞进第三方 `SKILL.md`。

## DONE

```text
skills/：
workspaces/<workspace_id>/skills/：
skill-creator：
兼容导入：
加载流程：
index.json：
权限：
测试记录：
生命周期：
绑定关系：
工作流节点：
浏览器验收：
```

