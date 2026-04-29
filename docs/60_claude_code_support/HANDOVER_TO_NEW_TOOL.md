# 换工具接手指南（HANDOVER_TO_NEW_TOOL）

> 本文件是当你想换掉 Claude Code、让另一个 AI 开发工具（Cursor / Copilot / Codex / Gemini / 自研 agent / 人类工程师）接手 **账房先生 V3** 项目时，必须交给它的**第一份文档**。
>
> **生成时间**：2026-04-24
> **当前进度**：Phase 0 已完成 3/7（P0-T1 / P0-T2 / P0-T3），剩余 15 张任务卡、约 33 人日
> **接手难度**：★★★☆☆（文档齐全 + 契约冻结 + pre-commit guard 护栏）

---

## 0. 你要交给新工具的一句话

> 本项目是**中文财务本地应用**，技术栈固定，契约锁死，按 `docs/20_execution/00_v3_execution_order.md` 从 **P0-T4** 开始继续。先读 §1 的"必读文档清单"，再读 §2 的"项目体检"，最后按 §3 的"Kickoff 五条"自检后再动手。**不得跳步、不得改契约、不得引入 pandas/numpy**。

---

## 1. 必读文档清单（**顺序不可乱**）

| # | 文档 | 作用 | 必读度 |
|---|---|---|---|
| 1 | `CLAUDE.md`（根目录） | 项目定位 + 技术栈固定清单 + 目录结构 + 开发顺序 | ★★★★★ |
| 2 | `docs/README.md` | 文档总索引（看得到所有层的位置） | ★★★★★ |
| 3 | `docs/00_governance/00_project_constitution.md` | **项目宪法**（9 条硬约束 §C1-§C9，SHA256 已锁） | ★★★★★ |
| 4 | `docs/00_governance/08_anti_drift.md` | 防跑偏手册（Kickoff 五条 + DoD 四项） | ★★★★★ |
| 5 | `docs/20_execution/00_v3_execution_order.md` | **唯一任务清单**（18 张卡，按顺序执行） | ★★★★★ |
| 6 | `docs/30_contracts/25_primitives_whitelist.md` | 基元白名单（37 个函数，已冻结） | ★★★★★ |
| 7 | `docs/30_contracts/20_database_schema.md` | 数据库契约（fund_events 12 列冻结） | ★★★★ |
| 8 | `docs/30_contracts/23_api_contracts.md` | API 契约（42 端点上限） | ★★★★ |
| 9 | `docs/60_claude_code_support/HANDOFF/handoff_P0-T3.md` | 最近一次交接（基元库完工） | ★★★★ |
| 10 | `contracts.lock` | 宪法 SHA256 基线（guard 校验用） | ★★★ |

**读完这 10 份再看代码**。直接看代码会错过整套约束。

---

## 2. 项目体检（新工具入场先跑一遍）

### 2.1 当前已交付的代码

```
backend/
├── db/tables.py                    ← ORM 模型（含 fund_events 等 v3 新表）
├── fund/primitives/                ← 37 个基元函数（已冻结，不得新增第 38 个）
│   ├── value_parsers.py           · §P2 · 5 个
│   ├── canonical.py               · §P3 · 4 个
│   ├── master_match.py            · §P4 · 4 个
│   ├── base_queries.py            · §P5 · 6 个
│   ├── aggregations.py            · §P6 · 6 个
│   ├── sheet_ops.py               · §P1 · 6 个
│   └── template_fill.py           · §P7 · 6 个
├── api/ services/ core/ agents/   ← v2 代码（v3 阶段要逐步改造 / 标 DEPRECATED）
alembic/versions/                   ← 4 个 v3 迁移（001-004）
tools/guards/                       ← 5 个 pre-commit 脚本
tests/
├── db/test_v3_tables.py
└── fund/primitives/test_*.py      ← 210 个单测，96% 覆盖率
docs/                               ← 所有契约/治理/执行/测试文档
```

### 2.2 pytest 绿基线

在 `backend/venv` 中跑：

```bash
cd F:/zhangfangxiansheng
backend/venv/Scripts/pytest.exe tests/ -q
```

**期望**：

```
210 passed in ~1.2s       (tests/fund/primitives/)
+ tests/db/               (v3 schema 约束测试)
```

### 2.3 Guard 绿基线

```bash
pre-commit run --all-files
```

5 个 guard 必须全绿：
- `check_contract_hash.py`（宪法 SHA256 vs `contracts.lock`）
- `check_canonical_schema.py`（fund_events 12 列）
- `check_primitives_whitelist.py`（artifact 只能用白名单 + stdlib）
- `check_placeholder_binding.py`（Rule 占位符绑定完整）
- `check_api_inventory.py`（API ≤ 42）

---

## 3. Kickoff 五条（每次开工前硬性自检）

摘自 `docs/00_governance/08_anti_drift.md` §7。新工具第一次说话之前**必须逐条确认**：

| # | 自检项 | 如何验证 |
|---|---|---|
| 1 | 我知道现在要做哪张任务卡（P?-T?） | 能报出 ID + 标题 + 前置依赖 |
| 2 | 我已经读完宪法 §C1-§C9 | 能复述 9 条约束的名字 |
| 3 | 我不会扩列（fund_events 12 列不变） | `check_canonical_schema` 会拦住 |
| 4 | 我不会加第 38 个基元 | `check_primitives_whitelist` 会拦住 |
| 5 | 我每步完成会写 Handoff 文档 | 模板在 `docs/60_claude_code_support/HANDOFF/` |

**任何一条不确定 → 先停下读文档，不要动手。**

---

## 4. 剩余 15 张任务卡 · 执行顺序

> 源文件：`docs/20_execution/00_v3_execution_order.md`

| 卡号 | 标题 | 前置 | 人日 |
|---|---|---|---:|
| **P0-T4** | Artifact 服务 + 沙箱 | P0-T3 ✅ | 3 |
| P0-T5 | Fund Agent 重建 | P0-T4 | 5 |
| P0-T6 | 字段字典种子 | P0-T3 ✅ | 0.5 |
| P0-T7 | few-shot 样本脱敏 | 无（并行） | 0.5 |
| 🚦 **Gate G0** | Phase 0 通过条件 | P0-T1~T7 | — |
| P1-T1 | 银行导入切 Parser artifact | G0 | 3 |
| P1-T2 | 手工流水 artifact 化 | P1-T1 | 3 |
| P1-T3 | 报表模板管理前端 | P1-T1 | 4 |
| P1-T4 | template.inference skill | P1-T3+P0-T5 | 2 |
| P1-T5 | 前端预览/批准页 | P1-T1+P1-T3 | 3 |
| P1-T6 | Rule Runtime | P1-T4 | 2 |
| P1-T7 | E2E 联调（7 家银行） | P1-T1~T6 | 1 |
| 🚦 **Gate G1** | Phase 1 通过条件 | P1-T1~T7 | — |
| P2-T1 | 异常中心独立页 | G1 | 2 |
| P2-T2 | 隐私三档生效 | G1 | 1 |
| P2-T3 | 集成测试（多银行 × 多模板） | P2-T1~T2 | 3 |
| P2-T4 | 文档收尾 + 归档 | P2-T3 | 1 |
| 🚦 **Gate G2** | 交付 | 全部 | — |

---

## 5. 技术栈（**不可换**）

| 层 | 技术 |
|---|---|
| Backend | Python 3.11+ / FastAPI / SQLAlchemy 2.x |
| DB | SQLite (V1) |
| 解析 | Polars / openpyxl（**禁止 pandas/numpy**，由 `check_primitives_whitelist` 强制） |
| Frontend | Vue 3 / Vite / Ant Design Vue / ECharts |
| OCR | PaddleOCR（后端集成） |
| 打包 | 前端静态编译 + 后端挂载 + PyInstaller |

**引入任何新栈必须先走 ChangeFlow（见 `docs/00_governance/08_anti_drift.md` §6）**。

---

## 6. 致命红线（**违反就停工**）

源头：`00_project_constitution.md` + `00_v3_execution_order.md §E4`

| # | 禁止 | 会被谁拦住 |
|---|---|---|
| 1 | 跳过 Gate 进入下一阶段 | Handoff 审核 |
| 2 | 给 `fund_events` 加第 13 列 | `check_canonical_schema.py` |
| 3 | 加第 38 个基元 | `check_primitives_whitelist.py` |
| 4 | 在 artifact 里 `import pandas` | `check_primitives_whitelist.py` |
| 5 | Rule 占位符少绑 | `check_placeholder_binding.py` |
| 6 | `backend/api/` 端点 > 42 | `check_api_inventory.py` |
| 7 | 改宪法不更新 `contracts.lock` | `check_contract_hash.py` |
| 8 | 动态 SQL 字符串拼接 | 安全审计 |
| 9 | Runtime 里直接调 LLM | 契约 §C8 |
| 10 | 用户样本原始数据发给 LLM provider | 隐私三档 §P10 |

---

## 7. 新工具接手第一天的 TODO

1. **读 §1 的 10 份文档**（约 3-4 小时）
2. **跑 §2 的体检**（pytest + pre-commit）确认没坏基线
3. **背 §3 的 Kickoff 五条**
4. **打开 `docs/60_claude_code_support/HANDOFF/handoff_P0-T3.md`** 看最后一张交付卡的风险提示
5. **宣布要做的第一张卡号**（P0-T4 或 P0-T6/P0-T7 并行）
6. **开始前**：写 DoD 四项草稿（变更范围、测试策略、回滚路径、Handoff 计划）
7. **开始后**：TDD 先写测试、再改实现、再过 5 个 guard、最后写 Handoff

---

## 8. 如果新工具问"前面的人留下什么坑"

**诚实清单**：

| 坑 | 位置 | 严重度 | 备注 |
|---|---|---|---|
| `backend/agents/master/` / `parser-assistant/` 是 v2 遗留 | - | 🟡 | P0-T5 要写 `DEPRECATED.md` 标记（不删） |
| `backend/services/bank_import_service.py` 等是 v2 逻辑 | - | 🟡 | P1-T1 重写 |
| `samples/` 样本未脱敏 | - | 🟡 | P0-T7 批量脱敏到 `fixtures/` |
| 前端当前是 v2 Vue 代码 | `frontend/src/` | 🟡 | P1-T3/T5 改造 |
| pre-commit 只对 guard 5 个启用，未加 lint/format | - | 🟢 | 可选增强 |
| sqlite WAL 文件 `zhangfang.db-wal` 在开发库里 | `backend/data/` | 🟢 | 正常 |

---

## 9. 目录地图（现状）

```
F:\zhangfangxiansheng\
├── .git/                    ← 版本控制
├── .claude/                 ← Claude Code 工作区（换工具可整目录忽略）
├── .pre-commit-config.yaml  ← 5 guard 挂载
├── alembic/                 ← v3 迁移
├── alembic.ini
├── contracts.lock           ← 宪法 SHA256
├── CLAUDE.md                ← 项目级 AI 指令
├── README.md
├── backend/
│   ├── main.py config.py database.py requirements.txt
│   ├── fund/primitives/     ← §C5 冻结的 37 函数（P0-T3 产物）
│   ├── db/tables.py         ← ORM（含 v3 新表）
│   ├── api/ services/ core/ agents/  ← v2 代码（逐步改造）
│   └── venv/                ← Python 虚拟环境
├── docs/                    ← 所有文档（新工具必读）
├── tests/
│   ├── db/                  ← v3 schema 测试
│   └── fund/primitives/     ← 210 个单测（P0-T3 产物，96% cov）
├── tools/guards/            ← 5 个 pre-commit 脚本
├── samples/ templates/ references/  ← v1/v2 样本与参考（P0-T7 要脱敏重建到 fixtures/）
├── frontend/                ← Vue 3 前端（P1 阶段改造）
├── exports/                 ← 运行时导出
└── _ARCHIVE_2026-04-24/     ← 历史遗留文件归档（见 ARCHIVE_MANIFEST.md）
```

---

## 10. 如果换了工具但还是要继续用 Claude Code 的格式（handoff / 文档）

- `docs/60_claude_code_support/HANDOFF/handoff_P?-T?.md` 模板已固化（参考 T1/T2/T3）
- `docs/60_claude_code_support/COLLABORATION_PROTOCOL.md`（如已存在）或 `docs/60_claude_code_support/12_claude_code_collaboration_protocol.md` 是协作协议
- 任何工具都要按此格式写 Handoff，否则下一棒接不住

---

## 11. 应急联系 / 冲突解决

- **文档冲突**：按 **governance → contracts → execution** 优先级，先报告再改
- **发现契约漏洞**：走 `08_anti_drift.md` §6 的 ChangeFlow，不得直接偷改
- **测试失败排查不掉**：先看 `HANDOFF/handoff_P0-T?.md` 里是否有同类已知风险

---

**本文件版本**：1.0 · 2026-04-24 · P0-T3 完工时生成
**下次更新时机**：每通过一个 Gate（G0 / G1 / G2）更新一次
