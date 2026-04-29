# Phase 2 交班单：Fund Agent 骨架

## 完成范围

- P2-1：创建 `backend/agents/fund/` 目录结构与 5 个 skill 模块承载位。
- P2-2：实现 `FundAgent` harness，冻结 5 skill 白名单，支持 schema 校验、模块分发、trace_id 与 `ai_call_logs` 记录。
- P2-3：实现 5 个 skill 的 Pydantic 输入/输出 schema。
- P2-4：实现 `memory.py`，覆盖 parser artifact、rule artifact、alias library 的基础读写与审核晋级。
- P2-5：5 个 skill 模块均为 Phase 3 占位，导入成功，调用时抛出带 Phase 3 提示的 `NotImplementedError`。
- P2-6：改写 `master/` 与 `parser-assistant/` 14 个 Markdown，明确 Fund Agent 是 V1 唯一活动业务 Agent，master 仅保留协调语义。
- P2-7：改写 `services/agent_init.py`，仅当 `backend/agents/fund/` 存在时注册 `agent_configs.agent_code='fund'`。

## 新增文件

- `backend/agents/fund/__init__.py`
- `backend/agents/fund/AGENT.md`
- `backend/agents/fund/harness.py`
- `backend/agents/fund/schemas.py`
- `backend/agents/fund/memory.py`
- `backend/agents/fund/sandbox.py`
- `backend/agents/fund/skills/__init__.py`
- `backend/agents/fund/skills/parser_bank.py`
- `backend/agents/fund/skills/parser_manual.py`
- `backend/agents/fund/skills/rule_template_fill.py`
- `backend/agents/fund/skills/rule_maintain.py`
- `backend/agents/fund/skills/template_inference.py`
- `docs/60_claude_code_support/HANDOFF/PHASE2_HANDOFF_2026-04-25.md`

## 修改文件

- `backend/agents/master/AGENT.md`
- `backend/agents/master/MEMORY.md`
- `backend/agents/master/RULES.md`
- `backend/agents/master/SOUL.md`
- `backend/agents/master/TOOLS.md`
- `backend/agents/master/USER.md`
- `backend/agents/master/WORKFLOW.md`
- `backend/agents/parser-assistant/AGENT.md`
- `backend/agents/parser-assistant/MEMORY.md`
- `backend/agents/parser-assistant/RULES.md`
- `backend/agents/parser-assistant/SOUL.md`
- `backend/agents/parser-assistant/TOOLS.md`
- `backend/agents/parser-assistant/USER.md`
- `backend/agents/parser-assistant/WORKFLOW.md`
- `backend/services/agent_init.py`

## 删除文件

- 无。

## 验收输出

```powershell
backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from agents.fund.harness import FundAgent; FundAgent(); print('fund agent ok')"
fund agent ok
```

```powershell
backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from agents.fund.schemas import ParserBankInput; obj=ParserBankInput(skill='parser.bank', account_code='X', sample_file='/tmp/x.xlsx'); print(obj.model_dump())"
{'skill': 'parser.bank', 'account_code': 'X', 'sample_file': '/tmp/x.xlsx', 'field_dictionary_snapshot': None, 'alias_library_snapshot': None, 'privacy_mode': 'standard'}
```

```powershell
backend\venv\Scripts\python.exe -c "import sys; sys.path.insert(0, 'backend'); from services.agent_init import init_agent_workspaces; init_agent_workspaces(); from database import SessionLocal; from db.tables import AgentConfig; db=SessionLocal(); row=db.query(AgentConfig).filter(AgentConfig.agent_code=='fund').first(); print(row.agent_code, row.agent_type, row.workspace_dir, row.status); db.close()"
fund fund backend/agents/fund active
```

```powershell
5 skill stub import + run()
parser.bank: Phase 3 P3-1 实现 parser.bank
parser.manual: Phase 3 P3-2 实现 parser.manual
rule.template_fill: Phase 3 P3-3 实现 rule.template_fill
rule.maintain: Phase 3 P3-4 实现 rule.maintain
template.inference: Phase 3 P3-5 实现 template.inference
```

```powershell
harness run_skill('parser.bank', ...)
fund.agent parser.bank not_implemented
```

```powershell
backend\venv\Scripts\python.exe -m compileall backend\agents backend\services\agent_init.py -q
# exit code 0
```

```powershell
python tools\guards\check_contract_hash.py
[OK] contracts.lock 校验通过（1 个契约文件）
```

## 已知风险

- 5 个 skill 当前按 Phase 2 要求只做占位，业务实现进入 Phase 3。
- `bank_import_service.py` 中仍有旧 `parser_assistant` 调用痕迹，未在 Phase 2 任务卡要求内改动；建议在 Phase 3 / Phase 6 接入 Fund Agent API 时统一替换。
- 运行 Python 命令时出现 `ZF_SECRET_KEY` 未设置的本地开发警告，不影响本 Phase 验收。

## 下一步入口

- Phase 3：按 P3-1 → P3-5 实现 5 个 skill。
- 优先从 `parser.bank` 与 `parser.manual` 开始，因为它们直接决定上传样本能否生成 ParserArtifact 草稿。
