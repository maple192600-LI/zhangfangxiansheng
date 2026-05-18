# 路线图

## 当前优先级

| 优先级 | 方向 | 说明 |
|--------|------|------|
| 1 | 文档和 guard 治理 | 重建文档体系、修正 guard、清理旧污染 |
| 2 | Artifact Runtime | 实现 `run_parser` 和 `run_rule` |
| 3 | 导入闭环 | 银行导入和手工 Excel 走 artifact runtime 执行 |
| 4 | 前端 placeholder 清理 | 移除 V1 禁止的 placeholder 路由 |

## 阶段

### 文档和 guard 治理（进行中）

- [x] Step 0：事实基线审计
- [x] Step 1：重写入口文档（README.md、AGENTS.md、CLAUDE.md、docs/README.md）
- [x] Step 2：修正 API inventory guard（effective path + duplicate detection）
- [x] Step 3：创建新 active documentation set（14 个文档）+ 文档生命周期治理补强
- [x] Step 4：清理保留的契约文件
- [x] Step 5：物理删除旧文档污染源
- [ ] Step 6：全量验证
- [ ] 后续：实现 `tools/guards/check_docs_governance.py`（禁止词、旧目录入口、缺少校准 footer、未登记新文档）

每完成一个功能阶段，必须更新本路线图状态或明确无需更新。

### Artifact Runtime 实现

- [x] Phase E1：`run_parser` 实现（确定性解析执行器）
- [ ] Phase H1：`run_rule` 实现（确定性规则执行器）

### 银行通用识别

Parser Runtime（Phase E1）只解决"代码能不能执行"。银行通用识别是独立能力，尚未实现。完整契约见 [`14_BANK_IMPORT_GENERALIZATION.md`](14_BANK_IMPORT_GENERALIZATION.md)。

- [x] Step 09B：建立银行通用识别 + 主数据归属匹配能力契约和文档
- [x] Step 09C：银行文件识别 + 身份线索提取服务（后端基础完成，尚未接入导入流程）
- [x] Step 09C2：加固银行身份匹配（移除硬编码银行词典、DB 驱动归一化、AccountAlias、收紧 fallback）
- [x] Step 09C3：银行原始文本候选收集 + DB 驱动短名/bank_code 识别
- [ ] Step 09D：ParserArtifact bank/format 级匹配（替代 account_code 匹配）
- [x] Step 09E：主数据账户/单位归属匹配服务（后端基础完成，尚未接入导入流程）
- [ ] Step 09F：parser 硬编码 guard
- [ ] Step 09G：前端展示银行识别和账户归属匹配结果
- [ ] Step 09H：多银行/多账户/多线索场景端到端验收

### 导入闭环

- [ ] 银行导入走 `run_parser` 路径
- [ ] 手工 Excel 走 `run_parser` 路径
- [ ] 报表生成走 `run_rule` 路径

### 前端 placeholder 清理

- [ ] 移除 V1 禁止的 placeholder 路由（OCR、贷款、预算，共 9 个）
- [ ] 决策其余 17 个 placeholder 路由的取舍

### 最终验收

- [ ] 全量 guard 通过
- [ ] 前端构建成功
- [ ] 浏览器验证核心流程

---
**校准来源：** `ai_coordination/doc-rebuild/00_master_plan.md`、`backend/core/artifact_runtime.py`
**最后校准：** 2026-05-17
