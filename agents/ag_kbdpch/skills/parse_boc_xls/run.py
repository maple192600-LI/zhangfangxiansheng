
import xlrd
import json
import os
import glob

def run(params):
    file_path = params.get("file_path", "")
    if not os.path.exists(file_path):
        candidates = glob.glob("/**/中行银行流水.xls", recursive=True)
        if not candidates:
            candidates = glob.glob("/**/*中行*.xls", recursive=True)
        if candidates:
            file_path = candidates[0]
        else:
            for root, dirs, files in os.walk("/"):
                for f in files:
                    if "中行" in f and f.endswith(".xls"):
                        file_path = os.path.join(root, f)
                        break
                if file_path and os.path.exists(file_path):
                    break
    wb = xlrd.open_workbook(file_path)
    result = {}
    for sheet_name in wb.sheet_names():
        ws = wb.sheet_by_name(sheet_name)
        rows = []
        for i in range(ws.nrows):
            row = []
            for j in range(ws.ncols):
                cell = ws.cell(i, j)
                cell_type = cell.ctype
                if cell_type == xlrd.XL_CELL_DATE:
                    try:
                        date_tuple = xlrd.xldate_as_tuple(cell.value, wb.datemode)
                        val = f"{date_tuple[0]:04d}-{date_tuple[1]:02d}-{date_tuple[2]:02d}"
                    except:
                        val = str(cell.value)
                elif cell_type == xlrd.XL_CELL_NUMBER:
                    if cell.value == int(cell.value) and abs(cell.value) < 1e15:
                        val = int(cell.value)
                    else:
                        val = cell.value
                else:
                    val = str(cell.value).strip()
                row.append(val)
            rows.append(row)
        result[sheet_name] = rows
    return {"ok": True, "data": result}
