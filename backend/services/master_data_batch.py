"""主数据批量操作与 Excel 导入服务"""
import json
import logging
import os
from datetime import date, datetime
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from db.tables import Account, AccountAlias, Division, Entity, FundEvent
from core.parser_engine import read_file_from_bytes, detect_format

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────
# 批量操作
# ──────────────────────────────────────────

def batch_action_divisions(db: Session, ids: List[int], action: str) -> Dict[str, Any]:
    from services.master_data_service import delete_division, toggle_division_status
    success, failed = 0, []
    for did in ids:
        try:
            if action == "delete":
                delete_division(db, did)
            elif action in ("enable", "disable"):
                toggle_division_status(db, did, "enabled" if action == "enable" else "disabled")
            else:
                raise ValueError(f"不支持的操作: {action}")
            success += 1
        except ValueError as e:
            failed.append({"id": did, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": did, "message": str(e)})
    return {"success": success, "failed": failed}


def batch_action_entities(db: Session, ids: List[int], action: str) -> Dict[str, Any]:
    from services.master_data_service import delete_entity, toggle_entity_status
    success, failed = 0, []
    for eid in ids:
        try:
            if action == "delete":
                delete_entity(db, eid)
            elif action in ("enable", "disable"):
                toggle_entity_status(db, eid, "enabled" if action == "enable" else "disabled")
            else:
                raise ValueError(f"不支持的操作: {action}")
            success += 1
        except ValueError as e:
            failed.append({"id": eid, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": eid, "message": str(e)})
    return {"success": success, "failed": failed}


def batch_action_accounts(db: Session, ids: List[int], action: str) -> Dict[str, Any]:
    success, failed = 0, []
    for aid in ids:
        try:
            acc = db.query(Account).filter(Account.id == aid).first()
            if not acc:
                raise ValueError("账户不存在")
            if action in ("enable", "disable"):
                acc.status = "enabled" if action == "enable" else "disabled"
                acc.updated_at = datetime.now()
                db.commit()
                success += 1
            elif action == "delete":
                from sqlalchemy import text as _sql_text
                ref = db.execute(
                    _sql_text("SELECT COUNT(*) FROM fund_events WHERE account_code = :acode"),
                    {"acode": acc.account_code}
                ).scalar()
                if ref and ref > 0:
                    raise ValueError(f"账户 {acc.account_code} 有 {ref} 条关联资金流水，请先删除流水再删除账户")
                db.execute(AccountAlias.__table__.delete().where(AccountAlias.account_id == acc.id))
                db.execute(Account.__table__.delete().where(Account.id == acc.id))
                db.commit()
                success += 1
            else:
                raise ValueError(f"不支持的操作: {action}")
        except ValueError as e:
            failed.append({"id": aid, "message": str(e)})
        except Exception as e:
            db.rollback()
            failed.append({"id": aid, "message": str(e)})

    return {"success": success, "failed": failed}


# ──────────────────────────────────────────
# 批量导入
# ──────────────────────────────────────────

FIELD_ALIASES = {
    "division_name":   ["核算组织", "板块名称", "板块", "核算组织名称"],
    "entity_name":     ["单位名称", "法人全称", "法人名称", "单位全称"],
    "entity_short":    ["单位简称", "法人简称", "简称"],
    "entity_code":     ["单位编码", "法人编码", "单位编号"],
    "bank_name":       ["开户银行", "银行", "银行名称"],
    "account_number":  ["银行账号", "账号", "银行账号/卡号"],
    "branch_name":     ["银行账户", "开户行名称", "开户网点", "账户名称", "开户行", "网点名称", "开户行网点"],
    "account_code":    ["账户编号", "账户编码", "账户代码"],
    "last_four":       ["账户后四位", "后四位"],
    "account_type":    ["账户类型"],
    "instrument_type": ["资金类型", "工具类型", "资金性质"],
    "has_online":      ["是否网银", "网银"],
    "input_method":    ["录入方式"],
    "currency":        ["币种"],
    "initial_balance": ["期初余额", "余额"],
    "balance_date":    ["余额日期", "日期"],
    "in_report":       ["是否纳入日报", "纳入日报"],
    "allow_manual":    ["是否允许手工录入", "允许手工录入", "是否允许手工"],
    "status":          ["状态"],
    "notes":           ["备注", "说明"],
}

FIELD_TO_API = {
    "division_name": "division_name",
    "entity_name": "entity_full_name",
    "entity_short": "entity_name",
    "entity_code": "entity_code",
    "bank_name": "bank_name",
    "account_number": "account_number",
    "branch_name": "branch_name",
    "account_code": "account_code",
    "last_four": "account_last_four",
    "account_type": "account_type",
    "instrument_type": "instrument_type",
    "has_online": "has_online_banking",
    "input_method": "input_method",
    "currency": "currency",
    "initial_balance": "initial_balance",
    "balance_date": "balance_date",
    "in_report": "include_in_daily_report",
    "allow_manual": "allow_manual_entry",
    "status": "status",
    "notes": "notes",
}

FIELD_RENDER_TYPES = {
    "division_name": "text",
    "entity_name": "text",
    "entity_short": "text",
    "entity_code": "text",
    "bank_name": "text",
    "account_number": "text",
    "branch_name": "text",
    "account_code": "code",
    "last_four": "text",
    "account_type": "tag",
    "instrument_type": "tag",
    "has_online": "bool",
    "input_method": "input_method",
    "currency": "text",
    "initial_balance": "money",
    "balance_date": "text",
    "in_report": "bool",
    "allow_manual": "bool",
    "status": "status",
    "notes": "text",
}


def _column_meta_path() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "column_meta.json")


def _clear_column_meta() -> None:
    path = _column_meta_path()
    if os.path.isfile(path):
        os.remove(path)


def save_column_meta(matched_columns: Dict[str, str]) -> None:
    columns = []
    for field_key, user_label in matched_columns.items():
        api_key = FIELD_TO_API.get(field_key)
        if not api_key:
            continue
        render_type = FIELD_RENDER_TYPES.get(field_key, "text")
        columns.append({"key": api_key, "label": user_label, "type": render_type})
    path = _column_meta_path()
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"columns": columns}, f, ensure_ascii=False, indent=2)


def load_column_meta() -> List[Dict[str, str]]:
    path = _column_meta_path()
    if not os.path.isfile(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("columns", [])
    except Exception:
        return []


def _build_column_map(header_row) -> Dict[str, int]:
    col_map: Dict[str, int] = {}
    for col_idx, cell in enumerate(header_row):
        if not cell:
            continue
        header = str(cell).strip()
        if not header:
            continue
        for field_name, aliases in FIELD_ALIASES.items():
            if field_name in col_map:
                continue
            if header in aliases:
                col_map[field_name] = col_idx
                break
    return col_map


def _parse_bool(val) -> bool:
    if not val:
        return False
    s = str(val).strip().lower()
    return s in ("是", "true", "1", "yes")


def _parse_input_method(val) -> str:
    if not val:
        return "manual"
    s = str(val).strip()
    if s in ("网银导入", "bank_import"):
        return "bank_import"
    if s in ("手工填写", "手工录入", "manual"):
        return "manual"
    return s


def _parse_status(val) -> str:
    if not val:
        return "enabled"
    s = str(val).strip()
    if s in ("启用", "enabled"):
        return "enabled"
    if s in ("停用", "已注销", "disabled"):
        return "disabled"
    return s


def batch_import_accounts(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    from services.master_data_service import CODE_CONFIG, _next_code

    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx")

    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空")

    header_row = rows[0]
    col_map = _build_column_map(header_row)

    if not col_map:
        raise ValueError("无法识别表头，请确保第一行包含列名（如：核算组织、单位名称、银行账号 等）")

    def _get(row_vals, field_name: str, default: str = "") -> str:
        idx = col_map.get(field_name)
        if idx is None or idx >= len(row_vals):
            return default
        v = row_vals[idx]
        if v is None:
            return default
        return str(v).strip()

    data_rows = rows[1:]
    if data_rows and data_rows[0]:
        first_cell = str(data_rows[0][0] or "").strip()
        if first_cell and ("必填" in first_cell or "怎么理解" in first_cell or "字段名" in first_cell):
            data_rows = data_rows[1:]

    created_divisions = 0
    created_entities = 0
    created_accounts = 0
    errors = []

    division_cache: Dict[str, int] = {}
    entity_cache: Dict[str, int] = {}
    account_cache: Dict[str, int] = {}

    for d in db.query(Division).all():
        division_cache[d.name] = d.id
    for e in db.query(Entity).all():
        entity_cache[e.entity_code] = e.id
    for a in db.query(Account).all():
        account_cache[a.account_code] = a.id

    for ri, row in enumerate(data_rows):
        row_no = ri + 2
        vals = [str(c).strip() if c and str(c).strip() else "" for c in row]

        div_name    = _get(vals, "division_name")
        ent_name    = _get(vals, "entity_name")
        ent_short   = _get(vals, "entity_short")
        ent_code    = _get(vals, "entity_code")
        bank_name   = _get(vals, "bank_name")
        acc_number  = _get(vals, "account_number")
        branch_name = _get(vals, "branch_name")
        acc_code    = _get(vals, "account_code")
        last_four   = _get(vals, "last_four")
        acc_type    = _get(vals, "account_type")
        inst_type   = _get(vals, "instrument_type")
        has_online  = _get(vals, "has_online")
        input_meth  = _get(vals, "input_method")
        currency    = _get(vals, "currency")
        balance_str = _get(vals, "initial_balance")
        date_str    = _get(vals, "balance_date")
        in_report   = _get(vals, "in_report")
        allow_man   = _get(vals, "allow_manual")
        status_str  = _get(vals, "status")
        notes       = _get(vals, "notes")

        if not acc_code and not ent_code and not div_name and not acc_number and not ent_name:
            continue

        if not acc_code:
            acc_cfg = CODE_CONFIG["account"]
            acc_code = _next_code(db, Account, acc_cfg["field"], acc_cfg["prefix"], acc_cfg["digits"])

        if not ent_code and ent_name:
            ent_cfg = CODE_CONFIG["entity"]
            ent_code = _next_code(db, Entity, ent_cfg["field"], ent_cfg["prefix"], ent_cfg["digits"])

        if not ent_code:
            errors.append(f"第{row_no}行: 缺少单位编码且无法自动生成")
            continue

        if div_name and div_name not in division_cache:
            div_cfg = CODE_CONFIG["division"]
            div_code = _next_code(db, Division, div_cfg["field"], div_cfg["prefix"], div_cfg["digits"])
            div = Division(division_code=div_code, name=div_name, sort_order=len(division_cache), status="enabled")
            db.add(div)
            db.flush()
            division_cache[div_name] = div.id
            created_divisions += 1

        if ent_code not in entity_cache:
            if not ent_name:
                errors.append(f"第{row_no}行: 新单位缺少名称")
                continue
            if not ent_short:
                ent_short = ent_name[:4] if len(ent_name) > 4 else ent_name
            div_id = division_cache.get(div_name) if div_name else None
            ent = Entity(
                division_id=div_id,
                entity_code=ent_code,
                name=ent_name,
                short_name=ent_short,
                status="enabled",
            )
            db.add(ent)
            db.flush()
            entity_cache[ent_code] = ent.id
            created_entities += 1

        if acc_code in account_cache:
            errors.append(f"第{row_no}行: 账户编号 {acc_code} 已存在，跳过")
            continue

        init_balance = 0.0
        if balance_str:
            try:
                init_balance = float(balance_str.replace(",", "").replace("，", ""))
            except ValueError:
                init_balance = 0.0

        balance_date_val = date.today()
        if date_str:
            from core.parser_engine import normalize_date
            ds = normalize_date(date_str)
            if ds:
                balance_date_val = date.fromisoformat(ds)

        parsed_last_four = last_four.strip()
        if not parsed_last_four and acc_number and len(acc_number) >= 4:
            parsed_last_four = acc_number[-4:]

        acc = Account(
            entity_id=entity_cache[ent_code],
            account_code=acc_code,
            account_alias=branch_name or acc_type or acc_code,
            bank_name=bank_name or None,
            branch_name=branch_name or None,
            account_number=acc_number or None,
            account_last_four=parsed_last_four or None,
            account_type=acc_type or "其他账户",
            instrument_type=inst_type or "银行存款",
            input_method=_parse_input_method(input_meth),
            has_online_banking=_parse_bool(has_online),
            include_in_daily_report=_parse_bool(in_report) if in_report else True,
            allow_manual_entry=_parse_bool(allow_man) if allow_man else True,
            currency=currency or "CNY",
            initial_balance=init_balance,
            balance_date=balance_date_val,
            status=_parse_status(status_str) if status_str else "enabled",
            notes=notes or None,
        )
        db.add(acc)
        db.flush()
        account_cache[acc_code] = acc.id
        created_accounts += 1

    db.commit()

    matched_headers = {k: header_row[v] if v < len(header_row) else "?" for k, v in col_map.items()}
    save_column_meta(matched_headers)

    return {
        "total_rows": len(data_rows),
        "created_divisions": created_divisions,
        "created_entities": created_entities,
        "created_accounts": created_accounts,
        "errors": errors[:20],
        "error_count": len(errors),
        "matched_columns": matched_headers,
    }
