# Phase 3 交班单：5 个 Fund Agent Skill 实现

## 完成范围

- P3-1 `parser.bank`：读取样本 Excel，识别表头，生成 Parser artifact 草稿，写入 `parser_artifacts`，并落地可扫描 `.py` artifact 文件。
- P3-2 `parser.manual`：复用表头识别与金额拆分逻辑，支持多主体样本的单位 / 账户 / 金额 / 摘要 / 对方 / 日期字段识别，生成 manual Parser artifact 草稿。
- P3-3 `rule.template_fill`：生成现金日记账 18 占位符 binding + loop.columns，写入 `rule_artifacts`，并落地可扫描 `.json` rule artifact 文件。
- P3-4 `rule.maintain`：按自然语言 change_request 在旧 rule 上做最小修改，新版保存为 draft，旧版不覆盖。
- P3-5 `template.inference`：扫描模板占位符，创建 `template_inference_job`，调用 `rule.template_fill` 生成 Rule 草稿，并写回 stage_b_output。

## 新增文件

- `backend/agents/fund/skills/_shared.py`
- `backend/fund/artifacts/parsers/*.py`
- `backend/fund/artifacts/rules/*.json`
- `docs/60_claude_code_support/HANDOFF/PHASE3_HANDOFF_2026-04-25.md`

## 修改文件

- `backend/agents/fund/schemas.py`
- `backend/agents/fund/skills/parser_bank.py`
- `backend/agents/fund/skills/parser_manual.py`
- `backend/agents/fund/skills/rule_template_fill.py`
- `backend/agents/fund/skills/rule_maintain.py`
- `backend/agents/fund/skills/template_inference.py`

## 删除文件

- 无。

## 验收证据

```powershell
parser.bank sample
artifact_id=7
sample_rows=1
parsed_rows=1
canonical_violations=0
amount_sum_in=300.00
```

```powershell
parser.manual sample
artifact_id=8
sample_rows=1
parsed_rows=1
canonical_violations=0
generated parse(...) => 1 row with CANONICAL_12 keys
```

```powershell
rule.template_fill
artifact_id=1
placeholder_bindings=12
loop.columns=6
placeholder_bound=18
placeholder_unbound=0
placeholder_extra=0
```

```powershell
rule.maintain
change_request="日期格式改成 MM月DD日"
previous_rule_id=1
new draft artifact_id=5
only 月/日 loop column format params changed
```

```powershell
template.inference
job_id=1
detected_placeholders=18
stage_b_output={'rule_artifact_id': 4, 'confidence': 0.9}
```

```powershell
python tools\guards\check_primitives_whitelist.py
[OK] 基元库白名单扫描通过（8 个文件）
```

```powershell
python tools\guards\check_placeholder_binding.py
[OK] 占位符绑定校验通过（7 个 Rule 各自覆盖 18/18）
```

```powershell
python tools\guards\check_contract_hash.py
[OK] contracts.lock 校验通过（1 个契约文件）
```

```powershell
backend\venv\Scripts\python.exe -m compileall backend\agents\fund -q
# exit code 0
```

```powershell
backend\venv\Scripts\python.exe -m pytest tests\fund -q
210 passed, 2 warnings
```

## 当前数据库验证

```text
parser_artifacts 8
rule_artifacts 7
template_inference_job 2
latest_ai_logs [('fund.agent', 'template.inference', 'ok'), ('fund.agent', 'template.inference', 'started'), ...]
```

## 已知风险

- 当前本地库没有默认 AI Provider 配置，5 个 skill 在无 provider 情况下走 deterministic fallback，仍可产出可审核 artifact 草稿；真实 LLM 语义增强需要在 Phase 7/8 隐私档位与真实样本回归中继续压测。
- 验收过程中生成了多条 draft artifact 与 artifact 文件，均为本轮 skill 调用产物；后续前端审核流接入后应由用户接受 / 拒绝 / 归档。
- `parser.bank` / `parser.manual` 已能在主数据空库时保底产出 CANONICAL_12 行，但账户归属的最终正确性仍需用户审核与 Phase 5 Runtime 入库守护。

## 是否达到下一 Phase 进入条件

- YES。
- 理由：5 个 skill 均可通过 harness 调用并产出 draft；Parser artifact 通过基元白名单；Rule artifact 覆盖 18/18 占位符；现有 fund primitives 测试保持绿色。
