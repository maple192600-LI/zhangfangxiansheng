"""银行流水导入服务层

上传 → 模板匹配 → 预览 → 确认提交 全流程。
"""
import json
import os
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core.parser_engine import (
    apply_mapping, detect_format, detect_header_row,
    match_template, normalize_amount, normalize_date,
    read_file_from_bytes,
)
from core.ai_call import chat
from core.security import decrypt_key
from db.tables import FundEvent, ImportBatch, ParserTemplate, AIConfig
from config import DATA_DIR
from services import log_service


# ──────────────────────────────────────────
# 上传
# ──────────────────────────────────────────

def upload_file(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx/csv")

    # 读取原始行
    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空或行数不足")

    # 检测表头
    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx] if h and h.strip()]

    # 查找匹配模板
    templates = _get_active_templates(db, "bank")
    tpl = match_template(headers, [
        {
            "sample_headers": t.sample_headers,
            "header_row": t.header_row,
            "skip_rows": t.skip_rows,
            "mapping_json": t.mapping_json,
            "id": t.id,
            "template_name": t.template_name,
        }
        for t in templates
    ])

    # 保存文件
    os.makedirs(os.path.join(DATA_DIR, "uploads"), exist_ok=True)
    batch_code = f"BANK_{date.today().strftime('%Y%m%d')}_{uuid.uuid4().hex[:4].upper()}"
    file_path = os.path.join(DATA_DIR, "uploads", f"{batch_code}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    # 创建批次
    batch = ImportBatch(
        batch_code=batch_code,
        source_type="bank",
        source_name=filename,
        status="uploaded",
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    result: Dict[str, Any] = {
        "batch_code": batch_code,
        "batch_id": batch.id,
        "file_name": filename,
        "detected_format": fmt,
        "row_count": len(rows) - header_idx - 1,
        "headers": headers,
        "header_row": header_idx,
        "template_match": None,
    }

    if tpl:
        result["template_match"] = {
            "matched": True,
            "template_id": tpl["id"],
            "template_name": tpl["template_name"],
            "confidence": "high",
        }

    log_service.write_log(db, action="batch_upload", module="bank_import", detail={
        "batch_code": batch_code, "filename": filename, "rows": len(rows) - header_idx - 1,
    }, batch_id=batch.id)
    return result


# ──────────────────────────────────────────
# 预览
# ──────────────────────────────────────────

def preview(
    db: Session,
    batch_code: str,
    template_id: Optional[int] = None,
    header_row: Optional[int] = None,
    mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    # 重新读取文件
    upload_dir = os.path.join(DATA_DIR, "uploads")
    file_data = None
    filename = batch.source_name or ""
    for f in os.listdir(upload_dir):
        if batch_code in f:
            with open(os.path.join(upload_dir, f), "rb") as fh:
                file_data = fh.read()
            break
    if not file_data:
        raise ValueError("原始文件未找到")

    fmt = detect_format(filename)
    rows = read_file_from_bytes(file_data, filename, fmt)

    # 确定模板
    tpl_mapping = mapping
    h_row = header_row if header_row is not None else detect_header_row(rows)

    if template_id and not tpl_mapping:
        tpl = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
        if not tpl:
            raise ValueError("模板不存在")
        h_row = tpl.header_row
        raw_mapping = tpl.mapping_json
        if isinstance(raw_mapping, str):
            tpl_mapping = json.loads(raw_mapping)
        else:
            tpl_mapping = raw_mapping

    if not tpl_mapping:
        return {
            "batch_code": batch_code,
            "headers": [h.strip() for h in rows[h_row] if h and h.strip()],
            "header_row": h_row,
            "parsed_rows": [],
            "abnormal_rows": [],
            "message": "未提供映射，请先配置模板或手动映射",
        }

    # 执行映射
    parsed = apply_mapping(rows, h_row, tpl_mapping)
    valid_rows = []
    abnormal_rows = []

    for row in parsed:
        errors = _validate_row(row)
        if errors:
            row["_errors"] = errors
            abnormal_rows.append(row)
        else:
            row["_errors"] = []
            valid_rows.append(row)

    # 更新批次状态
    batch.status = "previewed"
    db.commit()

    return {
        "batch_code": batch_code,
        "total_count": len(parsed),
        "valid_count": len(valid_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": valid_rows,
        "abnormal_rows": abnormal_rows,
    }


# ──────────────────────────────────────────
# 确认提交
# ──────────────────────────────────────────

def commit(db: Session, batch_code: str, parsed_rows: List[Dict]) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    committed = 0
    abnormal = 0

    for row in parsed_rows:
        event = FundEvent(
            batch_id=batch.id,
            source_type="bank",
            business_date=_to_date(row.get("business_date")),
            business_time=row.get("business_time", ""),
            entity_id=row.get("_entity_id"),
            account_id=row.get("_account_id"),
            direction=_infer_direction(row),
            income_amount=normalize_amount(row.get("income_amount", "0")),
            expense_amount=normalize_amount(row.get("expense_amount", "0")),
            counterparty_name=row.get("counterparty_name", ""),
            summary_text=row.get("summary_text", ""),
            previous_balance_input=normalize_amount(row.get("previous_balance_input", "")),
            ending_balance_input=normalize_amount(row.get("ending_balance_input", "")),
            parse_status="valid",
            raw_data_json=json.dumps(row, ensure_ascii=False),
        )

        errors = row.get("_errors", [])
        if errors:
            event.parse_status = "abnormal"
            event.abnormal_code = errors[0]
            abnormal += 1
        else:
            committed += 1

        db.add(event)

    batch.status = "committed"
    db.commit()

    log_service.write_log(db, action="batch_commit", module="bank_import", detail={
        "batch_code": batch_code, "committed": committed, "abnormal": abnormal,
    }, batch_id=batch.id)
    return {
        "batch_code": batch_code,
        "committed_count": committed,
        "abnormal_count": abnormal,
        "batch_status": "committed",
    }


# ──────────────────────────────────────────
# 模板 CRUD
# ──────────────────────────────────────────

def list_templates(db: Session, template_type: Optional[str] = None) -> List[Dict]:
    q = db.query(ParserTemplate)
    if template_type:
        q = q.filter(ParserTemplate.template_type == template_type)
    rows = q.order_by(ParserTemplate.id).all()
    return [_tpl_out(r) for r in rows]


def create_template(db: Session, data: Dict) -> Dict:
    obj = ParserTemplate(
        template_name=data["template_name"],
        template_type=data.get("template_type", "bank"),
        file_format=data.get("file_format", "xlsx"),
        header_row=data.get("header_row", 0),
        skip_rows=data.get("skip_rows", 0),
        sample_headers=json.dumps(data.get("sample_headers", []), ensure_ascii=False),
        mapping_json=json.dumps(data["mapping_json"], ensure_ascii=False) if isinstance(data["mapping_json"], dict) else data["mapping_json"],
        created_by=data.get("created_by", "manual"),
        status="active",
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return _tpl_out(obj)


# ──────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────

def _get_active_templates(db: Session, template_type: str) -> List[ParserTemplate]:
    return db.query(ParserTemplate).filter(
        ParserTemplate.template_type == template_type,
        ParserTemplate.status == "active",
    ).all()


def _validate_row(row: Dict) -> List[str]:
    errors = []
    biz_date = row.get("business_date", "")
    if not biz_date or not normalize_date(biz_date):
        errors.append("CORE_FIELD_MISSING")

    summary = row.get("summary_text", "")
    if not summary.strip():
        errors.append("CORE_FIELD_MISSING")

    income = normalize_amount(row.get("income_amount", ""))
    expense = normalize_amount(row.get("expense_amount", ""))
    if income is None and expense is None:
        errors.append("CORE_FIELD_MISSING")
    elif income and expense and income > 0 and expense > 0:
        errors.append("TEMPLATE_PARSE_FAILED")

    return errors


def _infer_direction(row: Dict) -> str:
    income = normalize_amount(row.get("income_amount", "")) or 0
    expense = normalize_amount(row.get("expense_amount", "")) or 0
    if income > 0:
        return "income"
    if expense > 0:
        return "expense"
    return "unknown"


def _to_date(val) -> Optional[date]:
    s = normalize_date(str(val)) if val else None
    if s:
        return date.fromisoformat(s)
    return None


def _tpl_out(r: ParserTemplate) -> Dict:
    mapping = r.mapping_json
    if isinstance(mapping, str):
        try:
            mapping = json.loads(mapping)
        except json.JSONDecodeError:
            mapping = {}
    sample = r.sample_headers
    if isinstance(sample, str):
        try:
            sample = json.loads(sample)
        except json.JSONDecodeError:
            sample = []
    return {
        "id": r.id,
        "template_name": r.template_name,
        "template_type": r.template_type,
        "file_format": r.file_format,
        "header_row": r.header_row,
        "skip_rows": r.skip_rows,
        "sample_headers": sample,
        "mapping_json": mapping,
        "created_by": r.created_by,
        "status": r.status,
        "created_at": r.created_at,
        "updated_at": r.updated_at,
    }


# ──────────────────────────────────────────
# AI 智能解析
# ──────────────────────────────────────────

# 标准字段列表（供 AI 参考映射）
STANDARD_FIELDS = {
    "business_date": "交易日期",
    "income_amount": "收入金额",
    "expense_amount": "支出金额",
    "counterparty_name": "对方户名/对方名称",
    "summary_text": "摘要/用途",
    "balance": "余额",
    "business_time": "交易时间",
    "counterpart_account": "对方账号",
    "counterpart_bank": "对方开户行",
    "voucher_no": "凭证号",
    "transaction_type": "交易类型",
}


def ai_parse_headers(db: Session, headers: list, sample_rows: list = None) -> Dict[str, Any]:
    """用 AI 分析银行流水表头，自动生成列映射。

    Args:
        headers: 检测到的表头列名列表
        sample_rows: 可选的前几行样本数据
    Returns:
        {"mapping": {银行列名: 标准字段}, "suggested_name": str, "confidence": str}
    """
    # 获取默认 AI 配置
    ai_cfg = db.query(AIConfig).filter(
        AIConfig.status == "active",
    ).order_by(AIConfig.is_default.desc()).first()

    if not ai_cfg:
        return {
            "ok": False,
            "error": "未配置 AI 提供商，请先在「系统设置 → AI配置」中添加 API KEY",
        }

    api_key = decrypt_key(ai_cfg.api_key_encrypted)

    # 构造 prompt
    field_desc = "\n".join(f"  - {k}: {v}" for k, v in STANDARD_FIELDS.items())
    header_list = ", ".join(f'"{h}"' for h in headers)

    sample_text = ""
    if sample_rows:
        lines = []
        for row in sample_rows[:3]:
            if isinstance(row, (list, tuple)):
                lines.append(" | ".join(str(c) for c in row))
        if lines:
            sample_text = f"\n\n前几行样本数据:\n" + "\n".join(lines)

    prompt = f"""你是一个银行流水解析专家。请分析以下银行流水的表头列名，将每列映射到对应的标准字段。

## 表头列名
{header_list}
{sample_text}

## 可用标准字段
{field_desc}

## 要求
1. 返回 JSON 格式：{{"银行列名": "标准字段code"}}
2. 只映射能匹配的列，不确定的不映射
3. business_date 是必须映射的核心字段
4. 如果列名含义不明确，参考样本数据判断
5. 同时建议一个模板名称（如：xx银行标准流水）

请严格返回如下 JSON 格式（不要包含其他文字）:
{{"mapping": {{"银行列名1": "field1", "银行列名2": "field2"}}, "template_name": "建议的模板名称"}}"""

    result = chat(
        provider=ai_cfg.provider,
        api_key=api_key,
        base_url=ai_cfg.base_url,
        model_name=ai_cfg.model_name,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=512,
        timeout=300,
    )

    if not result.get("ok"):
        return {"ok": False, "error": f"AI 调用失败: {result.get('error', '未知错误')}"}

    content = result["content"].strip()

    # 尝试从返回内容中提取 JSON
    try:
        # 去掉 markdown 代码块标记
        if content.startswith("```"):
            content = content.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        parsed = json.loads(content)
        mapping = parsed.get("mapping", {})
        template_name = parsed.get("template_name", "AI自动识别模板")
    except json.JSONDecodeError:
        return {"ok": False, "error": "AI 返回格式异常，请重试或手动配置映射", "raw": content}

    # 验证映射字段合法性
    valid_mapping = {}
    for bank_col, field_code in mapping.items():
        if field_code in STANDARD_FIELDS:
            valid_mapping[bank_col] = field_code

    if not valid_mapping:
        return {"ok": False, "error": "AI 未能识别出有效的列映射"}

    has_date = any(v == "business_date" for v in valid_mapping.values())
    confidence = "high" if has_date and len(valid_mapping) >= 3 else "medium" if has_date else "low"

    return {
        "ok": True,
        "mapping": valid_mapping,
        "template_name": template_name,
        "confidence": confidence,
        "matched_count": len(valid_mapping),
        "total_columns": len(headers),
    }
