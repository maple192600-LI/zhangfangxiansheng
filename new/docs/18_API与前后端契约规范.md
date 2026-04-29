# 18_API与前后端契约规范

## READ WHEN

设计或修改页面、按钮、表单、接口、错误码、前端 API 调用、后端路由、数据刷新、导出、上传、删除动作时必须读取。

## CORE RULE

用户看到的每个动作，都必须有明确前后端契约。

前端不能自己假装成功；后端不能有无人使用的接口长期存在。

## IMPLEMENTATION METHOD

每个用户动作按同一条链路实现：

```text
页面按钮 / 表单
-> frontend api function
-> backend api router
-> service
-> db/core tool
-> 统一响应
-> 前端刷新指定数据源
```

新增页面动作前必须先补页面 API 映射：

```text
用户动作
前端函数名
HTTP 方法和路径
请求体
响应 data
后端 service 函数
成功后刷新什么
失败时显示什么中文提示
```

核心接口约束：

```python
def ok(data: dict | None = None) -> dict:
    ...

def fail(code: str, message: str, data: dict | None = None) -> dict:
    ...
```

前端只能通过统一 client 调接口：

```ts
export async function request<T>(options: RequestOptions): Promise<T>
```

## CONTRACT LOCATION

API 契约放：

```text
docs/
```

推荐文件：

```text
docs/api_contract.md
docs/error_codes.md
docs/page_api_map.md
```

## RESPONSE FORMAT

接口响应必须统一：

```json
{
  "code": 0,
  "message": "ok",
  "data": {}
}
```

错误响应：

```json
{
  "code": "FILE_TEMPLATE_NOT_MATCHED",
  "message": "未匹配到可用模板",
  "data": {
    "suggested_action": "进入模板学习流程"
  }
}
```

## PAGE API MAP

每个页面必须维护页面到 API 的映射：

```markdown
| 页面 | 用户动作 | 前端函数 | API | 后端 service | 成功后刷新 | 错误提示 |
|---|---|---|---|---|---|---|
```

## MUST

- 新增按钮必须定义对应 API 或明确只做前端状态。
- 新增 API 必须有页面或工作流使用方。
- 修改 API 必须同步修改前端调用、测试、文档。
- 删除功能必须删除对应页面调用、API、service、测试和契约。
- 错误信息必须中文可读。
- 上传、导出、删除、确认、撤销、停用等动作必须有明确状态流转。
- 前端成功提示必须来自真实后端结果，不得写死假成功。

## STATE FLOW

涉及长任务或文件处理时，必须定义状态：

```text
idle
uploading
uploaded
parsing
preview_ready
waiting_confirm
confirmed
failed
cancelled
deleted
```

状态必须能刷新后恢复，不得只存在前端内存。

## ERROR CODE RULE

错误码必须稳定，错误文案必须中文可读。

错误码示例：

```text
FILE_TOO_LARGE
FILE_TYPE_UNSUPPORTED
FILE_TEMPLATE_NOT_MATCHED
FIELD_MAPPING_MISSING
VALIDATION_FAILED
WORKFLOW_NODE_FAILED
PERMISSION_DENIED
OBJECT_HAS_REFERENCES
DELETE_REQUIRES_CONFIRMATION
EXPORT_FAILED
```

## COMMAND CONTRACT

用户可见命令必须中文优先，底层动作必须稳定。

命令不能靠前端字符串判断直接执行业务逻辑，必须进入命令注册表：

```text
中文输入
-> frontend command parser
-> command_id
-> backend command router
-> permission check
-> service / core tool
-> 统一响应
```

命令契约必须维护：

```markdown
| 中文命令 | 别名 | command_id | 参数 | 权限 | 后端 handler | 成功提示 | 失败提示 |
|---|---|---|---|---|---|---|---|
```

示例：

```text
/压缩上下文 -> agent.compact
/查看工具 -> agent.tools.list
/运行工作流 -> workflow.run
/生成报表 -> report.generate
/查看连接器 -> connector.list
```

内部 `command_id`、API path、tool name 使用英文稳定标识；用户可见名称、说明、确认弹窗和错误提示使用中文。

## NEVER

- 不要只改前端不改 API 契约。
- 不要只加后端接口不接页面。
- 不要在前端写死成功数据。
- 不要吞掉后端错误。
- 不要让一个按钮调用多个含义不清的接口。
- 不要保留无人使用的 API。
- 不要让页面刷新后丢失关键状态。
- 不要让中文命令直接绕过 command_id 和权限检查。

## BROWSER CHECK

涉及 API 的用户动作必须验证：

- 点击按钮后请求真实发出。
- 成功结果显示正确。
- 失败提示中文可读。
- 刷新页面后状态正确。
- 相关列表或详情同步刷新。
- 删除或停用后不能继续调用失效对象。

## DONE

```text
API 契约：
页面 API 映射：
状态流转：
错误码：
前端调用：
后端 service：
浏览器验收：
```

