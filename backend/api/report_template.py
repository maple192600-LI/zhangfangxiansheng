"""报表模板 API — CRUD + Excel上传解析 + 默认模板"""
import logging
import os
import shutil
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.orm import Session

from database import get_db
from config import DATA_DIR
from core.response import success, error
from services import report_template_service as svc
from db.schemas import REPORT_TYPES

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/report-templates", tags=["report-templates"])


@router.get("/types")
def get_report_types():
    """获取11种报表类型列表"""
    return success(REPORT_TYPES)


@router.get("")
def list_templates(
    report_type: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """查询模板列表"""
    result = svc.list_templates(db, report_type, status)
    return success(result)


REPORT_TYPE_CODES = {rt["code"] for rt in REPORT_TYPES}


@router.get("/default/{report_type}")
def get_default_template(report_type: str, db: Session = Depends(get_db)):
    """获取某报表类型的默认模板"""
    if report_type not in REPORT_TYPE_CODES:
        return error(4001, f"不支持的报表类型: {report_type}")
    result = svc.get_default_template(db, report_type)
    return success(result)


@router.get("/{template_id}")
def get_template(template_id: int, db: Session = Depends(get_db)):
    """获取模板详情"""
    result = svc.get_template(db, template_id)
    if not result:
        return error(4004, "模板不存在")
    return success(result)


@router.post("")
async def create_template(request: Request, db: Session = Depends(get_db)):
    """创建模板"""
    try:
        body = await request.json()
        if body.get("report_type") not in REPORT_TYPE_CODES:
            return error(4001, f"不支持的报表类型: {body.get('report_type')}")
        result = svc.create_template(db, body)
        return success(result)
    except Exception as e:
        logger.error("创建模板失败: %s", str(e), exc_info=True)
        return error(5000, "创建模板失败")


@router.put("/{template_id}")
async def update_template(template_id: int, request: Request, db: Session = Depends(get_db)):
    """更新模板"""
    try:
        body = await request.json()
        result = svc.update_template(db, template_id, body)
        if not result:
            return error(4004, "模板不存在")
        return success(result)
    except Exception as e:
        logger.error("更新模板失败: %s", str(e), exc_info=True)
        return error(5000, "更新模板失败")


@router.delete("/{template_id}")
def delete_template(template_id: int, db: Session = Depends(get_db)):
    """软删除模板"""
    ok = svc.delete_template(db, template_id)
    if not ok:
        return error(4004, "模板不存在")
    return success(None, "已删除")


@router.put("/{template_id}/set-default")
def set_default(template_id: int, db: Session = Depends(get_db)):
    """设为默认模板"""
    result = svc.set_default(db, template_id)
    if not result:
        return error(4004, "模板不存在或已停用")
    return success(result)


@router.post("/upload")
async def upload_excel(
    file: UploadFile = File(...),
    report_type: Optional[str] = None,
    template_name: Optional[str] = None,
    save: bool = True,
    db: Session = Depends(get_db),
):
    """上传Excel：解析表头+布局，并默认直接入库保存为模板。

    Form 参数：
    - report_type: 报表类型 code（如 base_data、cash_journal、account_balance 等）
    - template_name: 模板名（不传时用文件名）
    - save: 默认 True；False 时仅预览，不入库
    """
    from fastapi import Form  # 局部 import 避免顶层循环
    if not file.filename or not file.filename.endswith((".xlsx", ".xls")):
        return error(4001, "仅支持 .xlsx / .xls 文件")

    upload_dir = os.path.join(DATA_DIR, "template_uploads")
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = os.path.basename(file.filename)
    # 保留原文件，加唯一前缀避免重名覆盖
    unique_prefix = datetime.now().strftime("%Y%m%d%H%M%S")
    saved_filename = f"{unique_prefix}_{safe_name}"
    file_path = os.path.join(upload_dir, saved_filename)
    keep_file = False
    try:
        with open(file_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        columns = svc.parse_excel_headers(file_path, report_type=report_type)
        if not columns:
            return error(4001, "未检测到表头，请检查Excel是否有内容")

        layout = svc.parse_excel_layout(file_path)

        result_payload = {"columns": columns, "layout": layout, "filename": file.filename}

        # —— 默认上传即保存 ——
        if save and report_type:
            if report_type not in REPORT_TYPE_CODES:
                return error(4001, f"未知报表类型: {report_type}，可用 {sorted(REPORT_TYPE_CODES)}")

            base_name = template_name or os.path.splitext(safe_name)[0]
            saved = svc.create_template(db, {
                "template_name": base_name,
                "report_type": report_type,
                "columns": columns,
                "layout": layout,
                "source_file_path": file_path,
                "is_default": True,
                "remark": f"从 {safe_name} 上传解析",
                "created_by": "upload",
            })
            result_payload["saved_template"] = saved
            keep_file = True  # 保留文件供后续渲染原表

        return success(result_payload)
    except Exception as e:
        logger.error("解析/保存模板失败: %s", str(e), exc_info=True)
        return error(5000, f"解析/保存模板失败: {str(e)}")
    finally:
        if not keep_file and os.path.exists(file_path):
            os.remove(file_path)


@router.get("/{template_id}/excel-html")
def get_excel_html(template_id: int, db: Session = Depends(get_db)):
    """返回模板原 Excel 的完整 HTML（保留合并/对齐/背景/字体）。

    - 若模板有 source_file_path 且文件存在，按原 Excel 渲染
    - 否则返回 404，前端 fallback 到表头模式
    """
    from db.tables import ReportTemplate
    t = db.query(ReportTemplate).filter(ReportTemplate.id == template_id).first()
    if not t:
        return error(4004, "模板不存在")
    if not t.source_file_path or not os.path.exists(t.source_file_path):
        return error(4005, "原 Excel 文件不存在，仅有表头数据")
    try:
        html = svc.excel_to_html(t.source_file_path)
        return success({"html": html, "template_id": template_id, "filename": os.path.basename(t.source_file_path)})
    except Exception as e:
        logger.error("生成 Excel HTML 失败: %s", str(e), exc_info=True)
        return error(5000, f"生成 Excel HTML 失败: {e}")


@router.get("/default/{report_type}/excel-html")
def get_default_excel_html(report_type: str, db: Session = Depends(get_db)):
    """业务页面用：拿到该报表类型的默认模板原 Excel HTML。"""
    from db.tables import ReportTemplate
    t = (
        db.query(ReportTemplate)
        .filter(
            ReportTemplate.report_type == report_type,
            ReportTemplate.is_default == True,
            ReportTemplate.status == "active",
        )
        .first()
    )
    if not t:
        return error(4004, "未配置默认模板")
    if not t.source_file_path or not os.path.exists(t.source_file_path):
        return error(4005, "原 Excel 文件不存在")
    try:
        html = svc.excel_to_html(t.source_file_path)
        return success({"html": html, "template_id": t.id, "template_code": t.template_code, "template_name": t.template_name})
    except Exception as e:
        logger.error("生成 Excel HTML 失败: %s", str(e), exc_info=True)
        return error(5000, f"生成 Excel HTML 失败: {e}")
