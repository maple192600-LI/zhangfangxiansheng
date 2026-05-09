"""数据库业务查询工具 — 查询主数据、资金流水等"""
import json
from datetime import date, datetime
from decimal import Decimal

from agents.tool_registry import register_tool, ToolContext


@register_tool(read_only=True)
def db_query_business(table_name: str, filters: dict = None, limit: int = 50, ctx: ToolContext = None) -> dict:
    """查询业务数据表，返回匹配的记录列表。

    支持的表：
    - entities: 法人实体（entity_code, entity_name, ...）
    - accounts: 银行/现金账户（account_code, account_name, account_type, entity_code, ...）
    - banks: 银行信息（bank_code, bank_name, ...）
    - fund_events: 资金流水记录（business_date, entity_code, account_code, amount_in, amount_out, balance, summary, counterparty, ...）
    - divisions: 核算部门
    - account_aliases: 账户别名

    参数说明：
    - table_name: 必需，要查询的表名（必须是上面列出的之一）
    - filters: 可选，筛选条件字典，键为列名，值为精确匹配值。示例：{"account_code": "ZH0008", "business_date": "2025-01-15"}
    - limit: 可选，最大返回条数，默认 50，上限 200

    使用场景：
    - 查询账户信息：table_name="accounts", filters={"account_code": "ZH0008"}
    - 查询资金流水：table_name="fund_events", filters={"account_code": "ZH0008"}, limit=100
    - 查询法人信息：table_name="entities"

    返回格式：{"ok": true, "table": "表名", "count": N, "rows": [{...}, ...]}
    """
    from database import SessionLocal
    from db import tables as tb

    TABLE_MAP = {
        "entities": tb.Entity,
        "accounts": tb.Account,
        "banks": tb.Bank,
        "fund_events": tb.FundEvent,
        "divisions": tb.Division,
        "account_aliases": tb.AccountAlias,
    }

    if table_name not in TABLE_MAP:
        available = ", ".join(TABLE_MAP.keys())
        return {"ok": False, "error": f"不支持的表: {table_name}，可用: {available}"}

    model = TABLE_MAP[table_name]
    db = ctx.db

    try:
        query = db.query(model)

        # 安全限制：fund_events 默认按时间倒序 + 限制条数
        if table_name == "fund_events":
            query = query.order_by(model.business_date.desc(), model.id.desc())

        # 简单筛选
        if filters:
            for key, val in filters.items():
                col = getattr(model, key, None)
                if col is not None:
                    query = query.filter(col == val)

        rows = query.limit(min(limit, 200)).all()
        result = [_row_to_dict(r) for r in rows]
        return {"ok": True, "table": table_name, "count": len(result), "rows": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register_tool(read_only=False)
def db_insert_fund_event(
    business_date: str,
    entity_code: str,
    entity_name: str,
    account_code: str,
    account_name: str,
    amount_in: float = 0,
    amount_out: float = 0,
    summary: str = "",
    counterparty: str = "",
    ctx: ToolContext = None,
) -> dict:
    """向 fund_events 资金流水表插入一条记录。

    使用场景：解析银行流水或录入手工流水后，将每条流水记录写入数据库。

    参数说明：
    - business_date: 必需，交易日期，格式 YYYY-MM-DD（如 "2025-01-15"）
    - entity_code: 必需，法人编码（如 "GS001"）。从 accounts 表查询获取，不要让用户提供
    - entity_name: 必需，法人名称（如 "XX有限公司"）。从 accounts 表查询获取
    - account_code: 必需，账户编码（如 "ZH0008"）
    - account_name: 必需，账户名称（如 "中国银行基本户"）。从 accounts 表查询获取
    - amount_in: 可选，收入金额，默认 0。正数表示收入
    - amount_out: 可选，支出金额，默认 0。正数表示支出。注意：amount_in 和 amount_out 不能同时大于 0
    - summary: 可选，交易摘要
    - counterparty: 可选，对方户名

    重要：写入前应先查询同日期+同金额+同摘要是否已存在，避免重复导入。

    返回格式：{"ok": true, "id": 新记录ID} 或 {"ok": false, "error": "错误原因"}
    """
    from db.tables import FundEvent

    if amount_in > 0 and amount_out > 0:
        return {"ok": False, "error": "收入和支出不能同时大于0"}

    try:
        evt = FundEvent(
            business_date=business_date,
            entity_code=entity_code,
            entity_name=entity_name,
            account_code=account_code,
            account_name=account_name,
            amount_in=amount_in,
            amount_out=amount_out,
            summary=summary,
            counterparty=counterparty,
            source="网银导入",
            state="正常",
        )
        ctx.db.add(evt)
        ctx.db.commit()
        return {"ok": True, "id": evt.id}
    except Exception as e:
        ctx.db.rollback()
        return {"ok": False, "error": str(e)}


def _row_to_dict(row) -> dict:
    """将 ORM 对象转为可序列化字典"""
    result = {}
    for col in row.__table__.columns:
        val = getattr(row, col.name, None)
        if isinstance(val, (date, datetime)):
            val = val.isoformat()
        elif isinstance(val, Decimal):
            val = float(val)
        elif isinstance(val, (bytes, bytearray)):
            val = "<binary>"
        result[col.name] = val
    return result
