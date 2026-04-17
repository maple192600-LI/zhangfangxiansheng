"""备份恢复服务"""
import os
import json
import zipfile
import shutil
from datetime import datetime
from typing import Dict, Optional

from sqlalchemy import text

from config import BACKUP_DIR, DATA_DIR, DB_PATH, BASE_DIR


def list_backups() -> Dict:
    """列出已有备份"""
    os.makedirs(BACKUP_DIR, exist_ok=True)
    files = sorted(
        [f for f in os.listdir(BACKUP_DIR) if f.startswith("bk_") and f.endswith(".zip")],
        reverse=True,
    )
    items = []
    for f in files:
        path = os.path.join(BACKUP_DIR, f)
        size_mb = os.path.getsize(path) / (1024 * 1024)
        items.append({
            "filename": f,
            "size_mb": round(size_mb, 2),
            "created_at": datetime.fromtimestamp(os.path.getmtime(path)).strftime("%Y-%m-%d %H:%M:%S"),
        })
    return {"items": items, "total": len(items)}


def create_backup(db) -> Dict:
    """创建备份 ZIP"""
    os.makedirs(BACKUP_DIR, exist_ok=True)

    # 生成序号
    today_str = datetime.now().strftime("%Y%m%d")
    existing = [f for f in os.listdir(BACKUP_DIR) if f.startswith(f"bk_{today_str}")]
    seq = len(existing) + 1
    filename = f"bk_{today_str}_{seq:03d}.zip"
    filepath = os.path.join(BACKUP_DIR, filename)

    # VACUUM INTO 生成干净副本
    vacuum_path = os.path.join(DATA_DIR, "zhangfang_vacuum.db")
    if os.path.exists(vacuum_path):
        os.remove(vacuum_path)
    db.execute(text(f"VACUUM INTO '{vacuum_path}'"))
    db.commit()

    # meta.json
    db_size_mb = os.path.getsize(vacuum_path) / (1024 * 1024)
    meta = {
        "version": "1.0",
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "db_size_mb": round(db_size_mb, 2),
    }

    # 打包
    with zipfile.ZipFile(filepath, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(vacuum_path, "db/zhangfang.db")
        zf.writestr("meta.json", json.dumps(meta, ensure_ascii=False, indent=2))
        # 打包 agents 目录（如果存在）
        agents_dir = os.path.join(BASE_DIR, "agents")
        if os.path.isdir(agents_dir):
            for root, dirs, files in os.walk(agents_dir):
                for f in files:
                    full = os.path.join(root, f)
                    arcname = os.path.relpath(full, BASE_DIR)
                    zf.write(full, arcname)

    # 清理临时文件
    if os.path.exists(vacuum_path):
        os.remove(vacuum_path)

    # 保留最近 20 份
    all_backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("bk_") and f.endswith(".zip")])
    while len(all_backups) > 20:
        old = os.path.join(BACKUP_DIR, all_backups.pop(0))
        os.remove(old)

    return {
        "filename": filename,
        "size_mb": round(os.path.getsize(filepath) / (1024 * 1024), 2),
    }


def restore_backup(filename: str) -> Dict:
    """从备份 ZIP 恢复"""
    filepath = os.path.join(BACKUP_DIR, filename)
    if not os.path.exists(filepath):
        raise ValueError("备份文件不存在")

    with zipfile.ZipFile(filepath, "r") as zf:
        # 解压数据库文件
        db_in_zip = "db/zhangfang.db"
        if db_in_zip not in zf.namelist():
            raise ValueError("备份文件中未找到数据库")

        # 先备份当前数据库
        backup_current = DB_PATH + ".pre_restore"
        if os.path.exists(DB_PATH):
            shutil.copy2(DB_PATH, backup_current)

        try:
            zf.extract(db_in_zip, os.path.dirname(DATA_DIR))
            extracted = os.path.join(os.path.dirname(DATA_DIR), db_in_zip)
            shutil.move(extracted, DB_PATH)
        except Exception:
            # 恢复失败则回滚
            if os.path.exists(backup_current):
                shutil.move(backup_current, DB_PATH)
            raise

        # 清理
        if os.path.exists(backup_current):
            os.remove(backup_current)

        # 解压 agents（如果有）
        agents_files = [n for n in zf.namelist() if n.startswith("agents/")]
        if agents_files:
            agents_dir = os.path.join(BASE_DIR, "agents")
            os.makedirs(agents_dir, exist_ok=True)
            for af in agents_files:
                zf.extract(af, BASE_DIR)

    return {"restored_from": filename}
