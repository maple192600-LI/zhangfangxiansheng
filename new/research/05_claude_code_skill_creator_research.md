# Claude Code Skill Creator 深度研究报告

> 研究日期：2026-04-30
> 数据来源：Anthropic 官方文档、GitHub anthropics/skills 仓库、clawbot.ai、verdent.ai、agentskills.io

---

## 一、SKILL.md 完整规范定义

### 1.1 目录结构

```
skill-name/
├── SKILL.md          ← 必须，技能入口文件
└── [可选资源目录]
    ├── scripts/      ← 可执行脚本，用于确定性/重复性任务
    ├── references/   ← 按需加载的参考文档
    └── assets/       ← 输出中使用的文件（模板、图标、字体等）
```

打包要求：`.skill` 文件或 `.zip` 压缩包必须包含 `skill-name/` 子目录，`SKILL.md` 位于该子目录内。

### 1.2 SKILL.md 文件结构

```yaml
---
# === YAML Frontmatter（元数据区）===
# 必需字段
name: skill-name                    # 技能名称，kebab-case，1-64 字符
description: "技能描述，略带'推销性'以避免触发不足"  # 技能描述

# 可选字段
compatibility: ">=1.0.0"            # 兼容性版本约束
dependencies:                       # 依赖的其他技能或工具
  - another-skill
  - tool:node>=18
when_to_use: "当需要...时使用此技能"    # 触发条件描述
allowed-tools:                      # 允许使用的工具列表
  - Read
  - Write
  - Edit
  - Bash
  - WebSearch
arguments:                          # 技能参数定义
  target_lang:
    description: "目标编程语言"
    required: true
  output_format:
    description: "输出格式"
    required: false
    default: "markdown"
context: inline                     # 执行模式：inline（注入当前上下文）或 fork（独立子代理）
agent: false                        # 是否作为独立代理运行
effort: medium                      # 推理努力级别：low / medium / high
model: sonnet                       # 使用的模型：sonnet / haiku / opus
disable-model-invocation: false     # 禁止模型调用（纯脚本技能）
user-invocable: true                # 用户是否可直接调用
hooks:                              # 生命周期钩子
  pre: "scripts/pre_check.sh"
  post: "scripts/post_cleanup.sh"
paths:                              # 作用路径限制
  include:
    - "src/**/*.py"
  exclude:
    - "tests/**"
---

# === Markdown Body（指令区）===

## 角色定义
你是一个 [具体角色描述]...

## 工作流程
1. 步骤一...
2. 步骤二...

## 规则
- 规则一...
- 规则二...

## 示例
### 示例 1: [场景描述]
输入: ...
输出: ...
```

### 1.3 全部可用 Frontmatter 字段一览

| 字段 | 类型 | 必需 | 说明 |
|------|------|------|------|
| `name` | string | **是** | 技能名称，kebab-case，1-64 字符 |
| `description` | string | **是** | 技能描述，建议包含触发关键词 |
| `compatibility` | string | 否 | 兼容性版本约束（语义化版本） |
| `dependencies` | list | 否 | 依赖的其他技能或工具 |
| `when_to_use` | string | 否 | 触发条件说明 |
| `allowed-tools` | list | 否 | 限制技能可使用的工具集合 |
| `arguments` | object | 否 | 参数定义，每个参数含 description/required/default |
| `context` | string | 否 | `inline`（默认，注入当前上下文）或 `fork`（独立子代理） |
| `agent` | bool | 否 | 是否作为独立代理运行（fork 模式下有意义） |
| `effort` | string | 否 | 推理努力级别：`low` / `medium` / `high` |
| `model` | string | 否 | 模型选择：`sonnet` / `haiku` / `opus` |
| `disable-model-invocation` | bool | 否 | 禁止模型调用，纯脚本执行 |
| `user-invocable` | bool | 否 | 用户是否可通过 `/skill-name` 直接调用 |
| `hooks` | object | 否 | 生命周期钩子（pre/post） |
| `paths` | object | 否 | 路径白名单/黑名单 |

### 1.4 安全属性分类

**安全属性（自动允许）：**
- `name`, `description`, `when_to_use`, `effort`, `model`, `user-invocable`

**不安全属性（需授权）：**
- `allowed-tools`, `hooks`, `scripts/` 目录中的可执行文件
- `disable-model-invocation`, `paths`

### 1.5 变量替换机制

| 变量 | 说明 |
|------|------|
| `$arg_name` | 参数引用（frontmatter 中定义的 arguments） |
| `${CLAUDE_SKILL_DIR}` | 当前技能的目录绝对路径 |
| `${CLAUDE_SESSION_ID}` | 当前会话 ID |

---

## 二、Skill 创建流程

### 2.1 用户创建步骤

```
1. 创建技能目录
   mkdir -p my-skill/scripts my-skill/references my-skill/assets

2. 编写 SKILL.md
   - 添加 YAML frontmatter（至少 name + description）
   - 编写 Markdown 指令体（角色、工作流、规则、示例）
   - 控制在 500 行以内

3. 本地测试
   - 放置到项目根目录的 .claude/skills/ 下
   - Claude Code 启动时自动发现
   - 通过 `/my-skill` 手动触发或让系统自动匹配

4. 迭代优化
   - 观察触发率（描述写得"推销性"一些可避免触发不足）
   - 补充 references/ 中的参考文档
   - 在 scripts/ 中添加自动化脚本
   - 编写 evals.json 进行量化评估

5. 发布
   - 推送到 GitHub 仓库
   - 用户通过 `npx skills add username/repo` 安装
   - 或打包为 .skill / .zip 文件分发
```

### 2.2 Progressive Disclosure（渐进式加载）

Skill 系统采用三级加载策略：

| 层级 | 内容 | 大小 | 加载时机 |
|------|------|------|----------|
| L1 - 元数据 | name + description | ~100 词 (~100 tokens) | 始终加载 |
| L2 - SKILL.md 主体 | Markdown 指令 | <500 行 | 被触发时加载 |
| L3 - 捆绑资源 | scripts/references/assets | 按需 | 需要时才加载 |

**关键设计原则：** 启动时每个技能只消耗约 100 tokens 的元数据开销。L2 和 L3 的内容只有在技能被实际触发或需要时才加载到上下文中。

### 2.3 SKILL.md 编写最佳实践

1. **保持聚焦**：一个技能做一件事，控制在 500 行以内
2. **使用祈使句**：指令用"Do X"而非"You should do X"
3. **解释 Why**：不仅告诉做什么，还要解释为什么
4. **提供示例**：每个关键步骤至少一个 concrete example
5. **描述优化**：description 是触发匹配的关键，建议：
   - 包含明确的触发短语（"When you need to..."）
   - 略带"推销性"避免触发不足（undertriggering）
   - 使用同义词和相关术语扩大匹配面
6. **增量测试**：先写最小版本，测试后再逐步增加复杂度

---

## 三、Skill 发现与加载机制

### 3.1 加载优先级

```
bundled（内置）> managed（~/.config/.claude/skills）> user（~/.claude/skills）> project（.claude/skills）> plugin > MCP
```

| 优先级 | 位置 | 说明 |
|--------|------|------|
| 1 - bundled | 内置于 Claude Code | 系统自带技能（commit, review-pr 等） |
| 2 - managed | `~/.config/.claude/skills/` | 全局管理的已安装技能 |
| 3 - user | `~/.claude/skills/` | 用户全局自定义技能 |
| 4 - project | `.claude/skills/` | 项目级技能，仓库可共享 |
| 5 - plugin | 通过插件系统加载 | 第三方插件提供的技能 |
| 6 - MCP | MCP 协议提供 | 通过 MCP 服务暴露的技能 |

### 3.2 发现流程

```
Claude Code 启动
    │
    ├── 扫描 bundled skills（内置）
    ├── 扫描 ~/.config/.claude/skills/
    ├── 扫描 ~/.claude/skills/
    ├── 扫描 .claude/skills/（项目级）
    │
    ├── 读取每个 SKILL.md 的 YAML frontmatter
    │   └── 提取 name + description（~100 tokens/技能）
    │
    └── 构建技能索引（L1 元数据缓存）
         │
         ├── 用户输入匹配 description/when_to_use
         │   └── 触发 → 加载 L2（SKILL.md 主体）
         │
         └── 技能指令引用 scripts/references/assets
              └── 按需加载 L3（捆绑资源）
```

### 3.3 触发匹配机制

- **自动触发**：系统根据用户输入与技能 `description` + `when_to_use` 的语义相似度自动匹配
- **手动触发**：用户输入 `/skill-name` 直接调用
- **参数化触发**：如 `/skill-name --arg1 value1`

### 3.4 上下文预算

| 项目 | Token 开销 |
|------|-----------|
| 技能元数据（L1） | ~100 tokens/技能 |
| 技能主体（L2） | 取决于 SKILL.md 长度，建议 <500 行 |
| fork 模式 | 独立 token 预算，不占用主上下文 |
| inline 模式 | 共享主上下文预算 |

---

## 四、Skill-Creator 工作流程

### 4.1 概述

`skill-creator` 是 Anthropic 官方提供的元技能——用于创建、修改和改进其他技能，并能量化衡量技能性能。位于 GitHub 仓库 `anthropics/skills/skills/skill-creator/`。

### 4.2 完整工作流

```
┌─────────────────────────────────────────────────────┐
│                 Skill-Creator 工作流                  │
├─────────────────────────────────────────────────────┤
│                                                     │
│  1. Capture Intent（捕获意图）                        │
│     ├── 用户描述想创建什么技能                          │
│     ├── 确认目标受众和使用场景                          │
│     └── 明确成功标准                                  │
│                                                     │
│  2. Interview / Research（访谈/研究）                  │
│     ├── 提出针对性问题补充细节                          │
│     ├── 搜索现有技能和模板                             │
│     └── 确定最佳实践和边界条件                          │
│                                                     │
│  3. Write SKILL.md（编写技能）                        │
│     ├── 生成 YAML frontmatter                        │
│     ├── 编写 Markdown 指令体                          │
│     ├── 创建 scripts/（如需要）                        │
│     └── 创建 references/（如需要）                     │
│                                                     │
│  4. Test Cases（编写测试用例）                         │
│     └── 生成 evals.json：                             │
│         {                                           │
│           "evals": [                                │
│             {                                       │
│               "id": "eval-001",                     │
│               "prompt": "测试提示",                    │
│               "expected_output": "期望输出",           │
│               "files": {"path": "content"},         │
│               "assertions": [                       │
│                 {"type": "contains", "value": "..."} │
│               ]                                     │
│             }                                       │
│           ]                                         │
│         }                                           │
│                                                     │
│  5. Run & Evaluate（运行与评估）                       │
│     ├── 使用三个子代理协同评估：                        │
│     │   ├── grader.md    → 逐条打分                  │
│     │   ├── comparator.md → 与基线对比               │
│     │   └── analyzer.md   → 分析失败模式              │
│     ├── 生成评估报告                                  │
│     └── 记录到 grading.json / benchmark.json          │
│                                                     │
│  6. Improve（改进）                                   │
│     ├── 根据 eval 结果修改 SKILL.md                    │
│     ├── 优化 description 提升触发率                    │
│     └── 补充边界情况处理                               │
│                                                     │
│  7. Repeat（迭代）                                    │
│     └── 回到步骤 5，直到通过所有 eval                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

### 4.3 Description 优化循环

Skill-creator 有一个专门优化触发描述的流程：

```
1. 生成 20 个触发评估查询
   ├── 8-10 个 should-trigger（应该触发）
   └── 8-10 个 should-not-trigger（不应触发）

2. 运行 scripts.run_loop 对每个查询测试
   └── 记录触发/未触发结果

3. 根据结果调整 description
   ├── 触发不足 → 增加相关关键词和触发短语
   ├── 误触发 → 收窄描述范围
   └── 重复直到命中率达标
```

### 4.4 评估体系

```json
// evals.json 结构
{
  "evals": [
    {
      "id": "unique-eval-id",
      "prompt": "用户输入模拟",
      "expected_output": "期望的技能行为描述",
      "files": {
        "relative/path/to/file": "文件内容"
      },
      "assertions": [
        {
          "type": "contains",        // 断言类型
          "value": "期望包含的文本"
        },
        {
          "type": "not_contains",
          "value": "不应包含的文本"
        },
        {
          "type": "matches_regex",
          "value": "正则表达式"
        }
      ]
    }
  ]
}
```

评估子代理：

| 子代理 | 文件 | 职责 |
|--------|------|------|
| grader | `grader.md` | 对每个 eval 逐条打分，评估输出质量 |
| comparator | `comparator.md` | 与基线版本对比，衡量改进幅度 |
| analyzer | `analyzer.md` | 分析失败模式，提供改进建议 |

### 4.5 平台适配

| 平台 | 限制 | 适配策略 |
|------|------|----------|
| **Claude.ai** | 无子代理、串行测试 | 单代理完成所有步骤 |
| **Claude Code** | 完整能力 | 使用子代理并行评估 |
| **Cowork** | 无浏览器 | 使用 `--static` 模式 |

---

## 五、适合嵌入第三方项目的 Skill 规范子集

### 5.1 最小子集（MVP）

对于需要在第三方项目中实现 Skill 系统的场景，以下是必需的最小规范子集：

```yaml
---
# 最小必需字段
name: skill-name          # 唯一标识，kebab-case
description: "描述"       # 触发匹配依据
---

# Markdown 指令体
## 工作流程
1. ...
```

仅两个字段 + Markdown 指令体即可运行一个基本技能。

### 5.2 推荐子集（生产级）

```yaml
---
name: skill-name
description: "包含触发关键词的详细描述"
when_to_use: "明确的触发条件"
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
arguments:
  param1:
    description: "参数说明"
    required: true
context: inline           # 或 fork
effort: medium
model: sonnet
---
```

### 5.3 嵌入实现建议

如果要在自己的 Agent Runtime（如本项目的 Agent V2）中实现 Skill 系统：

#### 目录结构映射

```
# Claude Code 原生结构        →  本项目映射
.claude/skills/               →  backend/data/agents/{agent_id}/skills/
  skill-name/                 →    skill-name/
    SKILL.md                  →      SKILL.md（保持一致）
    scripts/                  →      scripts/
    references/               →      references/
```

#### 核心接口设计

```python
from dataclasses import dataclass, field
from typing import Optional
from pathlib import Path

@dataclass
class SkillMeta:
    """L1 元数据 - 始终加载"""
    name: str
    description: str
    when_to_use: Optional[str] = None
    context: str = "inline"          # inline | fork
    effort: str = "medium"           # low | medium | high
    model: str = "sonnet"            # sonnet | haiku | opus
    allowed_tools: list[str] = field(default_factory=list)
    arguments: dict = field(default_factory=dict)

@dataclass
class Skill:
    """完整技能对象"""
    meta: SkillMeta
    body: str                          # L2 - Markdown 指令体
    skill_dir: Path                    # 技能目录路径
    scripts_dir: Optional[Path] = None # L3 - scripts/
    refs_dir: Optional[Path] = None    # L3 - references/
    assets_dir: Optional[Path] = None  # L3 - assets/

class SkillLoader:
    """技能加载器"""
    
    def scan_skills(self, skills_dir: Path) -> list[SkillMeta]:
        """扫描目录，构建 L1 索引"""
        ...
    
    def load_skill(self, name: str) -> Skill:
        """按名称加载完整技能（L1+L2）"""
        ...
    
    def load_resource(self, skill: Skill, resource_path: str) -> str:
        """按需加载 L3 资源"""
        ...
    
    def match_skill(self, user_input: str) -> list[SkillMeta]:
        """根据用户输入匹配最佳技能"""
        ...

class SkillExecutor:
    """技能执行器"""
    
    def execute_inline(self, skill: Skill, args: dict) -> str:
        """inline 模式：注入当前上下文"""
        ...
    
    def execute_fork(self, skill: Skill, args: dict) -> str:
        """fork 模式：独立子代理执行"""
        ...
```

#### 渐进式加载实现要点

```python
class SkillRegistry:
    """技能注册表 - 实现三级加载"""
    
    def __init__(self, skills_root: Path):
        self.skills_root = skills_root
        self._index: dict[str, SkillMeta] = {}  # L1 缓存
        self._loaded: dict[str, Skill] = {}      # L2 缓存
    
    def startup_scan(self):
        """启动时扫描所有 SKILL.md，只读 frontmatter"""
        for skill_dir in self.skills_root.iterdir():
            skill_file = skill_dir / "SKILL.md"
            if skill_file.exists():
                meta = self._parse_frontmatter(skill_file)
                self._index[meta.name] = meta
                # 每个技能仅 ~100 tokens 的元数据开销
    
    def trigger(self, user_input: str) -> Optional[Skill]:
        """匹配并加载技能"""
        matched = self._match(user_input)
        if matched:
            return self._load_full(matched)  # 加载 L2
        return None
    
    def get_resource(self, skill_name: str, path: str):
        """按需获取 L3 资源"""
        skill = self._loaded.get(skill_name)
        if skill:
            resource = skill.skill_dir / path
            if resource.exists():
                return resource.read_text()
        return None
```

### 5.4 与本项目 Agent V2 的集成路线

```
Phase 1: 基础加载
  - 实现 SkillMeta 解析
  - 扫描 backend/data/agents/{agent_id}/skills/ 下的 SKILL.md
  - 支持 name + description 最小字段

Phase 2: 触发匹配
  - 基于 description 的关键词/语义匹配
  - 支持手动触发（/skill-name）
  - 支持 when_to_use 条件

Phase 3: 执行引擎
  - inline 模式：将 SKILL.md body 注入 Agent prompt
  - fork 模式：创建独立子代理执行
  - 支持 arguments 参数传递

Phase 4: 资源管理
  - scripts/ 目录下的脚本执行
  - references/ 按需加载
  - 捆绑资源路径解析

Phase 5: 评估体系
  - evals.json 格式支持
  - 自动化测试运行器
  - 触发率统计与 description 优化建议
```

---

## 六、29 个内置技能一览

Claude Code 自带以下内置技能（bundled skills）：

| 技能名 | 用途 |
|--------|------|
| `commit` | 生成规范的 commit 消息 |
| `create-pr` | 创建 Pull Request |
| `review-pr` | 审查 Pull Request |
| `security-review` | 安全审查 |
| `verify` | 验证代码正确性 |
| `skillify` | 将代码模式提取为技能 |
| `debug` | 调试问题 |
| `test` | 生成测试 |
| `doc` | 生成文档 |
| `plan` | 规划实现方案 |
| `implement` | 实现功能 |
| `refactor` | 重构代码 |
| `performance` | 性能优化 |
| `accessibility` | 无障碍检查 |
| `typescript` | TypeScript 相关 |
| `python` | Python 相关 |
| `react` | React 相关 |
| `database` | 数据库相关 |
| `api` | API 设计相关 |
| `docker` | Docker 相关 |
| `ci` | CI/CD 相关 |
| `git` | Git 操作相关 |
| `deploy` | 部署相关 |
| `monitor` | 监控相关 |
| `migrate` | 迁移相关 |
| `explain` | 代码解释 |
| `translate` | 代码翻译 |
| `optimize` | 代码优化 |
| `scaffold` | 项目脚手架 |

---

## 七、关键发现总结

### 7.1 设计哲学

1. **渐进式加载**是核心设计理念——100 tokens 元数据始终加载，主体按需加载
2. **描述即触发**——description 是最关键的字段，直接影响自动触发率
3. **Skills 之间可组合**——通过 dependencies 字段声明依赖关系
4. **评估内建**——skill-creator 自带完整的 eval 体系，支持量化迭代

### 7.2 与本项目的关系

- 本项目 Agent V2 的 Skill 系统可直接采用 SKILL.md 规范作为标准格式
- `backend/data/agents/{agent_id}/skills/` 目录已存在，可作为技能存放路径
- 需要实现的三个核心组件：SkillLoader（解析加载）、SkillRegistry（注册索引）、SkillExecutor（执行调度）
- 建议优先实现 L1+L2，L3 资源加载可延后

### 7.3 参考资源

- Anthropic 官方帮助中心：https://support.claude.com/en/articles/12512198
- GitHub 仓库：https://github.com/anthropics/skills
- Skill 指南：https://clawbot.ai/claude-code/guides/skills-guide.html
- 构建教程：https://www.verdent.ai/guides/how-to-build-install-claude-skills
- 开放规范：https://agentskills.io/specification
