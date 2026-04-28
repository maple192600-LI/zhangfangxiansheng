"""银行流水解析引擎

文件格式检测、表头读取、模板匹配、映射执行。
支持 xls (xlrd) / xlsx (openpyxl) / csv。
"""
import csv
import io
import json
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

import openpyxl


def detect_format(filename: str) -> str:
    name = filename.lower()
    if name.endswith(".xlsx"):
        return "xlsx"
    if name.endswith(".xls"):
        return "xls"
    if name.endswith(".csv"):
        return "csv"
    return "unknown"


def read_file(filepath: str, fmt: str) -> List[List[str]]:
    """读取文件，返回原始二维字符串列表"""
    if fmt == "xlsx":
        return _read_xlsx(filepath)
    if fmt == "xls":
        return _read_xls(filepath)
    if fmt == "csv":
        return _read_csv(filepath)
    raise ValueError(f"不支持的文件格式: {fmt}")


def _read_xlsx(filepath: str) -> List[List[str]]:
    wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True)
    ws = wb.active
    rows = []
    for row in ws.iter_rows(values_only=True):
        rows.append([str(c) if c is not None else "" for c in row])
    wb.close()
    return rows


def _read_xls(filepath: str) -> List[List[str]]:
    import xlrd
    wb = xlrd.open_workbook(filepath)
    ws = wb.sheet_by_index(0)
    rows = []
    for r in range(ws.nrows):
        row = []
        for c in range(ws.ncols):
            cell = ws.cell(r, c)
            if cell.ctype == 3:  # XL_CELL_DATE
                val = xlrd.xldate_as_datetime(cell.value, wb.datemode)
                row.append(val.strftime("%Y-%m-%d") if val else "")
            else:
                row.append(str(cell.value) if cell.value != "" else "")
        rows.append(row)
    return rows


def _read_csv(filepath: str) -> List[List[str]]:
    rows = []
    with open(filepath, "r", encoding="utf-8-sig") as f:
        reader = csv.reader(f)
        for row in reader:
            rows.append(row)
    return rows


def read_file_from_bytes(data: bytes, filename: str, fmt: str) -> List[List[str]]:
    """从内存字节读取文件"""
    if fmt == "csv":
        text = data.decode("utf-8-sig", errors="replace")
        reader = csv.reader(io.StringIO(text))
        return [row for row in reader]

    # xlsx / xls 需要临时文件
    import tempfile, os
    suffix = ".xlsx" if fmt == "xlsx" else ".xls"
    fd, tmp = tempfile.mkstemp(suffix=suffix)
    try:
        os.write(fd, data)
        os.close(fd)
        return read_file(tmp, fmt)
    finally:
        os.unlink(tmp)


def detect_header_row(rows: List[List[str]], max_scan: int = 15) -> int:
    """自动检测表头所在行

    策略：
    1. 找到所有包含 3+ 个非空单元格的候选行
    2. 如果第一个候选行包含「日期/金额/摘要/对方/余额/交易」等银行流水关键词，
       它就是表头
    3. 否则跳过元数据行（如"账号:xxx 户名:xxx"），找下一个候选行
    """
    import re
    # 银行流水常见表头关键词
    header_keywords = {"交易", "日期", "金额", "摘要", "对方", "余额", "收入", "支出",
                       "用途", "账号", "开户", "凭证", "币种", "备注", "类型"}

    candidates = []
    for i, row in enumerate(rows[:max_scan]):
        non_empty = sum(1 for c in row if str(c).strip())
        if non_empty >= 3:
            candidates.append((i, row))

    if not candidates:
        return 0

    # 对每个候选行检查是否含银行表头关键词
    for idx, row in candidates:
        all_text = " ".join(str(c) for c in row if c)
        # 检查是否包含冒号分隔的元数据（如"账号:xxx"）
        has_meta = bool(re.search(r'[:：]', all_text))
        # 检查是否含表头关键词
        keyword_hits = sum(1 for kw in header_keywords if kw in all_text)

        if keyword_hits >= 2 and not has_meta:
            return idx

    # fallback: 如果只有一个候选，或都没有明显表头特征，返回第一个候选
    # 但排除包含冒号的元数据行
    for idx, row in candidates:
        all_text = " ".join(str(c) for c in row if c)
        has_meta = bool(re.search(r'[账号|户名|币种].*[:：]', all_text))
        if not has_meta:
            return idx

    return candidates[0][0] if candidates else 0


def match_template(
    headers: List[str],
    templates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """根据表头匹配模板

    匹配策略：表头集合与模板 sample_headers 的交集比例 >= 60%。
    """
    header_set = {h.strip() for h in headers if h.strip()}
    if not header_set:
        return None

    best_match = None
    best_score = 0.0

    for tpl in templates:
        sample = tpl.get("sample_headers", "")
        if isinstance(sample, str):
            try:
                sample_list = json.loads(sample)
            except (json.JSONDecodeError, TypeError):
                sample_list = []
        else:
            sample_list = sample

        sample_set = {h.strip() for h in sample_list if h.strip()}
        if not sample_set:
            continue

        overlap = len(header_set & sample_set)
        score = overlap / max(len(header_set), len(sample_set))

        if score > best_score and score >= 0.6:
            best_score = score
            best_match = tpl

    return best_match


def apply_mapping(
    rows: List[List[str]],
    header_idx: int,
    mapping: Dict[str, str],
    skip_rows: int = 0,
) -> List[Dict[str, str]]:
    """应用模板映射，将原始行转为标准字段字典列表"""
    if header_idx >= len(rows):
        return []

    headers = [h.strip() for h in rows[header_idx]]
    col_map = {}  # col_index -> field_code
    for ci, h in enumerate(headers):
        if h in mapping:
            col_map[ci] = mapping[h]

    data_start = header_idx + 1 + skip_rows
    result = []
    for ri in range(data_start, len(rows)):
        row = rows[ri]
        # 跳过空行
        non_empty = sum(1 for c in row if c and str(c).strip())
        if non_empty == 0:
            continue

        item: Dict[str, str] = {"_row_no": ri + 1}  # 1-based
        for ci, field_code in col_map.items():
            val = row[ci] if ci < len(row) else ""
            item[field_code] = str(val).strip() if val else ""
        result.append(item)

    return result


def normalize_date(val: str) -> Optional[str]:
    """将各种日期格式统一为 YYYY-MM-DD，支持带时间的格式"""
    if not val:
        return None
    val = val.strip()
    # 先尝试带时间的格式
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M",
                "%Y/%m/%d %H:%M", "%Y.%m.%d %H:%M:%S"):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # 纯日期格式
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
        try:
            dt = datetime.strptime(val, fmt)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    # 尝试从混合格式中提取
    import re
    m = re.match(r"(\d{4})[./\-](\d{1,2})[./\-](\d{1,2})", val)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    return None


def normalize_amount(val: str) -> Optional[float]:
    """将金额字符串转为 float"""
    if not val:
        return None
    val = val.strip().replace(",", "").replace("，", "").replace(" ", "")
    if not val or val == "-":
        return None
    try:
        return round(float(val), 2)
    except ValueError:
        return None
