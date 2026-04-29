# Fixture for check_primitives_whitelist.py negative test.
# §C5 违规样例：import pandas + open() + eval()。
# 扫描期望 exit 1 并列出 3+ 处违规。
import pandas as pd  # 违规 1：pandas 不在基元库白名单
from pathlib import Path  # 违规 2：pathlib 不在白名单

from fund.primitives.sheet_ops import read_sheet  # 合规


def parse(wb, ctx):
    data = open("secret.xlsx")  # 违规 3：内置 open()
    df = pd.DataFrame(data)  # 使用被禁模块
    code = eval("1 + 1")  # 违规 4：eval
    sheet = read_sheet(wb, index=0)
    return df
