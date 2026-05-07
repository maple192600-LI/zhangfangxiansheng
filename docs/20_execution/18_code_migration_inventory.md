# 18 · 代码旧入口迁移清单

本文档记录当前代码中仍然存在的旧新并存点。它是迁移清单，不是允许继续使用旧入口的授权。

本清单同时吸收全项目扫描发现和前端按钮、功能取舍审计。前端专项不得覆盖或降低后端、安全、Agent、数据库、部署、性能、可访问性等问题的优先级。

## 1. 迁移原则

- 同一能力最终只能保留一个入口。
- 旧入口先标记、再迁移调用方、再删除或兼容转发。
- 不新增平行实现绕过旧缺陷。
- 用户数据表重命名必须有迁移脚本和回滚方案。
- 每完成一项迁移，必须更新测试、guard 和浏览器验收记录。

## 2. 银行导入旧入口

| 旧点位 | 文件 | 处理方向 |
| --- | --- | --- |
| 映射提交接口 | `backend/api/bank_import.py` | 迁移到“匹配 Parser -> 预览 -> 确认入库”工作流后删除或兼容转发。 |
| 智能列映射接口 | `backend/api/bank_import.py` | 迁移到 Agent 创建 Parser 草稿流程。 |
| 旧模板模型 | `backend/db/tables.py`、`backend/services/bank_import_service.py` | 将规则中心展示迁移到 Parser artifact。 |
| 旧规则页面 | `frontend/src/views/BankRule.vue` | 改为规则中心的银行 Parser 视图。 |
| 前端旧提交调用 | `frontend/src/views/BankImport.vue` | 改为调用 Parser 匹配、预览和确认入库接口。 |

完成标准：

- 日常银行导入不走字段映射提交。
- 中国银行同格式不同账户可复用同一 Parser。
- 入库记录能追溯 Parser、文件、批次、用户确认。

## 3. 手工流水旧入口

| 旧点位 | 文件 | 处理方向 |
| --- | --- | --- |
| 智能列映射接口 | `backend/api/manual_flow.py` | 迁移到 Agent 创建手工 Parser 或模板规则流程。 |
| 上传后直接映射预览 | `backend/services/manual_flow_service.py` | 改为规则匹配、预览、异常维护、确认入库。 |
| 前端旧解析入口 | 手工流水相关页面和 API client | 改为统一规则中心链路。 |

完成标准：

- 快速录入和 Excel 上传最终都进入 `fund_events`。
- 用户不写映射。
- 异常行进入维护，不污染正式结果。

## 4. Artifact runtime 缺口

| 点位 | 文件 | 现状 | 处理方向 |
| --- | --- | --- | --- |
| Parser 执行 | `backend/core/artifact_runtime.py` | 当前未真正执行 Parser artifact | 实现已审核 Parser 的确定性执行。 |
| Rule 执行 | `backend/core/artifact_runtime.py` | 当前未真正执行 Rule artifact | 实现已审核 Rule 的确定性报表生成。 |
| 占位 Parser 草稿 | `backend/agents/fund/harness.py` | 可能只生成占位内容 | 改为能产出可校验草稿或明确失败原因。 |

完成标准：

- 已审核 Parser/Rule 可重复执行。
- 执行阶段不调用 LLM。
- 失败时进入异常或规则修正流程。

## 5. Agent、Skill、Memory 命名迁移

| 点位 | 文件 | 处理方向 |
| --- | --- | --- |
| 旧数据库表名 | `backend/db/tables.py` | 设计迁移脚本，目标为稳定概念命名。 |
| 旧 SQL 引用 | `backend/api/backup.py` | 改为 ORM 或迁移后的稳定表名。 |
| 旧 ORM 别名 | `backend/db/tables.py` | 删除兼容别名前必须完成调用方迁移。 |

完成标准：

- 代码层稳定使用 Agent、Skill、Memory。
- 数据迁移不丢用户会话、技能、记忆。
- 备份清理逻辑不再写裸旧表名。

## 6. API 端点收敛

当前 guard 迁移基线为 152，长期目标为 42。

优先收敛方向：

- 合并 Agent 管理、Skill 管理、Memory 管理的细碎入口。
- 合并主数据批量与单项操作的重复入口。
- 删除旧解析、旧模板、旧映射入口。
- 将报表查询与生成入口按 Rule 工作流统一。
- 更新 API 契约前先完成调用方盘点。

完成标准：

- `tools/guards/check_api_inventory.py` 通过。
- 不允许端点数量超过当前迁移基线；每完成一批收敛后下调基线。
- 前端 API client 不再调用已废弃路径。
- 浏览器主链路仍可跑通。

## 7. 第一批执行顺序

1. 银行导入：先让 Parser artifact 成为唯一长期规则资产。
2. Artifact runtime：实现 Parser 执行，跑通预览和入库。
3. 规则中心：把旧银行模板页面迁移为 Parser/Rule 资产视图。
4. 手工流水：迁移旧智能映射入口。
5. 报表：实现 Rule artifact 生成和确定性执行。
6. API：按真实调用方删除或合并旧入口。

## 8. 全项目扫描问题并入

### 8.1 覆盖范围

以下类别全部进入整改范围，不得只修前端或只修 Agent 主链路：

| 类别 | 主题 | 决策 |
| --- | --- | --- |
| A | 金额精度 | P0/P1。后端 Decimal、前端金额展示和合计不使用裸浮点。 |
| B | 时区和日期 | P0。替换前端 UTC 日期默认值，统一后端时间策略。 |
| C | SSE / Agent 聊天可靠性 | P0/P1。支持取消、超时、去重、卸载清理和切换保护。 |
| D | 安全漏洞 | P0/P1。沙箱、Skill 写入、LIKE、错误泄露、默认密码日志全部修。 |
| E、O | Agent Runtime 内部缺陷 | P0/P1。缺失 import、上下文持久化、消息序列、缓存清理。 |
| F、N、W | 数据完整性、服务层、并发 | P0/P1。导入、提交、回滚、余额重建必须事务化和可追溯。 |
| G | 文件解析兼容性 | P0/P1。CSV GBK fallback、多 sheet、中文日期、空文件处理。 |
| H、K、L、M、M4、M5 | 前端交互、状态、路由、上传、加载 | P0/P1。按钮链路、状态一致性和真实工作流优先。 |
| I | Agent/Prompt 系统设计 | P1。提示词注入、中文记忆检索、截断策略、记忆沉淀规则。 |
| P、Q | Agent 工具、Skill、Memory | P1。工具权限、安全扫描、原子写入、路径可靠性。 |
| R、S、T、U | 索引、迁移、查询性能、连接管理 | P1/P2。支持真实数据量和从零部署。 |
| X、Y | 备份恢复、部署启动 | P0/P1。恢复必须真正生效，启动脚本不能误杀或硬编码开发模式。 |
| Z、AA、AB、AC | 前端构建、可访问性、响应式、本地化 | P2。开源交付和目标用户体验必须达标。 |

### 8.2 立即修复队列

这些项目优先级高于功能扩张：

1. 金额精度：清点所有后端 `float()` 汇总、前端 `reduce` 金额合计、`fmtAmt` 对异常值的处理。
2. 日期时区：新增本地日期工具，替换所有 `toISOString().slice(0, 10)`。
3. SSE 生命周期：`sendMessageStream` 必须返回取消函数；`ChatPanel`、`AgentDetail` 在卸载、切换、删除时关闭连接。
4. 鉴权：路由守卫不能只看 token 字符串，首屏和 401 拦截必须统一。
5. 文件上传安全：所有上传接口限制文件名、大小、类型，并有清理策略。
6. 备份恢复可靠性：恢复后重建数据库连接，验证备份完整性。
7. Schema 迁移：新增正式 Alembic 迁移替代 `_patch_schema()` 漏洞。
8. 银行导入：删除前端对 `/bank-import/commit-by-mapping` 的依赖，改为 Parser artifact 工作流。
9. 规则中心：删除用户手写 JSON 映射入口，改为 Agent 创建、用户审核、资产启停。
10. 前端导航：隐藏或删除 26 个 Placeholder 路由，避免开源用户看到不可用入口。

### 8.3 前端功能取舍清单

当前静态盘点结果：

- `frontend/src/router/index.js` 中共有 60 个命名路由，其中 26 个指向 `Placeholder.vue`。
- 前端 Vue 文件中约有 242 个按钮或点击触点。
- `alert()` / `confirm()` 约 100 处，提示和危险确认分散。
- `toISOString().slice(0, 10)` 日期默认值 8 处，存在中国凌晨日期错误风险。
- 最大前端文件包括 `AccountManage.vue` 1417 行、`ChatPanel.vue` 854 行、`SkillsPanel.vue` 599 行、`AIConfig.vue` 562 行、`SettingsPanel.vue` 491 行、`CashJournal.vue` 465 行。

| 当前功能或页面 | 决策 | 说明 |
| --- | --- | --- |
| `Login.vue`、修改密码、退出 | 保留 | 必须补 token 有效性检查。 |
| `HomeDashboard.vue` | 保留 | 首页只做工作总览、待办、异常、最近结果。 |
| `HomeTasks.vue`、`HomeQuick.vue`、`HomeSystem.vue` | 合并 | 合并到首页卡片，不保持独立路线。 |
| `AccountManage.vue` | 保留并拆分 | 主数据是必须能力，但单文件过大，需要拆为组织、单位、账户、导入子组件。 |
| `BankImport.vue` | 保留并重接 | 从旧模板映射改为 Parser 匹配、创建、审核、预览、入库。 |
| `ManualFlow.vue` | 保留并重接 | 快速录入和上传都进入统一预览和异常维护。 |
| `ManualMaintenance.vue`、`UploadPreview.vue` | 合并 | 作为手工流水步骤，不再做独立导航页。 |
| `BaseDataTable.vue` | 保留 | `fund_events` 可视化事实源。 |
| 报表页面群 | 合并 | 合并为统一报表工作台，报表类型由 Rule 和模板驱动。 |
| `BankRule.vue`、`ReportTemplate.vue`、`AgentReview.vue` | 合并重做 | 形成统一规则中心和审核中心，不暴露 JSON、字段映射、代码编辑。 |
| `AgentDetail.vue` 及面板 | 保留但收束 | Agent 只服务规则创建、解释、维护和学习。 |
| `AIConfig.vue` | 保留 | 仅服务 Agent 创建规则阶段。 |
| `SystemMaintenance.vue`、`OperationLog.vue` | 保留并合并 | 备份恢复、数据清理、日志统一在系统维护。 |
| 票据、贷款、预算、权限、Agent 空分类、规则空分类、部门信息 | 隐藏或删除 | 当前范围外或只是 Placeholder。 |
| `BankManage.vue`、`BackupRestore.vue`、`DataCleanup.vue` 等未路由旧页面 | 删除或归档 | 不允许未来被误接回主导航。 |

### 8.4 点击路径验收要求

前端整改不能只删菜单。每个保留按钮必须完成点击路径审计：

1. 标出按钮文案、所在组件、handler、调用 API。
2. 说明 handler 读取和写入哪些本地状态或 Pinia store。
3. 检查后续调用是否撤销前面状态。
4. 检查失败时是否保留旧数据、展示错误、允许重试。
5. 检查同一动作是否有重复入口或旧 API。
6. 对导入、确认、删除、恢复、清理等危险操作进行浏览器验证。
