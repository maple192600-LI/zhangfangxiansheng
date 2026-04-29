# 本地开发与部署说明

本文面向接手开发或本地验证的维护者，描述账房先生 V1 在 Windows 本机的准备、启动、测试和打包流程。

## 1. 前置要求

- Windows 10/11
- Python 3.11 或更高版本
- Node.js 18 或更高版本
- Git

建议在项目根目录执行所有命令：

```powershell
cd F:\zhangfangxiansheng
```

## 2. 一键准备

```powershell
.\setup.bat
```

脚本会创建 `backend\venv`、安装后端依赖、安装前端依赖并执行 `npm run build`。

## 3. 后端开发启动

```powershell
cd backend
python -m venv venv
.\venv\Scripts\pip.exe install -r requirements.txt
.\venv\Scripts\python.exe main.py
```

默认服务地址：

```text
http://127.0.0.1:8000
```

启动时后端会执行 Alembic `upgrade head`，并初始化默认用户与 Agent 预留骨架。

## 4. 前端开发启动

```powershell
cd frontend
npm install
npm run dev
```

生产构建：

```powershell
npm run build
```

构建产物写入 `frontend\dist`。后端检测到该目录后会挂载 SPA 页面。

## 5. 环境变量

可从 `.env.example` 复制：

```text
ZF_SECRET_KEY=set_a_long_random_string_here
ZF_DB_PATH=backend/data/zhangfang.db
ZF_LOG_LEVEL=INFO
```

说明：

- `ZF_SECRET_KEY`：JWT 与本地安全相关密钥。生产或真实数据环境必须设置为足够长的随机字符串。
- `ZF_DB_PATH`：SQLite 数据库路径。测试临时库可以设置为其他 `.db` 文件。
- `ZF_LOG_LEVEL`：预留日志等级配置，当前主要用于部署约定。

## 6. 数据库迁移

后端启动会自动运行：

```powershell
backend\venv\Scripts\alembic.exe upgrade head
```

手工执行：

```powershell
backend\venv\Scripts\alembic.exe upgrade head
```

当前 B 方案基线为 v2 schema，v3 尝试迁移已归档到 `docs\99_archived\v3_attempt`。

## 7. 测试命令

后端全量：

```powershell
backend\venv\Scripts\pytest.exe tests\backend
```

服务层覆盖率：

```powershell
backend\venv\Scripts\pytest.exe tests\backend --cov=backend/services --cov-report=term-missing --cov-fail-under=70
```

端到端业务闭环：

```powershell
backend\venv\Scripts\pytest.exe tests\e2e\test_full_flow.py
```

当前本地环境未安装 Playwright；端到端脚本先覆盖服务级上传、预览、确认、日报、导出闭环。

## 8. 打包 exe

先构建前端：

```powershell
cd frontend
npm run build
cd ..
```

安装并执行 PyInstaller：

```powershell
backend\venv\Scripts\pip.exe install pyinstaller
backend\venv\Scripts\pyinstaller.exe --onefile --name zhangfang --paths backend backend\main.py
```

基础产物：

```text
dist\zhangfang.exe
```

正式交付前还需要校验：

- `frontend\dist` 是否随包分发或被正确定位
- `alembic.ini` 与 `alembic\versions` 是否随包可用
- `backend\data` 的初始目录是否存在
- 备份、上传、导出目录是否有写权限

## 9. 数据安全提醒

- `backend\data\zhangfang.db` 包含业务数据和本地明文 API Key，不要直接发送给无关人员。
- 做迁移、回滚、恢复前先复制数据库备份。
- 若测试真实银行流水，先放入 `tests\fixtures` 或 `samples` 的脱敏副本。
