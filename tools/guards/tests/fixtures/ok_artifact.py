# Fixture for check_primitives_whitelist.py positive test.
# §C5 合规：仅 import 白名单路径。
from datetime import date
from decimal import Decimal
import re

from fund.primitives.sheet_ops import read_sheet, detect_header_row, extract_headers, iter_data_rows
from fund.primitives.value_parsers import parse_date, parse_amount, parse_text
from fund.primitives.canonical import emit_row


def parse(wb, ctx):
    sheet = read_sheet(wb, index=0)
    header_row = detect_header_row(sheet)
    headers = extract_headers(sheet, header_row)
    for raw in iter_data_rows(sheet, header_row + 1):
        date_v = parse_date(raw.get(headers.get("日期")))
        amt_in = parse_amount(raw.get(headers.get("收入")))
        amt_out = parse_amount(raw.get(headers.get("支出")))
        if re.match(r"^\d{4}-\d{2}-\d{2}$", str(date_v)):
            yield emit_row(
                business_date=date_v,
                amount_in=amt_in,
                amount_out=amt_out,
            )
