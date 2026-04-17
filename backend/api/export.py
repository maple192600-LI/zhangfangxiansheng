"""导出 API — 生成 Excel 并下载"""
from typing import Optional

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from database import get_db
from core.response import success, error
from services import export_service as svc
from services import log_service

router = APIRouter(prefix="/export", tags=["export"])


class ExportRequest(BaseModel):
    export_type: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    entity_id: Optional[int] = None


@router.post("/report")
def export_report(req: ExportRequest, db: Session = Depends(get_db)):
    valid_types = ["base_data", "daily_report", "cash_journal", "account_balance", "income_list", "expense_list"]
    if req.export_type not in valid_types:
        return error(1001, f"不支持的导出类型: {req.export_type}")

    try:
        filepath = svc.generate_export(
            db, req.export_type, req.start_date, req.end_date, req.entity_id
        )
        log_service.write_log(db, action="export_excel", module="export", detail={
            "export_type": req.export_type,
            "start_date": req.start_date,
            "end_date": req.end_date,
            "filepath": filepath,
        })
        return FileResponse(
            filepath,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filepath.split("/")[-1].split("\\")[-1],
            headers={"Cache-Control": "no-cache"},
        )
    except Exception as e:
        return error(5000, f"导出失败: {str(e)}")
