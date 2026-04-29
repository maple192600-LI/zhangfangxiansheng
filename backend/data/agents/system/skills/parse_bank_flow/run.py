"""通用银行流水智能解析技能

功能：
1. 自动检测文件格式（xlsx/xls/csv）
2. 自动定位表头行
3. 自动识别表头字段（模糊匹配中文表头到标准字段）
4. 提取交易数据行
5. 匹配系统中的账户信息
6. 输出可直接写入 fund_events 表的结构化数据
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


# ── 字段映射：中文表头关键词 → fund_events 标准字段 ──

HEADER_FIELD_MAP = {
    # 日期字段
    "business_date": ["交易日期", "交易时间", "日期", "记账日期", "发生日期", "交易发生日", "记账日", "trans_date"],
    # 收入/贷方金额
    "amount_in": ["收入", "贷方金额", "收入金额", "存入金额", "贷方发生额", "入账金额", "收入(贷方)", "credit_amount"],
    # 支出/借方金额
    "amount_out": ["支出", "借方金额", "支出金额", "取出金额", "借方发生额", "出账金额", "支出(借方)", "debit_amount"],
    # 单一金额 + 方向
    "amount": ["交易金额", "发生额", "金额", "交易额", "发生金额"],
    "direction": ["收付标志", "借贷标志", "方向", "收支标志", "交易方向"],
    # 余额
    "rolling_balance": ["余额", "账户余额", "当前余额", "账面余额", "可用余额"],
    # 对方信息
    "counterparty": ["对方户名", "对方账户名称", "对方名称", "交易对方名称", "对方姓名", "付款人名称", "收款人", "对方账号名称", "付款人"],
    "counterparty_account": ["对方账号", "对方账户", "对方账号"],
    # 摘要
    "summary": ["摘要", "交易摘要", "备注", "交易备注", "用途", "交易附言", "交易内容", "备注信息"],
    # 账户信息（文件头可能包含）
    "account_name": ["账户名称", "户名", "账户名称"],
    "account_number": ["账号", "银行账号", "账户号码", "卡号"],
    "entity_name": ["公司名称", "客户名称", "开户名"],
}

# fund_events 需要的字段
FUND_EVENTS_REQUIRED = [
    "business_date", "entity_code", "entity_name",
    "account_code", "account_name",
    "amount_in", "amount_out", "rolling_balance",
    "summary", "counterparty", "source",
]


def _match_header_to_field(header_text: str) -> str | None:
    """将一个中文表头文本匹配到标准字段名"""
    h = header_text.strip()
    for field_code, keywords in HEADER_FIELD_MAP.items():
        for kw in keywords:
            if h == kw or kw in h or h in kw:
                return field_code
    return None


def _build_column_mapping(headers: list[str]) -> dict[int, str]:
    """从表头列表构建列索引→字段名映射"""
    col_map = {}
    for ci, h in enumerate(headers):
        h = h.strip()
        if not h:
            continue
        field = _match_header_to_field(h)
        if field and field not in col_map.values():
            col_map[ci] = field
    return col_map


def _extract_account_info_from_header(rows: list[list[str]], header_idx: int) -> dict:
    """从文件头部（表头之前的行）提取账户信息"""
    info = {}
    for ri in range(min(header_idx, 15)):
        row = rows[ri]
        for cell in row:
            text = str(cell).strip() if cell else ""
            if not text:
                continue
            # 匹配"账号：xxxx"格式
            for key in ["账号", "账户号码", "银行账号"]:
                if key in text and ":" in text:
                    info["account_number"] = text.split(":", 1)[1].strip()
                elif key in text and "：" in text:
                    info["account_number"] = text.split("：", 1)[1].strip()
            for key in ["账户名称", "户名", "客户名称"]:
                if key in text and ":" in text:
                    info["account_name"] = text.split(":", 1)[1].strip()
                elif key in text and "：" in text:
                    info["account_name"] = text.split("：", 1)[1].strip()
            for key in ["公司名称", "开户名"]:
                if key in text and ":" in text:
                    info["entity_name"] = text.split(":", 1)[1].strip()
                elif key in text and "：" in text:
                    info["entity_name"] = text.split("：", 1)[1].strip()
    return info


def _match_account_from_db(account_number: str = None, account_name: str = None) -> dict | None:
    """从数据库中匹配账户"""
    try:
        from database import SessionLocal
        from db.tables import Account, Entity

        db = SessionLocal()
        try:
            query = db.query(Account, Entity).join(Entity, Account.entity_id == Entity.id)

            matched = None
            if account_number:
                matched = query.filter(Account.account_number == account_number).first()
            if not matched and account_name:
                matched = query.filter(Account.account_alias == account_name).first()
            if not matched and account_number:
                # 模糊匹配后四位
                last_four = account_number[-4:] if len(account_number) >= 4 else account_number
                matched = query.filter(Account.account_last_four == last_four).first()

            if matched:
                acc, ent = matched
                return {
                    "account_id": acc.id,
                    "account_code": acc.account_code,
                    "account_name": acc.account_alias,
                    "account_number": acc.account_number,
                    "entity_id": ent.id,
                    "entity_code": ent.entity_code,
                    "entity_name": ent.short_name,
                    "bank_name": acc.bank_name,
                }
        finally:
            db.close()
    except Exception:
        pass
    return None


def run(params: dict) -> dict:
    file_path = params.get("file_path", "")
    entity_code = params.get("entity_code", "")
    account_code = params.get("account_code", "")

    if not file_path or not os.path.isfile(file_path):
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    # 1. 检测格式并读取
    fmt = detect_format(file_path)
    if fmt not in ("xlsx", "xls", "csv"):
        return {"ok": False, "error": f"不支持的文件格式: {fmt}"}

    try:
        rows = read_file(file_path, fmt)
    except Exception as e:
        return {"ok": False, "error": f"读取文件失败: {e}"}

    if len(rows) < 2:
        return {"ok": False, "error": "文件内容为空或行数不足"}

    # 2. 定位表头
    header_idx = detect_header_row(rows)
    headers = [h.strip() for h in rows[header_idx]]

    # 3. 构建列映射
    col_map = _build_column_mapping(headers)

    # 检查是否至少有日期和金额字段
    mapped_fields = set(col_map.values())
    has_date = "business_date" in mapped_fields
    has_amount = bool(mapped_fields & {"amount", "amount_in", "amount_out"})

    if not has_date or not has_amount:
        return {
            "ok": False,
            "error": "无法识别有效的交易数据表头。需要至少包含日期和金额相关的列。",
            "detected_headers": headers,
            "mapped_fields": list(mapped_fields),
        }

    # 4. 提取文件头部账户信息
    header_info = _extract_account_info_from_header(rows, header_idx)

    # 5. 匹配系统账户
    matched_account = None
    acc_num = params.get("account_number", "") or header_info.get("account_number", "")
    acc_name = header_info.get("account_name", "")
    if acc_num or acc_name:
        matched_account = _match_account_from_db(acc_num, acc_name)

    # 如果指定了 entity_code 或 account_code，覆盖
    if entity_code or account_code:
        try:
            from database import SessionLocal
            from db.tables import Account, Entity
            db = SessionLocal()
            try:
                q = db.query(Account, Entity).join(Entity, Account.entity_id == Entity.id)
                if account_code:
                    q = q.filter(Account.account_code == account_code)
                elif entity_code:
                    q = q.filter(Entity.entity_code == entity_code)
                m = q.first()
                if m:
                    acc, ent = m
                    matched_account = {
                        "account_id": acc.id,
                        "account_code": acc.account_code,
                        "account_name": acc.account_alias,
                        "entity_id": ent.id,
                        "entity_code": ent.entity_code,
                        "entity_name": ent.short_name,
                        "bank_name": acc.bank_name,
                    }
            finally:
                db.close()
        except Exception:
            pass

    # 6. 解析交易行
    data_start = header_idx + 1
    transactions = []

    for ri in range(data_start, len(rows)):
        row = rows[ri]
        non_empty = sum(1 for c in row if c and str(c).strip())
        if non_empty == 0:
            continue

        item = {"_row_no": ri + 1}

        for ci, field_code in col_map.items():
            val = row[ci] if ci < len(row) else ""
            item[field_code] = str(val).strip() if val else ""

        # 标准化日期
        if "business_date" in item:
            item["business_date"] = normalize_date(item["business_date"]) or item["business_date"]

        # 处理金额字段
        if "amount" in item:
            amt = normalize_amount(item["amount"])
            if amt is not None:
                direction = item.get("direction", "")
                if any(kw in direction for kw in ["付", "借", "支", "出"]):
                    item["amount_out"] = abs(amt)
                    item["amount_in"] = 0.0
                else:
                    item["amount_in"] = abs(amt)
                    item["amount_out"] = 0.0
                item["amount"] = amt

        # 标准化单独的收入/支出字段
        if "amount_in" in item and not isinstance(item["amount_in"], (int, float)):
            item["amount_in"] = normalize_amount(str(item["amount_in"])) or 0.0
        if "amount_out" in item and not isinstance(item["amount_out"], (int, float)):
            item["amount_out"] = normalize_amount(str(item["amount_out"])) or 0.0

        if "rolling_balance" in item:
            item["rolling_balance"] = normalize_amount(str(item["rolling_balance"]))

        # 补充系统账户信息
        if matched_account:
            item["entity_code"] = matched_account["entity_code"]
            item["entity_name"] = matched_account["entity_name"]
            item["account_code"] = matched_account["account_code"]
            item["account_name"] = matched_account["account_name"]

        item["source"] = "网银导入"
        transactions.append(item)

    # 7. 构建结果
    result = {
        "ok": True,
        "file_name": os.path.basename(file_path),
        "file_format": fmt,
        "total_rows": len(transactions),
        "transactions": transactions,
        "detected_headers": headers,
        "mapped_fields": {ci: f for ci, f in col_map.items()},
        "header_info": header_info,
        "matched_account": matched_account,
        "fund_events_fields": FUND_EVENTS_REQUIRED,
    }

    return result
