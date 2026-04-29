# Phase 4 交班单：沙箱与守护

## 完成范围

- P4-1：实现 `backend/agents/fund/sandbox.py`
  - `execute(code, workbook, ctx, timeout=30, mem_limit_mb=256, ai_config=None)`
  - 执行前调用 `tools/guards/check_primitives_whitelist.py::scan_source` 做 AST 扫描
  - 使用 `multiprocessing.Process` 子进程执行 `parse(wb, ctx)`
  - 超时后 terminate / kill
  - Linux 下尝试 `resource.setrlimit(RLIMIT_AS, mem_limit)`，Windows 退化为超时兜底
  - exec 环境只提供白名单内置函数和受控 `__import__`
  - 输出行强校验为 CANONICAL_12
- P4-2：`check_primitives_whitelist.py` 已覆盖 import、`open/eval/exec/compile/__import__`、dunder attribute 扫描；本轮用 sandbox 测试验证拒绝路径。
- P4-3：新增 6 个 sandbox 测试，覆盖合法 code、`import os`、`eval`、死循环、内存炸弹、从 ai_config 读取 timeout/mem 配置。

## 新增文件

- `tests/fund/test_sandbox.py`
- `docs/60_claude_code_support/HANDOFF/PHASE4_HANDOFF_2026-04-26.md`

## 修改文件

- `backend/agents/fund/sandbox.py`

## 删除文件

- 无。

## 验收证据

```powershell
backend\venv\Scripts\python.exe -m pytest tests\fund\test_sandbox.py -q
6 passed, 1 warning
```

```powershell
backend\venv\Scripts\python.exe -m pytest tests\fund\test_sandbox.py tests\fund\primitives -q
216 passed, 2 warnings
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
backend\venv\Scripts\python.exe -m compileall backend\agents\fund tests\fund\test_sandbox.py -q
# exit code 0
```

## 已知风险

- Windows 不支持 `resource.setrlimit(RLIMIT_AS)`，内存炸弹用子进程异常或 timeout 兜底；Linux 部署时会启用地址空间限制。
- Windows 下不建议用 `python -` / stdin 脚本直接调 `multiprocessing`；pytest、后端服务、普通模块入口均是文件入口，已验证测试通过。
- 当前 `ai_configs` 表没有专门的 sandbox 配置列；sandbox 兼容读取 `ai_config.sandbox_timeout` / `sandbox_mem_limit_mb` 动态属性，或从 `model_name` JSON 中读取同名键。无配置时使用函数入参默认值。

## 是否达到下一 Phase 进入条件

- YES。
- 理由：P4 指定的 5 类安全测试全部通过，sandbox 可执行合法 Parser 并拒绝危险代码；白名单与占位符 guard 保持绿色，可进入 Phase 5 Runtime 执行器。
