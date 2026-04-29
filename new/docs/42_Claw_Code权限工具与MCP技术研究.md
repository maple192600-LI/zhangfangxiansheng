# 42_Claw_Code权限工具与MCP技术研究

## READ WHEN

设计文件工具、命令工具、权限模式、MCP 连接器、Skill 命令入口时读取。

## SOURCE FILES

```text
claw-code/PARITY.md
claw-code/rust/crates/runtime/src/permission_enforcer.rs
claw-code/rust/crates/runtime/src/permissions.rs
claw-code/rust/crates/runtime/src/file_ops.rs
claw-code/rust/crates/runtime/src/mcp_tool_bridge.rs
claw-code/rust/crates/tools/src/lib.rs
claw-code/rust/crates/commands/src/lib.rs
```

## KEY FINDINGS

Claw Code 的价值在于本地执行边界，而不是界面：

```text
1. 所有工具有 ToolSpec，包含 name、description、input_schema、required_permission。
2. GlobalToolRegistry 会检查内置工具、插件工具、运行期工具的重名冲突。
3. PermissionPolicy 支持 read-only、workspace-write、danger-full-access、prompt、allow。
4. PermissionEnforcer 对工具、文件写入、bash 命令分开检查。
5. 文件工具有大小限制、二进制检测、路径标准化、边界校验、patch 元数据。
6. MCP 有连接状态、工具列表、资源列表、读取资源、调用工具、错误状态。
7. Skill 命令分为本地管理动作和转交给 Agent 的调用动作。
```

## PRODUCT IMPLEMENTATION PLAN

工具注册必须是统一入口：

```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict | None = None
    permission: str
    source: str
```

权限模式采用四档即可：

```text
read_only        只读
workspace_write 允许写工作区产物
external_write  允许写外部系统或企业系统
confirm          每次高风险动作等待用户确认
```

文件工具必须内置防护：

```text
resolve 绝对路径
检查是否在授权目录内
检查符号链接是否逃逸
检查文件大小
检查二进制文件
读取时支持 offset / limit
写入时返回结构化 patch
```

命令工具必须先分类：

```text
safe_read_command      可在 read_only 下运行
workspace_mutation     需要 workspace_write
external_mutation      需要 external_write 或 confirm
unknown_or_dangerous   必须等待确认或拒绝
```

MCP 连接器不得直接暴露给模型。必须先注册为受控工具：

```text
McpServerState
  server_id
  display_name
  status
  tools
  resources
  last_error
  updated_at
```

Agent 调 MCP 的流程：

```text
Agent tool_call
-> ToolRegistry 找到 connector.mcp.call
-> PermissionGuard 检查 server_id/tool_name/args
-> McpConnector 确认连接状态
-> 调用 MCP tool
-> 结果裁剪后返回 Agent
-> 事件写入审计日志
```

Skill 命令入口只做三类动作：

```text
list     列出可用 Skill 摘要
install  安装到 skills/ 或 workspaces/<workspace_id>/skills/
invoke   把 Skill 调用转换为 Agent 消息
```

## TESTS

```text
只读模式下读取文件成功。
只读模式下写文件失败。
未授权目录读取失败。
符号链接逃逸失败。
超大文件读取失败。
二进制文件按专用预览或拒绝处理。
工具重名注册失败。
MCP server 未连接时调用失败并返回中文错误。
MCP tool 不在允许列表时调用失败。
Skill invoke 只产生 Agent 消息，不直接执行脚本。
```

## DO NOT

```text
不要让业务代码直接调用文件系统。
不要让 MCP 工具跳过 ToolRegistry。
不要只做前端权限隐藏。
不要把所有命令都当成可执行命令。
不要保留两个同名工具实现。
```

