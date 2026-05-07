# 18 · 代码旧入口迁移清单

本文档记录当前代码中仍然存在的旧新并存点。它是迁移清单，不是允许继续使用旧入口的授权。

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
