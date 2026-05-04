# 01 · V1 范围与执行顺序

> 配合 [00_project_constitution.md](00_project_constitution.md)、[03_tech_constraints.md](03_tech_constraints.md) 使用。
> 本文档定义 V1 的功能边界、当前进度、剩余工作及开发顺序。

---

## §1 · V1 范围边界

### §1.1 · 包含

- **主数据中心**：板块、法人、银行、账户、账户别名、期初余额（CRUD + 批量操作）
- **基础数据表**：按 CANONICAL_12 查询 fund_events，支持日期、主体、账户、摘要、对方、状态、来源筛选
- **银行流水导入**：上传样本 → Agent 生成 Parser → 用户审核 → Runtime 执行入库
- **手工流水双轨**：快速录入直接写结构化数据；多主体 Excel 上传走 Agent 解析
- **报表系统**：资金日报、现金日记账、账户余额表、收支明细、周/月/年报
- **Fund Agent**：5 个 skill（parser.bank / parser.manual / rule.template_fill / rule.maintain / template.inference）
- **Agent 通用能力**：会话管理、记忆系统、工具注册、技能创建、文件解析、上下文构建
- **AI 配置**：多 Provider 支持、Agent 绑定、调用审计、隐私三档
- **首页总控台**：待办、进度、关键账户、收支趋势
- **导出**：Excel 导出（筛选结果与页面数据一致）
- **备份与恢复**：SQLite 备份、操作日志
- **认证**：JWT 单用户认证 + 默认用户初始化
- **模板推断**：`template.inference` 三阶段流水线

### §1.2 · 禁止

- 发票 OCR 正式流程
- 费用审批、合同审批、多人协作
- Electron / Tauri / Rust 重写
- 收费表格组件
- 集中部署（V1 纯本地）
- 用户在 UI 中直接编辑字段映射 / 正则 / JSON
- Runtime 阶段调用 LLM（§C8）
- Agent 产物绕过 AST 扫描入库
- 新增第 6 个 skill（§C4，需走 ChangeFlow）

---

## §2 · 当前进度（2026-05-02）

### §2.1 · 已完成模块

| 模块 | 状态 | 证据 |
|------|------|------|
| 项目骨架 + 可运行环境 | ✅ 完成 | FastAPI + Vue + SQLite 启动正常 |
| 数据库与基础表 | ✅ 完成 | 28 张表，Alembic 迁移正常 |
| 主数据中心 | ✅ 完成 | divisions(14), entities(51), accounts(196), banks(1) |
| 认证系统 | ✅ 完成 | JWT + 默认 admin 用户 |
| AI 配置 | ✅ 完成 | 4 条 ai_configs，64 条调用日志 |
| Agent 框架 | ✅ 完成 | 4 个 Agent 实例，15 个会话，440 条消息 |
| Agent 工具集 | ✅ 完成 | db_ops / fs / shell / openpyxl / memory / skill_ops / file_parse / ask_user |
| Agent 技能系统 | ✅ 完成 | skill_loader / scanner / registry / creator / executor |
| Agent 记忆系统 | ✅ 完成 | memory_store / provider / manager，2 条记忆
| 前端页面 | ✅ 完成 | 35+ Vue 视图，覆盖所有功能模块 |
| 银行导入 UI | ✅ 完成 | 上传、解析预览、规则管理 |
| 手工流水 | ✅ 完成 | 快速录入 + 多主体上传 + 字段池(19) + 模板方案(4) |
| 报表模板 | ✅ 完成 | 3 条 report_templates |
| 后端服务层 | ✅ 完成 | 20 个 service 文件 |
| API 路由 | ✅ 完成 | 23 个路由模块 |
| Fund Agent 骨架 | ✅ 完成 | harness / schemas / memory / 5 个 skill 文件 |

### §2.2 · 关键缺口

| 缺口 | 现状 | 影响 |
|------|------|------|
| **fund_events 为空** | 0 行数据 | 核心数据流未打通：银行导入 → fund_events → 报表 |
| **parser_artifacts 为空** | 0 条 | Agent 未生成过真实 Parser 产物 |
| **rule_artifacts 为空** | 0 条 | Agent 未生成过真实 Rule 产物 |
| **daily_report_runs 为空** | 0 条 | 日报生成未运行过 |
| **operation_logs 为空** | 0 条 | 操作日志未生效 |
| 数据端到端闭环 | 未验证 | 银行流水 → fund_events → 日报 → 导出，全链路未跑通 |

### §2.3 · 数据库现状

实际 28 张表（宪法 §C6 列 20 张），额外 8 张：
- `agents_v2` — Agent 实例表（重构后新增）
- `agent_sessions` — Agent 会话表
- `agent_messages` — Agent 消息表
- `agent_runs` — Agent 运行记录
- `agent_memories` — Agent 记忆表
- `skills_v2` — 技能注册表
- `sqlite_sequence` — SQLite 自增序列（系统表）

> **待办**：宪法 §C6 需更新以反映实际表数，需走 §ChangeFlow。

---

## §3 · 剩余工作与开发顺序

### 第一优先级：打通核心数据流

当前最关键的任务是让数据从导入到报表的完整链路跑通。

| 步骤 | 内容 | 完成条件 |
|------|------|----------|
| 1 | 银行导入 → fund_events 入库 | 上传真实银行流水，fund_events 有数据 |
| 2 | 手工录入 → fund_events 入库 | 快速录入写入 fund_events，数据格式正确 |
| 3 | 基础数据表展示 fund_events | 页面展示行数 = API 返回行数 |
| 4 | 日报生成 | daily_report_runs 有记录，金额与 fund_events 一致 |
| 5 | 导出验证 | 导出 Excel 行数 = 页面筛选行数 = API 返回行数 |

### 第二优先级：Agent 产物闭环

| 步骤 | 内容 | 完成条件 |
|------|------|----------|
| 6 | parser.bank 生成真实 Parser | parser_artifacts 有记录，sample_check_log 通过 |
| 7 | Runtime 执行 Parser artifact | 使用 artifact 代码导入流水，结果与手动导入一致 |
| 8 | rule.template_fill 生成真实 Rule | rule_artifacts 有记录，18 占位符全覆盖 |
| 9 | 报表填充执行 | 使用 Rule artifact 生成 Excel 报表 |

### 第三优先级：完善与稳定

| 步骤 | 内容 | 完成条件 |
|------|------|----------|
| 10 | 操作日志生效 | 关键操作写入 operation_logs |
| 11 | 首页总控台数据对接 | 待办、收支趋势等展示真实数据 |
| 12 | 备份与恢复测试 | 备份 + 恢复后数据完整 |
| 13 | 集成测试 + 真实样本回归 | pytest 全绿 |

---

## §4 · 验收清单

用户应能在不写代码、不改 JSON、不配置正则的前提下完成：

1. 双击启动系统，浏览器自动打开
2. 维护法人、银行、账户和期初余额
3. 上传一份银行流水，看到解析结果，确认入库
4. 手工录入或上传一份多主体流水，处理异常行
5. 查看基础数据表，筛选、搜索、核对金额
6. 生成资金日报和账户余额表
7. 上传一个报表模板，由 Agent 识别占位符并生成绑定
8. 导出 Excel，金额与页面数据一致
9. 创建备份并恢复
10. 查看操作日志

---

## §5 · 风险与应对

| 风险 | 应对 |
|------|------|
| 真实银行流水格式差异大 | 使用脱敏样本回归，沉淀 Parser artifact |
| Agent 产物质量不稳定 | 所有产物必须过样本校验 + AST 扫描 + 用户确认 |
| Runtime 与 Agent 边界混淆 | §C8：Runtime 只执行已审核 artifact，不调 LLM |
| fund_events 数据流断裂 | 第一优先级打通，确认后再扩展 |
| 宪法与实际不符（表数/skill 数/Agent 能力） | 统计差异，后续统一走 §ChangeFlow 修订 |

---

**版本**
- v4.0 · 2026-05-02 · 基于项目现状重写，标注实际进度与剩余工作
- v3.1 · 2026-04-25 · V1 AI-First 路线复位
- v3.0 · 2026-04-23 · AI-First artifact 方案
