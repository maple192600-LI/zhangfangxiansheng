# 项目状态总览

## 定位

账房先生 (ZhangFang)  — 面向中国财务人员的本地部署 Agent 驱动财务工作台。

## 关键事实数字

| 维度                                  | 数字                         |
| ----------------------------------- | -------------------------- |
| 前端 placeholder route                | 26                         |
| 前端 implemented route import entries | 33                         |
| 前端 `.vue` 文件                        | 40                         |
| 后端 API 模块                           | 22                         |
| 后端 service 模块                       | 25                         |
| ORM 表                               | 28                         |
| API inventory（effective path）       | 165 endpoints, 0 duplicate |

## 当前可用能力

- 主数据中心（板块/法人/账户/银行 CRUD + 批量导入）
- 银行流水导入（上传 → Parser 识别 → 解析预览 → 上传结果预览统一校验和提交）
- 手工流水快速录入（写入待确认 FundEvent，进入上传结果预览统一校验和提交）
- 手工流水 Excel 上传（上传 → 上传结果预览统一解析/校验/提交）
- 日报/报表生成（多个报表类型，硬编码模板填充）
- 导出打印
- 基础看板
- 备份/恢复/数据清理
- 操作日志
- AI 配置管理（多 provider、多模型）
- Agent 系统（通用 Agent、会话、消息、工具调用、记忆、技能）
- Artifact CRUD（ParserArtifact / RuleArtifact 的创建、审核、激活）
- Workflow 画布（Vue Flow 图形编辑器）
- 用户认证（登录、改密、JWT）

## 当前阻断能力

| 阻断点          | 位置                                     | 影响                         |
| ------------ | -------------------------------------- | -------------------------- |
| `run_parser` | `backend/core/artifact_runtime.py:109` | ParserArtifact 驱动的解析执行路径阻断 |
| `run_rule`   | `backend/core/artifact_runtime.py:153` | RuleArtifact 驱动的规则执行路径阻断   |

ParserArtifact 和 RuleArtifact 可以创建和审核，但无法被 artifact runtime 执行。

## Placeholder / 待清理能力

26 个 placeholder 路由中：

- 票据中心（4 个 OCR 路由）— V1 禁止
- 贷款管理（4 个）— V1 禁止
- 预算管理（1 个）— V1 禁止
- AI 智能体细分（7 个）— 待产品决策
- 数据/规则/权限中心（10 个）— 待产品决策

## 文档治理状态

文档体系已完成重建和清理。旧文档污染源已物理删除，当前 `docs/` 下只有 14 个 active docs 和 4 个受保护契约文件。

***

**校准来源：** `frontend/src/router/index.js`、`backend/main.py`、`backend/api/`、`backend/services/`、`backend/db/tables.py`、`backend/core/artifact_runtime.py`、`tools/guards/check_api_inventory.py --list`
**最后校准：** 2026-05-18
