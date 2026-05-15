# 工作台高级表格底座技术验证

> 文档版本：2026-05-15 | 状态：实验验证阶段

## 1. 实验目标

在浏览器端验证两件事：

1. **Tabulator** 能否作为 Vue 3 + keep-alive 场景下的高级表格底座（排序、筛选、分页、虚拟滚动）
2. **DuckDB-WASM** 能否在浏览器端做临时 SQL 分析（不写正式数据库）

验证完成后，这些能力可供后续正式页面（导入预览、临时数据分析等）复用。

## 2. 当前能力

| 能力 | 状态 | 说明 |
|------|------|------|
| Tabulator 高级表格组件 | 已验证 | AdvancedDataTable.vue |
| 排序 / 筛选 / 分页 | 已验证 | Tabulator 内置 |
| 列宽调整 / 列拖拽 | 已验证 | 通过 props 控制 |
| 行选择 | 已验证 | 通过 enableSelection prop |
| DuckDB 浏览器端 SQL | 已验证 | 仅允许 SELECT/WITH/DESCRIBE/SUMMARIZE |
| 同名表数据替换 | 已验证 | replaceJsonRows 先 DROP 再注册 |
| keep-alive 兼容 | 已验证 | composable 处理 onActivated |
| 组件卸载清理 | 已验证 | onUnmounted 销毁 Tabulator + 关闭 DuckDB |

## 3. 当前边界

- **不接入正式业务数据** — 实验页使用 mock 数据
- **不写入正式数据库** — DuckDB 查询结果不持久化
- **不替换现有报表页面** — 正式页面仍用手写 `<table>`
- **不加入正式导航** — 通过 URL 直接访问
- **不暴露自由 SQL 输入框** — 仅提供预设查询
- **不代表正式报表结论** — 查询结果仅供技术验证

## 4. 文件位置

### Tabulator 封装

| 文件 | 作用 |
|------|------|
| `frontend/src/composables/useTabulatorTable.js` | Tabulator 生命周期管理 composable |
| `frontend/src/components/workbench/AdvancedDataTable.vue` | 可复用高级表格组件 |
| `frontend/src/styles/tabulator-theme.css` | Tabulator 主题覆盖（对齐项目设计体系） |

### DuckDB 封装

| 文件 | 作用 |
|------|------|
| `frontend/src/services/duckdb/index.js` | DuckDB 懒初始化单例服务 |

### 实验页

| 文件 | 作用 |
|------|------|
| `frontend/src/views/workbench/WorkbenchTableLab.vue` | 隔离验证页 |
| `frontend/src/views/workbench/mockTransactionRows.js` | Mock 数据生成器 |

## 5. DuckDB 为什么只能做临时分析

- DuckDB 实例运行在浏览器 Web Worker 中，页面关闭即消失
- `queryReadonly` 只允许 SELECT / WITH / DESCRIBE / SUMMARIZE，禁止写入 SQL
- 数据通过 `replaceJsonRows` 注册，每次替换旧表（DROP TABLE IF EXISTS）
- 不与后端 SQLite 通信，不影响任何正式数据

## 6. 如何访问实验页

登录后浏览器地址栏输入：

```
http://localhost:5180/workbench/table-lab
```

该路由不在侧边栏导航中显示。

## 7. 如何验证

1. 打开实验页，确认 50 行表格正常显示
2. 切换到 5,000 / 50,000 行，确认不崩溃
3. 点击"启用 DuckDB 分析"，等待初始化完成
4. 执行"总行数"查询，确认结果等于当前行数
5. 切换行数后再次执行"总行数"，确认结果更新
6. 执行其他预设查询，确认有结果返回
7. 点击"关闭 DuckDB"，确认状态清理
8. 离开页面再回来，确认无控制台错误

## 8. 已知风险

| 风险 | 影响 | 建议 |
|------|------|------|
| DuckDB-WASM 使用 dev 版本 (1.33.1-dev45.0) | API 可能在正式版中变化 | 合并 main 前确认是否有对应稳定版 |
| Tabulator 体积较大 (~649KB gzipped 151KB) | 首次加载实验页有延迟 | 路由级懒加载已隔离，不影响其他页面 |
| 50,000 行 DuckDB 数据注册较慢 | 大数据量同步耗时明显 | 实际业务场景应考虑分批或增量 |
| DuckDB WASM 加载依赖浏览器兼容性 | 旧浏览器可能不支持 | 目标用户为 Chrome，风险可控 |

## 9. 后续正式接入条件

正式使用 AdvancedDataTable / DuckDB 服务前，需要满足：

1. 确认 DuckDB-WASM 有对应稳定版本或锁定 dev 版本 hash
2. 确认 Tabulator 在目标浏览器中的性能表现满足业务需求
3. 设计正式的数据注册流程（不能依赖前端 JSON 全量注册）
4. 定义 AdvancedDataTable 的列配置与后端字段的映射规范
5. 通过代码评审确认组件接口稳定性
