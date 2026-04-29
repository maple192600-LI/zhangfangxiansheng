# 24_Skill目录与生命周期

## READ WHEN

设计或实现 Skill 加载、创建、导入、安装、测试、启用、停用、绑定 Agent、注册工作流节点时读取。

## READ ALSO

`../docs/21_Skill目录与生命周期规范.md`

## MUST

- 账房先生必须有自己的 Skill 加载与治理机制。
- Skill 格式兼容 Claude Code / Agent Skills 的 `SKILL.md` 结构。
- 不把任何外部工具的 Skill 目录固定为产品主 Skill 目录。
- 只支持 `global` 和 `workspace` 两类作用域。
- 全局 Skill 直接放 `skills/<skill-name>/`，不加中间层目录。
- 工作区 Skill 放 `workspaces/<workspace_id>/skills/<skill-name>/`。
- `skill-creator` 放 `skills/skill-creator/`，所有 Agent 默认可见。
- 每个 Skill 目录只强制要求 `SKILL.md`。
- `SKILL.md` frontmatter 至少包含 `name`、`description`。
- 兼容导入 Claude Code、Codex、pi-mono、OpenClaw 的 Skill 目录。
- `index.json` 管理启用状态、权限、绑定 Agent、测试记录和工作流节点。
- Skill 额外依赖必须写入 `index.json.dependencies`。
- 安装依赖或调用外部工具路径必须经过用户确认和测试记录。
- 同名 Skill 不得静默覆盖，必须提示冲突。
- Skill 草稿不会自动启用。
- 启用前必须测试并由用户确认。
- Skill 实施方案必须写清扫描、索引、加载、依赖、测试、启用和调用链。

## METHOD

```text
SkillScanner 扫描目录
-> 读取 SKILL.md frontmatter
-> 合并 index.json
-> 过滤权限和状态
-> 注入摘要
-> 命中后加载完整 SKILL.md
-> 工具层执行脚本或测试
-> 用户确认后启用
```

## NEVER

- 不要把任何外部工具的 Skill 目录固定为产品主目录。
- 不要增加全局 Skill 的中间层目录。
- 不要按 Agent 单独创建 Skill 目录。
- 不要要求合法 Skill 必须带 `manifest.json`。
- 不要把产品权限、绑定关系、测试记录塞进第三方 `SKILL.md`。
- 不要把 `skill-creator` 做成某个 Agent 的私有 Skill。
- 不要让 Skill 绕过权限直接写正式数据。
- 不要让 Skill 偷偷安装依赖。
- 不要把某个 Skill 的 pandas、xlsxwriter、LibreOffice 等依赖提升为产品全局强依赖。
- 不要无测试启用 Skill。
- 不要把外部项目整包塞进产品目录。
- 不要让业务页面直接管理 Skill 草稿。
- 不要依赖未声明的本机全局环境。

## DONE

```text
skills/：
workspaces/<workspace_id>/skills/：
skill-creator：
兼容导入：
index.json：
权限：
依赖：
加载链路：
测试记录：
生命周期：
绑定关系：
浏览器验收：
```

