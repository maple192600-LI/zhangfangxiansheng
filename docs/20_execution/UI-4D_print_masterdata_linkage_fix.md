# UI-4D: 打印按钮 + 主数据联动 + Agent URL 修复

> 阶段：UI-4D | 分支：`audit/frontend-ui-4d-print-masterdata-linkage-fix` | 日期：2026-05-12

## 修复清单

| # | 问题 | 根因 | 修复方案 | 影响文件 |
|---|------|------|----------|----------|
| 1 | 打印按钮点击无反应 | `@click="window.print()"` 在 Vue 3 `<script setup>` 模板中无法正确解析全局 `window` 对象 | 改为 `@click="handlePrint"` + `function handlePrint() { window.print() }` 方法调用 | 7 个 Vue 文件 |
| 2 | 单位下拉 label 使用简称 | `get_accounts_tree` 返回 `entity_name=ent.short_name` | 扩展返回 4 字段：`entity_name`(简称优先/兼容)、`entity_full_name`(全称)、`entity_short_name`(简称)、`entity_display_name`(UI展示) | `master_data_service.py`, `schemas.py` |
| 3 | 停用账户仍在业务页下拉显示 | `get_accounts_tree` 未过滤 `Account.status` | 添加 `Account.status == "enabled"` 过滤条件 | `master_data_service.py` |
| 4 | `/agents/ag_42nugg` 无法加载 | `Number("ag_42nugg")` → `NaN`，`loadAgent()` 提前返回 | 后端参数改为 `str` 类型，先尝试 `int` 转换再回退 `agent_code` 查询；前端直接传原始 ID | `agent.py`, `AgentDetail.vue` |

## Issue 1：打印按钮修复

### 修改文件（7 个）

| 文件 | 行号 | 变更 |
|------|------|------|
| `views/AccountBalance.vue` | 16, 120 | `window.print()` → `handlePrint` |
| `views/DailyReport.vue` | 16, 142 | 同上 |
| `views/ExpenseList.vue` | 16, 120 | 同上 |
| `views/IncomeList.vue` | 16, 120 | 同上 |
| `views/CashJournal.vue` | 16, 422 | 同上 |
| `views/BaseDataTable.vue` | 20, 177 | 同上 |
| `composables/TemplateReport.vue` | 25, 133 | 同上 |

### 验证

- CDP 测试：拦截 `window.print` 后点击按钮 → `printTriggered: true`
- 真实鼠标事件序列（pointerdown → mousedown → pointerup → mouseup → click）→ `printTriggered: true`

## Issue 2：主数据字段语义澄清

### 修改

`backend/db/schemas.py` — EntityTreeGroup 新增 3 个字段：
```python
class EntityTreeGroup(BaseModel):
    entity_id: int
    entity_name: str           # 向后兼容，当前语义=简称优先
    entity_full_name: str      # 单位全称
    entity_short_name: str     # 单位简称
    entity_display_name: str   # UI 展示优先字段，当前=简称优先
    accounts: List[AccountTreeNode] = []
```

`backend/services/master_data_service.py`：
```python
entity_name=ent.short_name or ent.name,         # 向后兼容：简称优先
entity_full_name=ent.name,                       # 全称
entity_short_name=ent.short_name or "",          # 简称
entity_display_name=ent.short_name or ent.name,  # UI 展示
```

### 验证

API `/api/accounts/tree` 返回：
```json
{
  "entity_name": "养护",
  "entity_full_name": "山西喜跃发道路建设养护集团有限公司",
  "entity_short_name": "养护",
  "entity_display_name": "养护"
}
```

## Issue 3：停用账户过滤

### 修改

`backend/services/master_data_service.py` 第 306 行：
```python
# 之前
.filter(Account.entity_id == ent.id)
# 之后
.filter(Account.entity_id == ent.id, Account.status == "enabled")
```

### 验证

Entity id=275（山西路众道桥有限公司）：
- 修复前：8 个账户（含 1 个 disabled）
- 修复后：7 个账户（仅 enabled）

API 返回所有 51 个单位的账户全部 status="enabled"，无 disabled 账户混入。

## Issue 4：Agent URL 支持 agent_code

### 后端修改

`backend/api/agent.py` 第 108-120 行：
```python
# 之前
def get_agent(agent_id: int, ...)

# 之后
def get_agent(agent_id: str, ...):
    try:
        numeric_id = int(agent_id)
        agent = db.query(Agent).filter(Agent.id == numeric_id).first()
    except (ValueError, TypeError):
        agent = db.query(Agent).filter(Agent.agent_code == agent_id).first()
```

### 前端修改

`frontend/src/views/AgentDetail.vue` 第 98-106 行：
```javascript
// 之前
const id = Number(route.params.id)
if (!id) return

// 之后
const rawId = route.params.id
if (!rawId) return
agent.value = await agentsStore.getAgent(rawId)
const id = agent.value.id  // 从返回数据中获取数字 ID
```

### 验证

- `GET /api/agent/agents/1` → code=0, agent_code="ag_kbdpch", name="出纳助手"
- `GET /api/agent/agents/ag_42nugg` → code=0, id=5, name="IT助手"
- `GET /api/agent/agents/nonexist` → code=2001, "智能体不存在"

## 影响范围

- **报表页（6 个）+ TemplateReport composable**：打印按钮行为一致
- **所有使用 `getAccountsTree` 的页面（10 个）**：单位下拉 label 显示全称（entity_full_name），搜索覆盖全称+简称+兼容字段，排除停用账户
- **Agent 详情页**：URL 兼容数字 ID 和 agent_code
- **向后兼容**：数字 ID 路由（如 `/agents/5`）不受影响，`agent_code` 路由为新增能力

## 验证方法总结

| 验证项 | 方法 | 结果 |
|--------|------|------|
| 打印按钮 | CDP 拦截 window.print + 真实鼠标事件 | 通过 |
| 字段契约 | curl API 返回 4 字段 | 通过 |
| 停用过滤 | curl API 检查 accounts status | 通过 |
| Agent URL | curl 数字 ID 和 agent_code | 通过 |
| 前端构建 | `npx vite build` | 通过 |
