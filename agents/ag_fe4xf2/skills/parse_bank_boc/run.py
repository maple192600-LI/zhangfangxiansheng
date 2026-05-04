"""中国银行流水解析技能

解析中国银行流水 Excel/CSV 文件，提取交易字段。
"""
import os


def run(params: dict) -> dict:
    """解析中国银行流水文件

    params:
      file_path: 文件路径
    """
    file_path = params.get("file_path", "")

    if not file_path:
        return {"ok": False, "error": "缺少 file_path 参数"}

    if not os.path.isfile(file_path):
        return {"ok": False, "error": f"文件不存在: {file_path}"}

    ext = os.path.splitext(file_path)[1].lower()

    if ext in (".xlsx", ".xls"):
        return _parse_excel(file_path)
    elif ext == ".csv":
        return _parse_csv(file_path)
    else:
        return {"ok": False, "error": f"不支持的格式: {ext}"}


def _parse_excel(file_path: str) -> dict:
    try:
        import openpyxl
    except ImportError:
        return {"ok": False, "error": "缺少 openpyxl"}

    try:
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active

        rows = []
        for row in ws.iter_rows(values_only=True):
            cells = [str(c) if c is not None else "" for c in row]
            if any(cells):
                rows.append(cells)

        wb.close()

        if not rows:
            return {"ok": False, "error": "文件为空"}

        header = rows[0]
        data_rows = rows[1:]

        return {
            "ok": True,
            "file": os.path.basename(file_path),
            "bank": "中国银行",
            "header": header,
            "row_count": len(data_rows),
            "preview": data_rows[:5],
            "message": f"中行流水解析完成，共 {len(data_rows)} 行。请确认字段映射。",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _parse_csv(file_path: str) -> dict:
    try:
        import csv

        rows = []
        with open(file_path, "r", encoding="utf-8-sig", errors="replace") as f:
            for row in csv.reader(f):
                if any(cell.strip() for cell in row):
                    rows.append(row)

        if not rows:
            return {"ok": False, "error": "文件为空"}

        return {
            "ok": True,
            "file": os.path.basename(file_path),
            "bank": "中国银行",
            "header": rows[0],
            "row_count": len(rows) - 1,
            "preview": rows[1:6],
            "message": f"中行流水解析完成，共 {len(rows) - 1} 行。请确认字段映射。",
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
