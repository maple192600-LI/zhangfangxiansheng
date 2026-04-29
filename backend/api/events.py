"""Exception center API for fund events."""
import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.response import ErrorCode, error, success
from database import get_db
from services import exception_center_service as svc

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/events", tags=["events"])


class ResolveBody(BaseModel):
    fixes: Optional[Dict[str, Any]] = None
    note: Optional[str] = None
    operator: str = "admin"


class VoidBody(BaseModel):
    reason: Optional[str] = None
    operator: str = "admin"


@router.get("/pending")
def pending_events(
    state: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        return success(svc.query_pending_events(db, state, keyword, page, page_size))
    except ValueError as exc:
        return error(ErrorCode.PARAM_FORMAT, str(exc))
    except Exception as exc:
        logger.error("查询异常中心失败: %s", str(exc), exc_info=True)
        return error(ErrorCode.INTERNAL, "查询异常中心失败")


@router.put("/{event_id}/resolve")
def resolve_event(event_id: int, body: ResolveBody, db: Session = Depends(get_db)):
    try:
        return success(svc.resolve_event(db, event_id, body.fixes, body.note, body.operator))
    except LookupError as exc:
        return error(ErrorCode.NOT_FOUND, str(exc))
    except ValueError as exc:
        return error(ErrorCode.STATE_INVALID, str(exc))
    except Exception as exc:
        logger.error("处理异常流水失败: %s", str(exc), exc_info=True)
        return error(ErrorCode.INTERNAL, "处理异常流水失败")


@router.put("/{event_id}/void")
def void_event(event_id: int, body: VoidBody, db: Session = Depends(get_db)):
    try:
        return success(svc.void_event(db, event_id, body.reason, body.operator))
    except LookupError as exc:
        return error(ErrorCode.NOT_FOUND, str(exc))
    except ValueError as exc:
        return error(ErrorCode.STATE_INVALID, str(exc))
    except Exception as exc:
        logger.error("作废异常流水失败: %s", str(exc), exc_info=True)
        return error(ErrorCode.INTERNAL, "作废异常流水失败")
