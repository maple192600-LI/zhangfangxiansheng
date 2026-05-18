# 测试与验收

## pytest 分层

| 层 | 目录 | 文件数 | 说明 |
|----|------|--------|------|
| API 测试 | `tests/backend/api/` | 1 | Workflow API |
| Core 测试 | `tests/backend/core/` | 2 | AI 调用错误、PII 脱敏 |
| 集成测试 | `tests/backend/integration/` | 1 | Workflow 业务节点 |
| Service 测试 | `tests/backend/services/` | 11 | 银行导入、手工流水、报表、AI 配置、Workflow 等 |
| DB 测试 | `tests/db/` | 1 | 表结构验证 |
| E2E 测试 | `tests/e2e/` | 2 | 全流程、异常中心 |
| Fund primitives | `tests/fund/primitives/` | 6 | 基元库单元测试 |
| Artifact 测试 | `tests/` (根) | 5 | Artifact API、AST guard、runtime contract |
| Workflow 模块 | `tests/` (根) | 1 | Workflow 模块 |
| 脚本测试 | `tests/scripts/` | 1 | 清理残留 |

### 运行命令

```powershell
# 后端核心测试
backend\venv\Scripts\pytest.exe tests\backend\core tests\db tests\scripts -q

# Service 层测试 + 覆盖率
backend\venv\Scripts\pytest.exe tests\backend --cov=backend/services --cov-report=term-missing --cov-fail-under=70

# E2E
backend\venv\Scripts\pytest.exe tests\e2e -q
```

## Guard 清单

| Guard | 脚本 | 职责 | 运行位置 |
|-------|------|------|----------|
| Contract Hash | `check_contract_hash.py` | 宪法 SHA256 锁 | CI (blocking) + pre-commit |
| Canonical Schema | `check_canonical_schema.py` | FundEvent 12 列锁 | CI (blocking) + pre-commit |
| Primitives Whitelist | `check_primitives_whitelist.py` | 基元库白名单 AST 扫描 | CI (blocking) + pre-commit |
| Placeholder Binding | `check_placeholder_binding.py` | 18 占位符绑定锁 | CI (blocking) + pre-commit |
| API Inventory | `check_api_inventory.py` | 重复路由检测（effective path） | CI (blocking) + pre-commit |

### API Inventory Guard 新行为

- 解析 effective path = `include_prefix + router_prefix + decorator_path`
- 检测重复 effective path → exit 1
- 不再有端点数量上限
- 当前结果：166 endpoints, 0 duplicate route identities

### Guard 测试

`tools/guards/tests/run_negative_tests.py` 包含 6 条负面场景 + 4 条正面场景。

## 验收标准

- 用户可见功能必须通过**浏览器实际操作**验证
- 不能声称"代码存在 = 功能正常"
- 测试套件通过 + guard 通过 + 浏览器验证 = 验收

## 当前已知验证风险

- `run_parser` 已实现；`run_rule` 仍为 NotImplementedError。依赖 `run_parser` 的链路可端到端验证
- Case 4 of guard 测试依赖中文 fixture 内容，在某些终端编码下可能输出异常（已通过 UTF-8 环境变量缓解）

---
**校准来源：** `tests/`、`tools/guards/`、`.github/workflows/backend-tests.yml`、`.pre-commit-config.yaml`
**最后校准：** 2026-05-17
