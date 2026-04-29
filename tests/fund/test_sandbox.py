from __future__ import annotations

import pytest
from openpyxl import Workbook

from agents.fund import sandbox


def _workbook() -> Workbook:
    wb = Workbook()
    ws = wb.active
    ws.append(["Date", "EntityId", "AccountId", "Summary", "Income", "Expense"])
    ws.append(["2026-04-24", "E001", "A001", "receipt", "300.00", ""])
    return wb


LEGAL_CODE = """
from fund.primitives.sheet_ops import read_sheet, detect_header_row, extract_headers, iter_data_rows, is_empty_row
from fund.primitives.value_parsers import parse_date, parse_amount, parse_text
from fund.primitives.canonical import emit_row


def parse(wb, ctx):
    sheet = read_sheet(wb, index=0)
    header_row = detect_header_row(sheet)
    headers = extract_headers(sheet, header_row)
    for raw in iter_data_rows(sheet, header_row + 1):
        if is_empty_row(raw):
            continue
        yield emit_row(
            business_date=parse_date(raw[headers["Date"]]),
            entity_code=parse_text(raw[headers["EntityId"]]),
            entity_name="示例公司",
            account_code=parse_text(raw[headers["AccountId"]]),
            account_name="工行主户",
            summary=parse_text(raw[headers["Summary"]]),
            counterparty="",
            amount_in=parse_amount(raw[headers["Income"]]),
            amount_out=parse_amount(raw[headers["Expense"]]),
            source="网银导入",
        )
"""


def test_sandbox_accepts_legal_parser_code():
    rows = list(sandbox.execute(LEGAL_CODE, _workbook(), {}, timeout=5))
    assert len(rows) == 1
    assert list(rows[0].keys()) == [
        "business_date",
        "entity_code",
        "entity_name",
        "account_code",
        "account_name",
        "summary",
        "counterparty",
        "amount_in",
        "amount_out",
        "rolling_balance",
        "state",
        "source",
    ]
    assert rows[0]["amount_in"] == 300


def test_sandbox_rejects_import_os():
    code = "import os\n\ndef parse(wb, ctx):\n    return []\n"
    with pytest.raises(sandbox.SandboxRejected):
        list(sandbox.execute(code, _workbook(), {}, timeout=5))


def test_sandbox_rejects_eval_call():
    code = "def parse(wb, ctx):\n    eval('1 + 1')\n    return []\n"
    with pytest.raises(sandbox.SandboxRejected):
        list(sandbox.execute(code, _workbook(), {}, timeout=5))


def test_sandbox_kills_infinite_loop():
    code = "def parse(wb, ctx):\n    while True:\n        pass\n    return []\n"
    with pytest.raises(sandbox.SandboxTimeout):
        list(sandbox.execute(code, _workbook(), {}, timeout=1))


def test_sandbox_handles_memory_bomb_with_limit_or_timeout():
    code = "def parse(wb, ctx):\n    x = [1] * (10 ** 9)\n    return x\n"
    with pytest.raises((sandbox.SandboxExecutionError, sandbox.SandboxTimeout)):
        list(sandbox.execute(code, _workbook(), {}, timeout=2, mem_limit_mb=64))


def test_sandbox_reads_limits_from_ai_config_model_name_json():
    rows = list(
        sandbox.execute(
            LEGAL_CODE,
            _workbook(),
            {},
            timeout=30,
            mem_limit_mb=256,
            ai_config={"model_name": '{"sandbox_timeout": 5, "sandbox_mem_limit_mb": 128}'},
        )
    )
    assert len(rows) == 1
