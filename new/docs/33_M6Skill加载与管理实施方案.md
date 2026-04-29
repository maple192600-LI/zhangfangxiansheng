# 33_M6Skill加载与管理实施方案

## READ WHEN

执行 `24_产品代码开发路线图.md` 的 M6 Skill 加载与管理时读取。

## GOAL

实现全局 Skill、工作区 Skill、`skill-creator`、Skill 摘要加载、完整加载、依赖声明、测试记录、启用确认和绑定 Agent 的闭环。

## MUST READ

```text
AGENTS.md
docs/03_AI_Coding_开发协作规范.md
docs/15_浏览器验收记录规范.md
docs/21_Skill目录与生命周期规范.md
docs/24_产品代码开发路线图.md
docs/30_Agent_Runtime架构与实现蓝图.md
docs/41_pi-mono_Agent与Skill技术研究.md
docs/44_OpenClaw_Gateway与多Agent技术研究.md
docs/45_Hermes_Agent记忆压缩与自我改进技术研究.md
docs/46_Claude_Code工具契约与兼容边界研究.md
rules/24_Skill目录与生命周期.md
```

## REFERENCE BASIS

| 参考项目 | 借鉴点 | 本方案落点 |
|---|---|---|
| pi-mono | 启动只扫描 Skill 摘要，命中后再加载完整内容 | `SkillScanner`、`SkillLoader` |
| OpenClaw | workspace skill、Skill snapshot、运行前审计 | `skills/`、`workspaces/<workspace_id>/skills/`、Agent 级快照 |
| Claude Code / Agent Skills | `SKILL.md`、frontmatter、scripts、references、assets | Skill 包 ABI 和兼容导入 |
| Hermes Agent | 外部目录、平台匹配、禁用列表、frontmatter 解析、候选沉淀 | Skill 草稿、平台兼容、启用前评估 |

## ARCHITECTURE

```text
SkillManagementView
-> api/skills.ts
-> api/skills.py
-> skill_service.py
-> SkillScanner / SkillIndexStore / SkillLoader / SkillTester
-> skills/index.json 或 workspaces/<workspace_id>/skills/index.json
```

Agent 使用 Skill 时：

```text
AgentLoop
-> SkillScanner 摘要
-> ContextBuilder 注入 available_skills
-> 任务命中
-> SkillLoader 读取完整 SKILL.md
-> ToolExecutor 执行脚本或测试
-> Skill 事件记录
```

## MODIFY FILES

```text
app/backend/main.py
app/frontend/src/router/index.ts
app/frontend/src/views/AgentCenterView.vue
```

## CREATE FILES

```text
app/backend/schemas/skills.py
app/backend/services/skill_service.py
app/backend/api/skills.py
app/backend/core/skills/scanner.py
app/backend/core/skills/index_store.py
app/backend/core/skills/loader.py
app/backend/core/skills/tester.py
app/backend/core/skills/dependencies.py
app/backend/core/skills/snapshot.py
app/backend/core/skills/audit.py
app/backend/tests/test_skill_scanner.py
app/backend/tests/test_skill_lifecycle.py

app/frontend/src/api/skills.ts
app/frontend/src/types/skills.ts
app/frontend/src/views/SkillManagementView.vue
app/frontend/src/components/SkillList.vue
app/frontend/src/components/SkillDetail.vue
app/frontend/src/components/SkillTestPanel.vue
app/frontend/src/components/SkillPermissionPanel.vue
```

## CORE INTERFACES

```python
def scan_skills(workspace_id: str | None) -> list[SkillSummary]:
    ...

def load_skill(skill_name: str, scope: str, workspace_id: str | None) -> SkillPackage:
    ...

def create_skill_draft(input: SkillDraftInput) -> SkillIndexEntry:
    ...

def test_skill(skill_id: str, fixture_id: str | None) -> SkillTestReport:
    ...

def enable_skill(skill_id: str, confirmed_by: str) -> SkillIndexEntry:
    ...

def disable_skill(skill_id: str) -> SkillIndexEntry:
    ...

def build_agent_skill_snapshot(agent_id: str, workspace_id: str) -> SkillSnapshot:
    ...
```

## DATA FILES

必须读写：

```text
skills/index.json
workspaces/<workspace_id>/skills/index.json
dev/reports/skill_tests/
```

`index.json` 保存：

```text
enabled
status
source_kind
source_ref
version
hash
allowed_agents
permissions
dependencies
workflow_nodes
fixtures
test_report_ids
label_zh
description_zh
platforms
disabled_reason
snapshot_version
```

Skill 的 `name` 是稳定机器标识；用户界面显示 `label_zh` 和 `description_zh`。兼容导入的 Skill 如果没有中文字段，系统必须允许用户补充中文显示名和中文说明。

## API

```text
GET    /api/skills
GET    /api/skills/{skill_id}
POST   /api/skills/drafts
POST   /api/skills/{skill_id}/test
POST   /api/skills/{skill_id}/enable
POST   /api/skills/{skill_id}/disable
PATCH  /api/skills/{skill_id}/permissions
PATCH  /api/skills/{skill_id}/allowed-agents
```

## FLOW

```text
1. 页面打开 Skill 管理
2. 后端扫描全局 Skill 和当前工作区 Skill
3. 只返回摘要和登记信息
4. 用户查看详情时加载完整 SKILL.md
5. 用户创建或导入 Skill 草稿
6. 系统记录依赖和权限
7. 用户运行样本测试
8. 测试报告写入 dev/reports/skill_tests/
9. 用户确认启用
10. index.json 状态变为 enabled
11. 为可使用该 Skill 的 Agent 生成 skill snapshot
```

## AGENT INVOCATION METHOD

Agent 使用 Skill 时必须分两步：

```text
ContextBuilder 注入 Skill 摘要
-> 模型命中某个 Skill
-> SkillLoader 读取完整 SKILL.md
-> 解析 scripts / references / assets
-> 进入 ToolExecutor 或 WorkflowExecutor
```

不得把所有 Skill 全文放入 Agent 上下文。

## TESTS

```text
扫描全局 Skill
扫描工作区 Skill
缺少 description 的 Skill 不进入可用列表
同名冲突进入 conflict
草稿 Skill 不能被正式调用
未测试 Skill 不能启用
启用后 allowed_agents 生效
停用后工作流不能调用
依赖声明缺失时测试失败
Skill snapshot 更新后 Agent 可见 Skill 变化
缺少中文显示名时页面提示补充
```

## BROWSER ACCEPTANCE

```text
打开 /agents/skills 或 Skill 管理入口
看到 skill-creator
创建一个 Skill 草稿
查看 SKILL.md frontmatter
运行测试
测试失败时显示中文原因
测试成功后启用
绑定到指定 Agent
刷新页面后状态仍正确
停用 Skill 后不可调用
```

## EXIT CONDITION

```text
全局 Skill 可扫描：
工作区 Skill 可扫描：
完整 SKILL.md 可按需加载：
草稿生命周期可用：
测试记录可查：
启用确认可用：
Agent 绑定可用：
后端测试通过：
浏览器验收记录已落文件：
项目护栏检查通过：
```

## DO NOT

```text
不要把全部 Skill 内容塞进 Agent 上下文
不要让草稿 Skill 自动启用
不要让 Skill 偷偷安装依赖
不要把外部 Skill 包内部文件改成产品登记表
不要把 Skill 写死为固定业务模块
```
