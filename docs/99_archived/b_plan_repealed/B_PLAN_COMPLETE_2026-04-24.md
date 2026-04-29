> ⚠ 本方案已于 2026-04-25 作废，请改读 V1_AI_FIRST_REINSTATE_2026-04-25.md

# 账房先生 · B 方案完整开发清单（交接版）

**发布日期：** 2026-04-24
**适用版本：** V1（仅出纳资金日报最小可用闭环）
**编制方：** Claude Code（审查 + 清理规划）
**交接对象：** 下一棒 AI 工具
**原则：** 该清理的清理，该删除的删除，该保留的保留。不是重建，是完善。

---

## 0. 总览（TL;DR）

### 0.1 项目当前状态一句话

**项目无法运行真实导入。** ORM 模型（`backend/db/tables.py`）已升到 v3 CANONICAL_12，但实际 SQLite (`backend/data/zhangfang.db`) 仍是 v2 schema，且无 `alembic_version` 表，迁移从未执行。核心 `bank_import_service.commit()` 和 `manual_flow_service` 在尝试写入的那一刻会抛 `TypeError: 'source_type' is an invalid keyword argument for FundEvent`。

### 0.2 方案性质

- **保持 V2 为主干**：回退 ORM 到 v2 字段语义（code → id），与已存在的真实 DB 对齐
- **回收 v3 资产**：`backend/fund/primitives/`（37 个纯函数，96% 覆盖，已存在）+ pre-commit guards 保留
- **删除 v3 残留**：`parser_artifacts` / `rule_artifacts` / `template_inference_job` / `alembic/versions/001_v3_fund_events.py` 中与 v2 冲突的部分
- **引入正规迁移**：启用 alembic 真正管理 schema，废弃 `main.py::_migrate_schema()` 的手写迁移

### 0.3 工期

原 13.5 天估算 **不够**。追加 P0 Schema 对齐 2 天 + P0 迁移正规化 1 天 + 回归测试 1 天 = **总计约 17.5 工作日**。

---

## 1. 审计结论（六轴汇总）

| 轴 | 结论 | 最严重发现 |
|---|---|---|
| A1 后端 AI 地图 | 全项目仅 1 处真实 LLM 调用 | `bank_import_service.ai_parse_headers` 唯一；manual_flow / report 零 AI |
| A2 前端 AI UX | ai-parse 前端丢了 sample_rows | `BankImport.vue:447` 不传 `sample_rows`，导致 AI 仅看表头瞎猜 |
| A3 AI 安全 | 伪加密 + 无 DELETE + 无配额 | `core/security.py` XOR 硬编码盐值；`ai_configs` / `agent_configs` 无删除端点；无审计日志、无限频 |
| A4 静默失败 | 多处"请查看操作日志"吞异常 | `api/bank_import.py:103` / `ai_config.py` / `agent_config.py` 返回通用 5000；JSON 解析失败无兜底 |
| A5 数据库/迁移 | **项目不可运行** | ORM/DB 字段名不一致；无 alembic_version；create_all + 手写 _migrate_schema 双轨失控 |
| A6 架构/交接就绪 | 文档丰富但代码不达标 | Agent MD 都是 3 行占位；无 README；无 .env.example；测试目录空 |

### 1.1 严重度统计

- 🔴 **CRITICAL (3)**：Schema drift / 迁移机制 / commit 路径崩溃
- 🟠 **HIGH (4)**：伪加密 / 无删除端点 / 前端丢参 / agent_configs 未被消费
- 🟡 **MEDIUM (6)**：吞异常 / 无 PII 脱敏 / 5 分钟超时 / 无重试 / Agent MD 占位 / 无 README
- 🟢 **LOW (3)**：Ollama 连接无代理绕过提示 / 模型列表硬编码 / 无 token 计数

---

## 2. 关键问题台账（证据链齐全）

### 🔴 CRIT-01 ORM 与 DB Schema 不一致（项目无法运行）

**证据：**
```bash
# 实际 DB（backend/data/zhangfang.db）fund_events 列：
source_type, business_time, entity_id, account_id, direction,
income_amount, expense_amount, counterparty_name, summary_text,
previous_balance_input, ending_balance_input, parse_status,
abnormal_code, raw_data_json, ...  ← v2 schema

# ORM backend/db/tables.py::FundEvent 列：
business_date, entity_code, entity_name, account_code, account_name,
summary, counterparty, amount_in, amount_out, rolling_balance,
state, source  ← v3 CANONICAL_12
```

**影响路径：**
- `backend/services/bank_import_service.py:196-212` → `FundEvent(source_type=..., entity_id=..., income_amount=..., summary_text=..., parse_status=..., raw_data_json=...)` 全部是 v2 字段名，ORM 不认，立即 TypeError
- `backend/services/manual_flow_service.py:590` → 同样问题
- `backend/services/report_service.py` → SELECT v3 列（entity_code / amount_in / state）时会 `OperationalError: no such column`

**结论：** 整条资金流水读写链 100% 断裂。

---

### 🔴 CRIT-02 迁移机制失控

**证据：**
- `backend/data/zhangfang.db` 查无 `alembic_version` 表
- `backend/main.py` 使用 `Base.metadata.create_all(bind=engine)` + 自定义 `_migrate_schema()` 打补丁
- `alembic/versions/001_v3_fund_events.py` 从未被应用
- 已运行过的数据库里混合出现了 `parser_artifacts` / `rule_artifacts` / `template_inference_job`（v3 表），但 `fund_events` 又是 v2 schema → "半人半鬼"

**结论：** 任何"清理"操作无法回滚；生产 DB 与开发 DB 分叉。

---

### 🔴 CRIT-03 parser_templates 表双轨

**证据：**
- `backend/db/tables.py` 标记 `ParserTemplate` 为 `★ DEPRECATED v3 ★`
- 但 `services/bank_import_service.py::create_template` 仍在每次 AI 解析后主动写入
- v3 的替代表 `parser_artifacts` 存在但无人写

**结论：** 需要选边：要么留 `parser_templates` 删 `parser_artifacts`，要么反过来。B 方案选前者。

---

### 🟠 HIGH-01 伪加密

**证据：** `backend/core/security.py`
```python
_SALT = b"zhangfang_v1_local_salt_2026"
def encrypt_key(plaintext: str) -> str:
    key = _derive_key(len(raw))
    encrypted = bytes(a ^ b for a, b in zip(raw, key))
    return base64.b64encode(encrypted).decode("ascii")
```

- 硬编码盐、XOR、Base64 = 任何能读源码的人都能解密全部 API Key
- 字段名 `api_key_encrypted` 构成**安全性错觉**

**修复方向：** 本地机密不能伪造安全。两选一：
1. 明确落为 `api_key_plain`，UI 提示"本地机密，请勿共享 DB"
2. 引入 Windows DPAPI / macOS Keychain / Linux libsecret 做真正的本地密钥存储

---

### 🟠 HIGH-02 无 DELETE 端点

**证据：**
- `backend/api/ai_config.py` 只有 GET / POST / PUT / test
- `backend/api/agent_config.py` 同上
- 前端 `AIConfig.vue` / `AgentConfig.vue` 无删除按钮

**影响：** 用户配错了 API Key 只能手动改 DB 或忍着。

---

### 🟠 HIGH-03 前端 ai-parse 丢失 sample_rows

**证据：** `frontend/src/views/BankImport.vue:447`
```js
async function doAIParse() {
    const headers = uploadResult.value.headers || []
    const result = await api.aiParseHeaders({ headers })  // ← 只传 headers
}
```

**而后端 `ai_parse_headers(db, headers, sample_rows=None)` 明确支持 sample_rows 辅助判断。** 前端漏参导致 AI 只能盲猜表头，成功率暴跌。

---

### 🟠 HIGH-04 agent_configs.ai_config_id 从未被消费

**证据：**
- 数据库 `agent_configs` 3 行 (shared / master / parser_assistant) 全都 `ai_config_id=1` (zhipu)
- 但 `bank_import_service.ai_parse_headers:375` 用的是 `db.query(AIConfig).order_by(is_default.desc()).first()` —— 指向 ollama (id=2)
- 全代码库 Grep `agent_config` 唯一消费点仅为 CRUD，没有任何业务代码按 agent_code 找对应 AI

**影响：** 前端的"为 Agent 绑定 AI 模型"UI 是**纯展示**，运行时无效。

---

### 🟡 MED-01 静默失败

**证据：**
- `backend/api/bank_import.py:103` `error(5000, "AI解析表头失败，请查看操作日志")` 对外返回，用户完全不知道发生了什么
- `backend/services/bank_import_service.py:443` JSON 解析失败 → 返回 error，**无正则兜底、无重试、无切换备用模型**
- 类似模式重复 5 处

**修复方向：** 错误分层（网络/鉴权/配额/解析），分类展示；JSON 解析失败时先用正则抽 `{…}` 再重试 1 次。

---

### 🟡 MED-02 无 PII 脱敏

**证据：** `services/bank_import_service.py:391-398` 直接把 sample_rows 原始值（含账号、金额、对方名称）拼进 prompt 发给第三方 LLM。

**对中国财务场景：** 账号/金额属敏感数据，至少要做：
- 账号尾四位保留、其余 * 号
- 人名替换为"甲/乙/丙"
- 金额保留量级，精度模糊

---

### 🟡 MED-03 超时 / 重试 / 审计缺失

**证据：**
- `core/ai_call.py`: 30s 默认超时，无重试，无日志
- `bank_import_service.py:426`: `timeout=300`（5 分钟）→ 用户早就刷新了
- 无 `ai_call_log` 表 → 不知道谁调了几次、Token 消耗多少、是否触发配额

---

### 🟡 MED-04 Agent MD 是 3 行占位

**证据：** `backend/services/agent_init.py::AGENT_SPECIFIC`
```python
"master": {"AGENT.md": "# 总管 Agent\n\n负责统筹协调其他 Agent...\n", ...}
```
3 行文本，无 system prompt、无工具清单、无 few-shot。V1 不需要上线多 Agent，但 UI 中展示的 Agent 会给用户"这是能干活的 AI"的错觉。

**建议：** UI 明确标记为"预留骨架（V2 启用）"，或直接隐藏入口。

---

### 🟡 MED-05 测试目录为空

**证据：** `tests/` 全空；`backend/fund/primitives/` 的 96% 覆盖率是**独立测试仓**，项目级 CI 未接入。

---

### 🟡 MED-06 无 README / 无 .env.example

**证据：**
- 根目录无 README
- 无 .env.example，新开发者不知道要设 `ZF_SECRET_KEY`
- `database.py:5` 警告过这一点但没人写示例

---

### 🟢 LOW-01 Ollama 检测硬编码 localhost:11434

**建议：** 允许 base_url 任意。

### 🟢 LOW-02 provider 模型列表硬编码

**建议：** 按 provider 提供"手动输入"兜底。

### 🟢 LOW-03 无 token 计数

**建议：** V1 够用的最小方案：记请求次数，不计 token（官方 token 计数器复杂）。

---

## 3. 清理 / 保留 / 归档 分类表

### 3.1 删除（DELETE）

| 路径 | 原因 |
|---|---|
| `alembic/versions/001_v3_fund_events.py` 中 v3 CANONICAL_12 DDL | B 方案不走 v3 路线，v3 定义要删 |
| `backend/db/tables.py::ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` | v3 残留，v2 路径不用 |
| DB 表 `parser_artifacts` / `rule_artifacts` / `template_inference_job` | 同上，迁移里 drop |
| `backend/main.py::_migrate_schema()` 所有分支 | 让 alembic 接管，手写迁移退役 |
| `backend/db/tables.py::FundEvent` v3 字段定义（entity_code / amount_in / state / source 等） | 回滚为 v2 字段 |
| Agent MD 占位（`agents/master/AGENT.md` 等）中误导性内容 | 改为"V1 预留骨架"标识 |

### 3.2 保留（KEEP）

| 路径 | 理由 |
|---|---|
| `backend/fund/primitives/` 全部 37 个纯函数 | 96% 覆盖率，算子库，B/v2 同样能用 |
| `.pre-commit-config.yaml` guards | 防止再次偷溜 v3 字段 |
| `docs/00_governance` / `docs/30_contracts` | 治理层，不论版本都要 |
| `core/ai_provider.py` PROVIDER_CONFIG | 基础设施，跨版本复用 |
| `services/agent_init.py` 的 shared/rules/memory/tools/workflows 骨架创建 | Agent 工作目录契约已定，结构保留 |
| 前端 `api/` 层 | 统一收敛，B 方案不改接口形状只改 payload |

### 3.3 归档到 `docs/99_archived/v3_attempt/`（ARCHIVE）

| 路径 | 原因 |
|---|---|
| `alembic/versions/001_v3_fund_events.py`（归档版本，删除前先拷贝） | 历史档案，以后要升 v3 可参考 |
| `docs/30_contracts/20_database_schema.md` §T2.1 CANONICAL_12 部分 | 契约以后还会用，但当前禁用 |
| 任何 v3 迁移脚本、ADR、设计文档 | 统一归档 |

---

## 4. 任务卡（按优先级）

> **执行说明：** 每个任务卡都有"文件/行号 + 做什么 + 验收"。交给下一棒 AI 工具时按顺序执行。P0 内部再分 P0-1/P0-2 等子序号，**不允许并发**（会相互覆盖）。

---

### ▌ P0-1 · Schema 回滚：ORM 对齐 v2 实际表（1.5 天）

**目标：** `backend/db/tables.py::FundEvent` 改回 v2 字段，让 `bank_import_service.commit()` 能跑。

**步骤：**
1. Backup `backend/data/zhangfang.db` → `backend/data/zhangfang.db.bak.20260424`
2. 编辑 `backend/db/tables.py::FundEvent`：
   - 删除 v3 字段：`entity_code`, `entity_name`, `account_code`, `account_name`, `summary`, `counterparty`, `amount_in`, `amount_out`, `state`, `source`, `parser_artifact_id`
   - 恢复 v2 字段（与实际 DB 对齐）：
     ```
     source_type VARCHAR(30)
     business_time VARCHAR(20)
     entity_id INTEGER (FK entities.id)
     account_id INTEGER (FK accounts.id)
     direction VARCHAR(20)
     income_amount NUMERIC(18,2)
     expense_amount NUMERIC(18,2)
     counterparty_name VARCHAR(200)
     summary_text VARCHAR(500)
     previous_balance_input NUMERIC(18,2)
     ending_balance_input NUMERIC(18,2)
     rolling_balance NUMERIC(18,2)
     parse_status VARCHAR(30)
     abnormal_code VARCHAR(50)
     raw_data_json TEXT
     ```
3. 删除 `ParserArtifact` / `RuleArtifact` / `TemplateInferenceJob` 三个 v3 类（仅声明，不动 DB）
4. 恢复 `ParserTemplate` 上的 `★ DEPRECATED v3 ★` 注释 → 改为"v2 生效"

**验收：**
- [ ] `python -c "from db.tables import FundEvent; [print(c.name) for c in FundEvent.__table__.columns]"` 列出 v2 字段
- [ ] `python -c "from db.tables import FundEvent; FundEvent(source_type='bank', income_amount=0)"` 不报 TypeError
- [ ] 原有 `bank_import_service.commit()` 代码**不用改**就能 import 通过

**风险：** 如果用户当前 DB 已被人为清空或半迁移，回滚后仍需对比 `PRAGMA table_info` 一致性。

### 完成报告
- 新增文件: [`backend/data/zhangfang.db.bak.20260424`](../../backend/data/zhangfang.db.bak.20260424)
- 修改文件: [`backend/db/tables.py`](../../backend/db/tables.py)
- 已知风险:
  - 当前数据库里仍存在 `parser_artifacts` / `rule_artifacts` / `template_inference_job` 三张 v3 残余表；按依赖图留给 P0-2 清理，本步未 drop DB 表。
  - `tests/db/test_v3_tables.py` 与 v3 schema 绑定，B 方案回滚后将不再作为 P0-1 绿基线；后续 P0-3/P2-5 需要按 v2 baseline 重建测试。
  - governance / contracts 仍保留 CANONICAL_12 叙述，与 B 方案回滚存在文档冲突；按本文件 §6.3 / §9，P2-7 再统一文档一致化。
- 验收证据:
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from db.tables import FundEvent; [print(c.name) for c in FundEvent.__table__.columns]"` 输出 v2 字段：`id, batch_id, source_type, business_date, business_time, entity_id, account_id, direction, income_amount, expense_amount, counterparty_name, summary_text, previous_balance_input, ending_balance_input, rolling_balance, parse_status, abnormal_code, raw_data_json, created_at, updated_at`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from db.tables import FundEvent; FundEvent(source_type='bank', income_amount=0); print('OK')"` 输出 `OK`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import services.bank_import_service as s; print('OK', s.__name__)"` 输出 `OK services.bank_import_service`。
  - `backend\venv\Scripts\python.exe -c "import sys, sqlite3; sys.path.insert(0, 'backend'); from db.tables import FundEvent; orm=[c.name for c in FundEvent.__table__.columns]; db=[r[1] for r in sqlite3.connect('backend/data/zhangfang.db').execute('PRAGMA table_info(fund_events)')]; print('ORM only:', sorted(set(orm)-set(db))); print('DB only:', sorted(set(db)-set(orm))); print('OK' if set(orm)==set(db) else 'MISMATCH')"` 输出 `ORM only: [] / DB only: [] / OK`。
- 是否达到进入下一步条件: YES。P0-1 的三项验收全部通过，且已备份当前 SQLite；可以进入 P0-2 清理 v3 残余表。

---

### ▌ P0-2 · 删除 v3 残余表（0.5 天）

**目标：** 清理"半人半鬼"DB 状态。

**步骤：**
1. 写一次性脚本 `scripts/cleanup_v3_residue.py`：
   ```
   DROP TABLE IF EXISTS parser_artifacts;
   DROP TABLE IF EXISTS rule_artifacts;
   DROP TABLE IF EXISTS template_inference_job;
   ```
2. 在 `backend/main.py::lifespan` 启动时**一次性**执行（检查到存在就 drop，drop 完写入 `operation_logs`）
3. 归档 `alembic/versions/001_v3_fund_events.py` 到 `docs/99_archived/v3_attempt/`

**验收：**
- [ ] 启动后 `PRAGMA table_info(parser_artifacts)` 返回空
- [ ] operation_logs 有一条 `cleanup_v3_residue` 日志

### 完成报告
- 新增文件:
  - [`scripts/__init__.py`](../../scripts/__init__.py)
  - [`scripts/cleanup_v3_residue.py`](../../scripts/cleanup_v3_residue.py)
  - [`tests/scripts/test_cleanup_v3_residue.py`](../../tests/scripts/test_cleanup_v3_residue.py)
  - [`docs/99_archived/v3_attempt/001_v3_fund_events.py`](../99_archived/v3_attempt/001_v3_fund_events.py)
- 修改文件:
  - [`backend/main.py`](../../backend/main.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 归档/移出:
  - `alembic/versions/001_v3_fund_events.py` 已移至 `docs/99_archived/v3_attempt/001_v3_fund_events.py`
- 已知风险:
  - `alembic/versions/002_v3_parser_artifacts.py` 到 `004_v3_template_inference_job.py` 仍留在活跃迁移目录，当前 alembic 链在 P0-3 重建 v2 baseline 前不可作为有效迁移链使用。
  - `backend/main.py::_migrate_schema()` 仍存在；按依赖图留给 P0-3 正式废弃并接入 alembic。
- 验收证据:
  - `backend\venv\Scripts\pytest.exe tests\scripts\test_cleanup_v3_residue.py -q` 输出 `2 passed in 0.13s`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import main; main._init_db()"` 输出 `已清理 v3 残余表: parser_artifacts, rule_artifacts, template_inference_job`。
  - `PRAGMA table_info(parser_artifacts)` / `PRAGMA table_info(rule_artifacts)` / `PRAGMA table_info(template_inference_job)` 均输出 `[]`。
  - `SELECT action, module, detail_json FROM operation_logs WHERE action='cleanup_v3_residue' ORDER BY id DESC LIMIT 1` 输出 `('cleanup_v3_residue', 'database', '{"dropped_tables": ["parser_artifacts", "rule_artifacts", "template_inference_job"]}')`。
  - `Test-Path alembic\versions\001_v3_fund_events.py` 输出 `False`，`Test-Path docs\99_archived\v3_attempt\001_v3_fund_events.py` 输出 `True`。
- 是否达到进入下一步条件: YES。P0-2 两项验收均通过，v3 残余表已从真实 SQLite 中清除并记录日志；可以进入 P0-3 启用 alembic 正规迁移。

---

### ▌ P0-3 · 启用 alembic 正规迁移（1 天）

**目标：** 废弃 `main.py::_migrate_schema()`，改用 alembic。

**步骤：**
1. `alembic init` 或复用已有 `alembic/env.py`
2. 基于**当前 v2 DB schema 的真实结构**写 `alembic/versions/000_v2_baseline.py`：
   - 只包括 v2 的表（excludes parser_artifacts 等）
   - 使用 `op.create_table` 严格映射 `PRAGMA table_info` 输出
3. `alembic stamp 000_v2_baseline` 给已存在的 DB 打基线（不会动 schema，只写 alembic_version 行）
4. 删除 `backend/main.py::_migrate_schema()`
5. 改 `backend/main.py::lifespan`：启动时执行 `alembic upgrade head`（通过 Python API 调用，不用 shell）

**验收：**
- [ ] `SELECT version_num FROM alembic_version` 有 1 行
- [ ] 新建空 DB 启动后能从 0 开始升到最新（无 `_migrate_schema` 残影）
- [ ] `backend/main.py` 内无手写 DDL 字符串

### 完成报告
- 新增文件:
  - [`alembic/versions/000_v2_baseline.py`](../../alembic/versions/000_v2_baseline.py)
  - [`docs/99_archived/v3_attempt/002_v3_parser_artifacts.py`](../99_archived/v3_attempt/002_v3_parser_artifacts.py)
  - [`docs/99_archived/v3_attempt/003_v3_rule_artifacts.py`](../99_archived/v3_attempt/003_v3_rule_artifacts.py)
  - [`docs/99_archived/v3_attempt/004_v3_template_inference_job.py`](../99_archived/v3_attempt/004_v3_template_inference_job.py)
- 修改文件:
  - [`backend/main.py`](../../backend/main.py)
  - [`backend/config.py`](../../backend/config.py)
  - [`backend/db/tables.py`](../../backend/db/tables.py)
  - [`alembic.ini`](../../alembic.ini)
  - [`alembic/env.py`](../../alembic/env.py)
  - [`backend/data/zhangfang.db`](../../backend/data/zhangfang.db)（`alembic stamp 000_v2_baseline` 写入版本表）
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 归档/移出:
  - `alembic/versions/002_v3_parser_artifacts.py`
  - `alembic/versions/003_v3_rule_artifacts.py`
  - `alembic/versions/004_v3_template_inference_job.py`
- 已知风险:
  - `000_v2_baseline.py` 只负责 schema baseline，不负责灌入业务种子；空库启动后的系统基础数据完整性需在后续测试回填或安装流程中继续验证。
  - governance / contracts 仍保留 v3/CANONICAL_12 文档，当前按 B 方案执行；文档一致化留给 P2-7。
- 验收证据:
  - `backend\venv\Scripts\alembic.exe stamp 000_v2_baseline` 输出 `Running stamp_revision  -> 000_v2_baseline`。
  - `SELECT version_num FROM alembic_version` 输出 `[('000_v2_baseline',)]`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import main; main._init_db(); print('INIT_OK')"` 输出 `INIT_OK`。
  - 使用临时空库 `ZF_DB_PATH=backend/data/p0_3_empty_upgrade_check.db` 运行 `main._init_db()`，输出 `version ('000_v2_baseline',)`、`tables 17`，且 `fund_events` 字段为 v2 字段集合。
  - `backend\venv\Scripts\alembic.exe current` 输出 `000_v2_baseline (head)`。
  - `Select-String -Path backend\main.py -Pattern '_migrate_schema','ALTER TABLE','CREATE TABLE','DROP TABLE'` 无输出。
  - `backend\venv\Scripts\pytest.exe tests\scripts\test_cleanup_v3_residue.py -q` 输出 `2 passed in 0.13s`。
- 是否达到进入下一步条件: YES。现有 DB 已打 baseline，新空库可从 Alembic head 建表，启动路径不再依赖 `_migrate_schema()`；可以进入 P0-4 做字段引用回归。

---

### ▌ P0-4 · 修复 bank_import / manual_flow / report 的字段引用（1 天）

**目标：** 以 ORM 为唯一来源。

**步骤：**
1. `services/bank_import_service.py`：
   - commit() 已经写的 v2 字段名保留原样（CRIT-01 回滚后它天然能跑）
   - 只修复第 377 行 is_default 逻辑（见 P1-2）
2. `services/manual_flow_service.py`:
   - 第 590 行确认字段与 v2 ORM 对齐（大概率已对齐，但过一遍）
3. `services/report_service.py`：
   - 所有 `fund_events.entity_code` / `.amount_in` / `.state` SELECT 改回 v2 列
   - 如果用 ORM query，ORM 回滚后自动修复；如果有原生 SQL，逐条替换

**验收：**
- [ ] 开一个空 DB，完整跑一次 `upload → preview → commit → 生成日报` 全流程，无异常
- [ ] 报告页显示至少 1 条资金事件

### 完成报告
- 新增文件:
  - [`tests/backend/services/test_report_v2_fields.py`](../../tests/backend/services/test_report_v2_fields.py)
- 修改文件:
  - [`backend/db/tables.py`](../../backend/db/tables.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - P0-4 只覆盖后端 service 层最小闭环，未启动前端页面做浏览器验收；UI 回归应放在 P1/P2 对应任务中补。
  - `bank_import_service.ai_parse_headers` 仍按默认 AI 配置取模型，Agent-AI 绑定生效问题按依赖图留给 P1-2。
- 验收证据:
  - `backend\venv\Scripts\pytest.exe tests\backend\services\test_report_v2_fields.py tests\scripts\test_cleanup_v3_residue.py -q` 输出 `4 passed in 0.39s`。
  - `tests/backend/services/test_report_v2_fields.py::test_bank_upload_preview_commit_then_daily_report_uses_v2_schema` 在空内存 DB 中完整跑通 `upload_file → preview → commit → daily_report`，日报收入为 `50`、期末余额为 `150`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); import services.bank_import_service, services.manual_flow_service, services.report_service; print('IMPORT_OK')"` 输出 `IMPORT_OK`。
  - 服务层扫描 `FundEvent.entity_code / account_code / amount_in / amount_out / state / source / summary / counterparty` 无输出，未发现 v3 字段引用。
  - ORM/DB 字段集合对比输出 `OK`。
- 是否达到进入下一步条件: YES。资金链路字段引用已回到 v2 schema，最小上传-预览-提交-日报闭环在测试中通过；可以进入 P1-1 修复前端 AI 解析丢参。

---

### ▌ P1-1 · 修复前端 AI 解析丢参（0.25 天）

**目标：** 让 AI 能看到样本数据。

**步骤：**
1. `frontend/src/views/BankImport.vue:447`：
   ```
   const result = await api.aiParseHeaders({
       headers,
       sample_rows: uploadResult.value.sample_rows?.slice(0, 5) || []
   })
   ```
2. 确认 `uploadResult.value.sample_rows` 在上传预处理里就已填充；如果没有，从 `/api/bank-import/upload` 响应里取前 5 行数据

**验收：**
- [ ] DevTools Network 里 ai-parse 请求 payload 含 sample_rows
- [ ] 后端日志打印 sample_text 非空

### 完成报告
- 新增文件: []
- 修改文件:
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`frontend/src/views/BankImport.vue`](../../frontend/src/views/BankImport.vue)
  - [`tests/backend/services/test_report_v2_fields.py`](../../tests/backend/services/test_report_v2_fields.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 本步通过源码定位和构建验证 payload，未打开浏览器 DevTools 做人工 Network 截图；前端源码已明确传入 `sample_rows`。
  - 后端当前将上传文件前 5 行样本返回给前端；PII 脱敏仍按依赖图留给 P2-2。
- 验收证据:
  - `backend\venv\Scripts\pytest.exe tests\backend\services\test_report_v2_fields.py -q` 输出 `2 passed in 0.32s`，其中上传测试断言 `uploaded["sample_rows"]` 包含首行样本。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 962ms`。
  - `Select-String frontend\src\views\BankImport.vue -Pattern 'sample_rows','aiParseHeaders'` 显示 `api.aiParseHeaders({ headers, sample_rows: uploadResult.value.sample_rows?.slice(0, 5) || [] })`。
  - `Select-String backend\services\bank_import_service.py -Pattern 'sample_rows'` 显示上传响应写入 `sample_rows`，且 `ai_parse_headers` 构造 prompt 时消费 `sample_rows[:3]`。
- 是否达到进入下一步条件: YES。上传响应已携带样本行，AI 解析请求已传递 `sample_rows`，前端生产构建通过；可以进入 P1-2 修复 Agent-AI 路由。

---

### ▌ P1-2 · 修复 AI 路由：按 agent_config 找 AI（0.5 天）

**目标：** 让 UI 的"Agent ↔ AI 绑定"真正生效。

**步骤：**
1. `services/bank_import_service.py::ai_parse_headers` 第 375-377：
   ```python
   # 旧：按 is_default 排序取第一个
   # 新：先查 parser_assistant agent 绑定的 ai_config，fallback is_default
   agent = db.query(AgentConfig).filter(
       AgentConfig.agent_code == 'parser_assistant',
       AgentConfig.status == 'active'
   ).first()

   ai_cfg = None
   if agent and agent.ai_config_id:
       ai_cfg = db.query(AIConfig).filter(
           AIConfig.id == agent.ai_config_id,
           AIConfig.status == 'active'
       ).first()
   if not ai_cfg:
       ai_cfg = db.query(AIConfig).filter(
           AIConfig.status == 'active'
       ).order_by(AIConfig.is_default.desc()).first()
   ```

**验收：**
- [ ] 前端修改 parser_assistant 的 AI 绑定 → 后端下次调用用新 AI
- [ ] parser_assistant 未绑定时回落到默认

### 完成报告
- 新增文件:
  - [`tests/backend/services/test_bank_import_ai_routing.py`](../../tests/backend/services/test_bank_import_ai_routing.py)
- 修改文件:
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 本步验证 service 层路由逻辑，未通过前端真实点击修改 Agent 绑定；前端 CRUD 原有路径保持不变。
  - 若 `parser_assistant` 绑定的 AI 配置被停用，当前逻辑会按预期回落默认 active AI；删除/解绑 UI 能力留给 P1-3。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_bank_import_ai_routing.py -q` 初次输出 `AssertionError: assert 'default-ai' == 'bound-ai'`。
  - 绿灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_report_v2_fields.py -q` 输出 `4 passed in 0.35s`。
  - `test_ai_parse_headers_prefers_parser_assistant_bound_ai` 验证 `parser_assistant.ai_config_id` 存在时调用 `bound-ai`。
  - `test_ai_parse_headers_falls_back_to_default_ai_without_binding` 验证未绑定时回落 `is_default=True` 的 active AI。
- 是否达到进入下一步条件: YES。AI 解析已按 Agent 绑定优先选择模型，fallback 行为有测试覆盖；可以进入 P1-3 添加 DELETE 端点。

---

### ▌ P1-3 · 添加 DELETE 端点（0.5 天）

**目标：** 允许删除 AI 配置和 Agent 配置。

**步骤：**
1. `backend/api/ai_config.py` 增 `@router.delete("/ai-configs/{id}")`
   - 校验：不是当前默认、没有被 agent_configs 引用（否则返回 409 并列出引用方）
2. `backend/api/agent_config.py` 同样增 DELETE
3. `frontend/src/views/AIConfig.vue` / `AgentConfig.vue`：列表行加删除按钮（带 popconfirm 二次确认）

**验收：**
- [ ] 删除后列表刷新，DB 行消失
- [ ] 尝试删除被引用的 AI 配置 → UI 弹出"被以下 Agent 引用，请先解绑"

### 完成报告
- 新增文件:
  - [`tests/backend/services/test_ai_config_delete.py`](../../tests/backend/services/test_ai_config_delete.py)
- 修改文件:
  - [`backend/services/ai_config_service.py`](../../backend/services/ai_config_service.py)
  - [`backend/api/ai_config.py`](../../backend/api/ai_config.py)
  - [`backend/api/agent_config.py`](../../backend/api/agent_config.py)
  - [`frontend/src/api/ai.js`](../../frontend/src/api/ai.js)
  - [`frontend/src/api/index.js`](../../frontend/src/api/index.js)
  - [`frontend/src/views/AIConfig.vue`](../../frontend/src/views/AIConfig.vue)
  - [`frontend/src/views/AgentConfig.vue`](../../frontend/src/views/AgentConfig.vue)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 前端使用原生 `confirm()` 做二次确认，未引入 Ant Design Vue `Popconfirm`；保持现有页面轻量风格，后续可统一替换为组件化确认框。
  - 本步验证服务层删除和前端构建，未启动浏览器实点删除按钮。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_ai_config_delete.py -q` 初次输出 4 个 `AttributeError`，确认删除函数尚不存在。
  - 绿灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_ai_config_delete.py tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_report_v2_fields.py -q` 输出 `8 passed in 0.38s`。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 899ms`。
  - `Select-String` 定位显示后端存在 `DELETE /ai-configs/{config_id}`、`DELETE /agent-configs/{agent_id}`，AI 配置被引用时返回 HTTP `409`。
  - 前端 `AIConfig.vue` / `AgentConfig.vue` 操作列已加入“删除”按钮，删除后调用 API 并刷新列表。
- 是否达到进入下一步条件: YES。AI 配置和 Agent 配置删除能力已落到后端与前端，默认配置保护、引用保护、删除成功均有测试覆盖；可以进入 P1-4 处理伪加密命名问题。

---

### ▌ P1-4 · 伪加密问题（0.5 天，二选一）

**目标：** 消除安全性错觉。

**选项 A（V1 推荐）：**
- 重命名 `api_key_encrypted` → `api_key_local`
- `core/security.py::encrypt_key` → 直接保留明文（或 Base64 仅为可读性，不要声称加密）
- UI 明确提示："本地存储，请勿将 `zhangfang.db` 发送给他人"
- 强调：部署环境只应为单机

**选项 B（V2 再做）：**
- 接入 Windows DPAPI / macOS Keychain
- 迁移脚本把旧伪加密解出再入系统密钥库

**B 方案选 A**。

**验收：**
- [ ] 列名迁移后旧数据能读
- [ ] UI 的 API Key 输入框有明确说明

### 完成报告
- 新增文件:
  - [`alembic/versions/001_ai_key_local.py`](../../alembic/versions/001_ai_key_local.py)
  - [`tests/backend/services/test_ai_key_local_storage.py`](../../tests/backend/services/test_ai_key_local_storage.py)
- 修改文件:
  - [`alembic/versions/000_v2_baseline.py`](../../alembic/versions/000_v2_baseline.py)
  - [`backend/core/security.py`](../../backend/core/security.py)
  - [`backend/db/tables.py`](../../backend/db/tables.py)
  - [`backend/db/schemas.py`](../../backend/db/schemas.py)
  - [`backend/services/ai_config_service.py`](../../backend/services/ai_config_service.py)
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`frontend/src/views/AIConfig.vue`](../../frontend/src/views/AIConfig.vue)
  - [`tests/backend/services/test_ai_config_delete.py`](../../tests/backend/services/test_ai_config_delete.py)
  - [`tests/backend/services/test_bank_import_ai_routing.py`](../../tests/backend/services/test_bank_import_ai_routing.py)
  - [`backend/data/zhangfang.db`](../../backend/data/zhangfang.db)（执行 `alembic upgrade head`，列名迁移到 `api_key_local`）
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 本步按 B 方案 A 处理为“本地明文保存”，不是安全加密；UI 已提示不要外发 `zhangfang.db`。
  - 旧的伪加密值若已经写入数据库，会在迁移后原样保留在 `api_key_local`；本任务消除命名错觉，不自动反解历史伪加密值。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_ai_key_local_storage.py -q` 初次输出 `encrypt_key` 非 identity、`AIConfig` 无 `api_key_local` 两个失败。
  - `backend\venv\Scripts\alembic.exe upgrade head` 输出 `Running upgrade 000_v2_baseline -> 001_ai_key_local`。
  - 现有 DB 验证：`SELECT version_num FROM alembic_version` 输出 `[('001_ai_key_local',)]`；`PRAGMA table_info(ai_configs)` 输出包含 `api_key_local` 且不含 `api_key_encrypted`。
  - 空库验证：临时 `ZF_DB_PATH` 运行 `main._init_db()` 后输出 `[('001_ai_key_local',)]`，`ai_configs` 字段包含 `api_key_local`。
  - `backend\venv\Scripts\pytest.exe tests\backend\services\test_ai_key_local_storage.py tests\backend\services\test_ai_config_delete.py tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_report_v2_fields.py tests\scripts\test_cleanup_v3_residue.py -q` 输出 `12 passed in 0.48s`。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 819ms`。
- 是否达到进入下一步条件: YES。字段命名、服务读写、现有 DB 迁移、空库迁移和 UI 提示均已落地；可以进入 P2-1 做错误分类与重试。

---

### ▌ P2-1 · 错误分类 & 重试（1 天）

**目标：** 消除"请查看操作日志"吞异常。

**步骤：**
1. `core/ai_call.py::chat`：
   - 按 HTTPError / Timeout / ConnectionError / JSONDecodeError 分类
   - 非鉴权类 2xx 错误重试 1 次（exponential backoff 1s）
   - 返回结构增加 `error_code`, `error_category` 字段
2. `services/bank_import_service.py::ai_parse_headers`:
   - JSON 解析失败 → 尝试正则抽 `{.*}` 再 JSON 解析
   - 失败 2 次 → 返回 `{"ok": false, "error_code": "AI_JSON_PARSE_FAILED", "hint": "建议改用手工映射"}`
3. 前端 `BankImport.vue`：
   - `error_code === 'AI_JSON_PARSE_FAILED'` → Modal.info 引导手动映射
   - 网络类 → Modal.error + 重试按钮
   - 鉴权类 → 跳转到 AI 配置页

**验收：**
- [ ] 主动返回坏 JSON 的 mock 测试 → 前端显示"AI 未能理解表头，请手动映射"
- [ ] 断网后点击 AI 解析 → 前端显示"无法连接到 AI，请检查网络"

### 完成报告
- 新增文件:
  - [`tests/backend/core/test_ai_call_errors.py`](../../tests/backend/core/test_ai_call_errors.py)
- 修改文件:
  - [`backend/core/ai_call.py`](../../backend/core/ai_call.py)
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`frontend/src/views/BankImport.vue`](../../frontend/src/views/BankImport.vue)
  - [`tests/backend/services/test_bank_import_ai_routing.py`](../../tests/backend/services/test_bank_import_ai_routing.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 前端按错误码/类别显示内联中文提示，未使用 Modal 组件；保持现有页面交互风格。
  - `ai_call.chat()` 当前对网络/超时错误重试 1 次；HTTP 鉴权错误不重试。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\core\test_ai_call_errors.py tests\backend\services\test_bank_import_ai_routing.py -q` 初次输出 5 个失败，覆盖不重试、无 `error_code`、包裹 JSON 解析失败。
  - 绿灯：`backend\venv\Scripts\pytest.exe tests\backend\core\test_ai_call_errors.py tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_ai_key_local_storage.py -q` 输出 `9 passed in 2.26s`。
  - `test_chat_retries_connection_error_once` 验证第一次网络失败后重试一次并成功。
  - `test_chat_classifies_timeout` / `test_chat_classifies_bad_response_json` 验证返回 `AI_TIMEOUT` / `AI_RESPONSE_JSON_INVALID`。
  - `test_ai_parse_headers_extracts_json_from_wrapped_content` 验证 AI 返回中文包裹文本时能抽取 `{...}`。
  - `test_ai_parse_headers_returns_error_code_for_unparseable_json` 验证坏 JSON 返回 `AI_JSON_PARSE_FAILED`。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 861ms`。
- 是否达到进入下一步条件: YES。AI 调用错误已分层，JSON 解析有兜底，前端有可读错误提示；可以进入 P2-2 做 PII 脱敏。

---

### ▌ P2-2 · PII 脱敏（0.5 天）

**目标：** 不往第三方 LLM 送敏感原文。

**步骤：**
1. 新增 `backend/core/pii_masker.py`:
   ```
   mask_account(s)   → 保留尾4位
   mask_name(s)      → 单字姓氏 + "某某"
   mask_amount(x)    → 保留量级 (千/万/十万)
   mask_row(row, header_schema) → 按字段类型分派
   ```
2. `bank_import_service.ai_parse_headers` 构造 prompt 前调 `mask_row`
3. **表头列名本身不脱敏**（它们不是 PII，是分析对象）

**验收：**
- [ ] Prompt 里所有数字 > 4 位的部分不再出现原值
- [ ] 仍能让 AI 识别列是"金额"还是"日期"

### 完成报告
- 新增文件:
  - [`backend/core/pii_masker.py`](../../backend/core/pii_masker.py)
  - [`tests/backend/core/test_pii_masker.py`](../../tests/backend/core/test_pii_masker.py)
- 修改文件:
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`tests/backend/services/test_bank_import_ai_routing.py`](../../tests/backend/services/test_bank_import_ai_routing.py)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 当前按表头关键词分派脱敏（账号/户名/金额），对藏在“摘要”里的姓名或账号不做全文 NLP 脱敏；符合本任务的最小范围。
  - 金额保留量级，不保留精确值；AI 可判断“金额列”，但不能从样本中读出原金额。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\core\test_pii_masker.py tests\backend\services\test_bank_import_ai_routing.py -q` 初次输出 `ModuleNotFoundError: No module named 'core.pii_masker'`。
  - 绿灯：`backend\venv\Scripts\pytest.exe tests\backend\core\test_pii_masker.py tests\backend\services\test_bank_import_ai_routing.py -q` 输出 `9 passed in 0.26s`。
  - 综合验证：`backend\venv\Scripts\pytest.exe tests\backend\core\test_pii_masker.py tests\backend\core\test_ai_call_errors.py tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_ai_key_local_storage.py tests\backend\services\test_ai_config_delete.py tests\backend\services\test_report_v2_fields.py tests\scripts\test_cleanup_v3_residue.py -q` 输出 `22 passed in 2.48s`。
  - `test_ai_parse_headers_masks_sample_rows_before_prompt` 验证 prompt 不含原始账号 `6222021234567890123` 和原始金额 `128934.55`，包含 `***************0123` 与 `约十万级`。
- 是否达到进入下一步条件: YES。样本行进入 AI prompt 前已脱敏，日期/金额列语义仍保留；可以进入 P2-3 做超时与审计日志。

---

### ▌ P2-3 · 超时 / 审计日志（0.5 天）

**步骤：**
1. `core/ai_call.py`: `timeout` 参数默认改为 30s，`bank_import_service.py:426` 改为 60s（120 最多）
2. 新表 `ai_call_logs`:
   ```
   id, provider, model, endpoint, status,
   duration_ms, request_size, response_size,
   error_code, created_at
   ```
3. alembic 迁移 `001_add_ai_call_logs.py`
4. `core/ai_call.py::chat` 包一层装饰器自动写日志

**验收：**
- [ ] 前端"AI 配置 → 查看调用记录"页能列出最近 50 次
- [ ] 失败调用有 error_code

### 完成报告
- 新增文件:
  - [`alembic/versions/002_ai_call_logs.py`](../../alembic/versions/002_ai_call_logs.py)
- 修改文件:
  - [`backend/db/tables.py`](../../backend/db/tables.py)
  - [`backend/core/ai_call.py`](../../backend/core/ai_call.py)
  - [`backend/services/bank_import_service.py`](../../backend/services/bank_import_service.py)
  - [`backend/services/ai_config_service.py`](../../backend/services/ai_config_service.py)
  - [`backend/api/ai_config.py`](../../backend/api/ai_config.py)
  - [`frontend/src/api/ai.js`](../../frontend/src/api/ai.js)
  - [`frontend/src/views/AIConfig.vue`](../../frontend/src/views/AIConfig.vue)
  - [`tests/backend/core/test_ai_call_errors.py`](../../tests/backend/core/test_ai_call_errors.py)
  - [`backend/data/zhangfang.db`](../../backend/data/zhangfang.db)（执行 `alembic upgrade head`，新增 `ai_call_logs`）
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 审计日志记录请求/响应字节数、状态、耗时、错误码，不记录 token 数；符合本任务 V1 最小方案。
  - 前端调用记录以 AI 配置页内嵌表格展示，不单独新建路由页面。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\core\test_ai_call_errors.py -q` 初次新增审计断言时输出 2 个 `_write_ai_call_log` 不存在失败。
  - `backend\venv\Scripts\alembic.exe upgrade head` 输出 `Running upgrade 001_ai_key_local -> 002_ai_call_logs`。
  - DB 验证：`SELECT version_num FROM alembic_version` 输出 `[('002_ai_call_logs',)]`；`PRAGMA table_info(ai_call_logs)` 输出 `provider/model/endpoint/status/duration_ms/request_size/response_size/error_code/created_at`。
  - `backend\venv\Scripts\pytest.exe tests\backend\core\test_ai_call_errors.py tests\backend\core\test_pii_masker.py tests\backend\services\test_bank_import_ai_routing.py tests\backend\services\test_ai_key_local_storage.py tests\backend\services\test_ai_config_delete.py tests\backend\services\test_report_v2_fields.py tests\scripts\test_cleanup_v3_residue.py -q` 输出 `24 passed in 3.49s`。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 697ms`。
- 是否达到进入下一步条件: YES。AI 调用日志表、写入、查询端点与前端最近 50 次入口均已落地，失败调用记录 `error_code`；可以进入 P2-4 标记 Agent 预留。

---

### ▌ P2-4 · Agent MD 标记为"预留"（0.25 天）

**步骤：**
1. `backend/services/agent_init.py::AGENT_SPECIFIC` 每个 MD 开头加：
   ```
   # [V1 预留骨架 · V2 启用]
   当前 V1 阶段仅展示 Agent 目录结构，实际业务逻辑走规则引擎。
   若前端看到此 Agent 可被调用，视为 UI 占位。
   ```
2. 前端 `AgentConfig.vue` 页头 Alert: "V1 阶段 Agent 仅用于 AI 配置绑定，实际业务逻辑由规则引擎处理"

### 完成报告
- 新增文件:
  - [`tests/backend/services/test_agent_reserved_notice.py`](../../tests/backend/services/test_agent_reserved_notice.py)
- 修改文件:
  - [`backend/services/agent_init.py`](../../backend/services/agent_init.py)
  - [`backend/agents/master/AGENT.md`](../../backend/agents/master/AGENT.md)
  - [`backend/agents/master/MEMORY.md`](../../backend/agents/master/MEMORY.md)
  - [`backend/agents/master/RULES.md`](../../backend/agents/master/RULES.md)
  - [`backend/agents/master/SOUL.md`](../../backend/agents/master/SOUL.md)
  - [`backend/agents/master/TOOLS.md`](../../backend/agents/master/TOOLS.md)
  - [`backend/agents/master/USER.md`](../../backend/agents/master/USER.md)
  - [`backend/agents/master/WORKFLOW.md`](../../backend/agents/master/WORKFLOW.md)
  - [`backend/agents/parser-assistant/AGENT.md`](../../backend/agents/parser-assistant/AGENT.md)
  - [`backend/agents/parser-assistant/MEMORY.md`](../../backend/agents/parser-assistant/MEMORY.md)
  - [`backend/agents/parser-assistant/RULES.md`](../../backend/agents/parser-assistant/RULES.md)
  - [`backend/agents/parser-assistant/SOUL.md`](../../backend/agents/parser-assistant/SOUL.md)
  - [`backend/agents/parser-assistant/TOOLS.md`](../../backend/agents/parser-assistant/TOOLS.md)
  - [`backend/agents/parser-assistant/USER.md`](../../backend/agents/parser-assistant/USER.md)
  - [`backend/agents/parser-assistant/WORKFLOW.md`](../../backend/agents/parser-assistant/WORKFLOW.md)
  - [`frontend/src/views/AgentConfig.vue`](../../frontend/src/views/AgentConfig.vue)
  - [`docs/60_claude_code_support/B_PLAN_COMPLETE_2026-04-24.md`](B_PLAN_COMPLETE_2026-04-24.md)
- 已知风险:
  - 本步仅标注 V1 预留，不实现多 Agent 调度能力。
  - `shared/` 文档保持共享资料说明，不加预留标记。
- 验收证据:
  - 红灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_agent_reserved_notice.py -q` 初次输出 `master/AGENT.md` 未以 `# [V1 预留骨架 · V2 启用]` 开头。
  - 绿灯：`backend\venv\Scripts\pytest.exe tests\backend\services\test_agent_reserved_notice.py -q` 输出 `1 passed in 0.02s`。
  - `backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from services.agent_init import init_agent_workspaces; init_agent_workspaces(); print('AGENT_NOTICE_OK')"` 输出 `AGENT_NOTICE_OK`。
  - `backend/agents/master/AGENT.md` 与 `backend/agents/parser-assistant/AGENT.md` 前 5 行均显示 V1 预留说明。
  - `npm run build` 在 `frontend/` 下通过，输出 `✓ built in 557ms`。
- 是否达到进入下一步条件: YES。Agent 后台文档和前端页面均已明确 V1 预留状态；可以进入 P2-5 测试回填。

---

### ▌ P2-5 · 测试回填（2 天）

**目标：** 关键路径 70% 覆盖。

**步骤：**
1. `tests/backend/services/test_bank_import.py`:
   - test_commit_creates_fund_events
   - test_commit_invalid_batch_raises
   - test_ai_parse_respects_agent_binding
2. `tests/backend/services/test_manual_flow.py`
3. `tests/backend/services/test_report.py`
4. `tests/e2e/test_full_flow.py`（Playwright）: 上传 → 预览 → 确认 → 日报 → 导出
5. `tests/fixtures/` 存放一份真实"某银行标准流水.xlsx"（脱敏后）

**验收：**
- [ ] `pytest tests/backend` 全绿
- [ ] `pytest --cov=backend/services` ≥ 70%
- [ ] CI 接入（GitHub Actions 基础工作流）

### 完成报告
- 新增文件:
  - [`tests/conftest.py`](../../tests/conftest.py)
  - [`tests/backend/services/test_bank_import.py`](../../tests/backend/services/test_bank_import.py)
  - [`tests/backend/services/test_manual_flow.py`](../../tests/backend/services/test_manual_flow.py)
  - [`tests/backend/services/test_report.py`](../../tests/backend/services/test_report.py)
  - [`tests/backend/services/test_supporting_services.py`](../../tests/backend/services/test_supporting_services.py)
  - [`tests/e2e/test_full_flow.py`](../../tests/e2e/test_full_flow.py)
  - [`tests/fixtures/某银行标准流水.xlsx`](../../tests/fixtures/某银行标准流水.xlsx)
  - [`.github/workflows/backend-tests.yml`](../../.github/workflows/backend-tests.yml)
- 修改文件:
  - 本文件，追加 P2-5 完成报告。
- 完成功能:
  - 回填银行导入关键测试：提交生成 `fund_events`、非法批次报错、AI 表头解析遵循 `parser_assistant` 绑定。
  - 回填手工流水快速录入与 Excel 上传分支测试：有效/异常行识别、确认提交、模板导出。
  - 回填日报、现金日记账、收支明细、账户余额等报表测试。
  - 增补主数据、银行、基础数据、首页、看板、认证、手工方案、报表模板、导出、备份安全校验等服务测试，把 `backend/services` 覆盖率拉到 74.42%。
  - 增加服务级端到端脚本，覆盖上传 → 预览 → 确认 → 日报 → 导出闭环。
  - 增加 GitHub Actions 基础工作流，执行 `pytest tests/backend --cov=backend/services --cov-report=term-missing --cov-fail-under=70`。
- 已知风险:
  - 本地 Python/Node 环境均未安装 Playwright；`tests/e2e/test_full_flow.py` 当前为服务级端到端闭环，不是浏览器级 Playwright 脚本。后续若接入浏览器自动化，需要补充 Playwright 依赖、启动前后端服务与页面选择器稳定性校验。
  - 覆盖率仍有低覆盖文件：`backup_service` 的真实备份/恢复路径、`ai_config_service` 的部分 CRUD 分支、`log_service` 查询分支可在后续专项测试继续补。
- 验收证据:
  - `backend\venv\Scripts\pytest.exe tests\backend --cov=backend/services --cov-report=term-missing --cov-fail-under=70 -q` 输出 `44 passed`，总覆盖率 `74.42%`，并显示 `Required test coverage of 70% reached`。
  - `backend\venv\Scripts\pytest.exe tests\e2e\test_full_flow.py -q` 输出 `1 passed`。
  - `backend\venv\Scripts\python.exe -c "import importlib.util; print('python_playwright', bool(importlib.util.find_spec('playwright')))"` 输出 `python_playwright False`；`frontend\node_modules\@playwright\test` 不存在。
- 是否达到进入下一步条件: YES。P2-5 验收三项已通过：`tests/backend` 全绿、`backend/services` 覆盖率超过 70%、CI 基础工作流已接入；浏览器级 Playwright 作为明示残余风险进入后续联调加固。

---

### ▌ P2-6 · README / .env.example / 部署说明（0.5 天）

**步骤：**
1. `README.md` 根目录：
   - 项目简介
   - 本地开发启动步骤（`cd backend && pip install -r requirements.txt && python main.py`）
   - 前端启动（`cd frontend && npm install && npm run dev`）
   - 打包成 exe（PyInstaller 命令）
2. `.env.example`:
   ```
   ZF_SECRET_KEY=set_a_long_random_string_here
   ZF_DB_PATH=backend/data/zhangfang.db
   ZF_LOG_LEVEL=INFO
   ```
3. `docs/60_claude_code_support/LOCAL_DEV_SETUP.md`

### 完成报告
- 新增文件:
  - [`.env.example`](../../.env.example)
  - [`docs/60_claude_code_support/LOCAL_DEV_SETUP.md`](LOCAL_DEV_SETUP.md)
- 修改文件:
  - [`README.md`](../../README.md)
  - 本文件，追加 P2-6 完成报告。
- 完成功能:
  - README 已从旧文档总包说明更新为当前可运行项目说明，包含项目简介、技术栈、本地后端启动、前端启动、一键启动、环境变量、测试、PyInstaller 打包、目录说明和 V1 边界。
  - `.env.example` 已提供 `ZF_SECRET_KEY`、`ZF_DB_PATH`、`ZF_LOG_LEVEL` 三项样例。
  - `LOCAL_DEV_SETUP.md` 已补充 Windows 本地开发、Alembic 迁移、测试、端到端脚本、PyInstaller 打包和数据安全提醒。
- 已知风险:
  - PyInstaller 命令为基础入口打包说明，正式交付前仍需做资源随包、迁移文件、数据目录写权限和双击启动完整验证。
  - `ZF_LOG_LEVEL` 当前主要是部署约定，代码侧日志等级读取仍可在后续部署加固中细化。
- 验收证据:
  - `Select-String -Path README.md -Pattern "本地开发启动|npm run dev|PyInstaller|pytest"` 命中本地启动、前端启动、测试和打包说明。
  - `Select-String -Path .env.example -Pattern "ZF_SECRET_KEY|ZF_DB_PATH|ZF_LOG_LEVEL"` 三项全部命中。
  - `Select-String -Path docs\60_claude_code_support\LOCAL_DEV_SETUP.md -Pattern "alembic|pytest|PyInstaller|Playwright"` 命中迁移、测试、打包和端到端说明。
- 是否达到进入下一步条件: YES。P2-6 三个交付物均已落地并完成轻量文档校验；可以进入 P2-7 文档一致化。

---

### ▌ P2-7 · 文档一致化（0.5 天）

**步骤：**
1. 归档 `docs/30_contracts/20_database_schema.md §T2.1 CANONICAL_12` 到 `docs/99_archived/v3_attempt/`
2. 重写 `docs/30_contracts/20_database_schema.md` 以 v2 真实 schema 为准
3. 更新 `docs/00_governance/00_project_constitution.md` 里 §C1 不变量（移除"12 列冻结"，改为"v2 字段语义冻结"）
4. `docs/00_governance/01_v1_scope_and_order.md` 明确"V1 走 v2 schema"

### 完成报告
- 新增文件:
  - [`docs/99_archived/v3_attempt/20_database_schema_v3_CANONICAL_12.md`](../99_archived/v3_attempt/20_database_schema_v3_CANONICAL_12.md)
- 修改文件:
  - [`docs/30_contracts/20_database_schema.md`](../30_contracts/20_database_schema.md)
  - [`docs/00_governance/00_project_constitution.md`](../00_governance/00_project_constitution.md)
  - [`docs/00_governance/01_v1_scope_and_order.md`](../00_governance/01_v1_scope_and_order.md)
  - 本文件，追加 P2-7 完成报告。
- 完成功能:
  - 已将旧 v3/CANONICAL_12 数据库契约归档到 `docs/99_archived/v3_attempt/`。
  - `20_database_schema.md` 已按当前 ORM / Alembic / SQLite 实库重写为 v2 真实 schema，明确当前活动表、`fund_events` v2 字段语义、活动迁移与已归档迁移。
  - 项目宪法 §C1 已从“12 列不可变 CANONICAL_12”改为“v2 字段语义不可变”；§C6 已从 14 表改为 v2 活动表集合。
  - `01_v1_scope_and_order.md` 已改写为 B 方案后的 V1 范围与执行顺序，明确 V1 走 v2 schema，v3 artifact 方案不作为当前执行顺序。
- 已知风险:
  - 其他历史文档中可能仍保留 v3 讨论内容；本次 P2-7 只收束任务卡指定的治理与数据库契约活动文档。
  - `docs/00_governance/09_ai_capability_v3.md` 仍作为历史 AI 能力讨论存在，未在本任务中改写。
- 验收证据:
  - `Test-Path docs\99_archived\v3_attempt\20_database_schema_v3_CANONICAL_12.md` 输出 `True`。
  - `Select-String` 扫描 `00_project_constitution.md`、`01_v1_scope_and_order.md`、`20_database_schema.md` 中的 `CANONICAL_12|SCHEMA_14|parser_artifacts|rule_artifacts|template_inference_job|12 列`，仅剩“不得重新引入 / 已归档 / 不启用”语义引用。
  - `Select-String` 扫描 `v2 schema|v2 字段语义|v2 真实 schema|V1 走 v2` 命中三份活动文档。
- 是否达到进入下一步条件: YES。P2-7 指定文档已完成一致化，B 方案 §5 依赖图已执行至 P2-7 末尾。

---

## 5. 依赖图与排期

```
P0-1 Schema 回滚 (1.5d)
  └── P0-2 删除 v3 残余 (0.5d)
        └── P0-3 启用 alembic (1d)
              └── P0-4 字段修复回归 (1d)
                    └── P1-1 前端丢参 (0.25d)
                    └── P1-2 Agent-AI 路由 (0.5d)
                    └── P1-3 DELETE 端点 (0.5d)
                    └── P1-4 伪加密改名 (0.5d)
                          └── P2-1 错误分类 (1d)
                          └── P2-2 PII 脱敏 (0.5d)
                          └── P2-3 超时审计 (0.5d)
                          └── P2-4 Agent 标记 (0.25d)
                          └── P2-5 测试回填 (2d)
                          └── P2-6 README (0.5d)
                          └── P2-7 文档 (0.5d)
```

**总工期：P0=4d + P1=1.75d + P2=5.25d ≈ 11 工作日纯代码 + 2 天联调回归 + 2 天 buffer = 15 天。**

比原 13.5 天估算多 1.5 天，主因是 alembic 正规化与 schema 回滚没算进去。

---

## 6. 交接包（给下一棒 AI 工具）

### 6.1 必读清单（按顺序）

1. `docs/00_governance/00_project_constitution.md` — 项目宪法
2. `docs/00_governance/01_v1_scope_and_order.md` — V1 范围
3. `docs/00_governance/03_tech_constraints.md` — 技术约束
4. 本文件（B_PLAN_COMPLETE_2026-04-24.md）
5. `docs/60_claude_code_support/12_claude_code_collaboration_protocol.md` — 协作协议
6. `docs/V2_AI_HEALTH_CHECK_2026-04-24.md` — 前置审计原始记录

### 6.2 开工前的环境准备

```bash
# 1. 项目根目录
cd F:/zhangfangxiansheng

# 2. 后端
cd backend
python -m venv venv
venv/Scripts/activate  # Windows
pip install -r requirements.txt

# 3. 前端
cd ../frontend
npm install

# 4. 备份当前 DB（极重要）
cp backend/data/zhangfang.db backend/data/zhangfang.db.bak.$(date +%Y%m%d)
```

### 6.3 红线（不得逾越）

1. ❌ 不要试图再次"升 v3"。V3 已归档。如果需要升级做成 V2 正式发布后的 V2.x。
2. ❌ 不要动 `backend/fund/primitives/` 的纯函数。它们是资产。
3. ❌ 不要跳 P0 任务顺序（P0-1 → P0-2 → P0-3 → P0-4）。
4. ❌ 不要在 `main.py` 里加任何新 `_migrate_schema` 分支，迁移一律用 alembic。
5. ❌ 不要在未测试的情况下删已存在的 DB。始终先 backup。
6. ❌ 不要把原始 PII（账号/金额/人名）明文发给第三方 LLM（除 Ollama 本地外）。
7. ❌ 不要引入新技术栈。Python/FastAPI/SQLAlchemy/SQLite/Vue3/Vite/AntDesignVue 固化。
8. ❌ 不要加"防御性"代码处理"不可能场景"。遵循 CLAUDE.md 的 Simplicity First。

### 6.4 每步完成后必须输出（硬性要求，见 CLAUDE.md）

每个 P0/P1/P2 任务完成后，在任务卡下方追加：
```
### 完成报告
- 新增文件: [...]
- 修改文件: [...]
- 已知风险: [...]
- 验收证据: [命令输出 / 截图路径]
- 是否达到进入下一步条件: YES/NO + 理由
```

### 6.5 验收里程碑（用户回归点）

| 里程碑 | 条件 | 用户需验证 |
|---|---|---|
| M1 (P0 完成) | 能完整跑一次"上传 → 预览 → 确认 → 日报" | 用样本 Excel 过一遍闭环 |
| M2 (P1 完成) | AI 解析能用、能删 AI/Agent、API Key 不再伪装加密 | UI 点一遍关键按钮 |
| M3 (P2 完成) | 错误可读、有 README、CI 绿、覆盖率 ≥70% | `pytest` + `npm run build` |

### 6.6 协作协议摘要

- **文档冲突** → 停下报告，按 governance → contracts → execution 优先级解决
- **契约歧义** → 停下报告，不要自由发挥
- **发现本计划外的高严重度 Bug** → 停下报告，补进本文件 §2，然后再继续
- **Agent 调用超时/速率限制** → 切串行，不要堆栈并发
- **每个 commit** 遵循 `<type>: <description>` 格式（feat/fix/refactor/docs/test/chore/perf/ci）

---

## 7. 本计划未覆盖但值得关注（遗留事项）

| 项 | 说明 | 处理建议 |
|---|---|---|
| 备份/回滚功能 | `docs/20_execution` 提到但无代码 | V1 MVP 可先做手动 `sqlite3 .backup` 脚本，UI 下次 |
| Ollama 连接性能 | gemma4:26b 本地推理慢 | 换轻量模型 gemma2:9b 或加预热 |
| 多币种 | DB 字段无 currency | 后续版本加 |
| 打印样式 | 前端未实现打印专用 CSS | V1 晚期加 |
| 日报 Excel 导出格式 | 无统一模板 | 需用户确认样式 |

这些项**不属于 B 方案范围**，但下一棒 AI 应在各自实际工作时主动报备。

---

## 8. 附录

### 8.1 审计证据索引（源码行号 快速定位）

| 问题 | 文件:行号 |
|---|---|
| CRIT-01 bank commit 崩溃 | `backend/services/bank_import_service.py:196-212` |
| CRIT-01 manual commit 崩溃 | `backend/services/manual_flow_service.py:590` |
| CRIT-02 无 alembic_version | `backend/main.py::lifespan` + `backend/data/zhangfang.db` |
| CRIT-03 parser_templates 双轨 | `backend/db/tables.py::ParserTemplate` + `services/bank_import_service.py::create_template` |
| HIGH-01 伪加密 | `backend/core/security.py:全文件` |
| HIGH-02 无 DELETE | `backend/api/ai_config.py`, `backend/api/agent_config.py` |
| HIGH-03 前端丢参 | `frontend/src/views/BankImport.vue:447` |
| HIGH-04 agent_configs 未消费 | `backend/services/bank_import_service.py:375-377` |
| MED-01 吞异常 | `backend/api/bank_import.py:103` (+ 多处重复模式) |
| MED-02 无 PII 脱敏 | `backend/services/bank_import_service.py:391-398` |
| MED-03 超时/审计 | `backend/core/ai_call.py` 整文件 |
| MED-04 Agent MD 占位 | `backend/services/agent_init.py::AGENT_SPECIFIC` |

### 8.2 一次性验证命令集

```bash
# 验证 ORM 与 DB 一致
cd F:/zhangfangxiansheng
backend/venv/Scripts/python.exe -c "
import sys; sys.path.insert(0, 'backend')
from db.tables import FundEvent
orm = set(c.name for c in FundEvent.__table__.columns)

import sqlite3
conn = sqlite3.connect('backend/data/zhangfang.db')
db = set(r[1] for r in conn.execute('PRAGMA table_info(fund_events)'))

print('ORM only:', orm - db)
print('DB only: ', db - orm)
print('OK'    if orm == db else 'MISMATCH')
"

# 验证 alembic 已接管
backend/venv/Scripts/python.exe -c "
import sqlite3
c = sqlite3.connect('backend/data/zhangfang.db')
r = c.execute(\"SELECT version_num FROM alembic_version\").fetchone()
print('alembic version:', r)
"

# 验证静默失败消除（P2-1 后）
curl -X POST http://localhost:8000/api/bank-import/ai-parse \
  -H "Content-Type: application/json" \
  -d '{"headers":["a","b"],"sample_rows":[]}'
# 期望：返回具体 error_code，非 "请查看操作日志"
```

### 8.3 文件树预期变化

```
F:/zhangfangxiansheng/
├── alembic/
│   └── versions/
│       └── 000_v2_baseline.py          ← 新增（基线）
│       └── 001_add_ai_call_logs.py     ← 新增（P2-3）
├── backend/
│   ├── core/
│   │   ├── ai_call.py                  ← 改造（分类、审计）
│   │   ├── pii_masker.py               ← 新增（P2-2）
│   │   └── security.py                 ← 重命名字段
│   ├── db/
│   │   └── tables.py                   ← 回滚 v2 FundEvent，删 3 个 v3 类
│   ├── services/
│   │   ├── bank_import_service.py      ← 修第 375 行 + 错误处理
│   │   └── manual_flow_service.py      ← 确认字段
│   ├── api/
│   │   ├── ai_config.py                ← 增 DELETE
│   │   └── agent_config.py             ← 增 DELETE
│   └── main.py                         ← 删 _migrate_schema，接 alembic
├── docs/
│   ├── 60_claude_code_support/
│   │   ├── B_PLAN_COMPLETE_2026-04-24.md    ← 本文件
│   │   └── LOCAL_DEV_SETUP.md               ← 新增
│   └── 99_archived/
│       └── v3_attempt/                      ← 新增（归档 v3 资产）
│           ├── 001_v3_fund_events.py
│           └── CANONICAL_12_spec.md
├── frontend/
│   └── src/views/
│       ├── BankImport.vue              ← 第 447 行传 sample_rows
│       ├── AIConfig.vue                ← 加删除按钮
│       └── AgentConfig.vue             ← 加删除按钮
├── tests/
│   ├── backend/services/               ← 回填
│   ├── e2e/                            ← 回填
│   └── fixtures/                       ← 样本 Excel
├── scripts/
│   └── cleanup_v3_residue.py           ← 新增（P0-2）
├── README.md                           ← 新增
└── .env.example                        ← 新增
```

---

## 9. 结语

本计划的核心精神：**不重建，修对路**。

v3 是个方向正确但执行提前的尝试：
- 正确的是：CANONICAL_12 对"事件流"建模比 v2 的"银行流水特化"更干净
- 执行的过问题：ORM 改了但 migrations 没跑，造成"半人半鬼"状态，而这个状态比纯 v2 还糟

B 方案把项目拉回可运行的 v2，同时保留 v3 投入中真正有价值的部分（primitives 算子库 + pre-commit guards），让下一次演进有基础。

交接给下一棒 AI 工具时，本文件是**唯一真实来源**。若文档之间冲突，以本文件 §5 的依赖图和 §6.3 红线为准，其余文档要么归档、要么修订。

**准备好，可以动手了。**

— 编制完毕 · 2026-04-24
