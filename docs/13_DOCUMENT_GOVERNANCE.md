# 文档治理

## 文档真相源原则

- **代码是事实**，文档描述意图
- 如果文档与代码冲突，以代码为准，然后修正文档
- 技术栈真相源：`frontend/package.json`、`backend/requirements.txt`

## Active Docs 主集合

`docs/00_PROJECT_STATE.md` 到 `docs/13_DOCUMENT_GOVERNANCE.md` 是稳定的 active docs 主集合，共 14 个文档。

- 默认不新增顶层文档
- 新需求、新功能、新修复优先更新既有文档中的相关文档
- 新增永久文档必须满足：
  - 现有 14 个文档无法容纳
  - 有明确长期读者
  - 有维护责任人
  - 在 `docs/README.md` 增加入口
  - 写明校准来源和最后校准日期
  - 经用户明确确认

## 新文档规则

- 新文档必须有校准来源和最后校准日期（文档底部）
- 每个文档应短而准，不写历史流水账、旧 PR 日志、泛泛工程鸡汤

## 旧文档处理

- 旧文档污染源已物理删除；后续不得重新引入 archive/legacy docs
- 不创建 archive 目录
- 不以"AI Coding 工具默认不读旧目录"作为保留旧文档的变通理由
- 原因：AI Coding 工具读取行为不可完全控制，旧文档留在仓库里就会继续污染执行

## 污染禁止

新文档中不允许出现旧技术栈名称（实际使用 naive-ui）、未实施的 OCR 引擎、未安装的打包工具、`new/` 旧路径引用、或 archive 目录路径。

## 防止硬编码复发

文档中引用数字时，必须遵守以下规则：

| 数据类型 | 唯一真相源 | 写法要求 |
|----------|-----------|----------|
| 技术栈 | `frontend/package.json`、`backend/requirements.txt` | 列出依赖和版本 |
| API 端点数量 | `python tools/guards/check_api_inventory.py --list` | 写"当前为 N"，不写固定上限 |
| 路由/页面数量 | `frontend/src/router/index.js`、`frontend/src/views/` 扫描 | 写"当前为 N"，不写固定上限 |
| ORM 表数量 | `backend/db/tables.py` | 写"当前为 N"，不写固定上限 |

规则：
- 不允许写无法验证的"固定数字上限"
- 如果某个数字只是当前观测值，写成"当前为 N"，不能写成架构限制
- 后续应新增 `tools/guards/check_docs_governance.py`，扫描：禁止词、旧目录入口、缺少校准 footer、`docs/README.md` 中未登记的新顶层文档

## 文档更新责任

- 谁改代码/接口/数据流/页面/业务规则，谁负责同步相关文档
- Claude Code 执行任务时，结果报告必须包含"文档影响判断"：
  - 无需更新文档，并说明原因
  - 已更新哪些 active docs
  - 需要用户/Codex 决策后再更新
- 用户只负责产品/范围/取舍确认，不负责手工追文档

## AI Coding 入口

- `docs/README.md` 是唯一文档入口
- 不要在多个文件中建立竞争性入口
- 所有任务类型导航从 `docs/README.md` 出发

## 暂时保留的契约文件

以下文件暂时保留，修改或引用前必须与代码核对：
- `docs/00_governance/00_project_constitution.md`（被 `contracts.lock` SHA256 锁定）
- `docs/30_contracts/20_database_schema.md`
- `docs/30_contracts/23_api_contracts.md`
- `docs/30_contracts/25_primitives_whitelist.md`

---
**校准来源：** `AGENTS.md`、`frontend/package.json`、`backend/requirements.txt`、`tools/guards/check_api_inventory.py --list`
**最后校准：** 2026-05-17
