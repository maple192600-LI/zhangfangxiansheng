"""银行流水导入服务层

上传 → Parser 匹配 → 预览 → 确认提交 全流程。
"""
import json
import os
import re
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from core import artifact_runtime
from core.parser_engine import (
    apply_mapping, detect_format, detect_header_row,
    match_template, normalize_amount, normalize_date,
    read_file_from_bytes,
)
from core.ai_call import chat
from core.ai_parse_utils import (
    strip_thinking_tags, extract_and_parse_json,
    find_active_agent, call_agent_for_mapping,
    shorten_headers, format_sample_text,
    restore_mapping_keys, validate_mapping_confidence,
)
from core.pii_masker import mask_row
from core.security import decrypt_key
from db.tables import FundEvent, ImportBatch, ParserArtifact, ParserTemplate, AIConfig
from config import DATA_DIR
from services import log_service


# ──────────────────────────────────────────
# 上传
# ──────────────────────────────────────────

def _fix_filename(filename: str) -> str:
    """修复 multipart 上传中文文件名编码问题。

    浏览器发送 UTF-8 编码的 filename，但 HTTP multipart 头部按 latin-1 解码，
    导致中文变成乱码。通过反向操作恢复：encode('latin-1') → decode('utf-8')。
    """
    if not filename:
        return filename
    # 纯 ASCII 不需要修复
    try:
        filename.encode("ascii")
        return filename
    except UnicodeEncodeError:
        pass
    # 尝试 latin-1 → UTF-8 反向修复
    try:
        raw_bytes = filename.encode("latin-1")
        decoded = raw_bytes.decode("utf-8")
        # 如果解码成功且包含中文字符，说明修复成功
        if any("\u4e00" <= c <= "\u9fff" for c in decoded):
            return decoded
    except (UnicodeDecodeError, UnicodeEncodeError):
        pass
    return filename


def upload_file(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    filename = _fix_filename(filename)
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
    sample_rows = [
        [str(c).strip() if c else "" for c in row[:len(headers)]]
        for row in rows[header_idx + 1:header_idx + 6]
        if any(c and str(c).strip() for c in row)
    ]

    # 查找兼容模板，辅助旧数据迁移和账号线索识别。
    templates = _get_active_templates(db, "bank")
    tpl = match_template(headers, [
        {
            "sample_headers": t.sample_headers,
            "header_row": t.header_row,
            "skip_rows": t.skip_rows,
            "mapping_json": t.mapping_json,
            "id": t.id,
            "template_name": t.template_name,
            "account_code": t.account_code,
        }
        for t in templates
    ])
    matched_account_code = tpl.get("account_code") if tpl else None
    parser_artifact = _match_active_parser_artifact(db, "bank", matched_account_code)

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
        "sample_rows": sample_rows,
        "header_row": header_idx,
        "parser_match": _parser_match_out(parser_artifact) if parser_artifact else None,
        "template_match": None,
    }

    if tpl:
        # 提取模板的 mapping_json（可能是字符串或已解析的 dict）
        tpl_mapping = tpl.get("mapping_json", {})
        if isinstance(tpl_mapping, str):
            try:
                tpl_mapping = json.loads(tpl_mapping)
            except json.JSONDecodeError:
                tpl_mapping = {}
        result["template_match"] = {
            "matched": True,
            "template_id": tpl["id"],
            "template_name": tpl["template_name"],
            "mapping": tpl_mapping,
            "header_row": tpl.get("header_row", header_idx),
            "account_code": tpl.get("account_code"),
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
    parser_artifact_id: Optional[int] = None,
    template_id: Optional[int] = None,
    header_row: Optional[int] = None,
    mapping: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    filename = batch.source_name or ""
    file_path = _find_uploaded_file(batch_code, filename)
    if not file_path:
        raise ValueError("原始文件未找到")

    if parser_artifact_id:
        rows = list(
            artifact_runtime.run_parser(
                db,
                parser_artifact_id,
                file_path,
                {"batch_code": batch_code},
            )
        )
        result = _preview_from_canonical_rows(batch_code, rows)
        batch.status = "previewed"
        db.commit()
        return result

    # 兼容旧 mapping 模板预览。
    with open(file_path, "rb") as fh:
        file_data = fh.read()
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
        # 规范化日期字段显示
        raw_date = row.get("business_date", "")
        norm_date = normalize_date(raw_date)
        if norm_date:
            row["business_date"] = norm_date
        # 自动生成 fallback 摘要
        _ensure_summary(row)
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

def commit(db: Session, batch_code: str, parser_artifact_id: int) -> Dict[str, Any]:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")
    file_path = _find_uploaded_file(batch_code, batch.source_name or "")
    if not file_path:
        raise ValueError("原始上传文件未找到")

    db.query(FundEvent).filter(FundEvent.batch_id == batch.id).delete()
    rows = list(
        artifact_runtime.run_parser(
            db,
            parser_artifact_id,
            file_path,
            {"batch_code": batch_code},
        )
    )
    for row in rows:
        db.add(FundEvent(**row, batch_id=batch.id, parser_artifact_id=parser_artifact_id))
    batch.status = "committed"
    batch.updated_at = datetime.now()
    db.commit()

    log_service.write_log(
        db,
        action="batch_commit",
        module="bank_import",
        detail={
            "batch_code": batch_code,
            "parser_artifact_id": parser_artifact_id,
            "inserted_rows": len(rows),
        },
        batch_id=batch.id,
    )
    return {
        "batch_code": batch_code,
        "parser_artifact_id": parser_artifact_id,
        "inserted_rows": len(rows),
    }


def commit_by_mapping(
    db: Session,
    batch_code: str,
    account_code: Optional[str] = None,
    mapping: Optional[Dict[str, str]] = None,
    template_id: Optional[int] = None,
    template_name: str = None,
    sample_headers: list = None,
) -> Dict[str, Any]:
    """基于模板映射直接提交入库（不依赖 fund agent parser artifact）。account_code 可从模板自动获取。"""
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError("批次不存在")

    file_path = _find_uploaded_file(batch_code, batch.source_name or "")
    if not file_path:
        raise ValueError("原始上传文件未找到")

    # 获取账户信息 — 优先使用传入的 account_code，否则从模板获取
    tpl_mapping = mapping
    h_row = None
    tpl = None

    if template_id:
        tpl = db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
        if tpl:
            h_row = tpl.header_row
            raw_mapping = tpl.mapping_json
            if isinstance(raw_mapping, str):
                tpl_mapping = json.loads(raw_mapping)
            else:
                tpl_mapping = raw_mapping
            if not account_code:
                account_code = tpl.account_code

    if not account_code:
        raise ValueError("未指定账户，且模板中也无关联账户，请先通过 AI 智能体创建包含账户的解析规则")

    from db.tables import Account, Entity
    account = db.query(Account).filter(Account.account_code == account_code).first()
    if not account:
        raise ValueError(f"账户不存在: {account_code}")
    entity = db.query(Entity).filter(Entity.id == account.entity_id).first()
    entity_code = entity.entity_code if entity else ""
    entity_name = entity.name if entity else ""
    account_alias = account.account_alias or account_code

    # 读取文件并应用映射
    fmt = detect_format(batch.source_name or "")
    with open(file_path, "rb") as fh:
        file_data = fh.read()
    rows_raw = read_file_from_bytes(
        file_data,
        batch.source_name or "",
        fmt,
    )
    header_idx = detect_header_row(rows_raw)

    if h_row is None:
        h_row = header_idx

    if not tpl_mapping:
        raise ValueError("未提供列映射，请先配置模板或手动映射")

    parsed = apply_mapping(rows_raw, h_row, tpl_mapping)

    # 清除旧数据
    db.query(FundEvent).filter(FundEvent.batch_id == batch.id).delete()

    inserted = 0
    for row in parsed:
        # 自动生成 fallback 摘要
        _ensure_summary(row)
        biz_date_str = normalize_date(row.get("business_date", ""))
        if not biz_date_str:
            continue

        income = normalize_amount(row.get("income_amount", "")) or 0
        expense = normalize_amount(row.get("expense_amount", "")) or 0

        # 处理单列金额（正负值）：负值视为支出
        if income < 0:
            expense = abs(income)
            income = 0

        event = FundEvent(
            business_date=date.fromisoformat(biz_date_str),
            entity_code=entity_code,
            entity_name=entity_name,
            account_code=account_code,
            account_name=account_alias,
            summary=row.get("summary_text", "")[:500],
            counterparty=row.get("counterparty_name", "")[:200],
            amount_in=income,
            amount_out=expense,
            rolling_balance=normalize_amount(row.get("balance", "")),
            state="正常",
            source="网银导入",
            batch_id=batch.id,
        )
        db.add(event)
        inserted += 1

    batch.status = "committed"
    batch.updated_at = datetime.now()

    # 自动保存映射为解析模板（规则中心 → 银行流水规则）
    _auto_save_template(db, batch, h_row, tpl_mapping, account_alias,
                        account_code=account_code,
                        template_name=template_name, sample_headers=sample_headers)

    db.commit()

    log_service.write_log(
        db,
        action="batch_commit",
        module="bank_import",
        detail={
            "batch_code": batch_code,
            "account_code": account_code,
            "inserted_rows": inserted,
            "mode": "mapping",
        },
        batch_id=batch.id,
    )
    return {
        "batch_code": batch_code,
        "account_code": account_code,
        "inserted_rows": inserted,
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


def _match_active_parser_artifact(
    db: Session,
    kind: str,
    account_code: Optional[str] = None,
) -> Optional[ParserArtifact]:
    query = db.query(ParserArtifact).filter(
        ParserArtifact.kind == kind,
        ParserArtifact.status == "active",
    )
    if account_code:
        account_parser = query.filter(ParserArtifact.account_code == account_code).order_by(
            ParserArtifact.version.desc(),
            ParserArtifact.id.desc(),
        ).first()
        if account_parser:
            return account_parser
    return query.filter(
        ParserArtifact.account_code.is_(None) | (ParserArtifact.account_code == "null")
    ).order_by(
        ParserArtifact.version.desc(),
        ParserArtifact.id.desc(),
    ).first()


def _parser_match_out(artifact: ParserArtifact) -> Dict[str, Any]:
    return {
        "matched": True,
        "parser_artifact_id": artifact.id,
        "name": artifact.name,
        "kind": artifact.kind,
        "account_code": artifact.account_code,
        "confidence": str(artifact.confidence) if artifact.confidence is not None else None,
        "sample_check_log": artifact.sample_check_log or {},
    }


def _find_uploaded_file(batch_code: str, source_name: str) -> Optional[str]:
    upload_dir = os.path.join(DATA_DIR, "uploads")
    if not os.path.isdir(upload_dir):
        return None
    for filename in os.listdir(upload_dir):
        if filename.startswith(batch_code + "_") and os.path.isfile(os.path.join(upload_dir, filename)):
            return os.path.join(upload_dir, filename)
    return None


def _display_scalar(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _preview_from_canonical_rows(batch_code: str, rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    valid_rows = []
    abnormal_rows = []
    for row in rows:
        preview_row = {
            "business_date": _display_scalar(row.get("business_date")),
            "entity_code": _display_scalar(row.get("entity_code")),
            "entity_name": _display_scalar(row.get("entity_name")),
            "account_code": _display_scalar(row.get("account_code")),
            "account_name": _display_scalar(row.get("account_name")),
            "summary_text": _display_scalar(row.get("summary")),
            "counterparty_name": _display_scalar(row.get("counterparty")),
            "income_amount": _display_scalar(row.get("amount_in")),
            "expense_amount": _display_scalar(row.get("amount_out")),
            "balance": _display_scalar(row.get("rolling_balance")),
            "state": _display_scalar(row.get("state")),
            "source": _display_scalar(row.get("source")),
            "_errors": [],
        }
        errors = []
        if not row.get("business_date") or not row.get("account_code"):
            errors.append("CORE_FIELD_MISSING")
        if row.get("state") != "正常":
            errors.append("ROW_STATE_NOT_NORMAL")
        if errors:
            preview_row["_errors"] = errors
            abnormal_rows.append(preview_row)
        else:
            valid_rows.append(preview_row)
    return {
        "batch_code": batch_code,
        "total_count": len(rows),
        "valid_count": len(valid_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": valid_rows,
        "abnormal_rows": abnormal_rows,
    }


def _ensure_summary(row: Dict) -> None:
    """当 summary_text 为空时，基于已有字段自动生成 fallback 摘要"""
    if row.get("summary_text", "").strip():
        return
    parts = []
    # 按优先级从已有字段拼凑摘要
    for field in ("_purpose", "_remark", "_notes", "_reference", "transaction_type"):
        val = row.get(field, "").strip()
        if val:
            parts.append(val)
    counterparty = row.get("counterparty_name", "").strip()
    if counterparty:
        parts.append(counterparty)
    if parts:
        row["summary_text"] = "-".join(parts[:3])
    else:
        # 最后兜底：用交易类型描述
        income = normalize_amount(row.get("income_amount", "")) or 0
        expense = normalize_amount(row.get("expense_amount", "")) or 0
        if income > 0:
            row["summary_text"] = "收入"
        elif expense > 0:
            row["summary_text"] = "支出"
        else:
            row["summary_text"] = "交易"


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


def ai_parse_headers(db: Session, headers: list, sample_rows: list = None, agent_id: int = None) -> Dict[str, Any]:
    """通过指定智能体分析银行流水表头，自动生成列映射。"""
    agent = find_active_agent(db, agent_id)
    if not agent or not agent.ai_config:
        return {"ok": False, "error": "未找到可用的 AI 智能体，请先在「AI智能体」中创建并配置"}

    field_desc = "\n".join(f"  - {k}: {v}" for k, v in STANDARD_FIELDS.items())
    short = shorten_headers(headers)
    header_list = ", ".join(f'"{h}"' for h in short)
    sample_text = format_sample_text(
        sample_rows,
        max_rows=3,
        mask_fn=lambda row: mask_row(row, short),
    )

    user_message = f"""请分析以下银行流水的表头和样本数据，将每列映射到对应的标准字段。

## 表头列名
{header_list}
{sample_text}

## 可用标准字段
{field_desc}

## 关键说明
- 这是银行对账单/流水，每行是一笔交易记录
- 「收入金额」列为空表示该笔交易无收入（纯支出）
- 「支出金额」列为空表示该笔交易无支出（纯收入）
- 日期列可能包含时间信息（如 "2025-12-11 10:02:58"），应映射为 business_date
- 「对方户名」是交易对方的公司/个人名称，应映射为 counterparty_name
- 「摘要」或「用途」描述交易原因，应映射为 summary_text

## 要求
1. 返回 JSON 格式：{{"银行列名": "标准字段code"}}
2. 仔细分析样本数据确认每列的真实含义，不要只看列名
3. business_date 和 summary_text 是必须映射的核心字段
4. 同时建议一个模板名称（根据银行名称，如"农业银行流水模板"）

请严格返回如下 JSON 格式（不要包含其他文字）:
{{"mapping": {{"银行列名1": "field1", "银行列名2": "field2"}}, "template_name": "建议的模板名称"}}"""

    ai_result = call_agent_for_mapping(agent, user_message)
    if not ai_result.get("ok"):
        return ai_result

    parsed = ai_result["parsed"]
    mapping = parsed.get("mapping", {})
    template_name = parsed.get("template_name", "AI自动识别模板")
    mapping = restore_mapping_keys(mapping, headers)

    valid_mapping = {k: v for k, v in mapping.items() if v in STANDARD_FIELDS}
    if not valid_mapping:
        return {"ok": False, "error": "AI 未能识别出有效的列映射"}

    return {
        "ok": True,
        "mapping": valid_mapping,
        "template_name": template_name,
        "confidence": validate_mapping_confidence(valid_mapping, len(headers)),
        "matched_count": len(valid_mapping),
        "total_columns": len(headers),
    }


def _auto_save_template(
    db: Session,
    batch: ImportBatch,
    header_row: int,
    mapping: Dict[str, str],
    account_alias: str,
    account_code: str = None,
    template_name: str = None,
    sample_headers: list = None,
) -> None:
    """提交成功后自动保存解析模板到规则中心（银行流水规则）。

    模板名称包含银行中文简称，确保与账户关联。
    如果已存在相同名称的模板则更新，否则新建。
    """
    if not mapping:
        return

    # 确定模板名称：优先使用传入的名称，否则从文件名推断
    source_name = batch.source_name or ""
    if template_name:
        tpl_name = template_name
    else:
        bank_name = _infer_bank_name(source_name, account_alias)
        tpl_name = f"{bank_name}流水解析规则"

    # 检查是否已存在同名模板
    existing = db.query(ParserTemplate).filter(
        ParserTemplate.template_name == tpl_name,
        ParserTemplate.template_type == "bank",
    ).first()

    mapping_str = json.dumps(mapping, ensure_ascii=False)
    headers_str = json.dumps(sample_headers or [], ensure_ascii=False) if sample_headers else "[]"

    if existing:
        existing.mapping_json = mapping_str
        existing.sample_headers = headers_str
        existing.account_code = account_code
        existing.updated_at = datetime.now()
    else:
        obj = ParserTemplate(
            template_name=tpl_name,
            template_type="bank",
            file_format=detect_format(source_name) or "xlsx",
            header_row=header_row,
            skip_rows=0,
            sample_headers=headers_str,
            mapping_json=mapping_str,
            account_code=account_code,
            created_by="ai_assist",
            status="active",
        )
        db.add(obj)


def _infer_bank_name(source_name: str, account_alias: str) -> str:
    """从文件名或账户别名推断银行中文名称"""
    bank_keywords = {
        "工商": "工商银行", "ICBC": "工商银行", "icbc": "工商银行",
        "建设": "建设银行", "CCB": "建设银行", "ccb": "建设银行",
        "农业": "农业银行", "ABC": "农业银行", "abc": "农业银行",
        "中国银行": "中国银行", "BOC": "中国银行", "boc": "中国银行",
        "招商": "招商银行", "CMB": "招商银行", "cmb": "招商银行",
        "交通": "交通银行", "BOCOM": "交通银行", "bocom": "交通银行",
        "浦发": "浦发银行", "SPDB": "浦发银行", "spdb": "浦发银行",
        "民生": "民生银行", "CMBC": "民生银行", "cmbc": "民生银行",
        "兴业": "兴业银行", "CIB": "兴业银行", "cib": "兴业银行",
        "光大": "光大银行", "CEB": "光大银行", "ceb": "光大银行",
        "华夏": "华夏银行", "HXB": "华夏银行", "hxb": "华夏银行",
        "平安": "平安银行", "PAB": "平安银行", "pab": "平安银行",
        "中信": "中信银行", "CITIC": "中信银行", "citic": "中信银行",
        "邮储": "邮储银行", "PSBC": "邮储银行", "psbc": "邮储银行",
    }

    combined = f"{source_name} {account_alias}"
    for keyword, name in bank_keywords.items():
        if keyword in combined:
            return name

    return account_alias or "未知银行"
