"""数据库业务查询工具 — 查询主数据、资金流水等"""
import json
from datetime import date, datetime

from agents_v2.tool_registry import register_tool, ToolContext


@register_tool(read_only=True)
def db_query_business(table_name: str, filters: dict = None, limit: int = 50, ctx: ToolContext = None) -> dict:
    """查询业务数据表。支持: entities(法人), accounts(账户), fund_events(资金流水), banks(银行)。filters 为筛选条件字典。"""
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
    """向 fund_events 资金流水表插入一条记录。business_date 格式 YYYY-MM-DD。"""
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


@register_tool(read_only=False)
def db_save_parser_template(
    template_name: str,
    file_format: str = "xlsx",
    header_row: int = 0,
    skip_rows: int = 0,
    sample_headers: str = "[]",
    mapping_json: str = "{}",
    ctx: ToolContext = None,
) -> dict:
    """保存银行流水解析规则模板到规则中心。template_name 规则名称（如"中国银行流水规则"），file_format 文件格式(xlsx/xls/csv)，header_row 表头所在行号(0起)，skip_rows 数据跳过行数，sample_headers 样本表头JSON数组字符串，mapping_json 列映射JSON字符串（银行列名→标准字段）。标准字段包括: business_date(交易日期), business_time(交易时间), income_amount(收入金额), expense_amount(支出金额), balance(余额), counterparty_name(对方户名), summary_text(摘要), counterpart_account(对方账号), counterpart_bank(对方开户行), transaction_type(交易类型), voucher_no(凭证号)。"""
    from db.tables import ParserTemplate
    import json as _json

    # 解析 JSON 字符串
    try:
        headers = _json.loads(sample_headers) if isinstance(sample_headers, str) else sample_headers
    except _json.JSONDecodeError:
        return {"ok": False, "error": "sample_headers JSON 格式错误"}

    try:
        mapping = _json.loads(mapping_json) if isinstance(mapping_json, str) else mapping_json
    except _json.JSONDecodeError:
        return {"ok": False, "error": "mapping_json JSON 格式错误"}

    if not isinstance(mapping, dict) or not mapping:
        return {"ok": False, "error": "mapping_json 必须是非空的列映射字典"}

    try:
        obj = ParserTemplate(
            template_name=template_name,
            template_type="bank",
            file_format=file_format,
            header_row=header_row,
            skip_rows=skip_rows,
            sample_headers=_json.dumps(headers, ensure_ascii=False),
            mapping_json=_json.dumps(mapping, ensure_ascii=False),
            created_by="ai_assist",
            status="active",
        )
        ctx.db.add(obj)
        ctx.db.commit()
        ctx.db.refresh(obj)
        return {
            "ok": True,
            "id": obj.id,
            "template_name": obj.template_name,
            "message": f"规则模板「{template_name}」已保存到规则中心",
        }
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
        elif isinstance(val, (bytes, bytearray)):
            val = "<binary>"
        result[col.name] = val
    return result
