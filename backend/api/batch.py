"""批次管理 API — 列表 / 回滚"""
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from db.tables import ImportBatch, FundEvent
from services import log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/batches", tags=["batch"])


@router.get("")
def list_batches(
    page: int = 1,
    page_size: int = 20,
    db: Session = Depends(get_db),
):
    try:
        total = db.query(ImportBatch).count()
        items = (
            db.query(ImportBatch)
            .order_by(ImportBatch.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return success({
            "items": [
                {
                    "id": b.id,
                    "batch_code": b.batch_code,
                    "source_type": b.source_type,
                    "source_name": b.source_name,
                    "status": b.status,
                    "event_count": db.query(FundEvent).filter(FundEvent.batch_id == b.id).count(),
                    "created_at": b.created_at.strftime("%Y-%m-%d %H:%M:%S") if b.created_at else "",
                }
                for b in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
        })
    except Exception as e:
        logger.error("获取批次列表失败: %s", str(e), exc_info=True)
        return error(5000, "获取批次列表失败")


@router.post("/{batch_id}/rollback")
def rollback_batch(batch_id: int, db: Session = Depends(get_db)):
    try:
        batch = db.query(ImportBatch).filter(ImportBatch.id == batch_id).first()
        if not batch:
            return error(2001, "批次不存在")

        # 将关联事件标记为 rolled_back
        events = db.query(FundEvent).filter(FundEvent.batch_id == batch_id).all()
        for e in events:
            e.state = "已作废"

        batch.status = "rolled_back"
        db.commit()

        log_service.write_log(db, action="batch_rollback", module="batch", detail={
            "batch_id": batch_id,
            "batch_code": batch.batch_code,
            "affected_events": len(events),
        })

        return success({"batch_id": batch_id, "rolled_back_events": len(events)})
    except Exception as e:
        db.rollback()
        logger.error("回滚失败: %s", str(e), exc_info=True)
        return error(5000, "回滚失败，请查看操作日志")
