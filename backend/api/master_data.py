"""主数据 API 路由

板块 / 法人 / 账户 / 别名 — CRUD + usage + 批量操作 + 批量导入。
"""
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from config import DATA_DIR
from core.response import error, success
from database import get_db
from db.schemas import (
    AccountCreate, AccountUpdate, AliasCreate,
    DivisionCreate, DivisionUpdate, EntityCreate, EntityUpdate,
    InitialBalanceSet, StatusToggle,
)
from services import master_data_service as svc

logger = logging.getLogger(__name__)

router = APIRouter()


class BatchAction(BaseModel):
    ids: List[int]
    action: str  # "enable" | "disable" | "delete"
    cascade: bool = False  # 级联删除下属数据


# ──────────────────────────────────────────
# 板块
# ──────────────────────────────────────────

@router.get("/divisions")
def get_divisions(
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    items = svc.list_divisions(db, status=status)
    return success([{
        "id": d.id, "division_code": d.division_code, "name": d.name,
        "sort_order": d.sort_order, "status": d.status,
        "created_at": d.created_at, "updated_at": d.updated_at,
    } for d in items])


@router.post("/divisions")
def create_division(body: DivisionCreate, db: Session = Depends(get_db)):
    try:
        obj = svc.create_division(db, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "division_code": obj.division_code, "name": obj.name,
        "sort_order": obj.sort_order, "status": obj.status,
    })


@router.put("/divisions/{division_id}")
def update_division(
    division_id: int, body: DivisionUpdate, db: Session = Depends(get_db),
):
    try:
        obj = svc.update_division(db, division_id, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "division_code": obj.division_code, "name": obj.name,
        "sort_order": obj.sort_order, "status": obj.status,
    })


@router.put("/divisions/{division_id}/status")
def toggle_division_status(
    division_id: int, body: StatusToggle, db: Session = Depends(get_db),
):
    try:
        obj = svc.toggle_division_status(db, division_id, body.status)
    except ValueError as e:
        return error(2001, str(e))
    return success({"id": obj.id, "status": obj.status})


@router.delete("/divisions/{division_id}")
def delete_division(division_id: int, force: bool = Query(False), db: Session = Depends(get_db)):
    try:
        svc.delete_division(db, division_id, force=force)
    except ValueError as e:
        return error(2001, str(e))
    return success(None, message="核算组织已删除")


@router.get("/divisions/{division_id}/usage")
def get_division_usage(division_id: int, db: Session = Depends(get_db)):
    try:
        return success(svc.get_division_usage(db, division_id))
    except ValueError as e:
        return error(2001, str(e))


@router.post("/divisions/batch")
def batch_divisions(body: BatchAction, db: Session = Depends(get_db)):
    return success(svc.batch_action_divisions(db, body.ids, body.action, cascade=body.cascade))


# ──────────────────────────────────────────
# 法人
# ──────────────────────────────────────────

@router.get("/entities")
def get_entities(
    division_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    result = svc.list_entities(
        db, division_id=division_id, status=status, keyword=keyword,
        page=page, page_size=page_size,
    )
    return success(result.model_dump())


@router.post("/entities")
def create_entity(body: EntityCreate, db: Session = Depends(get_db)):
    try:
        obj = svc.create_entity(db, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "entity_code": obj.entity_code, "name": obj.name,
        "short_name": obj.short_name, "status": obj.status,
    })


@router.put("/entities/{entity_id}")
def update_entity(
    entity_id: int, body: EntityUpdate, db: Session = Depends(get_db),
):
    try:
        obj = svc.update_entity(db, entity_id, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "entity_code": obj.entity_code, "name": obj.name,
        "short_name": obj.short_name, "status": obj.status,
    })


@router.put("/entities/{entity_id}/status")
def toggle_entity_status(
    entity_id: int, body: StatusToggle, db: Session = Depends(get_db),
):
    try:
        obj = svc.toggle_entity_status(db, entity_id, body.status)
    except ValueError as e:
        return error(2001, str(e))
    return success({"id": obj.id, "status": obj.status})


@router.delete("/entities/{entity_id}")
def delete_entity(entity_id: int, db: Session = Depends(get_db)):
    try:
        svc.delete_entity(db, entity_id)
    except ValueError as e:
        return error(2001, str(e))
    return success(None, message="单位已删除")


@router.get("/entities/{entity_id}/usage")
def get_entity_usage(entity_id: int, db: Session = Depends(get_db)):
    try:
        return success(svc.get_entity_usage(db, entity_id))
    except ValueError as e:
        return error(2001, str(e))


@router.post("/entities/batch")
def batch_entities(body: BatchAction, db: Session = Depends(get_db)):
    return success(svc.batch_action_entities(db, body.ids, body.action, cascade=body.cascade))


# ──────────────────────────────────────────
# 账户
# ──────────────────────────────────────────

@router.get("/accounts")
def get_accounts(
    entity_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    account_type: Optional[str] = Query(None),
    instrument_type: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    result = svc.list_accounts(
        db, entity_id=entity_id, status=status, keyword=keyword,
        account_type=account_type, instrument_type=instrument_type,
        page=page, page_size=page_size,
    )
    data = result.model_dump()
    # 附加列元数据（来自用户上次导入的模板列名）
    data["columns"] = svc.load_column_meta()
    return success(data)


@router.get("/accounts/columns")
def get_account_columns():
    """获取当前账户列元数据（基于用户上次导入的模板）"""
    return success(svc.load_column_meta())


@router.get("/accounts/tree")
def get_accounts_tree(db: Session = Depends(get_db)):
    tree = svc.get_accounts_tree(db)
    return success([g.model_dump() for g in tree])


@router.post("/accounts")
def create_account(body: AccountCreate, db: Session = Depends(get_db)):
    try:
        obj = svc.create_account(db, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "account_code": obj.account_code,
        "account_alias": obj.account_alias, "status": obj.status,
    })


@router.put("/accounts/{account_id}")
def update_account(
    account_id: int, body: AccountUpdate, db: Session = Depends(get_db),
):
    try:
        obj = svc.update_account(db, account_id, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "account_code": obj.account_code,
        "account_alias": obj.account_alias, "status": obj.status,
    })


@router.post("/accounts/{account_id}/initial-balance")
def set_initial_balance(
    account_id: int, body: InitialBalanceSet, db: Session = Depends(get_db),
):
    try:
        obj = svc.set_initial_balance(db, account_id, body)
    except ValueError as e:
        return error(3001, str(e))
    return success({
        "id": obj.id, "initial_balance": float(obj.initial_balance),
        "balance_date": obj.balance_date.isoformat(),
    })


# ──────────────────────────────────────────
# 别名
# ──────────────────────────────────────────

@router.post("/accounts/batch")
def batch_accounts(body: BatchAction, db: Session = Depends(get_db)):
    return success(svc.batch_action_accounts(db, body.ids, body.action))


# ──────────────────────────────────────────
# 别名
# ──────────────────────────────────────────

@router.get("/accounts/{account_id}/aliases")
def get_aliases(account_id: int, db: Session = Depends(get_db)):
    items = svc.list_aliases(db, account_id)
    return success([{
        "id": a.id, "account_id": a.account_id,
        "alias_text": a.alias_text, "alias_type": a.alias_type,
        "created_at": a.created_at,
    } for a in items])


@router.post("/accounts/{account_id}/aliases")
def create_alias(
    account_id: int, body: AliasCreate, db: Session = Depends(get_db),
):
    try:
        obj = svc.create_alias(db, account_id, body)
    except ValueError as e:
        return error(2001, str(e))
    return success({
        "id": obj.id, "alias_text": obj.alias_text, "alias_type": obj.alias_type,
    })


@router.delete("/accounts/{account_id}/aliases/{alias_id}")
def delete_alias(
    account_id: int, alias_id: int, db: Session = Depends(get_db),
):
    try:
        svc.delete_alias(db, account_id, alias_id)
    except ValueError as e:
        return error(2001, str(e))
    return success(None, message="别名已删除")


# ──────────────────────────────────────────
# 批量导入
# ──────────────────────────────────────────

@router.get("/accounts/template")
def download_template():
    """下载账户批量导入模板（用户提供的标准模板）"""
    import os
    from fastapi.responses import FileResponse

    template_path = os.path.join(DATA_DIR, "account_import_template.xlsx")
    if not os.path.isfile(template_path):
        return error(5000, "导入模板文件不存在")
    return FileResponse(
        template_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename="账户数据中心_导入模板.xlsx",
    )


@router.post("/accounts/import")
async def batch_import(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """批量导入账户（含自动创建板块和法人）"""
    if not file.filename:
        return error(1001, "缺少文件名")
    data = await file.read()
    if not data:
        return error(1001, "文件为空")
    try:
        result = svc.batch_import_accounts(db, data, file.filename)
    except ValueError as e:
        return error(3001, str(e))
    return success(result)
