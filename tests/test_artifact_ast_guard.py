"""Tests for artifact AST whitelist guard."""
import pytest

from core.artifact_ast_guard import (
    BLOCKED_BUILTINS,
    BLOCKED_IMPORT_MODULES,
    validate_artifact_code,
)
from core.artifact_runtime import PrimitivesViolationError


# ── Allowed imports ──

def test_allows_fund_primitives_import():
    code = "from fund.primitives.sheet_ops import read_sheet"
    validate_artifact_code(code)


def test_allows_fund_primitives_canonical():
    code = "from fund.primitives.canonical import emit_row"
    validate_artifact_code(code)


def test_allows_datetime_import():
    code = "import datetime"
    validate_artifact_code(code)


def test_allows_decimal_import():
    code = "from decimal import Decimal"
    validate_artifact_code(code)


def test_allows_typing_import():
    code = "from typing import Optional"
    validate_artifact_code(code)


def test_allows_re_import():
    code = "import re"
    validate_artifact_code(code)


def test_allows_collections_import():
    code = "from collections import defaultdict"
    validate_artifact_code(code)


def test_allows_multiple_allowed_imports():
    code = """
import datetime
from decimal import Decimal
from fund.primitives.sheet_ops import read_sheet
from fund.primitives.value_parsers import parse_date
"""
    validate_artifact_code(code)


def test_allows_bare_code_no_imports():
    validate_artifact_code("x = 1 + 2")


# ── Blocked imports ──

def test_blocks_import_os():
    with pytest.raises(PrimitivesViolationError, match="os"):
        validate_artifact_code("import os")


def test_blocks_import_subprocess():
    with pytest.raises(PrimitivesViolationError, match="subprocess"):
        validate_artifact_code("import subprocess")


def test_blocks_import_pathlib():
    with pytest.raises(PrimitivesViolationError, match="pathlib"):
        validate_artifact_code("from pathlib import Path")


def test_blocks_import_requests():
    with pytest.raises(PrimitivesViolationError, match="requests"):
        validate_artifact_code("import requests")


def test_blocks_import_pandas():
    with pytest.raises(PrimitivesViolationError, match="pandas"):
        validate_artifact_code("import pandas")


def test_blocks_import_numpy():
    with pytest.raises(PrimitivesViolationError, match="numpy"):
        validate_artifact_code("import numpy as np")


def test_blocks_import_socket():
    with pytest.raises(PrimitivesViolationError, match="socket"):
        validate_artifact_code("import socket")


def test_blocks_import_shutil():
    with pytest.raises(PrimitivesViolationError, match="shutil"):
        validate_artifact_code("import shutil")


def test_blocks_import_sys():
    with pytest.raises(PrimitivesViolationError, match="sys"):
        validate_artifact_code("import sys")


def test_blocks_import_importlib():
    with pytest.raises(PrimitivesViolationError, match="importlib"):
        validate_artifact_code("import importlib")


# ── Blocked builtins ──

def test_blocks_open():
    with pytest.raises(PrimitivesViolationError, match="open"):
        validate_artifact_code("open('/etc/passwd')")


def test_blocks_eval():
    with pytest.raises(PrimitivesViolationError, match="eval"):
        validate_artifact_code("eval('1+1')")


def test_blocks_exec():
    with pytest.raises(PrimitivesViolationError, match="exec"):
        validate_artifact_code("exec('print(1)')")


def test_blocks_compile():
    with pytest.raises(PrimitivesViolationError, match="compile"):
        validate_artifact_code("compile('x', '', 'exec')")


def test_blocks_dunder_import():
    with pytest.raises(PrimitivesViolationError, match="__import__"):
        validate_artifact_code("__import__('os')")


def test_blocks_importlib_import_module():
    with pytest.raises(PrimitivesViolationError, match="importlib"):
        validate_artifact_code("importlib.import_module('os')")


# ── Syntax errors ──

def test_syntax_error_raises_violation():
    with pytest.raises(PrimitivesViolationError, match="SyntaxError"):
        validate_artifact_code("def foo(")


# ── Error carries artifact_id ──

def test_violation_carries_artifact_id():
    with pytest.raises(PrimitivesViolationError) as exc_info:
        validate_artifact_code("import os", artifact_id=42)
    assert exc_info.value.artifact_id == 42
    assert "os" in str(exc_info.value)


# ── Mixed code ──

def test_allows_valid_parser_function():
    code = """
from fund.primitives.sheet_ops import read_sheet, detect_header_row
from fund.primitives.canonical import emit_row
from datetime import date
from decimal import Decimal

def parse(wb, ctx):
    sheet = read_sheet(wb, index=0)
    yield emit_row(business_date="2026-01-01", summary="test")
"""
    validate_artifact_code(code)


def test_rejects_parser_with_os():
    code = """
import os
from fund.primitives.canonical import emit_row

def parse(wb, ctx):
    os.listdir('/')
    yield emit_row(business_date="2026-01-01", summary="test")
"""
    with pytest.raises(PrimitivesViolationError, match="os"):
        validate_artifact_code(code)
