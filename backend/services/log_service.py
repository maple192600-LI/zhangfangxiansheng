"""操作日志服务"""
import json
from datetime import datetime, date
from typing import Optional, Dict, Any

from sqlalchemy.orm import Session
from sqlalchemy import func

from db.tables import OperationLog


def write_log(
    db: Session,
    action: str,
    module: str,
    detail: Dict[str, Any],
    batch_id: Optional[int] = None,
) -> OperationLog:
    """写入一条操作日志"""
    log = OperationLog(
        action=action,
        module=module,
        batch_id=batch_id,
        detail_json=json.dumps(detail, ensure_ascii=False),
        created_at=datetime.now(),
    )
    db.add(log)
    db.flush()
    return log


def query_logs(
    db: Session,
    module: Optional[str] = None,
    action: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> Dict:
    """查询操作日志（分页）"""
    q = db.query(OperationLog).order_by(OperationLog.created_at.desc())

    if module:
        q = q.filter(OperationLog.module == module)
    if action:
        q = q.filter(OperationLog.action == action)
    if start_date:
        q = q.filter(OperationLog.created_at >= start_date)
    if end_date:
        end_dt = f"{end_date} 23:59:59"
        q = q.filter(OperationLog.created_at <= end_dt)

    total = q.count()
    items = q.offset((page - 1) * page_size).limit(page_size).all()

    return {
        "items": [
            {
                "id": log.id,
                "action": log.action,
                "module": log.module,
                "batch_id": log.batch_id,
                "detail": json.loads(log.detail_json) if log.detail_json else {},
                "created_at": log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
            }
            for log in items
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
    }
