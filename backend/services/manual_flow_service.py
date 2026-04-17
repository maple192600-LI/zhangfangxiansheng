"""手工流水服务 — Track A 快速录入 + Track B Excel上传，收敛到统一预览/提交流程"""
import json
import os
import uuid
from datetime import datetime, date as date_type
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import text

from config import DATA_DIR
from core.parser_engine import (
    detect_format,
    read_file_from_bytes,
    detect_header_row,
    normalize_date,
    normalize_amount,
)
from db.tables import FundEvent, ImportBatch, Account, Entity, AccountAlias
from services.manual_scheme_service import get_scheme_by_code
from services import log_service


# ── 实体/账户匹配 ──────────────────────────────

def _match_entity(db: Session, match_key: str) -> Optional[Tuple[int, str]]:
    """匹配法人：entity_code > short_name > alias > name 部分匹配"""
    if not match_key or not match_key.strip():
        return None
    key = match_key.strip()

    # 1. entity_code 精确
    row = db.query(Entity).filter(Entity.entity_code == key, Entity.status == "enabled").first()
    if row:
        return (row.id, row.short_name)

    # 2. short_name 精确
    row = db.query(Entity).filter(Entity.short_name == key, Entity.status == "enabled").first()
    if row:
        return (row.id, row.short_name)

    # 3. 别名匹配（通过 account_aliases）
    alias = db.query(AccountAlias).filter(AccountAlias.alias_text == key).first()
    if alias:
        acct = db.query(Account).filter(Account.id == alias.account_id).first()
        if acct:
            ent = db.query(Entity).filter(Entity.id == acct.entity_id, Entity.status == "enabled").first()
            if ent:
                return (ent.id, ent.short_name)

    # 4. name 包含匹配
    rows = db.query(Entity).filter(Entity.name.contains(key), Entity.status == "enabled").all()
    if len(rows) == 1:
        return (rows[0].id, rows[0].short_name)

    return None


def _match_account(db: Session, match_key: str, entity_id: int = None) -> Optional[Tuple[int, str]]:
    """匹配账户：account_code > alias > account_alias"""
    if not match_key or not match_key.strip():
        return None
    key = match_key.strip()

    q = db.query(Account).filter(Account.status == "enabled")
    if entity_id:
        q = q.filter(Account.entity_id == entity_id)

    # 1. account_code 精确
    row = q.filter(Account.account_code == key).first()
    if row:
        return (row.id, row.account_alias)

    # 2. alias
    alias_q = db.query(AccountAlias).filter(AccountAlias.alias_text == key)
    alias = alias_q.first()
    if alias:
        acct = db.query(Account).filter(Account.id == alias.account_id, Account.status == "enabled")
        if entity_id:
            acct = acct.filter(Account.entity_id == entity_id)
        acct = acct.first()
        if acct:
            return (acct.id, acct.account_alias)

    # 3. account_alias 精确
    row = q.filter(Account.account_alias == key).first()
    if row:
        return (row.id, row.account_alias)

    return None


# ── 行验证 ──────────────────────────────

def _validate_row(parsed: Dict) -> List[str]:
    """返回异常代码列表"""
    errors = []
    if not parsed.get("_entity_id"):
        errors.append("ENTITY_MATCH_FAILED")
    if not parsed.get("_account_id"):
        errors.append("ACCOUNT_MATCH_FAILED")
    biz_date = parsed.get("business_date")
    if not biz_date:
        errors.append("DATE_INVALID")
    elif isinstance(biz_date, str) and not _is_valid_date(biz_date):
        errors.append("DATE_INVALID")
    if not parsed.get("summary_text"):
        errors.append("SUMMARY_MISSING")
    inc = parsed.get("income_amount") or 0
    exp = parsed.get("expense_amount") or 0
    has_balance = parsed.get("previous_balance_input") or parsed.get("ending_balance_input")
    if inc == 0 and exp == 0 and not has_balance:
        errors.append("AMOUNT_INVALID")
    elif inc > 0 and exp > 0:
        errors.append("AMOUNT_INVALID")
    return errors


def _is_valid_date(s: str) -> bool:
    try:
        datetime.strptime(s[:10], "%Y-%m-%d")
        return True
    except (ValueError, IndexError):
        try:
            datetime.strptime(s[:10], "%Y/%m/%d")
            return True
        except (ValueError, IndexError):
            return False


# ── 列映射构建 ──────────────────────────────

def _build_column_mapping(db: Session, scheme_code: str) -> Dict[str, str]:
    """field_name_cn → field_code"""
    from db.tables import ManualFieldPool
    scheme = get_scheme_by_code(db, scheme_code)
    if not scheme:
        return {}
    pool = {f.field_code: f.field_name_cn for f in db.query(ManualFieldPool).all()}
    mapping = {}
    for fc in scheme.selected_fields:
        cn = pool.get(fc)
        if cn:
            mapping[cn] = fc
    return mapping


# ── 批次创建 ──────────────────────────────

def _create_batch(db: Session, source_type: str, source_name: str = None, status: str = "uploaded") -> ImportBatch:
    batch = ImportBatch(
        batch_code=f"M-{uuid.uuid4().hex[:8].upper()}",
        source_type=source_type,
        source_name=source_name,
        status=status,
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)
    return batch


# ── Track A: 快速录入保存 ──────────────────────────────

def quick_entry_save(db: Session, rows: List[Dict], scheme_code: str = "manual_multi_subject_basic") -> Dict:
    batch = _create_batch(db, "manual_quick", "快速录入", "previewed")
    saved = 0
    abnormal = 0

    for row in rows:
        parsed = _process_row(db, row)
        errors = _validate_row(parsed)
        parsed["parse_status"] = "valid" if not errors else "abnormal"
        parsed["abnormal_code"] = ",".join(errors) if errors else None
        if errors:
            abnormal += 1
        else:
            saved += 1
        _create_fund_event(db, batch.id, "manual", parsed)

    db.commit()
    log_service.write_log(db, action="batch_upload", module="manual_flow", detail={
        "batch_code": batch.batch_code, "saved": saved, "abnormal": abnormal,
    }, batch_id=batch.id)
    return {
        "batch_code": batch.batch_code,
        "batch_id": batch.id,
        "saved_count": saved,
        "abnormal_count": abnormal,
        "total_count": saved + abnormal,
    }


# ── Track B: Excel上传 ──────────────────────────────

def upload_workbook(db: Session, file_data: bytes, filename: str, scheme_code: str) -> Dict:
    fmt = detect_format(filename)
    if fmt not in ("xlsx", "xls", "csv"):
        raise ValueError(f"不支持的文件格式: {filename}")

    rows = read_file_from_bytes(file_data, filename, fmt)
    if not rows:
        raise ValueError("文件内容为空")

    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx] if h and h.strip()]
    data_rows = rows[header_idx + 1:]
    # 过滤空行
    data_rows = [r for r in data_rows if any(c and c.strip() for c in r)]

    # 保存文件
    upload_dir = os.path.join(DATA_DIR, "uploads")
    os.makedirs(upload_dir, exist_ok=True)
    file_path = os.path.join(upload_dir, f"manual_{uuid.uuid4().hex[:8]}_{filename}")
    with open(file_path, "wb") as f:
        f.write(file_data)

    batch = _create_batch(db, "manual_excel", filename)

    return {
        "batch_code": batch.batch_code,
        "batch_id": batch.id,
        "file_name": filename,
        "row_count": len(data_rows),
        "headers": headers,
        "scheme_code": scheme_code,
    }


def preview_manual(db: Session, batch_code: str, scheme_code: str = None) -> Dict:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError(f"批次不存在: {batch_code}")

    if not scheme_code:
        scheme_code = "manual_multi_subject_basic"

    # ── 分支：快速录入从DB读，Excel上传从文件读 ──
    if batch.source_type == "manual_quick":
        return _preview_from_events(db, batch)
    else:
        return _preview_from_file(db, batch, scheme_code)


def _preview_from_events(db: Session, batch: ImportBatch) -> Dict:
    """快速录入：从已有的 FundEvent 记录构建预览"""
    events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).order_by(FundEvent.id).all()

    parsed_rows = []
    abnormal_rows = []

    for i, ev in enumerate(events):
        row = _event_to_dict(ev)
        row["_row_no"] = i + 1
        if ev.parse_status == "abnormal":
            abnormal_rows.append(row)
        else:
            parsed_rows.append(row)

    batch.status = "previewed"
    db.commit()

    return {
        "batch_code": batch.batch_code,
        "total_count": len(events),
        "valid_count": len(parsed_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": parsed_rows,
        "abnormal_rows": abnormal_rows,
    }


def _preview_from_file(db: Session, batch: ImportBatch, scheme_code: str) -> Dict:
    """Excel上传：重新读取上传文件构建预览"""
    mapping = _build_column_mapping(db, scheme_code)

    upload_dir = os.path.join(DATA_DIR, "uploads")
    source = batch.source_name or ""
    fmt = detect_format(source)
    file_path = None
    for f in os.listdir(upload_dir):
        if batch.batch_code.replace("M-", "manual_") in f or source in f:
            file_path = os.path.join(upload_dir, f)
            break

    if not file_path or not os.path.isfile(file_path):
        raise ValueError("上传文件已丢失，请重新上传")

    file_data = open(file_path, "rb").read()
    rows = read_file_from_bytes(file_data, source, fmt)
    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx]]
    data_rows = rows[header_idx + 1:]
    data_rows = [r for r in data_rows if any(c and c.strip() for c in r)]

    parsed_rows = []
    abnormal_rows = []

    # 删除旧的 fund_events（文件类预览允许重复）
    db.query(FundEvent).filter(FundEvent.batch_id == batch.id).delete()

    for i, raw in enumerate(data_rows):
        row_dict = _map_raw_row(headers, raw, mapping)
        parsed = _process_row(db, row_dict)
        errors = _validate_row(parsed)
        parsed["parse_status"] = "valid" if not errors else "abnormal"
        parsed["abnormal_code"] = ",".join(errors) if errors else None
        parsed["_row_no"] = i + 1
        parsed["_raw"] = [c.strip() if c else "" for c in raw]
        _create_fund_event(db, batch.id, "manual", parsed)
        if errors:
            abnormal_rows.append(parsed)
        else:
            parsed_rows.append(parsed)

    batch.status = "previewed"
    db.commit()

    return {
        "batch_code": batch.batch_code,
        "total_count": len(data_rows),
        "valid_count": len(parsed_rows),
        "abnormal_count": len(abnormal_rows),
        "parsed_rows": parsed_rows,
        "abnormal_rows": abnormal_rows,
    }


def commit_manual(db: Session, batch_code: str, confirm_rows: List[int] = None, fixes: List[Dict] = None) -> Dict:
    batch = db.query(ImportBatch).filter(ImportBatch.batch_code == batch_code).first()
    if not batch:
        raise ValueError(f"批次不存在: {batch_code}")

    # 获取预览数据
    preview = preview_manual(db, batch_code)

    if batch.source_type == "manual_quick":
        # 快速录入：events 已存在，直接更新状态
        committed = len(preview["parsed_rows"])
        abnormal = len(preview["abnormal_rows"])

        # 处理修复
        if fixes:
            fix_map = {f.get("_row_no"): f for f in fixes if f.get("_row_no")}
            events = db.query(FundEvent).filter(FundEvent.batch_id == batch.id).order_by(FundEvent.id).all()
            for i, ev in enumerate(events):
                row_no = i + 1
                if row_no in fix_map:
                    fix = fix_map[row_no]
                    if fix.get("entity_id"):
                        ev.entity_id = fix["entity_id"]
                    if fix.get("account_id"):
                        ev.account_id = fix["account_id"]
                    # 重新验证
                    row = _event_to_dict(ev)
                    row["_entity_id"] = ev.entity_id
                    row["_account_id"] = ev.account_id
                    errors = _validate_row(row)
                    if not errors:
                        ev.parse_status = "valid"
                        ev.abnormal_code = None
                        committed += 1
                        abnormal -= 1
                    else:
                        ev.abnormal_code = ",".join(errors)
        # 有效行状态确认
        db.query(FundEvent).filter(
            FundEvent.batch_id == batch.id,
            FundEvent.parse_status == "valid"
        ).update({"parse_status": "valid"})
    else:
        # Excel上传：删除旧events重新创建
        db.query(FundEvent).filter(FundEvent.batch_id == batch.id).delete()

        committed = 0
        abnormal = 0

        for row in preview["parsed_rows"]:
            if confirm_rows and row.get("_row_no") not in confirm_rows:
                continue
            row["parse_status"] = "valid"
            _create_fund_event(db, batch.id, "manual", row)
            committed += 1

        if fixes:
            fix_map = {f.get("_row_no"): f for f in fixes if f.get("_row_no")}
            for row in preview["abnormal_rows"]:
                row_no = row.get("_row_no")
                if row_no in fix_map:
                    fix = fix_map[row_no]
                    if fix.get("entity_id"):
                        row["_entity_id"] = fix["entity_id"]
                        row["_entity_name"] = fix.get("entity_name", "")
                    if fix.get("account_id"):
                        row["_account_id"] = fix["account_id"]
                        row["_account_name"] = fix.get("account_name", "")
                    errors = _validate_row(row)
                    if not errors:
                        row["parse_status"] = "valid"
                        row["abnormal_code"] = None
                        _create_fund_event(db, batch.id, "manual", row)
                        committed += 1
                    else:
                        abnormal += 1
                else:
                    abnormal += 1

    batch.status = "committed"
    db.commit()

    log_service.write_log(db, action="batch_commit", module="manual_flow", detail={
        "batch_code": batch_code, "committed": committed, "abnormal": abnormal,
    }, batch_id=batch.id)
    return {
        "batch_code": batch_code,
        "committed_count": committed,
        "abnormal_count": abnormal,
        "batch_status": batch.status,
    }


# ── 导出模板 ──────────────────────────────

def export_template(db: Session, scheme_code: str, include_example: bool = False) -> bytes:
    import openpyxl
    from io import BytesIO

    scheme = get_scheme_by_code(db, scheme_code)
    if not scheme:
        raise ValueError(f"方案不存在: {scheme_code}")

    pool_map = {f.field_code: f for f in db.query(__import__("db.tables", fromlist=["ManualFieldPool"]).ManualFieldPool).all()}
    headers = []
    hints = []
    for fc in scheme.selected_fields:
        field = pool_map.get(fc)
        if field:
            headers.append(field.field_name_cn)
            hints.append(f"{'必填' if field.is_core else '选填'} ({field.data_type})")
        else:
            headers.append(fc)
            hints.append("")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "手工流水录入"
    ws.append(headers)
    ws.append(hints)

    if include_example:
        example = []
        for fc in scheme.selected_fields:
            if fc == "entity_match_key":
                example.append("E001")
            elif fc == "account_match_key":
                example.append("A001")
            elif fc == "business_date":
                example.append("2026-04-17")
            elif fc == "summary_text":
                example.append("测试摘要")
            elif fc == "counterparty_name":
                example.append("对方公司")
            elif fc == "income_amount":
                example.append("10000.00")
            elif fc == "expense_amount":
                example.append("")
            elif fc == "note_text":
                example.append("示例行")
            else:
                example.append("")
        ws.append(example)

    # 说明页
    ws2 = wb.create_sheet("字段说明")
    ws2.append(["字段代码", "中文名称", "数据类型", "是否必填", "说明"])
    for fc in scheme.selected_fields:
        field = pool_map.get(fc)
        if field:
            ws2.append([field.field_code, field.field_name_cn, field.data_type,
                        "是" if field.is_core else "否", field.field_name_cn])

    buf = BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ── 内部辅助 ──────────────────────────────

def _process_row(db: Session, row: Dict) -> Dict:
    """匹配实体/账户 + 规范化日期/金额"""
    parsed = dict(row)

    entity_key = str(row.get("entity_match_key", "")).strip()
    account_key = str(row.get("account_match_key", "")).strip()

    ent = _match_entity(db, entity_key)
    if ent:
        parsed["_entity_id"] = ent[0]
        parsed["_entity_name"] = ent[1]
    else:
        parsed["_entity_id"] = None
        parsed["_entity_name"] = entity_key

    acct = _match_account(db, account_key, parsed.get("_entity_id"))
    if acct:
        parsed["_account_id"] = acct[0]
        parsed["_account_name"] = acct[1]
    else:
        parsed["_account_id"] = None
        parsed["_account_name"] = account_key

    # 日期规范化
    raw_date = str(row.get("business_date", "")).strip()
    parsed["business_date"] = normalize_date(raw_date) if raw_date else raw_date

    # 金额规范化
    for amt_field in ("income_amount", "expense_amount", "previous_balance_input", "ending_balance_input"):
        raw_val = row.get(amt_field)
        if raw_val is not None and str(raw_val).strip():
            parsed[amt_field] = normalize_amount(str(raw_val))
        elif raw_val is not None:
            parsed[amt_field] = None

    return parsed


def _map_raw_row(headers: List[str], raw: List[str], mapping: Dict[str, str]) -> Dict:
    """原始行 → field_code dict"""
    result = {}
    for i, h in enumerate(headers):
        if not h:
            continue
        fc = mapping.get(h)
        val = raw[i].strip() if i < len(raw) and raw[i] else ""
        if fc:
            result[fc] = val
        else:
            # 尝试直接作为 field_code
            result[h] = val
    return result


def _event_to_dict(ev: FundEvent) -> Dict:
    """FundEvent ORM → 预览用的 dict"""
    return {
        "_entity_id": ev.entity_id,
        "_entity_name": ev.entity.short_name if ev.entity else None,
        "_account_id": ev.account_id,
        "_account_name": ev.account.account_alias if ev.account else None,
        "business_date": str(ev.business_date) if ev.business_date else "",
        "business_time": ev.business_time,
        "summary_text": ev.summary_text,
        "counterparty_name": ev.counterparty_name,
        "income_amount": float(ev.income_amount) if ev.income_amount else None,
        "expense_amount": float(ev.expense_amount) if ev.expense_amount else None,
        "previous_balance_input": float(ev.previous_balance_input) if ev.previous_balance_input else None,
        "ending_balance_input": float(ev.ending_balance_input) if ev.ending_balance_input else None,
        "parse_status": ev.parse_status,
        "abnormal_code": ev.abnormal_code,
    }


def _create_fund_event(db: Session, batch_id: int, source_type: str, parsed: Dict):
    biz_date = parsed.get("business_date", "")
    if isinstance(biz_date, str) and biz_date:
        try:
            biz_date = datetime.strptime(biz_date[:10], "%Y-%m-%d").date()
        except ValueError:
            try:
                biz_date = datetime.strptime(biz_date[:10], "%Y/%m/%d").date()
            except ValueError:
                biz_date = None
    else:
        biz_date = None

    inc = parsed.get("income_amount")
    exp = parsed.get("expense_amount")
    if inc is not None:
        try:
            inc = float(inc)
        except (ValueError, TypeError):
            inc = None
    if exp is not None:
        try:
            exp = float(exp)
        except (ValueError, TypeError):
            exp = None

    event = FundEvent(
        batch_id=batch_id,
        source_type=source_type,
        business_date=biz_date,
        business_time=parsed.get("business_time"),
        entity_id=parsed.get("_entity_id"),
        account_id=parsed.get("_account_id"),
        direction="income" if (inc and inc > 0) else ("expense" if (exp and exp > 0) else "unknown"),
        income_amount=inc,
        expense_amount=exp,
        counterparty_name=parsed.get("counterparty_name"),
        summary_text=parsed.get("summary_text", ""),
        previous_balance_input=parsed.get("previous_balance_input"),
        ending_balance_input=parsed.get("ending_balance_input"),
        parse_status=parsed.get("parse_status", "pending"),
        abnormal_code=parsed.get("abnormal_code"),
        raw_data_json=json.dumps(parsed, ensure_ascii=False, default=str),
    )
    db.add(event)
