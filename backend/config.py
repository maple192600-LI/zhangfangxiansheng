"""账房先生 V1 配置"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
DB_PATH = os.path.join(DATA_DIR, "zhangfang.db")
BACKUP_DIR = os.path.join(BASE_DIR, "..", "backups")
EXPORT_DIR = os.path.join(BASE_DIR, "..", "exports")

HOST = "127.0.0.1"
PORT = 8000

FRONTEND_DIST = os.path.join(BASE_DIR, "..", "frontend", "dist")

# ── 认证配置 ──
_DEFAULT_SECRET = "zf-v1-default-secret-key-change-in-prod"
SECRET_KEY = os.environ.get("ZF_SECRET_KEY", _DEFAULT_SECRET)
TOKEN_EXPIRE_MINUTES = int(os.environ.get("ZF_TOKEN_EXPIRE_MINUTES", "480"))

# 启动时检测默认密钥
if SECRET_KEY == _DEFAULT_SECRET:
    import hashlib
    # 基于数据库路径生成确定性密钥（本地部署场景）
    _derived = hashlib.sha256(DB_PATH.encode()).hexdigest()
    SECRET_KEY = _derived
    import warnings
    warnings.warn(
        "未设置 ZF_SECRET_KEY 环境变量，已基于数据库路径自动生成安全密钥。"
        "建议设置 ZF_SECRET_KEY 环境变量。",
        UserWarning,
        stacklevel=2,
    )

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
