# 15 Export Dashboard Backup Execution

> 状态：reference。本文为导出、看板、备份参考，交付前需按真实代码和 guard 结果复核。

## 1. Module goal

Finish the V1 closing loop:

- export
- print
- basic dashboard
- logs
- backup
- restore
- rollback

## 2. Pages

- `frontend/src/views/Dashboard.vue`
- `frontend/src/views/SystemSettings.vue`
- `frontend/src/views/BackupRestore.vue`
- `frontend/src/views/OperationLog.vue`

## 3. Required functions

### export / print
- export current report view to Excel
- print current report view with clean print CSS

#### Export 技术规范

- **导出库**：使用 openpyxl（已在技术栈中）生成 xlsx 文件
- **文件命名**：`{报表类型}_{开始日期}_{结束日期}_{导出时间戳}.xlsx`
  - 例：`基础数据表_20260301_20260305_20260410100000.xlsx`
- **Sheet 结构**：
  - Sheet 1：数据内容（表头+数据行）
  - 表头行：冻结首行，背景色 `#f7f4ee`，字体加粗
  - 数据行：金额列右对齐，千分位格式 `#,##0.00`
  - 日期列：`YYYY-MM-DD` 格式
- **中文兼容**：确保 encoding 正确，打开不乱码

#### Print 技术规范

- **前端打印方案**：使用 `window.print()` + CSS `@media print` 规则
- **打印样式要求**：
  ```css
  @media print {
    .sidebar, .topbar, .filters-bar, .btn-row, .footer-note { display: none !important; }
    .main { padding: 0; }
    .shell { box-shadow: none; border: none; }
    table { font-size: 11px; break-inside: auto; }
    tr { break-inside: avoid; break-after: auto; }
    thead { display: table-header-group; }  /* 每页重复表头 */
  }
  ```
- **打印内容**：仅保留面包屑+表格区域，隐藏导航、按钮和筛选器
- **页眉页脚**：浏览器默认，V1 不做自定义

### basic dashboard
- total income
- total expense
- total balance
- trend chart (使用 ECharts，已在技术栈中)
- account balance composition (饼图，ECharts)

#### Dashboard 图表规范

| 图表 | 类型 | ECharts 组件 | 数据源 API |
|------|------|-------------|-----------|
| 收支趋势 | 折线图 | LineChart | `/api/dashboard/trends` |
| 账户余额分布 | 饼图 | PieChart | `/api/dashboard/metrics` |
| 指标卡片 | 数字展示 | 纯 HTML | `/api/dashboard/metrics` |

图表配色跟随 Design Tokens：主色 `#7f9b7a`，辅助 `#c8b48a`，警示 `#b87b5d`，信息 `#6e88a7`。

### logs
At least record:
- import
- manual save
- template confirmation
- report generation
- export
- rollback
- backup
- restore

#### Log action codes

| action 值 | 含义 | detail_json 示例 |
|-----------|------|-----------------|
| `batch_upload` | 文件上传 | `{ "batch_code": "...", "file_name": "...", "row_count": 36 }` |
| `batch_commit` | 批次确认 | `{ "batch_code": "...", "committed_count": 34 }` |
| `batch_rollback` | 批次回滚 | `{ "batch_code": "...", "removed_count": 36 }` |
| `report_generate` | 日报生成 | `{ "report_code": "...", "start_date": "...", "end_date": "..." }` |
| `report_rebuild` | 基础数据重建 | `{ "total_rows": 49 }` |
| `export_excel` | Excel 导出 | `{ "export_type": "...", "row_count": 49 }` |
| `backup_create` | 创建备份 | `{ "backup_id": "...", "file_size_mb": 12.3 }` |
| `backup_restore` | 恢复备份 | `{ "backup_id": "..." }` |

### backup and restore
Must include:
- SQLite database file
- required config files
- agent directory skeleton

#### 备份技术规范

- **备份格式**：ZIP 压缩包，使用 Python `zipfile` 标准库
- **命名规则**：`bk_{YYYYMMDD}_{序号}.zip`，例 `bk_20260410_001.zip`
- **存储位置**：`backups/` 目录（相对于应用根目录）
- **ZIP 内部结构**：
  ```
  bk_20260410_001.zip
  ├── db/
  │   └── zhangfang.db          ← SQLite 数据库文件完整复制
  ├── agents/
  │   ├── shared/               ← Agent workspace 文件
  │   ├── master/
  │   └── parser-assistant/
  └── meta.json                 ← { "version": "1.0", "created_at": "...", "db_size_mb": ... }
  ```
- **备份方式**：先执行 SQLite `VACUUM INTO` 生成干净副本，再打包
- **恢复方式**：解压后覆盖数据库文件，重启应用
- **最大保留数**：默认保留最近 20 份，超出时自动清理最旧的

### rollback
- rollback by batch id
- keep operation log
- prompt re-generation after rollback

#### 回滚技术规范

- **回滚操作**：将 `fund_events` 中 `batch_id` 匹配的记录的 `parse_status` 改为 `rolled_back`（非物理删除）
- **关联处理**：`import_batches` 的 `status` 改为 `rolled_back`
- **日志保留**：operation_logs 中的历史记录不受影响
- **UI 提示**：回滚后提示"X 条记录已回滚，建议重新生成受影响的日报"

### export / print
- export current report view to Excel
- print current report view with clean print CSS

### basic dashboard
- total income
- total expense
- total balance
- trend chart
- account balance composition

### logs
At least record:
- import
- manual save
- template confirmation
- report generation
- export
- rollback
- backup
- restore

### backup and restore
Must include:
- SQLite database file
- required config files
- agent directory skeleton

### rollback
- rollback by batch id
- keep operation log
- prompt re-generation after rollback

## 4. APIs

- `GET /api/dashboard/summary`
- `GET /api/dashboard/trends`
- `GET /api/dashboard/composition`
- `POST /api/export/report`
- `POST /api/backup/create`
- `POST /api/backup/restore`
- `POST /api/batches/{batch_id}/rollback`
- `GET /api/logs`

## 5. Done standard

Complete only if:

- export is usable
- print layout is readable
- dashboard reads real data
- rollback removes target batch effect
- backup and restore can be run by normal UI
