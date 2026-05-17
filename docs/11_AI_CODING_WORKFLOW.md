# AI Coding 工作流

## 临时计划文档放哪里

- 功能修复/新增功能/审计/重构计划放在 `ai_coordination/<workstream>/prompts/`
- 执行结果放在 `ai_coordination/<workstream>/claude_results/`
- `ai_coordination/` 是协作工作区，**不是正式项目文档入口**
- 任务完成后，临时计划中的长期事实必须被提炼进 active docs，原始 prompt/result 不作为长期事实源
- 如果这些协调文件未来要提交进仓库，必须有单独决策

## 任务包格式

AI Coding 工具（Claude Code / Codex）执行的任务包应包含：

```markdown
# 任务标题

## 目标
一句话说明要完成什么。

## 背景与当前事实
为什么做这件事，当前状态是什么。引用代码事实而非文档断言。

## 必读文件
列出必须读取的文件路径。

## 影响范围
列出受影响的模块、页面、API、数据流。

## 允许修改范围
列出允许修改的文件路径。不在列表中的文件禁止修改。

## 禁止修改范围
明确列出禁止修改的范围。

## 实施步骤
按顺序列出具体步骤。

## 数据/接口/页面影响
改了哪些数据结构、API 签名、页面行为。

## 文档影响
- 无需更新文档（说明原因）
- 已更新哪些 active docs
- 需要用户/Codex 决策后再更新

## 测试方式
如何验证改动正确。

## 验收标准
明确的可检查标准。

## 回滚方案
如果出问题怎么回滚。

## 结果报告路径
结果文件路径，必须包含：修改文件、运行命令、结果摘要、失败、未完成事项。
```

## Codex / Claude Code 文件传递流程

```
Codex                          Claude Code
  │                                │
  ├─ 写 prompt 文件 ──────────────→│ 读取并执行
  │  prompts/NN_step.md            │
  │                                │
  │←────── 写 result 文件 ─────────┤
  │         claude_results/NN_     │
  │         step_result.md         │
  │                                │
  ├─ 审查（在对话中给出结论）──────→│
  │  通过 → 写下一步 prompt         │
  │  不通过 → 写 revision prompt    │
```

## 功能修复/新增功能计划模板

计划写在 `ai_coordination/<workstream>/prompts/NN_*.md`，**不是**直接新增 `docs/某某功能计划.md`。

```markdown
## 目标
## 背景与当前事实
## 必读文件
## 影响范围
## 允许修改范围
## 禁止修改范围
## 实施步骤
## 数据/接口/页面影响
## 文档影响
## 测试方式
## 验收标准
## 回滚方案
## 结果报告路径
```

## 文档更新责任

- 谁改代码/接口/数据流/页面/业务规则，谁负责同步相关文档
- Claude Code 执行任务时，结果报告必须包含"文档影响判断"
- 用户只负责产品/范围/取舍确认，不负责手工追文档

## 核心规则

- **不在 `main` 直接开发**，使用功能分支
- **不提交、不进入下一步**，除非 prompt 明确要求
- 每次只执行 Codex 指定的一个 prompt 文件
- 结果写入指定路径，不跳步
- 如果 prompt 要求只读审计，绝对不修改任何文件

## 项目文件交接目录

```
ai_coordination/
└── doc-rebuild/              ← 当前治理工作流
    ├── prompts/              ← 计划文件
    ├── claude_results/       ← 执行结果
    └── codex_reviews/        ← 审查文件（可选）
```

---
**校准来源：** `ai_coordination/doc-rebuild/00_master_plan.md`、`AGENTS.md`
**最后校准：** 2026-05-17
