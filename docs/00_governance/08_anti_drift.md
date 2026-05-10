# 08 · 防跑偏六层机制（v3）

> 本文件针对"AI 开发过程中自我扩展 / 逐步失真 / 悄悄改契约"的行为，部署**六层纵深防御**。
> 配合 [00_project_constitution.md](00_project_constitution.md) 使用。

---

## §1 · 七种跑偏模式（D1–D7）

| 代号 | 模式 | 案例 | 对应防御层 |
|---|---|---|---|
| D1 | **契约蠕变** | AI 偷偷往 fund_events 加第 13 列 | Layer 2 guards |
| D2 | **基元逃逸** | Parser 里写 `import pandas` 绕过基元库 | Layer 2 guards |
| D3 | **占位符污染** | Rule 里多绑/漏绑占位符 | Layer 2 guards |
| D4 | **API 膨胀** | 路由器文件里悄悄加第 43 个端点 | Layer 2 guards |
| D5 | **阶段越位** | Phase 0 还没过 Gate G0 就开始写业务 | Layer 3 DoD + Layer 5 kickoff |
| D6 | **上下文失忆** | 换了一轮对话，AI 忘了 §C1–C9 | Layer 5 kickoff + Layer 1 宪法 |
| D7 | **KPI 偏移** | 把"提高准确率"变成"改宽容忍区间" | Layer 6 目标硬化 |

---

## §2 · 六层防御总览

```
┌─────────────────────────────────────────────────────┐
│ Layer 1 · 契约冻结（00_project_constitution.md）   │ ← 对应 D1/D6
├─────────────────────────────────────────────────────┤
│ Layer 2 · 自动化 guards（tools/guards/*.py）       │ ← 对应 D1/D2/D3/D4
├─────────────────────────────────────────────────────┤
│ Layer 3 · 每步 DoD（每个任务 4 项交付）            │ ← 对应 D5
├─────────────────────────────────────────────────────┤
│ Layer 4 · Handoff 文档（阶段交接凭据）             │ ← 对应 D5/D6
├─────────────────────────────────────────────────────┤
│ Layer 5 · Kickoff 五条确认（每次会话开始）         │ ← 对应 D5/D6
├─────────────────────────────────────────────────────┤
│ Layer 6 · 目标硬化（强验收标准）                   │ ← 对应 D7
└─────────────────────────────────────────────────────┘
```

---

## §3 · Layer 1 · 契约冻结

所有 FROZEN 清单集中在 [`00_project_constitution.md`](00_project_constitution.md) 的 §C1–C9 + §ChangeFlow：

- §C1 基础数据表 12 列
- §C2 模板 18 占位符
- §C3 账户主数据 20 列
- §C4 Fund Agent 5 skill
- §C5 基元库白名单
- §C6 数据库 24 张业务 ORM 表
- §C7 API 端点清单（数量以 23_api_contracts.md 当前版本为准，旧 42 上限已失效）
- §C8 Runtime 无 AI
- §C9 用户零编程原则

**变更规则**：只有用户本人书面同意才能修改。任何 AI 修改宪法 = 立即回滚 + 作废当次会话。

---

## §4 · Layer 2 · 自动化 guards（5 个脚本）

目录位置：`tools/guards/`（项目根下，pre-commit 全部启用）

| 脚本 | 检查点 | 行为规约 |
|---|---|---|
| `check_canonical_schema.py` | §C1 · 12 列基础表 | 解析 `fund_events` DDL，列序 / 列名 / 枚举与宪法不符则退出 1 |
| `check_primitives_whitelist.py` | §C5 · 基元库 | 对所有 `parser_artifacts.code` + `rule_artifacts.code` 做 AST 扫描，禁用非白名单 import / 危险调用 |
| `check_placeholder_binding.py` | §C2 · 18 占位符 | Rule artifact 的 bindings + loop.columns 必须恰好覆盖 18 个占位符 |
| `check_api_inventory.py` | §C7 · API 端点 | 遍历 `backend/api/**/*.py` 的路由注册，与 `23_api_contracts.md` 比对 |
| `check_contract_hash.py` | 宪法完整性 | 对 00 宪法做 SHA256，与 `contracts.lock` 不符拒绝 |

### §4.1 · 扩展 guard（推荐）

- `check_runtime_no_llm.py` —— 扫描 `backend/services/` + `backend/fund/rule_runtime.py` + `backend/fund/sandbox.py`，不得出现 `ai_call` / `openai` / `httpx.post("https://api.")` 等 LLM 调用
- `check_artifact_sample.py` —— 新入库的 Parser / Rule 必须带 `sample_check_log`

### §4.2 · CI 集成

`.github/workflows/guards.yml` 或本地 pre-commit hook 调用：

```bash
python tools/guards/check_contract_hash.py
python tools/guards/check_canonical_schema.py
python tools/guards/check_primitives_whitelist.py
python tools/guards/check_placeholder_binding.py
python tools/guards/check_api_inventory.py
```

任一非零 → 阻断提交。

> **注意**：`check_api_inventory.py` 的旧 42 端点上限已失效。当前 API 数量以 `23_api_contracts.md` 为准。如该 guard 脚本尚未更新，标记为待修复，不得让它误导开发。

---

## §5 · Layer 3 · 每步 DoD（Definition of Done）

每个任务（如 P0-T1、P1-T3）完成时必须输出 **4 项**：

| # | 交付物 | 内容 |
|---|---|---|
| 1 | **文件清单** | 新增 / 修改 / 删除的文件路径（git diff 能印证） |
| 2 | **测试证据** | 单元测试通过日志 / 覆盖率数字 / 手动验证截图 |
| 3 | **Guards 绿** | 5 个 guards 脚本全部通过（贴命令和输出） |
| 4 | **Handoff 文档** | 在 commit message 中说明任务目标、变更内容和影响范围 |

**任一缺失** = 任务未完成，不允许进入下一任务。

---

## §6 · Layer 4 · Handoff 约定

每次重大变更的 commit message 必须包含：

```text
chore/feat/fix(scope): 简述

目标：本次变更要达成什么
变更：新增/修改/删除了哪些文件
影响：对其他模块的影响
验证：如何确认变更正确（测试命令或手动验证步骤）
```
- coverage report: 93%

## Guards
- check_contract_hash.py → OK
- check_primitives_whitelist.py → OK（本任务是基元库本体，特殊跳过）
- check_canonical_schema.py → OK
- check_placeholder_binding.py → N/A
- check_api_inventory.py → OK

## 风险 / 已知问题
- `parse_amount` 对"贷记/借记"中文符号的处理未覆盖港澳格式
- `match_account` 的模糊匹配阈值 0.85，可能需要后续调参

## 进入下一步的理由
- Phase 0 Gate G0 条件"基元库覆盖率 ≥ 90%" 已满足（93%）
- 所有枚举、类型约束与 §C1/§C3 一致
- 没有新增非白名单依赖
```

---

## §7 · Layer 5 · Kickoff 五条确认

**每次会话开始前**（无论换 AI 工具还是换人），必须先回答以下 5 条：

```
1. 我要做的任务属于哪个 Phase / Task ID？
   答：________________

2. 该任务的 DoD 清单是什么？
   答：（引 §5 的 4 项交付物）

3. 本任务会触发哪些 guard？需要通过哪些？
   答：________________

4. 本任务会不会涉及修改宪法（§C1–C9）？
   答：若涉及，先停下走 §ChangeFlow；若不涉及，继续。

5. 如果中途发现"基元库不够 / 占位符不够 / 端点不够"，我会怎么办？
   答：停下，写 ChangeFlow 申请；绝不在 PR 里悄悄加。
```

缺任一条 = 不开工。

---

## §8 · Layer 6 · 目标硬化

### §8.1 · 禁止的模糊目标

| 模糊 | 硬化 |
|---|---|
| "让它能工作" | "在 fixtures/bank/icbc_*.xlsx 上，生成的 Parser 通过 100% 样本校验" |
| "让报表差不多对" | "金额准确率 ≥ 99.5%；占位符覆盖率 100%；18 占位符无漏绑无多绑" |
| "优化性能" | "单次 parse 耗时 ≤ 3s；单次 render 耗时 ≤ 5s；内存 ≤ 512MB" |
| "提升用户体验" | "用户零编程 6 步完成（§V1 验收清单）" |

### §8.2 · Karpathy 四原则落地

本项目引入 [Karpathy CLAUDE.md](../../CLAUDE.md) 四条原则，对 AI 的硬化约束如下：

| 原则 | 本项目硬化 |
|---|---|
| **Think Before Coding** | 每次开工必走 §7 kickoff 五条 |
| **Simplicity First** | 基元库锁死 37 个；多写一个函数要走 ChangeFlow |
| **Surgical Changes** | 每个 PR 只改文件清单里的文件；不得顺手 refactor 相邻代码 |
| **Goal-Driven Execution** | 每个任务有具体的验证命令（见 §8.1） |

---

## §9 · 违规严重度与应对

| 级别 | 典型场景 | 应对 |
|---|---|---|
| **CRITICAL** | 修改宪法 / Runtime 调 LLM / 绕基元库 | **立即回滚 PR** + 作废当次会话 |
| **HIGH** | 绕 guards / 漏 Handoff / 跳 Gate | 退回到上一个 Gate + 补 Handoff |
| **MEDIUM** | DoD 缺 1–2 项 | 补齐后重新评审 |
| **LOW** | 文案 / 注释 / 格式 | code review 中指出，下一个 PR 修 |

---

## §10 · 本机制生效条件

- `tools/guards/` 5 个脚本存在且可执行 → Layer 2 生效
- `contracts.lock` 存在且与宪法 SHA256 一致 → Layer 1 可验证
- `.pre-commit-config.yaml` 已配置 → pre-commit 生效
- 每次会话首屏看到 Kickoff 五条 → Layer 5 生效

以上任一缺失 = 整个防御链有漏洞，暂停新开发直到补齐。

---

**版本**
- v3.1 · 2026-05-10 · 修正 §C6 表数为 24 张业务 ORM 表；旧 42 端点 guard 标记为已失效
- v3.0 · 2026-04-23 · 首次发布
