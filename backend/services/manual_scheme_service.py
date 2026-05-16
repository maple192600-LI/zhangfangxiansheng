"""手工流水方案服务 — 字段池查询 + 方案CRUD"""
import json
from typing import List, Optional

from sqlalchemy.orm import Session

from db.tables import ManualFieldPool, ManualTemplateScheme
from db.schemas import (
    ManualFieldPoolOut,
    ManualSchemeCreate,
    ManualSchemeOut,
    ManualSchemeUpdate,
)

# 核心字段 code，不可从方案中移除
CORE_FIELD_CODES = {
    "entity_match_key", "account_match_key", "business_date",
    "summary_text", "counterparty_name", "income_amount", "expense_amount",
}


def list_field_pool(db: Session) -> List[ManualFieldPoolOut]:
    rows = db.query(ManualFieldPool).filter(
        ManualFieldPool.status == "active"
    ).order_by(ManualFieldPool.id).all()
    return [ManualFieldPoolOut.model_validate(r) for r in rows]


def list_schemes(db: Session) -> List[ManualSchemeOut]:
    rows = db.query(ManualTemplateScheme).filter(
        ManualTemplateScheme.status == "active"
    ).order_by(ManualTemplateScheme.id).all()
    return [_scheme_to_out(r) for r in rows]


def get_scheme_by_code(db: Session, scheme_code: str) -> Optional[ManualSchemeOut]:
    row = db.query(ManualTemplateScheme).filter(
        ManualTemplateScheme.scheme_code == scheme_code,
        ManualTemplateScheme.status == "active",
    ).first()
    return _scheme_to_out(row) if row else None


def get_scheme_by_id(db: Session, scheme_id: int) -> Optional[ManualSchemeOut]:
    row = db.query(ManualTemplateScheme).filter(
        ManualTemplateScheme.id == scheme_id,
    ).first()
    return _scheme_to_out(row) if row else None


def create_scheme(db: Session, data: ManualSchemeCreate):
    _validate_scheme_fields(data.selected_fields)
    scheme = ManualTemplateScheme(
        scheme_code=data.scheme_code,
        scheme_name=data.scheme_name,
        description=data.description,
        selected_fields_json=json.dumps(data.selected_fields, ensure_ascii=False),
        is_default=data.is_default,
        status="active",
    )
    db.add(scheme)
    db.commit()
    db.refresh(scheme)
    return _scheme_to_out(scheme)


def update_scheme(db: Session, scheme_id: int, data: ManualSchemeUpdate):
    scheme = db.query(ManualTemplateScheme).filter(
        ManualTemplateScheme.id == scheme_id
    ).first()
    if not scheme:
        return None

    if data.scheme_name is not None:
        scheme.scheme_name = data.scheme_name
    if data.description is not None:
        scheme.description = data.description
    if data.is_default is not None:
        scheme.is_default = data.is_default
    if data.status is not None:
        scheme.status = data.status
    if data.selected_fields is not None:
        _validate_scheme_fields(data.selected_fields)
        scheme.selected_fields_json = json.dumps(data.selected_fields, ensure_ascii=False)

    db.commit()
    db.refresh(scheme)
    return _scheme_to_out(scheme)


def _validate_scheme_fields(selected_fields: List[str]):
    missing = CORE_FIELD_CODES - set(selected_fields)
    if missing:
        raise ValueError(f"核心字段不可移除: {', '.join(sorted(missing))}")


def _scheme_to_out(row: ManualTemplateScheme) -> ManualSchemeOut:
    fields = []
    if row.selected_fields_json:
        try:
            parsed = json.loads(row.selected_fields_json)
            if isinstance(parsed, list):
                fields = parsed
            elif isinstance(parsed, dict) and "fields" in parsed:
                fields = parsed["fields"]
        except (json.JSONDecodeError, TypeError):
            fields = []
    return ManualSchemeOut(
        id=row.id,
        scheme_code=row.scheme_code,
        scheme_name=row.scheme_name,
        description=row.description,
        selected_fields=fields,
        is_default=row.is_default,
        status=row.status,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )
