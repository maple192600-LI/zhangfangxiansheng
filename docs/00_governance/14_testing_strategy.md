# 14 · 测试策略

> 配合 [13_coding_conventions.md](13_coding_conventions.md)、[12_tech_constraints.md](12_tech_constraints.md) 使用。
> 测试框架：pytest，覆盖率目标：80%。

---

## §1 · 测试分层

```
tests/
├── backend/              ← 后端单元/集成测试
│   ├── services/         ← Service 层测试
│   └── core/             ← 核心引擎测试
├── fund/                 ← Fund Agent 专项测试
│   └── primitives/       ← 基元库测试（37 函数）
├── e2e/                  ← 端到端业务闭环测试
└── conftest.py           ← 全局 fixture
```

| 层级 | 路径 | 职责 | 运行频率 |
|------|------|------|----------|
| 单元测试 | `tests/backend/services/` | 测试单个 service 函数 | 每次提交 |
| 核心引擎 | `tests/backend/core/` | 测试 parser_engine / pii_masker 等 | 每次提交 |
| Fund Agent | `tests/fund/` | 测试基元库、artifact、沙箱 | 每次提交 |
| E2E | `tests/e2e/` | 测试完整业务链路 | 合并前 |

---

## §2 · 现有测试清单

### §2.1 · 后端服务测试

| 测试文件 | 测试目标 |
|----------|----------|
| `test_bank_import.py` | 银行导入核心流程 |
| `test_bank_import_ai_routing.py` | AI 解析路由 |
| `test_manual_flow.py` | 手工流水录入 |
| `test_report.py` | 报表生成 |
| `test_report_v2_fields.py` | 报表 V2 字段 |
| `test_ai_key_local_storage.py` | AI 密钥本地存储 |
| `test_ai_config_delete.py` | AI 配置删除 |
| `test_agent_reserved_notice.py` | Agent 保留通知 |
| `test_supporting_services.py` | 辅助服务 |

### §2.2 · 核心引擎测试

| 测试文件 | 测试目标 |
|----------|----------|
| `test_pii_masker.py` | PII 脱敏 |
| `test_ai_call_errors.py` | AI 调用错误处理 |

### §2.3 · Fund Agent 测试

| 测试文件 | 测试目标 |
|----------|----------|
| `test_sheet_ops.py` | Excel 读取操作 |
| `test_value_parsers.py` | 值解析（日期/金额） |
| `test_canonical.py` | CANONICAL_12 行产出 |
| `test_master_match.py` | 单位/账户匹配 |
| `test_base_queries.py` | 基础数据查询 |
| `test_template_fill.py` | 模板填充 |
| `test_aggregations.py` | 聚合运算 |
| `test_sandbox.py` | AST 沙箱扫描 |
| `test_artifact_runtime.py` | Artifact 执行 |
| `test_phase6_api.py` | Phase 6 API 测试 |
| `test_phase7_privacy.py` | 隐私三档测试 |

### §2.4 · E2E 测试

| 测试文件 | 测试目标 |
|----------|----------|
| `test_full_flow.py` | 完整业务闭环 |
| `test_security_regression.py` | 安全回归 |
| `test_exception_center.py` | 异常中心 |

---

## §3 · Fixture 规范

### §3.1 · 全局 Fixture（conftest.py）

```python
# tests/conftest.py
@pytest.fixture
def db_session():
    """测试数据库会话（使用内存 SQLite）"""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield session
    session.close()
```

### §3.2 · 测试隔离

- 每个测试用独立数据库（内存 SQLite），不共享状态
- 测试之间不依赖执行顺序
- 不依赖外部服务（AI Provider、网络）

---

## §4 · 运行命令

```bash
# 运行全部测试
pytest

# 运行特定模块
pytest tests/backend/services/
pytest tests/fund/primitives/
pytest tests/e2e/

# 运行单个文件
pytest tests/backend/services/test_bank_import.py

# 带覆盖率
pytest --cov=backend --cov-report=term-missing

# 只跑非 E2E
pytest --ignore=tests/e2e
```

---

## §5 · 缺口与优先级

当前 31 个测试文件，覆盖：
- ✅ Service 层基本覆盖
- ✅ Fund Agent 基元库完整覆盖
- ✅ 安全和隐私有测试
- ❌ Agent 运行时（runtime.py）无直接测试
- ❌ 记忆系统无测试
- ❌ 技能注册/匹配无测试
- ❌ 上下文压缩无测试

新增测试优先级：
1. Agent runtime 核心循环测试
2. 记忆系统测试（save / prefetch / sync）
3. 技能注册与匹配测试
4. API 端点集成测试补全

---

**版本**
- v1.0 · 2026-05-02 · 首次发布
