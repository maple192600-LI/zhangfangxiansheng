# 账房先生

账房先生是面向中国财务人员的本地财务 Agent 工作台。产品目标是让用户通过上传 Excel、预览结果、确认入库和生成报表完成日常资金工作。

Agent 的职责是帮助创建、维护和校验规则。日常导入、入库、汇总和报表生成必须由已审核的 Parser 或 Rule 确定性执行。

## 当前主链路

```text
上传流水或模板
  -> 匹配已有规则
  -> 无规则时由 Agent 创建 Parser 或 Rule
  -> 用户审核接受
  -> 规则中心保存
  -> 确定性执行
  -> 基础数据表 fund_events
  -> 报表生成与导出
```

## 技术栈

| 层级 | 技术 |
| --- | --- |
| 后端 | Python / FastAPI / SQLAlchemy / SQLite / Alembic |
| 数据处理 | openpyxl / Polars |
| 前端 | Vue / Vite / Ant Design Vue / ECharts |
| 打包 | 前端静态构建 + 后端挂载 + PyInstaller |

## 本地启动

首次准备环境：

```powershell
.\setup.bat
```

启动：

```powershell
.\start.bat
```

手动启动后端：

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

手动启动前端：

```powershell
cd frontend
npm install
npm run dev
```

## 重要目录

| 目录 | 用途 |
| --- | --- |
| `backend/` | FastAPI 后端、服务层、数据库模型、Agent 系统 |
| `frontend/` | Vue 前端 |
| `docs/` | 项目权威文档入口 |
| `agents/` | Agent 运行时数据与技能 |
| `samples/` | 测试样本 |
| `templates/` | 模板文件 |
| `references/` | 原始参考资料和视觉参考 |
| `new/` | 第三方参考源码、研究资料、旧项目文档归档，不是项目权威 |
| `tools/guards/` | 项目守卫脚本 |
| `tests/` | 自动化测试 |

## 验证

后端测试示例：

```powershell
backend\venv\Scripts\pytest.exe tests\backend
```

守卫检查示例：

```powershell
backend\venv\Scripts\python.exe tools\guards\check_canonical_schema.py
backend\venv\Scripts\python.exe tools\guards\check_primitives_whitelist.py
backend\venv\Scripts\python.exe tools\guards\check_placeholder_binding.py
backend\venv\Scripts\python.exe tools\guards\check_api_inventory.py
```

前端构建：

```powershell
cd frontend
npm run build
```

## 开发流程

项目按 GitHub Flow 开发：

- `main` 保持可运行。
- 每个任务新建短分支。
- 提交使用 Conventional Commits。
- 所有合并通过 Pull Request。
- PR 必须写明变更、验证、风险和未完成项。
- 合并前必须通过测试、guard，以及必要的浏览器验证。

## 开发边界

- 不在 `main` 上开发。
- 不保留同一能力的平行实现。
- 不让用户写 JSON、正则、SQL 或字段映射。
- 不在确定性执行阶段调用 LLM。
- 不提交运行时数据、日志、数据库、依赖目录或临时文件。
