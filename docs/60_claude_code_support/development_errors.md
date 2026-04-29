# 账房先生 — 开发错误记录

> 记录开发过程中遇到的所有错误、原因分析和解决方案。按 Round 分组，每个错误记录：现象、根因、修复方式、预防措施。

---

## Round 1-3：基础框架搭建阶段

### ERR-001: SQLite 数据库文件路径不一致

- **现象**: 每次重启后数据库被重新创建，数据丢失
- **根因**: `config.py` 中 `DATA_DIR` 使用相对路径，不同工作目录导致数据库文件位置不同
- **修复**: 使用 `__file__` 计算绝对路径，确保 `DATA_DIR` 始终指向 `backend/data/`
- **预防**: 配置路径始终使用绝对路径，不依赖 CWD

### ERR-002: 前端 API 请求 404

- **现象**: 前端所有 API 请求返回 404
- **根因**: FastAPI 路由前缀 `/api` 配置不一致，`main.py` 中 include_router 未设置 prefix
- **修复**: 统一所有 router 注册时添加 `prefix="/api"`
- **预防**: 新增路由时检查 prefix 配置

---

## Round 4：银行流水导入

### ERR-003: openpyxl 读取 Excel 返回空数据

- **现象**: 上传 Excel 文件后解析结果为空列表
- **根因**: `load_workbook` 使用了 `read_only=True` 但随后尝试修改数据；同时 Excel 文件中的 sheet 名与代码中硬编码的名称不匹配
- **修复**: 使用 `wb.worksheets[0]` 代替 `wb[SheetName]`，确保始终读取第一个 sheet
- **预防**: 不硬编码 sheet 名称

### ERR-004: 文件上传路径中文乱码

- **现象**: 上传含中文文件名的文件时，服务端收到乱码文件名
- **根因**: Windows 下 multipart/form-data 的 filename 编码与 FastAPI 默认解析不匹配
- **修复**: 使用 `UploadFile.filename` 并做 `unquote` 处理
- **预防**: 所有文件名处理都做 URL decode

---

## Round 5：手工流水双轨

### ERR-005: 手工流水日期格式不一致

- **现象**: 前端传入的日期格式 `2024-04-21T00:00:00.000Z` (ISO) 与后端期望的 `YYYY-MM-DD` 不匹配
- **根因**: Vue 的 `<input type="date">` 返回 ISO 格式，但前端传给后端时未截断时间部分
- **修复**: 前端发送前截取 `date.slice(0, 10)`
- **预防**: 统一日期格式为 `YYYY-MM-DD`，前后端都做格式约束

### ERR-006: Excel 批量导入时列映射错误

- **现象**: 多主体 Excel 上传后，数据写入错误的列
- **根因**: Excel 列顺序与数据库字段顺序不一致，代码用位置索引映射而非列名映射
- **修复**: 改用列名（header）匹配方式映射字段
- **预防**: 所有 Excel 导入都基于列名匹配，不依赖位置

---

## Round 6：全局 UI 统一 + 后端修复

### ERR-007: CSS 变量未定义导致样式丢失

- **现象**: 部分页面样式异常，颜色和间距不对
- **根因**: `common.css` 中定义了 CSS 变量，但某些页面未 import common.css
- **修复**: 所有 Vue 页面统一 `@import './common.css'`
- **预防**: 新建页面模板必须包含 common.css 引用

### ERR-008: 报表 API 返回数据格式不一致

- **现象**: 部分报表接口返回裸数组，部分返回 `{code:0, data:[...]}` 包装
- **根因**: 不同 API handler 的返回方式不统一，有的用 `JSONResponse`，有的直接 return
- **修复**: 统一使用 `ApiResponse` 包装函数，确保所有接口返回 `{code, message, data}` 格式
- **预防**: 所有新增 API 端点使用统一的响应格式

---

## Round 7-8：报表模板管理 + 导出

### ERR-009: __pycache__ 导致路由注册失败 (CRITICAL)

- **现象**: 所有 `/api/report-templates/*` 路由返回 404，但代码中明明已注册路由
- **根因**: Python 的 `__pycache__` 缓存了旧版 bytecode，新增的 router import 和注册代码虽然已写入 .py 文件，但运行时 Python 加载的是旧的 .pyc 文件，导致新路由未生效
- **修复**:
  1. 手动删除所有 `__pycache__` 目录
  2. 在 `start.bat` 中添加启动前自动清理 `__pycache__` 的逻辑
- **预防**: 每次启动前清理 bytecode 缓存；开发时修改代码后重启

### ERR-010: Excel 表头解析只返回 1 列 (CRITICAL)

- **现象**: 用户上传 "现金日记账_空白月账模板.xlsx"（含合并单元格和多 sheet），解析结果只有 1 列
- **根因** (双重错误):
  1. `wb.active` 返回的是 Excel 中最后活跃的 sheet（"模板说明"描述页），而非第一个数据 sheet（"现金日记账模板"）
  2. 代码只读取第 1 行作为表头，但实际 Excel 的第 1 行是合并标题行（只有 1 个非空单元格），真正表头在第 4 行
- **修复**: 完全重写 `parse_excel_headers` 函数:
  1. 使用 `wb.worksheets[0]` 始终取第一个 sheet
  2. 扫描前 20 行，找非空单元格最多的行作为表头行
  3. 跳过合并标题行（只有 1-2 个非空单元格的行）
- **预防**: 解析用户上传的 Excel 时，永远不要假设表头位置，必须自动检测

### ERR-011: 模板已上传但报表页面不显示表头

- **现象**: 用户上传模板并设为默认后，对应报表页面仍为空白，无表头无数据
- **根因**: Vue 模板中 `v-if="rows.length"` 作为 table 的渲染条件。当没有查询数据时，即使有模板列配置，table 元素也不会被渲染
- **修复**: 将条件改为 `v-if="rows.length || templateColumns"`，并在无数据时显示提示信息行
- **预防**: 表格的渲染条件应考虑"有模板无数据"的情况

### ERR-012: 导出 API 对新报表类型返回 405

- **现象**: major_balance, month_check, week_report, month_report, year_report 五个报表导出请求返回 405 Method Not Allowed
- **根因**:
  1. `export.py` 中 `VALID_EXPORT_TYPES` 列表只包含前 6 种报表类型
  2. `ExportRequest` model 缺少 `year` 和 `month` 字段
- **修复**: 扩展 valid_types 到全部 11 种，添加 year/month 参数支持
- **预防**: 新增报表类型时同步更新导出配置

### ERR-013: Windows curl 发送中文乱码

- **现象**: 使用 curl 向 API 发送中文 JSON 数据时，服务端收到乱码
- **根因**: Windows curl 默认使用 GBK 编码发送请求体，但 FastAPI 期望 UTF-8
- **修复**: 改用 Python `requests` 库或 Playwright 进行 API 测试
- **预防**: Windows 环境下避免用 curl 发送中文数据

### ERR-014: Playwright 浏览器扩展被阻止

- **现象**: 使用 Playwright MCP 工具操作浏览器时弹出 "extension blocked" 错误
- **根因**: 浏览器中安装的某个扩展（ID: mmlmfjhmonkocbjadbfplnigmagldckm）被安全策略阻止
- **修复**: 改用 Node.js `playwright` 库直接启动 headless 浏览器，绕过 MCP 扩展问题
- **预防**: 测试时使用独立的无扩展浏览器上下文

### ERR-015: 浏览器测试认证问题

- **现象**: 通过 localStorage 注入 token 后，页面仍被重定向到 /login
- **根因**: 前端 auth store 在初始化时会验证 token 的有效性（检查过期时间等），直接注入 raw token 可能时序不对
- **修复**: 先通过登录表单登录获取合法 token，再导航到目标页面
- **预防**: 浏览器测试应模拟真实登录流程，不要跳过登录步骤

---

## 通用预防措施

1. **__pycache__ 清理**: 每次代码变更后重启前清理缓存，start.bat 已集成自动清理
2. **Excel 解析**: 不假设 sheet 位置和表头行位置，必须自动检测
3. **日期格式**: 全系统统一 YYYY-MM-DD，前后端一致
4. **API 响应格式**: 所有接口使用 `{code:0, message:"ok", data:...}` 统一包装
5. **文件名处理**: 处理中文文件名时注意编码转换
6. **Vue 条件渲染**: 考虑"有配置无数据"的边界情况
7. **Windows 环境测试**: 避免用 curl 发送中文，使用 Python/Node 测试工具
8. **浏览器测试**: 模拟完整用户流程（登录 → 操作 → 验证），不跳过步骤
