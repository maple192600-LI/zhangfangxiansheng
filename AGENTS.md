# AGENTS.md

## 业务上下文

遇到业务相关任务时：
1. 先读 `project_context/business/INDEX.md`
2. 根据 INDEX.md 按需读取 1-3 个相关文件
3. **不要**一次性读取全部 project_context

## 关键事实

- **FundEvent** 是标准资金流水记录，**不是**旧 FundAgent
- 旧 FundAgent 已删除，禁止恢复
- `backend/fund/` 是确定性执行基础设施，不等于旧 FundAgent
- 当前可用主线：手工快速录入 → 报表查询/导出
- 报表生成禁止调 LLM（§C8 约束）
- 增强层不阻断核心功能：模板缺失时降级到默认列
