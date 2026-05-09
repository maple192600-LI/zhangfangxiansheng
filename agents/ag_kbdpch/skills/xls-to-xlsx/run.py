#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xls转xlsx"""
import xlrd
from openpyxl import Workbook

input_path = 'workspace/inbox/中行银行流水.xls'
output_path = 'workspace/inbox/中行银行流水.xlsx'

wb_in = xlrd.open_workbook(input_path)
ws_in = wb_in.sheet_by_index(0)
wb_out = Workbook()
ws_out = wb_out.active
ws_out.title = "Sheet1"
for r in range(ws_in.nrows):
    ws_out.append([ws_in.cell(r, c).value for c in range(ws_in.ncols)])
wb_out.save(output_path)
print("转换完成:", output_path)