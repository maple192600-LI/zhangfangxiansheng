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

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(EXPORT_DIR, exist_ok=True)
