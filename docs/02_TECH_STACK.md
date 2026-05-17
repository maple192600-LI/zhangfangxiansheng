# 技术栈

> 以下信息完全来自 `frontend/package.json` 和 `backend/requirements.txt`，以代码为准。

## 后端

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 运行时 |
| FastAPI | 0.136.0 | Web 框架 |
| uvicorn[standard] | 0.44.0 | ASGI 服务器 |
| starlette | 1.0.0 | ASGI 工具包 |
| SQLAlchemy | 2.0.49 | ORM |
| Alembic | 1.18.4 | 数据库迁移 |
| Pydantic | 2.13.1 | 数据验证 |
| SQLite | — | 嵌入式数据库 |
| openpyxl | 3.1.5 | Excel 读写 |
| xlrd | 2.0.2 | 旧格式 Excel 读取 |
| Polars | 1.39.3 | 数据处理 |
| httpx | 0.28.1 | HTTP 客户端（LLM API 调用） |
| python-multipart | 0.0.26 | 文件上传 |
| PyJWT | 2.9.0 | JWT 认证 |
| bcrypt | 4.2.0 | 密码哈希 |
| watchfiles | 1.1.1 | 热重载 |
| PyYAML | 6.0.3 | YAML 解析 |

测试依赖：pytest 9.0.3、coverage 7.13.5

## 前端

| 依赖 | 版本 | 用途 |
|------|------|------|
| Vue | ^3.5.32 | UI 框架 |
| Vue Router | ^4.6.4 | 路由 |
| Pinia | ^3.0.4 | 状态管理 |
| naive-ui | ^2.44.1 | UI 组件库 |
| ECharts | ^6.0.0 | 图表 |
| Axios | ^1.15.0 | HTTP 客户端 |
| tabulator-tables | ^6.4.0 | 高级表格 |
| @vue-flow/core | ^1.48.2 | 工作流画布 |
| @vue-flow/background | ^1.3.2 | 画布背景 |
| @vue-flow/controls | ^1.1.3 | 画布控件 |
| @vue-flow/minimap | ^1.5.4 | 画布缩略图 |
| @duckdb/duckdb-wasm | 1.33.1-dev45.0 | 本地分析引擎 |
| @vicons/ionicons5 | ^0.13.0 | 图标 |
| Vite | ^8.0.4 | 构建工具（devDep） |

## 未安装 / 未实施

以下技术曾出现在旧文档中但**未安装或未实施**：
- 打包工具（单 exe 打包）— 未安装，流程未落地
- OCR 引擎 — 未安装，OCR 为后续阶段

---
**校准来源：** `frontend/package.json`、`backend/requirements.txt`
**最后校准：** 2026-05-17
