# 18 · 部署与打包指南

> 配合 [03_tech_constraints.md](../00_governance/03_tech_constraints.md) 使用。

---

## §1 · 开发环境启动

### §1.1 · 后端

```bash
# 安装依赖
pip install -r backend/requirements.txt

# 启动后端（默认 127.0.0.1:8000）
python backend/main.py
```

启动时自动完成：
- Alembic 数据库迁移
- Schema 增量补列
- 默认 admin 用户创建
- 全局技能注册
- 自动打开浏览器

### §1.2 · 前端

```bash
# 安装依赖
cd frontend && npm install

# 开发模式（默认 localhost:5180）
npm run dev

# 生产构建
npm run build
```

构建产物在 `frontend/dist/`，后端自动挂载。

---

## §2 · 生产部署

### §2.1 · 前端构建 + 后端挂载

```bash
cd frontend && npm run build
```

后端 `main.py` 自动检测 `frontend/dist/` 目录并挂载为静态资源：
- 有扩展名的文件 → 直接返回（带 no-cache）
- 其余路径 → 返回 `index.html`（SPA 路由兜底）

### §2.2 · PyInstaller 打包

```bash
pyinstaller --onefile backend/main.py
```

产出单可执行文件，用户双击启动。

---

## §3 · 环境变量

| 变量 | 默认值 | 用途 |
|------|--------|------|
| `ZF_DB_PATH` | `backend/data/zhangfang.db` | SQLite 数据库路径 |
| `ZF_SECRET_KEY` | 自动生成 | JWT 签名密钥 |
| `ZF_TOKEN_EXPIRE_MINUTES` | `480` | Token 有效期 |
| `ZF_CORS_ORIGINS` | `localhost:5180,localhost:8000` | CORS 允许域名 |

生产环境建议设置 `ZF_SECRET_KEY`。

---

## §4 · 数据目录

```
backend/data/
├── zhangfang.db        ← SQLite 数据库
├── uploads/            ← 上传文件（银行流水、手工流水）
├── exports/            ← 导出文件（报表 Excel）
└── backups/            ← 数据库备份

agents/                  ← Agent 运行时数据
├── {agent_code}/
│   ├── workspace/      ← 工作区文件
│   ├── sessions/       ← 会话数据
│   ├── memory/         ← 记忆存储
│   └── skills/         ← 该 Agent 创建的技能
└── system/
    └── skills/         ← 系统级全局技能
```

---

## §5 · 常见问题排查

### §5.1 · 端口被占用

```bash
# 查找占用进程
netstat -ano | findstr :8000
# 终止进程
taskkill /PID {pid} /F
```

### §5.2 · 数据库锁定

SQLite WAL 模式下极少出现锁定。如出现：
1. 确认没有多个进程同时写入
2. 检查 `backend/data/zhangfang.db-wal` 文件是否存在异常

### §5.3 · 前端构建失败

```bash
# 清理重新安装
rm -rf frontend/node_modules frontend/dist
cd frontend && npm install && npm run build
```

### §5.4 · AI 连接失败

1. 检查 AI 配置页面中的 Provider 地址和密钥
2. 确认网络能访问 Provider API
3. 查看 `ai_call_logs` 表中的错误信息

---

**版本**
- v1.0 · 2026-05-02 · 首次发布
