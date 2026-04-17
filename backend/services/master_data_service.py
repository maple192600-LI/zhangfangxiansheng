"""主数据 CRUD 服务层

板块 / 法人 / 账户 / 别名 的全部业务逻辑。
"""
import math
from datetime import date, datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, or_
from sqlalchemy.orm import Session, joinedload

from db.tables import (
    Account, AccountAlias, Division, Entity, FundEvent,
)
from db.schemas import (
    AccountCreate, AccountTreeNode, AccountUpdate, AliasCreate,
    DivisionCreate, DivisionUpdate, EntityCreate, EntityTreeGroup,
    EntityUpdate, InitialBalanceSet, PaginatedData,
)
from core.parser_engine import read_file_from_bytes, detect_format


# ──────────────────────────────────────────
# 板块
# ──────────────────────────────────────────

def list_divisions(db: Session, status: Optional[str] = None) -> List[Division]:
    q = db.query(Division)
    if status:
        q = q.filter(Division.status == status)
    return q.order_by(Division.sort_order, Division.id).all()


def create_division(db: Session, data: DivisionCreate) -> Division:
    existing = db.query(Division).filter(Division.name == data.name).first()
    if existing:
        raise ValueError(f"板块名称已存在: {data.name}")
    obj = Division(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_division(db: Session, division_id: int, data: DivisionUpdate) -> Division:
    obj = db.query(Division).filter(Division.id == division_id).first()
    if not obj:
        raise ValueError("板块不存在")
    if data.name is not None:
        dup = db.query(Division).filter(
            Division.name == data.name, Division.id != division_id
        ).first()
        if dup:
            raise ValueError(f"板块名称已存在: {data.name}")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────
# 法人
# ──────────────────────────────────────────

def list_entities(
    db: Session,
    division_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedData:
    q = db.query(Entity)
    if division_id is not None:
        q = q.filter(Entity.division_id == division_id)
    if status:
        q = q.filter(Entity.status == status)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(Entity.name.like(kw), Entity.entity_code.like(kw)))
    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(Entity.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedData(
        items=[_entity_to_dict(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def create_entity(db: Session, data: EntityCreate) -> Entity:
    existing = db.query(Entity).filter(Entity.entity_code == data.entity_code).first()
    if existing:
        raise ValueError(f"单位编码已存在: {data.entity_code}")
    obj = Entity(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_entity(db: Session, entity_id: int, data: EntityUpdate) -> Entity:
    obj = db.query(Entity).filter(Entity.id == entity_id).first()
    if not obj:
        raise ValueError("单位不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────
# 账户
# ──────────────────────────────────────────

def list_accounts(
    db: Session,
    entity_id: Optional[int] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
    account_type: Optional[str] = None,
    instrument_type: Optional[str] = None,
    page: int = 1,
    page_size: int = 50,
) -> PaginatedData:
    q = db.query(Account).options(joinedload(Account.entity))
    if entity_id is not None:
        q = q.filter(Account.entity_id == entity_id)
    if status:
        q = q.filter(Account.status == status)
    if account_type:
        q = q.filter(Account.account_type == account_type)
    if instrument_type:
        q = q.filter(Account.instrument_type == instrument_type)
    if keyword:
        kw = f"%{keyword}%"
        q = q.filter(or_(
            Account.account_alias.like(kw),
            Account.account_code.like(kw),
            Account.bank_name.like(kw),
            Account.account_number.like(kw),
        ))
    total = q.count()
    total_pages = math.ceil(total / page_size) if page_size else 1
    items = (
        q.order_by(Account.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return PaginatedData(
        items=[_account_to_dict(a) for a in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


def get_accounts_tree(db: Session) -> List[EntityTreeGroup]:
    entities = (
        db.query(Entity)
        .filter(Entity.status == "enabled")
        .order_by(Entity.id)
        .all()
    )
    result: List[EntityTreeGroup] = []
    for ent in entities:
        accounts = (
            db.query(Account)
            .outerjoin(AccountAlias)
            .filter(Account.entity_id == ent.id)
            .order_by(Account.id)
            .all()
        )
        account_nodes = []
        for acc in accounts:
            aliases = (
                db.query(AccountAlias)
                .filter(AccountAlias.account_id == acc.id)
                .all()
            )
            account_nodes.append(AccountTreeNode(
                id=acc.id,
                account_code=acc.account_code,
                account_alias=acc.account_alias,
                account_type=acc.account_type,
                status=acc.status,
                aliases=aliases,
            ))
        result.append(EntityTreeGroup(
            entity_id=ent.id,
            entity_name=ent.short_name,
            accounts=account_nodes,
        ))
    return result


def create_account(db: Session, data: AccountCreate) -> Account:
    existing = db.query(Account).filter(Account.account_code == data.account_code).first()
    if existing:
        raise ValueError(f"账户编码已存在: {data.account_code}")
    obj = Account(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def update_account(db: Session, account_id: int, data: AccountUpdate) -> Account:
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise ValueError("账户不存在")
    for key, val in data.model_dump(exclude_unset=True).items():
        setattr(obj, key, val)
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


def set_initial_balance(
    db: Session, account_id: int, data: InitialBalanceSet
) -> Account:
    obj = db.query(Account).filter(Account.id == account_id).first()
    if not obj:
        raise ValueError("账户不存在")
    event_count = (
        db.query(FundEvent)
        .filter(FundEvent.account_id == account_id)
        .count()
    )
    if event_count > 0:
        raise ValueError("该账户已有资金流水，无法修改期初余额")
    obj.initial_balance = data.initial_balance
    obj.balance_date = data.balance_date
    obj.updated_at = datetime.now()
    db.commit()
    db.refresh(obj)
    return obj


# ──────────────────────────────────────────
# 别名
# ──────────────────────────────────────────

def list_aliases(db: Session, account_id: int) -> List[AccountAlias]:
    return (
        db.query(AccountAlias)
        .filter(AccountAlias.account_id == account_id)
        .order_by(AccountAlias.id)
        .all()
    )


def create_alias(db: Session, account_id: int, data: AliasCreate) -> AccountAlias:
    account = db.query(Account).filter(Account.id == account_id).first()
    if not account:
        raise ValueError("账户不存在")
    obj = AccountAlias(account_id=account_id, **data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def delete_alias(db: Session, account_id: int, alias_id: int) -> None:
    obj = (
        db.query(AccountAlias)
        .filter(AccountAlias.id == alias_id, AccountAlias.account_id == account_id)
        .first()
    )
    if not obj:
        raise ValueError("别名不存在")
    db.delete(obj)
    db.commit()


# ──────────────────────────────────────────
# 内部辅助
# ──────────────────────────────────────────

def _entity_to_dict(e: Entity) -> Dict[str, Any]:
    return {
        "id": e.id,
        "division_id": e.division_id,
        "entity_code": e.entity_code,
        "name": e.name,
        "short_name": e.short_name,
        "status": e.status,
        "created_at": e.created_at,
        "updated_at": e.updated_at,
    }


def _account_to_dict(a: Account) -> Dict[str, Any]:
    return {
        "id": a.id,
        "entity_id": a.entity_id,
        "account_code": a.account_code,
        "account_alias": a.account_alias,
        "bank_name": a.bank_name,
        "branch_name": a.branch_name,
        "account_number": a.account_number,
        "account_type": a.account_type,
        "instrument_type": a.instrument_type,
        "input_method": a.input_method,
        "currency": a.currency,
        "initial_balance": float(a.initial_balance) if a.initial_balance else 0,
        "balance_date": a.balance_date,
        "status": a.status,
        "notes": a.notes,
        "entity_name": a.entity.short_name if a.entity else None,
        "created_at": a.created_at,
        "updated_at": a.updated_at,
    }


# ──────────────────────────────────────────
# 批量导入
# ──────────────────────────────────────────

# 新模板列顺序（与用户提供的 Excel 模板一致）:
# 核算组织, 单位名称, 单位简称, 单位编码, 开户银行, 银行账号, 开户行名称,
# 账户编号, 账户后四位, 账户类型, 资金类型, 是否网银, 录入方式, 币种,
# 期初余额, 余额日期, 是否纳入日报, 是否允许手工录入, 状态, 备注

# 旧模板列顺序（兼容旧文件）:
# 板块名称, 法人编码, 法人全称, 法人简称, 账户编码, 账户名称,
# 开户银行, 开户网点, 银行账号, 账户类型, 工具类型, 录入方式, 币种,
# 期初余额, 余额日期, 备注

def _detect_template_version(header_row) -> str:
    """根据表头判断模板版本"""
    if not header_row:
        return "unknown"
    first_val = str(header_row[0] or "").strip()
    # 新模板第一列是"核算组织"
    if first_val == "核算组织":
        return "v2"
    # 旧模板第一列是"板块名称"
    if first_val in ("板块名称", "板块"):
        return "v1"
    # 按列数判断：20列=new, 16列=old
    non_empty = sum(1 for c in header_row if c and str(c).strip())
    if non_empty >= 18:
        return "v2"
    return "v1"


def _parse_bool(val) -> bool:
    """解析布尔值：是/否/true/false/1/0"""
    if not val:
        return False
    s = str(val).strip().lower()
    return s in ("是", "true", "1", "yes")


def _parse_input_method(val) -> str:
    """解析录入方式：网银导入→bank_import, 手工填写→manual, 原值保留"""
    if not val:
        return "manual"
    s = str(val).strip()
    if s in ("网银导入", "bank_import"):
        return "bank_import"
    if s in ("手工填写", "手工录入", "manual"):
        return "manual"
    return s


def _parse_status(val) -> str:
    """解析状态：启用→enabled, 停用/已注销→disabled"""
    if not val:
        return "enabled"
    s = str(val).strip()
    if s in ("启用", "enabled"):
        return "enabled"
    if s in ("停用", "已注销", "disabled"):
        return "disabled"
    return s


def batch_import_accounts(db: Session, file_data: bytes, filename: str) -> Dict[str, Any]:
    fmt = detect_format(filename)
    if fmt == "unknown":
        raise ValueError("不支持的文件格式，仅支持 xls/xlsx")

    rows = read_file_from_bytes(file_data, filename, fmt)
    if len(rows) < 2:
        raise ValueError("文件内容为空")

    # 检测模板版本
    version = _detect_template_version(rows[0])

    # 跳过表头行
    data_rows = rows[1:]
    # 跳过提示行（如果第2行包含"必填"/"怎么理解"等说明文字）
    if data_rows and data_rows[0]:
        first_cell = str(data_rows[0][0] or "").strip()
        if first_cell and ("必填" in first_cell or "怎么理解" in first_cell or "填写" in first_cell):
            data_rows = data_rows[1:]

    created_divisions = 0
    created_entities = 0
    created_accounts = 0
    errors = []

    division_cache: Dict[str, int] = {}  # name -> id
    entity_cache: Dict[str, int] = {}  # code -> id
    account_cache: Dict[str, int] = {}  # code -> id

    # 预加载已有数据
    for d in db.query(Division).all():
        division_cache[d.name] = d.id
    for e in db.query(Entity).all():
        entity_cache[e.entity_code] = e.id
    for a in db.query(Account).all():
        account_cache[a.account_code] = a.id

    for ri, row in enumerate(data_rows):
        row_no = ri + 2
        vals = [str(c).strip() if c and str(c).strip() else "" for c in row]

        if version == "v2":
            # 新模板：20列
            while len(vals) < 20:
                vals.append("")
            div_name   = vals[0]   # 核算组织
            ent_name   = vals[1]   # 单位名称
            ent_short  = vals[2]   # 单位简称
            ent_code   = vals[3]   # 单位编码
            bank_name  = vals[4]   # 开户银行
            acc_number = vals[5]   # 银行账号
            branch     = vals[6]   # 开户行名称
            acc_code   = vals[7]   # 账户编号
            last_four  = vals[8]   # 账户后四位
            acc_type   = vals[9]   # 账户类型
            inst_type  = vals[10]  # 资金类型
            has_online = vals[11]  # 是否网银
            input_meth = vals[12]  # 录入方式
            currency   = vals[13]  # 币种
            balance_str = vals[14] # 期初余额
            date_str   = vals[15]  # 余额日期
            in_report  = vals[16]  # 是否纳入日报
            allow_man  = vals[17]  # 是否允许手工录入
            status_str = vals[18]  # 状态
            notes      = vals[19]  # 备注
        else:
            # 旧模板：16列（兼容）
            while len(vals) < 16:
                vals.append("")
            div_name   = vals[0]   # 板块名称
            ent_code   = vals[1]   # 法人编码
            ent_name   = vals[2]   # 法人全称
            ent_short  = vals[3]   # 法人简称
            acc_code   = vals[4]   # 账户编码
            _acc_alias = vals[5]   # 账户名称
            bank_name  = vals[6]   # 开户银行
            branch     = vals[7]   # 开户网点
            acc_number = vals[8]   # 银行账号
            acc_type   = vals[9]   # 账户类型
            inst_type  = vals[10]  # 工具类型
            input_meth = vals[11]  # 录入方式
            currency   = vals[12]  # 币种
            balance_str = vals[13] # 期初余额
            date_str   = vals[14]  # 余额日期
            notes      = vals[15]  # 备注
            last_four  = ""
            has_online = ""
            in_report  = ""
            allow_man  = ""
            status_str = ""

        # 跳过空行
        if not acc_code and not ent_code and not div_name:
            continue

        # 必填校验
        if not acc_code:
            errors.append(f"第{row_no}行: 缺少账户编号")
            continue
        if not ent_code:
            errors.append(f"第{row_no}行: 缺少单位编码")
            continue

        # 自动创建核算组织（板块）
        if div_name and div_name not in division_cache:
            div = Division(name=div_name, sort_order=len(division_cache), status="enabled")
            db.add(div)
            db.flush()
            division_cache[div_name] = div.id
            created_divisions += 1

        # 自动创建单位（法人）
        if ent_code not in entity_cache:
            if not ent_name or not ent_short:
                errors.append(f"第{row_no}行: 新单位缺少名称或简称")
                continue
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

        # 账户去重
        if acc_code in account_cache:
            errors.append(f"第{row_no}行: 账户编号 {acc_code} 已存在，跳过")
            continue

        # 解析余额
        init_balance = 0.0
        if balance_str:
            try:
                init_balance = float(balance_str.replace(",", "").replace("，", ""))
            except ValueError:
                init_balance = 0.0

        # 解析日期
        balance_date = None
        if date_str:
            from core.parser_engine import normalize_date
            ds = normalize_date(date_str)
            if ds:
                balance_date = date.fromisoformat(ds)

        # 解析后四位（从银行账号自动提取如果没填）
        parsed_last_four = last_four.strip()
        if not parsed_last_four and acc_number and len(acc_number) >= 4:
            parsed_last_four = acc_number[-4:]

        acc = Account(
            entity_id=entity_cache[ent_code],
            account_code=acc_code,
            account_alias=acc_type or acc_code,
            bank_name=bank_name or None,
            branch_name=branch or None,
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
            balance_date=balance_date,
            status=_parse_status(status_str) if status_str else "enabled",
            notes=notes or None,
        )
        db.add(acc)
        db.flush()
        account_cache[acc_code] = acc.id
        created_accounts += 1

    db.commit()

    return {
        "total_rows": len(data_rows),
        "created_divisions": created_divisions,
        "created_entities": created_entities,
        "created_accounts": created_accounts,
        "errors": errors[:20],
        "error_count": len(errors),
    }
