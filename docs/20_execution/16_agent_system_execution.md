# 16 · Agent 系统执行规范

本文件定义当前 Agent 系统应怎样参与产品工作流。

## Agent 定位

Agent 是规则创建、规则维护、解释和学习引擎。它不替代确定性执行。

Agent 可以：

- 分析用户上传的脱敏样本。
- 创建或改进 Parser。
- 创建或改进 Rule。
- 询问用户确认。
- 记录用户偏好、业务事实、规则经验和纠错记录。

Agent 不可以：

- 在导入入库执行阶段调用 LLM。
- 在报表生成执行阶段调用 LLM。
- 绕过 Parser/Rule 审核直接写业务结果。
- 要求用户写 JSON、正则、SQL 或字段映射。

## 主链路

```text
银行流水:
上传 -> 匹配 Parser -> 无匹配则 Agent 创建 Parser -> 用户审核
     -> Parser 确定性执行 -> 预览 -> 确认入库 -> fund_events

报表模板:
上传模板 -> 匹配 Rule -> 无匹配则 Agent 创建 Rule -> 用户审核
       -> Rule 确定性执行 -> 生成报表
```

## 核心模块

| 模块 | 职责 |
| --- | --- |
| `backend/agents/runtime.py` | Agent 对话、工具调用、错误恢复 |
| `backend/agents/prompt_builder.py` | 拼装 Agent 身份、Memory、Skill 和工具说明 |
| `backend/agents/skill_registry.py` | 发现、加载和匹配 Skill |
| `backend/agents/memory_manager.py` | 记忆预加载、注入、同步、清洗 |
| `backend/agents/tools/` | Agent 可调用工具 |
| `backend/agents/fund/` | 创建 Parser/Rule 的财务专用流程 |
| `backend/fund/primitives/` | Parser/Rule artifact 可调用的确定性基元 |
| `backend/core/artifact_runtime.py` | Parser/Rule 执行入口 |

不得再新增平行 Agent 运行时目录。

## Parser

Parser 是银行流水或手工流水解析规则的长期资产。

要求：

- 由 Agent 根据样本创建或维护。
- 用户审核后才能激活。
- 执行时只调用白名单基元。
- 输出必须符合 `fund_events` 基础数据表需要的字段。
- 同银行同格式 Parser 应可跨账户复用，账户归属由主数据和别名库决定。

## Rule

Rule 是报表模板填充规则的长期资产。

要求：

- 由 Agent 根据模板和字段字典创建或维护。
- 用户审核后才能激活。
- 执行时只从基础数据表和主数据取数。
- 不在执行阶段调用 LLM。
- 每次生成结果应可追溯到 Rule、模板、期间和数据来源。

## Memory

Memory 只保存可复用经验，不保存原始敏感流水明细。

分类：

- `preference`：用户偏好和操作习惯。
- `business_fact`：单位、账户、银行、报表口径等业务事实。
- `rule_experience`：字段别名、银行格式、模板经验。
- `correction`：用户纠错和确认意见。

Memory 必须可查看、可脱敏、可删除。

## API 与前端边界

前端工作台只表达业务流程，不暴露底层规则编辑细节。

规则中心负责：

- 查看 Parser 和 Rule。
- 展示样本校验结果。
- 审核、启用、停用、归档规则。
- 显示规则来源、最近使用时间和关联批次。

银行导入页负责：

- 上传。
- 展示匹配结果。
- 引导创建规则。
- 预览基础数据表行。
- 确认入库。

报表页负责：

- 选择期间、主体、账户和模板。
- 调用已激活 Rule 生成报表。
- 展示生成结果和下载入口。
