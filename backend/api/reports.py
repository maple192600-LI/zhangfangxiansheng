"""报表 API — 日报/日记账/余额表/收支明细"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import report_service as svc
from services.base_data_service import _parse_date
from services import log_service

router = APIRouter(prefix="/reports", tags=["reports"])


def _to_date(s: Optional[str], default: Optional[str] = None) -> date:
    if s:
        return _parse_date(s)
    if default:
        return _parse_date(default)
    return date.today()


@router.get("/daily")
def get_daily_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        today = date.today().isoformat()
        sd = _to_date(start_date, today)
        ed = _to_date(end_date, today)
        result = svc.daily_report(db, sd, ed, entity_id)
        log_service.write_log(db, action="report_generate", module="daily_report", detail={
            "start_date": str(sd), "end_date": str(ed), "entity_id": entity_id,
        })
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "生成日报失败，请检查参数后重试")


@router.get("/cash-journal")
def get_cash_journal(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    account_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        today = date.today().isoformat()
        sd = _to_date(start_date, today)
        ed = _to_date(end_date, today)
        result = svc.cash_journal(db, sd, ed, account_id)
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "查询日记账失败，请检查参数后重试")


@router.get("/account-balance")
def get_account_balance(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        sd = _to_date(start_date, month_start)
        ed = _to_date(end_date, today.isoformat())
        result = svc.account_balance(db, sd, ed, entity_id)
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "查询余额表失败，请检查参数后重试")


@router.get("/income-list")
def get_income_list(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        sd = _to_date(start_date, month_start)
        ed = _to_date(end_date, today.isoformat())
        result = svc.income_list(db, sd, ed, entity_id, page, page_size)
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "查询收入明细失败，请检查参数后重试")


@router.get("/expense-list")
def get_expense_list(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    try:
        today = date.today()
        month_start = today.replace(day=1).isoformat()
        sd = _to_date(start_date, month_start)
        ed = _to_date(end_date, today.isoformat())
        result = svc.expense_list(db, sd, ed, entity_id, page, page_size)
        return success(result)
    except ValueError as e:
        return error(4001, str(e))
    except Exception:
        return error(5000, "查询支出明细失败，请检查参数后重试")
