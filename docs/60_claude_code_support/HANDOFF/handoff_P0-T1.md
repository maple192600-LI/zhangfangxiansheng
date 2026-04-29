# Handoff · P0-T1 · pre-commit guards 上线

> 契约锚点: `docs/00_governance/08_anti_drift.md` §4 Layer-2 · `docs/20_execution/00_v3_execution_order.md` §E1 P0-T1
> 完成日期: 2026-04-23

---

## 任务

实现 §C1–C9 的自动化守门员（Layer-2），构建 `tools/guards/` 下 5 个 pre-commit 脚本 + `contracts.lock` + `.pre-commit-config.yaml`。目标：任何绕宪法、漏占位符、逃基元库、超端点数、改契约的 commit 都在本地 / CI 被当场拒绝。

---

## 交付清单

### 新增

| 路径 | 行数 | 说明 |
|---|---|---|
| `tools/guards/check_contract_hash.py` | 137 | §ChangeFlow · 宪法 SHA256 锁；支持 `--update` 重算 |
| `tools/guards/check_canonical_schema.py` | 138 | §C1 · `fund_events` 12 列 AST 解析 |
| `tools/guards/check_primitives_whitelist.py` | 168 | §C5 · import / call / attr 三层 AST 禁用扫描 |
| `tools/guards/check_placeholder_binding.py` | 122 | §C2 · Rule JSON 18 占位符恰好覆盖 |
| `tools/guards/check_api_inventory.py` | 124 | §C7 · FastAPI 路由计数 ≤ 42 |
| `contracts.lock` | 9 | 冻结 `docs/00_governance/00_project_constitution.md` 的 SHA256 |
| `.pre-commit-config.yaml` | 39 | 本地 pre-commit 挂载 5 guard |
| `tools/guards/tests/run_negative_tests.py` | 172 | 6 负面 + 4 正面场景验证脚本 |
| `tools/guards/tests/fixtures/ok_canonical.py` | — | §C1 12 列合规样例 |
| `tools/guards/tests/fixtures/bad_canonical_13col.py` | — | §C1 违规（13 列） |
| `tools/guards/tests/fixtures/ok_artifact.py` | — | §C5 白名单合规样例 |
| `tools/guards/tests/fixtures/bad_artifact_pandas.py` | — | §C5 违规（pandas/open/eval） |
| `tools/guards/tests/fixtures/ok_rule_18.json` | — | §C2 18 占位符合规样例 |
| `tools/guards/tests/fixtures/bad_rule_17.json` | — | §C2 违规（漏绑"月末余额"） |
| `tools/guards/tests/fixtures/bad_api_43routes.py` | — | §C7 违规（43 条路由） |
| `docs/60_claude_code_support/HANDOFF/handoff_P0-T1.md` | 本文 | 本 Handoff |

### 修改

- 无。

### 删除

- 无。

---

## 测试证据

### 负面 6 条（故意违规）

```
python tools/guards/tests/run_negative_tests.py

============================================================
P0-T1 · 6 条负面场景 + 4 条正面场景
============================================================
Case 1 · 篡改宪法（改动 §C1 任一字符）→ check_contract_hash 拒绝
  [PASS] 被 check_contract_hash 拒绝（exit != 0）
  [PASS] stderr 指向 §ChangeFlow 修复步骤

Case 2 · fund_events 第 13 列 → check_canonical_schema 拒绝
  [PASS] exit != 0
  [PASS] stderr 报 CANONICAL_12 不符

Case 3 · Artifact 里 import pandas / open / eval → check_primitives_whitelist 拒绝
  [PASS] exit != 0
  [PASS] stderr 列出 pandas 违规
  [PASS] stderr 列出 open 违规

Case 4 · Rule 少绑占位符 → check_placeholder_binding 拒绝
  [PASS] exit != 0
  [PASS] stderr 列出『月末余额』为缺失

Case 5 · API 43 条 → check_api_inventory 拒绝
  [PASS] exit != 0（43 > 42）
  [PASS] stderr 报超限

Case 6 · contracts.lock 缺失 → check_contract_hash 拒绝
  [PASS] exit != 0
  [PASS] stderr 提示 --update

--- Positive sanity checks ---
  [PASS] Positive · ok_canonical 12 列通过
  [PASS] Positive · ok_artifact 白名单通过
  [PASS] Positive · ok_rule_18 绑定通过
  [PASS] Positive · contracts.lock 现状通过

============================================================
  RESULT · 7/7 groups passed
============================================================
```

映射到 `00_v3_execution_order.md` P0-T1 验证清单：

- [x] 5 个脚本在本地 pre-commit 可触发（`.pre-commit-config.yaml` 挂载）
- [x] 故意改宪法 → `check_contract_hash.py` 拒绝（Case 1）
- [x] 故意 `import pandas` 加到某 artifact → `check_primitives_whitelist.py` 拒绝（Case 3）
- [x] 故意把 fund_events 加第 13 列 → `check_canonical_schema.py` 拒绝（Case 2）
- [x] 故意让 Rule 少绑占位符 → `check_placeholder_binding.py` 拒绝（Case 4）
- [x] 故意让 `backend/api/` 超出 42 端点 → `check_api_inventory.py` 拒绝（Case 5）
- [x] `docs/60_claude_code_support/HANDOFF/handoff_P0-T1.md` 已写（本文）

---

## Guards 对当前仓库的基线读数（已知期望失败）

5 guards 在当前 v2 代码上运行的真实输出：

| Guard | 结果 | 原因 | 何时转绿 |
|---|---|---|---|
| `check_contract_hash` | **OK** | contracts.lock 刚生成，哈希匹配 | 已绿 |
| `check_canonical_schema` | **FAIL** | v2 `fund_events` 20 列（`id, batch_id, source_type, ...`），不符 §C1 12 列 | **P0-T2**（新表 DDL + 迁移） |
| `check_primitives_whitelist` | **OK**（SKIP） | 尚无 artifact 源码；默认目录不存在 | 保持绿，直到 P0-T5 产出 Parser |
| `check_placeholder_binding` | **OK**（SKIP） | 尚无 Rule JSON | 保持绿，直到 P1-T3/T4 产出 Rule |
| `check_api_inventory` | **FAIL** | v2 `backend/api/` 当前 92 个端点（> 42 上限） | **Phase 1 重写**（合并作废端点） |

**这是期望行为，不是缺陷**：guards 的职责是把 v3 契约当"棘轮"钉死——任何向 v3 靠拢的 PR 都会让失败数单调递减，任何往 v2 回滚或向 v3 不符方向演化的 PR 都会当场被阻断。

当前 commit 如需本地绕过 `guard-canonical-schema` 或 `guard-api-inventory` 做无关改动，使用：

```bash
SKIP=guard-canonical-schema,guard-api-inventory git commit -m "docs: ..."
```

`SKIP` 必须在 commit message 正文中说明原因，并仅限于无涉及这两份契约的文件。CI 不允许 SKIP（见 §CI 注意）。

---

## Guards 设计要点

### 1. `check_contract_hash.py`

- 锁定 `docs/00_governance/00_project_constitution.md`（未来可扩 14 表 DDL / 42 端点表）。
- `contracts.lock` 使用 JSON（`version / generated_at / algorithm / files{path: sha256}`），便于 diff 和扩充。
- `--update` 是 §ChangeFlow 第 3 步的显式动作，commit message 必须 `chore(constitution):`。

### 2. `check_canonical_schema.py`

- 纯 AST 扫描，不需要数据库；对 `backend/db/tables.py` 解析 SQLAlchemy ORM 类。
- 识别 `class X(Base): __tablename__ = "fund_events"` + `x = Column(...)` 的声明顺序。
- 列序不变量（§C1）：按**声明次序**严格等于 `CANONICAL_12`。
- 目标文件不存在或未定义该表时返回 **SKIP**（pre-P0-T2 兼容）。

### 3. `check_primitives_whitelist.py`

- AST 三层拦截：
  - `Import` / `ImportFrom` 目标必须在 `{fund.primitives.*, datetime, decimal, typing, re}`。
  - `Call` 禁用 `{open, eval, exec, compile, __import__, globals, locals, vars, getattr, setattr, delattr}`（后 4 个额外加入以防反射绕过）。
  - `Attribute` / `attr-call` 禁用 dunder：`{__class__, __subclasses__, __globals__, __builtins__, __bases__, __mro__, __dict__, __code__}`。
- 默认扫描 `backend/fund/artifacts/` + `artifacts/`，CLI 可传入任意路径。
- 无文件时 **SKIP**（Agent 产物上线前兼容）。

### 4. `check_placeholder_binding.py`

- 读 Rule JSON，聚合 `placeholder_bindings.keys() ∪ loop.columns.keys()`。
- 与 §C2 的 18 占位符集合做**全等**比较（缺失 + 多余都报）。
- 支持 JSON 根即 rule，或含 `"rule": {...}` 包装。

### 5. `check_api_inventory.py`

- AST 扫描 `@router.<verb>("/path")` 装饰器；去重 `(METHOD, path)`。
- `--list` 输出全量清单（便于 Phase 1 对照 §A1 42 端点盘点）。
- 当前 v2 基线：92 端点 → 修复路径：Phase 1 重写 + `__init__.py` 删掉不再注册的路由器。

---

## 风险 / 已知问题

| # | 问题 | 严重度 | 处理 |
|---|---|---|---|
| 1 | Windows 下若用户 PATH 的 `python` 指向 LibreOffice 的受限运行时，`subprocess.run([sys.executable, ...])` 会因为权限被拒 | LOW | 已在 Handoff 注明使用 `Python311/python.exe`；CI 用 setup-python 不受影响 |
| 2 | `check_primitives_whitelist` 当前额外封禁 `getattr/setattr/delattr/vars/globals/locals`（§P8.2 未显式列出） | LOW | 这是**严于契约**的偏保守选择，可防反射逃逸；若 artifact 需要 `getattr`，走 §ChangeFlow |
| 3 | `check_api_inventory` 仅识别 `router.get / app.post` 调用式装饰器，若用 `router.add_api_route(...)` 则逃脱 | MEDIUM | Phase 1 重写阶段统一使用装饰器写法；必要时加规则扫 `add_api_route` |
| 4 | `contracts.lock` 只锁宪法本体；未来 14 表 DDL、42 端点表等契约视需要追加 | LOW | `LOCKED_FILES` 常量直改即可，但变更要走 §ChangeFlow |

---

## 进入下一步（P0-T2）的理由

- P0-T1 的 6 个验证清单项全部通过。
- Guards 在**负面场景 + 正面场景 + 当前仓库真实状态**上的表现符合设计：
  - 该拒的都拒了（6/6）。
  - 该放的都放了（4/4 正面 + 2 个 SKIP 为预期）。
  - 当前 v2 仓库在 2 个 guard 上红（`canonical_schema`、`api_inventory`），这是**把 v2 债务外显化**的效果，不是 P0-T1 的失败。
- 宪法 SHA256 入锁；后续会话开始前跑 `check_contract_hash.py` 1 秒内可验证上下游协议无变。
- 下一步 P0-T2（3 张新表 DDL + Alembic 迁移）会让 `check_canonical_schema` 转绿。

---

## 启动 P0-T2 的前置检查

- [x] Gate G0 条件之一 "5 guards 在 CI 全绿" → 当前 **未全绿**（预期失败详见上表）；不阻断 P0-T2 启动，但阻断 **Phase 0 → Phase 1** 的 Gate G0。
- [x] `contracts.lock` 存在且校验通过。
- [x] `docs/30_contracts/20_database_schema.md` §T2 明确了新 `fund_events` DDL。
- [x] `docs/30_contracts/25_primitives_whitelist.md` 作为 `check_primitives_whitelist` 的治外法权清单落位（但基元本体尚未实现，属 P0-T3）。

---

**结论**：P0-T1 按 §E1 验证清单全部达成。5 guards 就位，`contracts.lock` 已锁宪法，pre-commit 配置完成。下一任务 **P0-T2 · 3 张新表 DDL + Alembic 迁移**。
