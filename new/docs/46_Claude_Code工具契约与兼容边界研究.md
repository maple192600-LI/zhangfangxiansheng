# 46_Claude_Code工具契约与兼容边界研究

## READ WHEN

设计工具 schema、文件读写输出、Agent 子任务、MCP 输出、兼容 Skill 包时读取。

## SOURCE FILES

```text
C:/Users/Administrator/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/sdk-tools.d.ts
C:/Users/Administrator/AppData/Roaming/npm/node_modules/@anthropic-ai/claude-code/README.md
C:/Users/Administrator/AppData/Roaming/npm/claude.ps1
```

## KEY FINDINGS

Claude Code npm 包可读材料主要是 CLI 入口和工具类型声明。可借鉴的是工具契约，不是内部实现：

```text
1. 工具输入输出有明确 TypeScript schema。
2. Agent 工具输出包含 agentId、agentType、token、耗时、toolStats。
3. 异步 Agent 可返回 outputFile，调用方可读进度。
4. FileReadOutput 区分 text、image、notebook、pdf、parts、file_unchanged。
5. MCP resource 输出包含 uri、name、mimeType、description、server。
6. 文件工具输出包含 filePath、content、numLines、startLine、totalLines。
```

## PRODUCT IMPLEMENTATION PLAN

本产品工具契约必须类型化：

```python
class ToolCall(BaseModel):
    id: str
    name: str
    args: dict

class ToolResult(BaseModel):
    tool_call_id: str
    tool_name: str
    content: list[dict]
    details: dict
    is_error: bool = False
    usage: dict | None = None
```

Agent 子任务输出必须包含：

```text
agent_id
session_id
status
summary
total_duration_ms
total_tokens
tool_stats
artifact_refs
```

文件读取输出必须按类型分流：

```text
text      文本、CSV、JSON、Markdown
sheet     Excel、CSV 结构化表格预览
image     图片预览和尺寸
pdf       PDF 基础信息或页图引用
parts     多页或多 sheet 拆分结果
unchanged 文件未变化
```

异步任务必须提供进度读取：

```text
POST /api/agents/{agent_id}/tasks
GET  /api/agents/tasks/{task_id}
GET  /api/agents/tasks/{task_id}/events
POST /api/agents/tasks/{task_id}/cancel
```

兼容 Skill 包时，只接受结构：

```text
<skill-name>/SKILL.md
<skill-name>/scripts/
<skill-name>/references/
<skill-name>/assets/
```

导入后必须写入本产品的 skill index，不能依赖外部目录作为运行事实源。

## TESTS

```text
每个工具输入 schema 可校验。
每个工具输出可序列化。
Agent 子任务能返回 token、耗时、工具统计。
异步任务可查询进度。
文件读取能区分 text/sheet/image/pdf。
MCP resource 输出能映射到统一资源卡片。
导入 Skill 后不依赖原路径仍可加载。
```

## DO NOT

```text
不要把未公开内部实现当成依据。
不要用无类型 dict 在前后端之间传递工具结果。
不要让异步任务没有可查询进度。
不要把外部 Skill 原路径当成唯一运行来源。
```

