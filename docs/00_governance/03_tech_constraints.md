# 03 · 技术约束

本文档定义当前项目的技术栈、分层规则和工程边界。它约束“怎么实现”，不替代产品链路文档。

## 1. 技术栈

未经用户明确同意，不得更换主技术栈。

| 层级 | 技术 |
| --- | --- |
| 后端 | Python、FastAPI、SQLAlchemy、SQLite、Alembic |
| 数据处理 | openpyxl、Polars、xlrd |
| 前端 | Vue、Vite、Ant Design Vue、ECharts、Pinia、Vue Router、Axios |
| 认证 | JWT、本地单用户 |
| 打包 | 前端静态构建、后端挂载、PyInstaller |
| 测试 | pytest、前端构建、浏览器验证、guard |

## 2. 后端分层

```text
backend/
  api/       路由层：参数校验、调用 service、统一响应
  services/ 业务层：主业务规则
  db/       ORM、schema、数据库表
  core/     跨模块确定性能力和安全守卫
  agents/   Agent 运行时、工具、Skill、Memory、规则创建
```

规则：

- 路由层不写业务逻辑。
- 业务规则放在 service。
- 数据库访问优先走 ORM。
- 裸 SQL 只允许出现在迁移、备份或经过审计的底层工具中。
- Agent 创建规则，确定性 runtime 执行已审核规则。

## 3. 前端分层

```text
frontend/src/
  views/       页面
  components/ 复用组件
  api/        API client
  stores/     Pinia 状态
  router/     路由
  styles/     全局样式
  utils/      工具函数
```

规则：

- 用户界面以表格、上传、预览、确认、导出为核心。
- 所有用户可见文案和错误提示使用中文。
- 不引入第二套主 UI 组件库。
- 页面按钮必须串起真实工作流，不能只调用孤立旧接口。
- 不暴露 JSON、正则、SQL、字段映射编辑给普通用户。

## 4. Agent 与规则边界

Agent 可以：

- 讨论业务含义。
- 分析样本。
- 创建 Parser 或 Rule 草稿。
- 创建或维护 Skill。
- 保存可审计 Memory。
- 解释异常。

Agent 不可以：

- 绕过审核写正式数据。
- 在导入、入库、报表生成阶段调用 LLM。
- 把一次性聊天结果当长期规则。
- 把敏感流水明细隐藏写入 Memory。

## 5. 数据流约束

`fund_events` 是报表唯一流水事实源。

银行流水、手工流水、模板报表必须收敛到：

```text
上传或录入 -> 匹配或创建规则 -> 预览 -> 用户确认 -> fund_events -> 报表
```

每条结果必须可追溯到：

- 来源文件或录入批次。
- Parser 或 Rule。
- 用户确认记录。
- 原始行快照或模板来源。

## 6. 目录边界

- `backend/data/` 是本地运行数据，不应提交数据库、上传文件、生成报表、日志。
- `agents/ag_*/` 是用户运行时 Agent 数据，不作为项目默认架构权威。
- `agents/system/skills/` 是系统技能入口，应使用 `SKILL.md` 标准。
- `new/` 是参考源码和研究资料，不参与开发权威排序。
- `product/` 如存在，不得混入文档、fixtures、运行数据或测试产物。

## 7. 变更约束

- 不创建平行实现绕过旧缺陷。
- 不新增版本化概念名称。
- 不静默修改冻结契约。
- Schema 变更必须有迁移方案。
- API 合并或删除必须有调用方盘点。
- 用户已有数据必须保留或提供迁移路径。

## 8. 验证约束

每个阶段至少给出：

- 变更文件清单。
- 后端测试结果。
- 前端构建结果。
- guard 结果。
- 浏览器主链路验证结果。
- 已知未解决冲突。
