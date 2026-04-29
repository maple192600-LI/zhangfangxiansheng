"""
中国银行流水专用解析技能

文件格式识别规则：
- 表头位于第9行（0-based index 8），共38列中英文双语表头
- 第1-8行为查询信息（账号、总笔数等），需跳过
- 第10行起为交易数据（0-based index 9）
- 交易类型列（Col 0）：来账=收入，往账=支出
- 交易金额列（Col 13）：正数=收入，负数=支出
- 余额列（Col 14）：交易后余额
- 对方判断：来账取付款人名称（Col 5），往账取收款人名称（Col 9）
- 本方账号：Col 4（付款人账号）
- 本方户名：Col 5（付款人名称）
- 摘要生成策略：优先用用途(Col 24)→附言(Col 25)→业务类型(Col 1)+对方
"""
import os
import sys
import json
import re

_BACKEND = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
if _BACKEND not in sys.path:
    sys.path.insert(0, _BACKEND)

from core.parser_engine import (
    detect_format, read_file, detect_header_row,
    normalize_date, normalize_amount,
)

# 中国银行特定配置
BOC_HEADER_ROW_INDEX = 8  # 0-based，表头在第9行
BOC_DATA_START_ROW = 9     # 数据从第10行开始
BOC_SKIP_ROWS = list(range(0, 8))  # 跳过第1-8行（查询信息）

# 列索引映射
COL_MAP = {
    "direction": 0,        # 交易类型：来账/往账
    "business_type": 1,    # 业务类型：网上支付、大额支付、短信收费等
    "payer_bank_no": 2,    # 付款人开户行号
    "payer_bank_name": 3,  # 付款人开户行名
    "payer_account": 4,    # 付款人账号（本方账号）
    "payer_name": 5,       # 付款人名称（本方户名/对方-来账时）
    "payee_bank_no": 6,    # 收款人开户行行号
    "payee_bank_name": 7,  # 收款人开户行名
    "payee_account": 8,    # 收款人账号
    "payee_name": 9,       # 收款人名称（对方-往账时）
    "business_date": 10,   # 交易日期
    "transaction_time": 11, # 交易时间
    "currency": 12,        # 交易货币
    "amount": 13,          # 交易金额（正=收入，负=支出）
    "rolling_balance": 14, # 交易后余额
    "value_date": 15,      # 起息日期
    "exchange_rate": 16,   # 汇率
    "ref_no": 17,          # 交易流水号
    "client_app_no": 18,   # 客户申请号
    "customer_ref": 19,    # 客户业务编号
    "voucher_type": 20,    # 凭证类型
    "voucher_no": 21,      # 凭证号码
    "record_id": 22,       # 记录标识号
    "raw_summary": 23,     # 摘要[Reference]
    "purpose": 24,         # 用途[Purpose]
    "remark": 25,          # 交易附言[Remark]
    "notes": 26,           # 备注[Remarks]
}

# fund_events 需要的字段
FUND_EVENTS_REQUIRED = [
    "business_date", "entity_code", "entity_name",
    "account_code", "account_name",
    "amount_in", "amount_out", "rolling_balance",
    "summary", "counterparty", "source",
]


def _generate_summary(item: dict) -> str:
    """根据中行流水字段生成可读摘要"""
    biz_type = item.get("business_type", "").strip()
    purpose = item.get("purpose", "").strip()
    remark = item.get("remark", "").strip()
    counterparty = item.get("counterparty", "").strip()

    # 1. 明确费用类
    fee_keywords = ["收费", "手续费", "短信", "邮费", "询证", "回单"]
    if biz_type and any(kw in biz_type for kw in fee_keywords):
        if purpose:
            return purpose
        return biz_type

    # 2. 利息类
    if biz_type == "结息":
        return "结息收入"

    # 3. 贷款类
    if "贷款" in biz_type:
        if biz_type == "贷款还款":
            return "贷款还款"
        if biz_type == "贷款放款":
            return "贷款放款"

    # 4. 用途列
    if purpose:
        return purpose

    # 5. 交易附言
    if remark and remark != "转款":
        return remark

    # 6. 业务类型 + 对方
    if biz_type and counterparty:
        return f"{biz_type}-{counterparty}"
    if biz_type:
        return biz_type

    # 7. 兜底
    return "待补摘要"


def _get_counterparty(item: dict) -> str:
    """根据方向判断对方名称"""
    direction = item.get("direction", "").strip()
    payer_name = item.get("payer_name", "").strip()
    payee_name = item.get("payee_name", "").strip()

    if direction == "来账":
        # 收入，对方是付款人
        return payer_name if payer_name else ""
    else:
        # 往账，对方是收款人
        return payee_name if payee_name else ""


def _get_own_account_info(rows: list, header_idx: int) -> dict:
    """从文件头部提取本方账户信息"""
    info = {}
    # 从查询信息行提取
    for ri in range(header_idx):
        row = rows[ri]
        for cell in row:
            text = str(cell).strip() if cell else ""
            if not text:
                continue
            # 账号
            if "查询账号" in text or "Inquirer" in text:
                idx = row.index(cell)
                if idx + 1 < len(row):
                    info["account_number"] = str(row[idx + 1]).strip()
    return info


def _is_valid_trade_row(row: list) -> bool:
    """判断是否为有效的交易行"""
    if not row or len(row) < 3:
        return False
    # 交易行至少要有交易类型（来账/往账）和交易日期
    col0 = str(row[0]).strip() if row[0] else ""
    col10 = str(row[10]).strip() if len(row) > 10 and row[10] else ""
    col13 = str(row[13]).strip() if len(row) > 13 and row[13] else ""

    if col0 not in ["来账", "往账"]:
        return False
    if not col10 or not col10.isdigit():
        return False
    if not col13:
        return False
    return True


def run(params: dict) -> dict:
    """主入口函数

    Args:
        params: {
            "file_path": str,  # 文件路径
            "entity_code": str | None,  # 可选，指定法人编码
            "account_code": str | None,  # 可选，指定账户编号
        }

    Returns:
        dict: 解析结果
    """
    file_path = params.get("file_path", "")
    entity_code = params.get("entity_code")
    account_code = params.get("account_code")

    if not file_path or not os.path.exists(file_path):
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    # 1. 检测格式并读取
    fmt = detect_format(file_path)
    if fmt not in ("xlsx", "xls", "csv"):
        return {"ok": False, "error": f"不支持的文件格式: {fmt}"}

    try:
        rows = read_file(file_path, fmt)
    except Exception as e:
        return {"ok": False, "error": f"读取文件失败: {str(e)}"}

    # 2. 确认表头行
    header_idx = BOC_HEADER_ROW_INDEX
    headers = [str(c).strip() if c else "" for c in rows[header_idx]]

    # 3. 提取账户信息
    own_account = _get_own_account_info(rows, header_idx)

    # 4. 匹配系统账户
    matched_account = None
    if own_account.get("account_number"):
        try:
            from database import SessionLocal
            from db.tables import Account, Entity

            db = SessionLocal()
            try:
                acc_num = own_account["account_number"]
                query = db.query(Account, Entity).join(Entity, Account.entity_id == Entity.id)
                for acc, ent in query.all():
                    if acc.account_code and acc_num in acc.account_code:
                        matched_account = {
                            "account_id": acc.id,
                            "account_code": acc.account_code,
                            "account_name": acc.account_alias,
                            "entity_id": ent.id,
                            "entity_code": ent.entity_code,
                            "entity_name": ent.short_name,
                            "bank_name": acc.bank_name,
                        }
                        break
            finally:
                db.close()
        except Exception:
            pass

    # 如果传入了entity_code/account_code，覆盖
    if entity_code or account_code:
        try:
            from database import SessionLocal
            from db.tables import Account, Entity

            db = SessionLocal()
            try:
                query = db.query(Account, Entity).join(Entity, Account.entity_id == Entity.id)
                if entity_code:
                    query = query.filter(Entity.entity_code == entity_code)
                if account_code:
                    query = query.filter(Account.account_code == account_code)
                for acc, ent in query.all():
                    matched_account = {
                        "account_id": acc.id,
                        "account_code": acc.account_code,
                        "account_name": acc.account_alias,
                        "entity_id": ent.id,
                        "entity_code": ent.entity_code,
                        "entity_name": ent.short_name,
                        "bank_name": acc.bank_name,
                    }
                    break
            finally:
                db.close()
        except Exception:
            pass

    # 5. 解析交易行
    transactions = []
    skip_detail = {"header_info_rows": [], "non_trade_rows": []}

    # 记录跳过的头部信息行
    for ri in range(min(header_idx, len(rows))):
        row_text = " | ".join(str(c) if c else "" for c in rows[ri])
        if row_text.strip():
            skip_detail["header_info_rows"].append({
                "row_index": ri,
                "content": row_text
            })

    for ri in range(BOC_DATA_START_ROW, len(rows)):
        row = rows[ri]
        col0 = str(row[0]).strip() if row[0] else ""

        # 跳过后面的汇总行或空行
        if not col0 and all(not (c and str(c).strip()) for c in row):
            continue
        if col0 and col0 not in ["来账", "往账"]:
            row_text = " | ".join(str(c) if c else "" for c in row)
            skip_detail["non_trade_rows"].append({
                "row_index": ri,
                "content": row_text[:200]
            })
            continue
        if not _is_valid_trade_row(row):
            row_text = " | ".join(str(c) if c else "" for c in row)
            skip_detail["non_trade_rows"].append({
                "row_index": ri,
                "content": row_text[:200]
            })
            continue

        # 提取原始数据
        item = {"_row_no": ri + 1}

        for field, col_idx in COL_MAP.items():
            val = row[col_idx] if col_idx < len(row) else ""
            item[field] = str(val).strip() if val else ""

        # 明确方向
        direction = item.get("direction", "")
        if direction == "来账":
            item["direction_label"] = "收入"
        else:
            item["direction_label"] = "支出"

        # 处理金额
        amt_str = item.get("amount", "0")
        amt = normalize_amount(amt_str)
        if amt is not None:
            if amt >= 0:
                item["amount_in"] = amt
                item["amount_out"] = 0.0
            else:
                item["amount_in"] = 0.0
                item["amount_out"] = abs(amt)
            item["amount"] = amt
        else:
            item["amount_in"] = 0.0
            item["amount_out"] = 0.0
            item["amount"] = 0.0

        # 处理余额
        bal_str = item.get("rolling_balance", "0")
        bal = normalize_amount(bal_str)
        item["rolling_balance"] = bal if bal else 0.0

        # 标准化日期
        date_str = item.get("business_date", "")
        norm_date = normalize_date(date_str)
        item["business_date"] = norm_date if norm_date else date_str

        # 对方
        item["counterparty"] = _get_counterparty(item)

        # 生成摘要
        item["summary"] = _generate_summary(item)

        # 保存原始摘要（用于追溯）
        item["_raw_summary"] = item.get("raw_summary", "")

        # 本方账户信息
        if matched_account:
            item["entity_code"] = matched_account["entity_code"]
            item["entity_name"] = matched_account["entity_name"]
            item["account_code"] = matched_account["account_code"]
            item["account_name"] = matched_account["account_name"]
        else:
            item["entity_code"] = ""
            item["entity_name"] = ""
            item["account_code"] = own_account.get("account_number", "")
            item["account_name"] = item.get("payer_name", "")

        item["source"] = "中行网银导入"
        transactions.append(item)

    # 6. 构建结果
    result = {
        "ok": True,
        "file_name": os.path.basename(file_path),
        "file_format": fmt,
        "bank_name": "中国银行",
        "total_rows": len(transactions),
        "transactions": transactions,
        "header_info": {
            "header_row": header_idx,
            "data_start_row": BOC_DATA_START_ROW,
            "total_file_rows": len(rows),
            "columns_detected": len(headers),
            "skip_detail": skip_detail,
        },
        "own_account": own_account,
        "matched_account": matched_account,
        "mapping_rules": {
            "date_column": "Col 10 - 交易日期",
            "direction_column": "Col 0 - 交易类型（来账=收入，往账=支出）",
            "amount_column": "Col 13 - 交易金额（正=收入，负=支出）",
            "balance_column": "Col 14 - 交易后余额",
            "counterparty_income": "Col 5 - 付款人名称（来账时）",
            "counterparty_expense": "Col 9 - 收款人名称（往账时）",
            "summary_strategy": "用途→附言→业务类型+对方",
            "own_account_column": "Col 4 - 付款人账号",
        },
        "fund_events_fields": FUND_EVENTS_REQUIRED,
    }

    return result
