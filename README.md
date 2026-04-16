# 账房先生｜完整开发文档与模板总包

这是一个可直接放进项目目录的完整文档包，目标是让 Claude Code / Codex 能按既定设计完成第一阶段开发。

## 包内内容

### 1. docs/00_governance
上位约束层。控制当前阶段范围、技术边界、用户边界、Claude Code 执行边界。

### 2. docs/10_product_design
产品与设计沉淀层。用于统一脑子，防止讨论漂移。

### 3. docs/20_execution
模块执行层。Claude Code 真正开工时的直接输入。

### 4. docs/30_contracts
契约层。数据库、字段、API、页面状态、异常处理全部在这里对齐。

### 5. docs/40_expected_outputs
期望输出层。定义输入进系统后页面、数据库、导出、异常池应该长成什么样。

### 6. docs/50_tests
测试与验收层。模块测试、端到端验收、真实样本回归。

### 7. docs/60_claude_code_support
Claude Code 开工与协作辅助层。包括开工手册、目录规范、样本计划、交付定义、协作协议。

### 8. templates
当前阶段可直接参考和使用的模板与前端原型。

### 9. samples
样本与期望结果目录骨架。后续把你的脱敏真实文件直接补进去。

### 10. references
原始需求、风格规范、早期设计材料和截图参考。

## 推荐阅读顺序

1. `docs/00_governance/00_project_constitution.md`
2. `docs/00_governance/01_v1_scope_and_order.md`
3. `docs/00_governance/02_user_constraints.md`
4. `docs/00_governance/03_tech_constraints.md`
5. `docs/10_product_design/`
6. `docs/20_execution/`
7. `docs/30_contracts/`
8. `docs/40_expected_outputs/`
9. `docs/50_tests/`
10. `docs/60_claude_code_support/`

## 你现在还需要补的硬材料

这份包已经把文档和模板整理完整了，但要真正高质量开工，还需要你后续补进来两类真实材料：

- `samples/bank/` 里的脱敏银行流水样本
- `samples/manual/` 里的脱敏手工总表样本

没有真实样本，Claude Code 只能先完成结构和流程，真实解析稳不稳还需要回归验证。

## 直接使用建议

- 把整个包解压到项目根目录
- 保持 `docs/`、`templates/`、`samples/`、`references/` 目录结构不变
- 让 Claude Code 按 README 的阅读顺序执行
- 每做完一个模块，就拿 `docs/40_expected_outputs/` 和 `docs/50_tests/` 对照验收
