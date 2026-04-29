"""报表 API — 日报/日记账/余额表/收支明细"""
import logging
import os
import time
import uuid
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import DATA_DIR
from database import get_db
from core.response import success, error
from db.tables import RuleArtifact, TemplateInferenceJob
from services import report_service as svc
from services.base_data_service import _parse_date
from services import log_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


class GenerateReportBody(BaseModel):
    rule_id: int
    account_code: str
    period_start: str
    period_end: str
    entity_code: Optional[str] = None
    template_file: Optional[str] = None


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
    except Exception as e:
        logger.error("生成日报失败: %s", str(e), exc_info=True)
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
    except Exception as e:
        logger.error("查询日记账失败: %s", str(e), exc_info=True)
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
    except Exception as e:
        logger.error("查询余额表失败: %s", str(e), exc_info=True)
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
    except Exception as e:
        logger.error("查询收入明细失败: %s", str(e), exc_info=True)
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
    except Exception as e:
        logger.error("查询支出明细失败: %s", str(e), exc_info=True)
        return error(5000, "查询支出明细失败，请检查参数后重试")


@router.get("/major-balance")
def get_major_balance(
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
        result = svc.major_balance(db, sd, ed, entity_id)
        return success(result)
    except Exception as e:
        logger.error("查询主要账户余额表失败: %s", str(e), exc_info=True)
        return error(5000, "查询主要账户余额表失败")


@router.get("/month-check")
def get_month_check(
    year: int = Query(date.today().year),
    month: int = Query(date.today().month),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        result = svc.month_check(db, year, month, entity_id)
        return success(result)
    except Exception as e:
        logger.error("查询月末盘点表失败: %s", str(e), exc_info=True)
        return error(5000, "查询月末盘点表失败")


@router.get("/week-report")
def get_week_report(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        today = date.today()
        week_ago = today - timedelta(days=6)
        sd = _to_date(start_date, week_ago.isoformat())
        ed = _to_date(end_date, today.isoformat())
        result = svc.week_report(db, sd, ed, entity_id)
        return success(result)
    except Exception as e:
        logger.error("查询资金周报失败: %s", str(e), exc_info=True)
        return error(5000, "查询资金周报失败")


@router.get("/month-report")
def get_month_report(
    year: int = Query(date.today().year),
    month: int = Query(date.today().month),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        result = svc.month_report(db, year, month, entity_id)
        return success(result)
    except Exception as e:
        logger.error("查询资金月报失败: %s", str(e), exc_info=True)
        return error(5000, "查询资金月报失败")


@router.get("/year-report")
def get_year_report(
    year: int = Query(date.today().year),
    entity_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    try:
        result = svc.year_report(db, year, entity_id)
        return success(result)
    except Exception as e:
        logger.error("查询资金年报失败: %s", str(e), exc_info=True)
        return error(5000, "查询资金年报失败")


@router.post("/generate")
def generate_report(body: GenerateReportBody, db: Session = Depends(get_db)):
    started = time.perf_counter()
    rule = db.query(RuleArtifact).filter(RuleArtifact.id == body.rule_id).first()
    if rule is None:
        return error(2001, "Rule artifact 不存在")
    if rule.status != "active":
        return error(2002, "Rule artifact 尚未审批通过")

    template_file = body.template_file or _template_file_for_rule(db, body.rule_id)
    if not template_file or not os.path.isfile(template_file):
        return error(2001, "报表模板文件不存在")

    ctx = {
        "template_file": template_file,
        "account_code": body.account_code,
        "entity_code": body.entity_code,
        "start_date": _to_date(body.period_start),
        "end_date": _to_date(body.period_end),
        "period_start": _to_date(body.period_start),
        "period_end": _to_date(body.period_end),
    }
    try:
        wb = svc.generate_report(db, body.rule_id, ctx)
        report_id = f"rpt-{date.today().strftime('%Y%m%d')}-{uuid.uuid4().hex[:8]}"
        out_dir = os.path.join(DATA_DIR, "generated_reports")
        os.makedirs(out_dir, exist_ok=True)
        out_path = os.path.join(out_dir, f"{report_id}.xlsx")
        wb.save(out_path)
        elapsed_ms = int((time.perf_counter() - started) * 1000)
        placeholder_filled = len(rule.placeholder_bindings or {}) + len(((rule.loop_config or {}).get("columns") or {}))
        log_service.write_log(
            db,
            action="report_generate",
            module="reports",
            detail={"report_id": report_id, "rule_id": body.rule_id, "runtime_ms": elapsed_ms},
        )
        return success({
            "report_id": report_id,
            "download_url": f"/api/reports/download/{report_id}",
            "placeholder_filled": placeholder_filled,
            "rows_written": 0,
            "runtime_ms": elapsed_ms,
        })
    except Exception as exc:
        logger.error("Rule artifact 生成报表失败: %s", str(exc), exc_info=True)
        return error(5000, f"生成报表失败: {exc}")


@router.get("/download/{report_id}")
def download_report(report_id: str):
    safe_id = os.path.basename(report_id)
    path = os.path.join(DATA_DIR, "generated_reports", f"{safe_id}.xlsx")
    if not os.path.isfile(path):
        return error(2001, "报表文件不存在")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{safe_id}.xlsx",
    )


def _template_file_for_rule(db: Session, rule_id: int) -> Optional[str]:
    job = (
        db.query(TemplateInferenceJob)
        .filter(TemplateInferenceJob.rule_artifact_id == rule_id)
        .order_by(TemplateInferenceJob.id.desc())
        .first()
    )
    if job is None:
        return None
    return job.file_path or job.template_file
