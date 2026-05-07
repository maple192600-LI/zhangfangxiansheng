# 14 · 基础数据表与报表执行规范

## 1. 模块目标

基础数据表负责把已确认的银行流水和手工流水统一展示为 `fund_events`。报表模块负责从 `fund_events` 和已审核 Rule 生成日报、余额表、日记账和明细表。

报表生成阶段不得读取原始上传文件，不得调用 LLM，不得绕过 `fund_events`。

## 2. 输入来源

允许进入基础数据表的来源只有：

- 银行流水确认入库结果。
- 手工快速录入确认入库结果。
- 手工 Excel 上传确认入库结果。

所有来源必须先完成预览、异常维护和用户确认，再写入 `fund_events`。

## 3. 主链路

```text
已确认导入批次
  -> fund_events
  -> 基础数据表展示
  -> 匹配已审核 Rule
  -> 选择日期范围和报表类型
  -> 确定性生成报表
  -> 预览
  -> 导出
```

## 4. 页面职责

基础数据表页面：`frontend/src/views/BaseDataTable.vue`

报表页面当前包括：

- `frontend/src/views/DailyReport.vue`
- `frontend/src/views/CashJournal.vue`
- `frontend/src/views/AccountBalance.vue`
- `frontend/src/views/IncomeList.vue`
- `frontend/src/views/ExpenseList.vue`

后续前端收束时，报表页面可以合并为统一报表工作台，但不得改变报表只从 `fund_events` 和 Rule 取数的原则。

页面必须支持：

- 按日期、主体、账户、方向、来源批次筛选基础数据。
- 查看来源文件、批次、Parser、用户确认记录。
- 选择报表类型和日期范围。
- 预览报表结果。
- 导出 Excel。

页面不得要求用户写 SQL、公式、字段映射或 JSON。

## 5. 报表 Rule

Rule 是报表生成的唯一长期规则资产。

Rule 至少描述：

- 适用报表类型。
- 所需字段。
- 筛选条件。
- 分组和排序方式。
- 汇总口径。
- 模板填充位置或导出格式。
- 样本校验结果和用户确认记录。

模板首次上传时，Agent 可以帮助创建 Rule 草稿。Rule 经用户审核后进入规则中心。日常生成报表时，只执行已审核 Rule。

## 6. 报表类型

当前范围内的报表类型：

| 报表 | 取数口径 |
| --- | --- |
| 基础数据表 | 展示 `fund_events` 明细。 |
| 现金日记账 | 按账户和日期展示收入、支出、余额变化。 |
| 账户余额表 | 按主体和账户汇总期初、本期收入、本期支出、期末余额。 |
| 收入明细表 | 仅展示收入方向明细。 |
| 支出明细表 | 仅展示支出方向明细。 |
| 资金日报 | 按日期和主体汇总收入、支出、净变动和日终余额。 |

## 7. 滚动余额

滚动余额必须基于有效 `fund_events` 计算。

计算原则：

- 以账户期初余额和期初日期作为起点。
- 只计算 `parse_status = 'valid'` 的资金事件。
- 按业务日期和稳定行序排序。
- 收入增加余额，支出减少余额。
- 回滚、手工维护、重新提交批次后必须支持重新计算。

如果导入文件提供期末余额，系统可以用它做校验。校验不一致时进入异常状态，不得静默覆盖。

## 8. 后端职责

主要文件：

- `backend/api/base_data.py`
- `backend/api/reports.py`
- `backend/services/base_data_service.py`
- `backend/services/report_service.py`
- `backend/core/artifact_runtime.py`

职责划分：

- API 层负责筛选参数、报表类型、导出请求和响应格式。
- Service 层负责查询 `fund_events`、计算余额、生成报表数据。
- Artifact runtime 执行已审核 Rule。
- Agent 只负责创建、解释或修正 Rule 草稿。

## 9. API 方向

目标 API 应围绕以下动作收敛：

- 查询基础数据。
- 重算账户滚动余额。
- 查询可用报表类型和 Rule。
- 生成报表预览。
- 导出报表。
- 查询报表生成记录。

旧的按页面分散取数、直接从原始上传行生成报表、绕开 Rule 的入口属于迁移对象。

## 10. 完成标准

- 银行流水和手工流水确认后都能进入 `fund_events`。
- 基础数据表能展示来源、批次、Parser、确认记录。
- 报表只从 `fund_events` 和已审核 Rule 取数。
- 报表支持日期范围筛选和 Excel 导出。
- 滚动余额可重算、可校验、可追溯。
- 确定性报表生成阶段不调用 LLM。
