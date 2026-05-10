# 04 · 编码规范

> 配合 [00_project_constitution.md](00_project_constitution.md)、[05_tech_constraints.md](05_tech_constraints.md) 使用。

---

## §1 · Python 后端规范

### §1.1 · 命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 文件名 | snake_case | `bank_import_service.py` |
| 类名 | PascalCase | `BankImportService` |
| 函数/方法 | snake_case | `parse_bank_statement()` |
| 常量 | UPPER_SNAKE_CASE | `MAX_BATCH_SIZE = 1000` |
| 私有方法 | _前缀 | `_validate_headers()` |
| ORM 模型 | PascalCase，表名 snake_case | `class FundEvent` → `fund_events` |

### §1.2 · 分层调用规则

```
api/（路由层）→ 只做参数校验 + 调 service + 返回响应
  ↓
services/（业务层）→ 所有业务逻辑
  ↓
db/（数据层）→ ORM 模型定义
  ↓
database.py → 引擎与会话管理
```

- 路由层禁止：直接查数据库、调用 AI、写业务逻辑
- Service 层禁止：直接操作 request/response 对象
- ORM 层禁止：包含业务逻辑方法

### §1.3 · 响应格式

所有 API 响应统一走 `core/response.py`：

```python
from core.response import success, error

# 成功
return success(data={"items": items, "total": len(items)})

# 失败
return error(code=1001, message="参数缺失")
```

禁止在路由层直接构造 JSON 响应。

### §1.4 · 数据库访问

- 统一通过 `get_db()` 依赖注入获取会话
- 禁止裸 SQL（Alembic 迁移脚本除外）
- 使用 `try/finally` 确保会话关闭
- 批量操作使用 `bulk_insert_mappings`

### §1.5 · 错误处理

- 路由层：捕获 Service 层异常，转为错误响应
- Service 层：抛出有意义的异常（不要吞掉错误）
- 全局：`main.py` 的 `_global_exception_handler` 兜底，返回中文提示

### §1.6 · 类型注解

所有函数签名必须有类型注解：

```python
def import_bank_statement(
    file_path: str,
    account_code: str,
    batch_id: int | None = None,
) -> dict[str, Any]:
```

---

## §2 · Vue 前端规范

### §2.1 · 文件组织

```
views/           ← 页面组件（按功能模块命名）
  agent/         ← Agent 相关页面子目录
components/      ← 通用可复用组件
composables/     ← Vue 组合式函数（use 开头）
stores/          ← Pinia 状态管理
api/             ← 接口请求封装
router/          ← 路由配置
styles/          ← 全局样式
```

### §2.2 · 命名

| 类型 | 规范 | 示例 |
|------|------|------|
| 页面组件 | PascalCase.vue | `BankImport.vue` |
| 通用组件 | PascalCase.vue | `DataTable.vue` |
| 组合式函数 | camelCase，use 前缀 | `useTableFilter.js` |
| API 文件 | camelCase | `bankImport.js` |
| CSS class | kebab-case | `page-header` |

### §2.3 · API 调用

统一通过 `src/api/` 封装，不直接在组件中写 axios 调用：

```javascript
// src/api/bankImport.js
import request from './request'

export function uploadBankFile(file) {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/bank/import', formData)
}

// 在组件中使用
import { uploadBankFile } from '@/api/bankImport'
```

### §2.4 · 状态管理

- 全局状态放 Pinia store（如用户信息、Agent 配置）
- 页面局部状态用 `ref` / `reactive`
- 不在组件间直接传递 props 超过 3 层

---

## §3 · 通用规范

### §3.1 · 全中文

- 所有 UI 文案、错误提示、日志信息均为中文
- API 响应的 `message` 字段为中文
- 代码注释按需使用中文（非强制）

### §3.2 · 文件大小

| 类型 | 上限 | 超出处理 |
|------|------|----------|
| Python 文件 | 500 行 | 拆分模块 |
| Vue 文件 | 400 行 | 抽取组件 |
| 单个函数 | 50 行 | 拆分子函数 |

### §3.3 · Git 提交

格式：`<type>: <中文描述>`

type: feat / fix / refactor / docs / test / chore / perf

```
feat: 银行导入支持多格式自动检测
fix: 日报金额汇总精度丢失问题
refactor: Agent 运行时核心循环简化
```

---

**版本**
- v1.0 · 2026-05-02 · 首次发布
