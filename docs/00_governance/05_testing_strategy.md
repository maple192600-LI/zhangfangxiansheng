# 05 · 测试与验收规范

本项目的测试目标是证明主工作流可用、数据可追溯、Agent 不越权、确定性执行不调用 LLM。

## 测试分层

| 层级 | 路径 | 目标 |
| --- | --- | --- |
| 单元测试 | `tests/backend/`、`tests/fund/` | 验证 service、基元、Parser/Rule runtime |
| 集成测试 | `tests/backend/services/` | 验证上传、预览、确认、入库、报表服务 |
| 端到端测试 | `tests/e2e/` | 验证浏览器主链路 |
| 守卫脚本 | `tools/guards/` | 阻止契约漂移、平行实现、运行时 LLM、脏目录提交 |

## 必验主链路

```text
上传银行流水
  -> 命中已有 Parser 或创建 Parser 草稿
  -> 用户审核接受
  -> 预览基础数据表行
  -> 确认入库
  -> 查看 fund_events
  -> 生成报表
```

同一银行不同账户必须能够复用同一类 Parser，账户归属由主数据和别名库匹配，不把 Parser 绑定到单个账户。

## 文档验收

权威文档中不得再新增版本化分裂表达。检查内容包括：

- 不存在失效入口路径。
- 不把 `new/` 作为项目权威。
- 不出现乱码。
- 新文档不引入 Agent/Skill/Memory 的版本后缀命名。

冻结契约文件如需修改，必须单独走契约变更流程。

## 守卫验收

常规检查：

```powershell
backend\venv\Scripts\python.exe tools\guards\check_canonical_schema.py
backend\venv\Scripts\python.exe tools\guards\check_primitives_whitelist.py
backend\venv\Scripts\python.exe tools\guards\check_placeholder_binding.py
backend\venv\Scripts\python.exe tools\guards\check_api_inventory.py
backend\venv\Scripts\python.exe tools\guards\check_no_runtime_llm.py
backend\venv\Scripts\python.exe tools\guards\check_no_parallel_implementations.py
backend\venv\Scripts\python.exe tools\guards\check_product_purity.py
```

冻结契约哈希检查单独运行：

```powershell
backend\venv\Scripts\python.exe tools\guards\check_contract_hash.py
```

如果哈希失败，不得自动更新锁文件，必须报告给用户。

## 前端验收

前端可见变更至少运行：

```powershell
cd frontend
npm run build
```

涉及页面工作流时，必须用浏览器验证实际点击路径，不只看编译结果。

## 完成定义

一个任务只有在以下内容齐全时才算完成：

- 代码或文档已落到唯一权威路径。
- 不存在新的平行实现。
- 相关自动化验证已运行并记录结果。
- 若存在失败，已明确说明失败命令、失败原因和下一步。

## PR 验收门槛

每个 PR 合并前必须满足：

- 分支从最新 `main` 创建，且不含无关改动。
- PR 描述列出变更范围和影响范围。
- 后端相关改动运行对应 pytest。
- 前端可见改动运行 `npm run build` 并完成浏览器验证。
- 文档或架构改动运行相关 guard。
- 所有守卫脚本通过，或明确说明仍处于迁移基线并没有继续扩大问题。
- 不提交运行时数据、上传文件、日志、数据库、依赖目录或本地环境文件。

开源仓库建立后，CI 应至少运行：

- 后端测试。
- 前端构建。
- guard 检查。
- 后续主链路稳定后补充浏览器端到端测试。
