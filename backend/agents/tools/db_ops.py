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
    - parser_templates: 解析规则模板（id, template_name, template_type, mapping_json, ...）
    - parser_artifacts: 解析器产物（id, name, kind, account_code, status, code, ...）

    参数说明：
    - table_name: 必需，要查询的表名（必须是上面列出的之一）
    - filters: 可选，筛选条件字典，键为列名，值为精确匹配值。示例：{"account_code": "ZH0008", "business_date": "2025-01-15"}
    - limit: 可选，最大返回条数，默认 50，上限 200

    使用场景：
    - 查询账户信息：table_name="accounts", filters={"account_code": "ZH0008"}
    - 查询资金流水：table_name="fund_events", filters={"account_code": "ZH0008"}, limit=100
    - 查询解析规则：table_name="parser_templates", filters={"template_type": "bank"}
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
        "parser_templates": tb.ParserTemplate,
        "parser_artifacts": tb.ParserArtifact,
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


@register_tool(read_only=False)
def db_save_parser_template(
    template_name: str,
    account_code: str = "",
    file_format: str = "xlsx",
    header_row: int = 0,
    skip_rows: int = 0,
    sample_headers: str = "[]",
    mapping_json: str = "{}",
    ctx: ToolContext = None,
) -> dict:
    """保存解析规则模板（不推荐，建议使用 db_create_parser_artifact 代替）。

    注意：此工具保存到 parser_templates 表，不会出现在「规则中心 → 银行解析器」页面。
    如需创建规则中心可见的解析器，请使用 db_create_parser_artifact 工具。

    使用场景：
    - 仅当需要保存简单的列映射模板时使用

    参数说明：
    - template_name: 必需，规则名称（如"中国银行流水规则"、"XX日报填充规则"）
    - account_code: 可选，关联的账户编号（如"ZH0008"），银行流水规则必须填写
    - file_format: 文件格式，"xlsx"（默认）/"xls"/"csv"
    - header_row: 表头所在行号，从 0 开始计数
    - skip_rows: 数据区前需要跳过的行数
    - sample_headers: 样本表头，JSON 数组字符串。如 '["交易日期","贷方发生额","余额","摘要"]'
    - mapping_json: 列映射规则，JSON 对象字符串，键为银行原始列名，值为标准字段名。mapping_json 必须是非空字典。

    标准字段名（mapping_json 的值只能用这些）：
    - business_date: 交易日期
    - business_time: 交易时间
    - income_amount: 收入金额
    - expense_amount: 支出金额
    - balance: 余额
    - counterparty_name: 对方户名
    - summary_text: 摘要
    - counterpart_account: 对方账号
    - counterpart_bank: 对方开户行
    - transaction_type: 交易类型
    - voucher_no: 凭证号

    mapping_json 示例：
    '{"交易日期": "business_date", "贷方发生额": "income_amount", "余额": "balance", "摘要": "summary_text"}'

    返回格式：{"ok": true, "id": 模板ID, "template_name": "名称"} 或 {"ok": false, "error": "错误原因"}
    """
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
            account_code=account_code or None,
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


@register_tool(read_only=False)
def db_create_parser_artifact(
    name: str,
    kind: str,
    account_code: str,
    code: str,
    primitives_imports: str = "[]",
    sample_check_log: str = "{}",
    confidence: float = 0.8,
    ctx: ToolContext = None,
) -> dict:
    """创建银行解析器并保存到规则中心（推荐使用此工具，而非 db_save_parser_template）。

    创建的解析器会出现在「规则中心 → 银行解析器」页面，状态为"待审核"。

    使用场景：
    - 分析完银行流水文件结构后，创建可执行的解析器
    - 用户确认解析结果正确后，调用此工具固化为规则

    参数说明：
    - name: 必需，解析器名称，如"中国银行流水解析器"
    - kind: 必需，类型，"bank"（银行流水）或 "manual"（手工流水）
    - account_code: 必需，关联账户编码（如"ZH0008"）
    - code: 必需，解析器 Python 代码。必须是可执行的解析函数代码。
    - primitives_imports: 可选，需要导入的基元模块列表，JSON 数组字符串，默认 "[]"。
      可用基元：fund.primitives.value_parsers（parse_date, parse_amount, parse_text, parse_counterparty）
    - sample_check_log: 可选，样本校验结果，JSON 对象字符串，如 '{"canonical_rows": 10, "errors": 0}'
    - confidence: 可选，置信度 0~1，默认 0.8

    code 模板示例：
    ```python
    from fund.primitives.value_parsers import parse_date, parse_amount, parse_text, parse_counterparty

    def parse(ws):
        rows = []
        for row in ws.iter_rows(min_row=3, values_only=True):
            if not row[0]: continue
            rows.append({
                "business_date": parse_date(row[0]),
                "income_amount": parse_amount(row[2]),
                "expense_amount": parse_amount(row[3]),
                "balance": parse_amount(row[4]),
                "summary_text": parse_text(row[5]),
                "counterparty_name": parse_counterparty(row[6]),
            })
        return rows
    ```

    返回格式：{"ok": true, "artifact_id": ID, "name": "名称", "status": "draft", "version": 1}
    """
    import json as _json
    from agents.fund.memory import create_parser_draft

    if kind not in ("bank", "manual"):
        return {"ok": False, "error": "kind 必须是 bank 或 manual"}

    try:
        imports = _json.loads(primitives_imports) if isinstance(primitives_imports, str) else primitives_imports
    except _json.JSONDecodeError:
        return {"ok": False, "error": "primitives_imports JSON 格式错误"}

    try:
        check_log = _json.loads(sample_check_log) if isinstance(sample_check_log, str) else sample_check_log
    except _json.JSONDecodeError:
        return {"ok": False, "error": "sample_check_log JSON 格式错误"}

    try:
        artifact = create_parser_draft(
            db=ctx.db,
            name=name,
            kind=kind,
            account_code=account_code,
            code=code,
            primitives_imports=imports,
            sample_check_log=check_log,
            confidence=confidence,
            created_by="agent",
        )
        return {
            "ok": True,
            "artifact_id": artifact.id,
            "name": artifact.name,
            "status": artifact.status,
            "version": artifact.version,
            "message": f"解析器「{name}」已创建，状态为待审核。可在规则中心查看和审核。",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


@register_tool(read_only=False)
def db_delete_parser_template(
    template_id: int,
    ctx: ToolContext = None,
) -> dict:
    """删除规则中心的一条解析规则模板。template_id 为规则模板的 ID。"""
    from db.tables import ParserTemplate

    try:
        obj = ctx.db.query(ParserTemplate).filter(ParserTemplate.id == template_id).first()
        if not obj:
            return {"ok": False, "error": f"未找到 ID 为 {template_id} 的规则模板"}
        name = obj.template_name
        ctx.db.delete(obj)
        ctx.db.commit()
        return {"ok": True, "message": f"规则模板「{name}」（ID={template_id}）已删除"}
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
