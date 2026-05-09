#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""中国银行流水导入脚本 - 读取zh0008_preview.tsv，生成fund_events插入语句"""

import csv
from datetime import date

# 读取TSV
records = []
with open('zh0008_preview.tsv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter='\t')
    header = next(reader)  # 跳过表头
    for row in reader:
        if len(row) >= 10:
            records.append(row)

print(f"共 {len(records)} 条记录")

def parse_date(s):
    s = s.strip()
    if len(s) == 8:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    return None

# 按序号排序输出
for i, row in enumerate(records):
    seq = row[0]
    biz_date = parse_date(row[2])
    direction = row[3]
    income = float(row[5]) if row[5] else 0
    expense = float(row[6]) if row[6] else 0
    summary = row[8]
    counterparty = row[9]
    state = row[1]
    
    print(f"[{seq}] {biz_date} | {direction} | +{income:.2f} / -{expense:.2f} | [{summary}] | {counterparty} | {state}")