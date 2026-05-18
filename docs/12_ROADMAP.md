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
