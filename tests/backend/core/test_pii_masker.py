import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "backend"))

from core.pii_masker import mask_account, mask_amount, mask_name, mask_row


def test_mask_account_keeps_only_last_four_digits():
    assert mask_account("6222021234567890123") == "***************0123"
    assert mask_account("1234") == "1234"


def test_mask_name_keeps_first_character_only():
    assert mask_name("张三") == "张某某"
    assert mask_name("北京测试有限公司") == "北某某"


def test_mask_amount_keeps_order_of_magnitude():
    assert mask_amount("128934.55") == "约十万级"
    assert mask_amount("9800") == "约千级"


def test_mask_row_dispatches_by_header():
    row = ["6222021234567890123", "张三", "128934.55", "2026-04-24"]
    headers = ["对方账号", "对方户名", "收入金额", "交易日期"]

    assert mask_row(row, headers) == ["***************0123", "张某某", "约十万级", "2026-04-24"]
