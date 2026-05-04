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


def detect_header_row(rows: List[List[str]], max_scan: int = 30) -> int:
    """自动检测表头所在行

    策略：
    1. 找到所有包含 3+ 个非空单元格的候选行（扫描范围扩大到 30 行）
    2. 对每个候选行评分：关键词命中数 × 非空列数
    3. 优先选择关键词命中多且列数多的行（真正的表头通常 6+ 列且命中多个关键词）
    4. 排除元数据行（含冒号分隔的 key:value 或 key  value 模式）
    """
    import re
    # 银行流水常见交易表头关键词（按权重分类）
    strong_keywords = {"交易日", "交易日期", "借方金额", "贷方金额", "摘要", "余额",
                       "对方户名", "对方名称", "收入金额", "支出金额", "用途",
                       "起息日", "流水号"}
    general_keywords = {"交易", "日期", "金额", "摘要", "对方", "余额", "收入", "支出",
                        "用途", "账号", "开户", "凭证", "币种", "备注", "类型",
                        "交易时间", "交易类型", "贷方", "借方", "发生额"}

    candidates = []
    for i, row in enumerate(rows[:max_scan]):
        non_empty = sum(1 for c in row if str(c).strip())
        if non_empty >= 3:
            candidates.append((i, row))

    if not candidates:
        return 0

    best_idx = candidates[0][0]
    best_score = 0

    for idx, row in candidates:
        cells = [str(c).strip() for c in row if str(c).strip()]
        non_empty = len(cells)
        all_text = " ".join(cells)

        # 计算关键词命中
        strong_hits = sum(1 for kw in strong_keywords if kw in all_text)
        general_hits = sum(1 for kw in general_keywords if kw in all_text)
        total_hits = strong_hits * 3 + general_hits

        # 排除元数据行：含冒号分隔的 key:value 对，或类似"接口版本 2.0 银行码 5456"的元数据模式
        has_colon_meta = bool(re.search(r'[：:]', all_text))
        # 检测 key-value 对模式：中文标签后面紧跟数字/日期/代码（非中文的值）
        kv_pairs = re.findall(r'[\u4e00-\u9fff]{2,6}\s+[\d.:/\-]+', all_text)
        # 如果含数字值的 KV 对 >= 2，且关键词命中少，这是元数据行
        if kv_pairs and len(kv_pairs) >= 2 and total_hits < 5:
            continue

        # 评分：关键词权重 × 非空列数（真正表头通常 6+ 列）
        # 元数据行通常 2-4 列有价值信息，表头通常 6+ 列
        score = total_hits * non_empty

        if has_colon_meta:
            score = score // 3  # 含冒号的大概率是元数据，降权

        if score > best_score:
            best_score = score
            best_idx = idx

    return best_idx


def match_template(
    headers: List[str],
    templates: List[Dict[str, Any]],
) -> Optional[Dict[str, Any]]:
    """根据表头匹配模板

    匹配策略：
    - 核心指标：模板覆盖率 = overlap / len(sample_set)（模板的列有多少比例在文件中能找到）
    - 最低要求：覆盖率 >= 70%，且至少命中 3 个列
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
            # 回退：用 mapping_json 的 key 作为匹配源
            mapping = tpl.get("mapping_json", {})
            if isinstance(mapping, str):
                try:
                    mapping = json.loads(mapping)
                except (json.JSONDecodeError, TypeError):
                    mapping = {}
            if isinstance(mapping, dict) and "_columns" in mapping:
                mapping = mapping["_columns"]
            sample_set = {h.strip() for h in mapping.keys() if h.strip()}
            if not sample_set:
                continue

        overlap = len(header_set & sample_set)
        if overlap < 3:
            continue

        # 模板覆盖率：模板的列有多少能在文件中找到
        score = overlap / len(sample_set)

        if score > best_score and score >= 0.7:
            best_score = score
            best_match = tpl

    return best_match


def apply_mapping(
    rows: List[List[str]],
    header_idx: int,
    mapping: Dict[str, Any],
    skip_rows: int = 0,
) -> List[Dict[str, str]]:
    """应用模板映射，将原始行转为标准字段字典列表。

    mapping 支持：
    - 简单映射: {"银行列名": "标准字段code"}
    - 带后处理: {"_columns": {"银行列名": "标准字段code"}, "post_process": {...}}
    """
    if header_idx >= len(rows):
        return []

    # 分离列映射和后处理规则
    col_mapping: Dict[str, str] = {}
    post_process: Dict[str, Any] = {}
    if "_columns" in mapping:
        col_mapping = mapping["_columns"]
        post_process = mapping.get("post_process", {})
    else:
        # 兼容旧格式：顶层全部视为列映射，排除 post_process 键
        post_process = mapping.get("post_process", {})
        col_mapping = {k: v for k, v in mapping.items() if k != "post_process"}

    headers = [h.strip() for h in rows[header_idx]]
    col_map = {}  # col_index -> field_code
    for ci, h in enumerate(headers):
        if h in col_mapping:
            col_map[ci] = col_mapping[h]

    # 为条件映射构建额外的列索引
    cond_cols = _build_conditional_indices(headers, post_process)

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

        # 执行后处理
        if post_process:
            _apply_post_process(item, row, post_process, cond_cols)

        # 清除临时字段（以 _ 开头但不是 _row_no / _errors 的字段）
        item = {k: v for k, v in item.items() if not (k.startswith("_") and k not in ("_row_no", "_errors"))}

        result.append(item)

    return result


def _build_conditional_indices(
    headers: List[str], post_process: Dict[str, Any]
) -> Dict[str, int]:
    """为后处理规则中的列引用构建列名→索引映射"""
    cols = {}
    if not post_process:
        return cols

    # 收集所有引用的列名
    ref_names = set()
    for rule in post_process.get("conditional_field", []):
        if "condition_column" in rule:
            ref_names.add(rule["condition_column"])
        for branch in rule.get("branches", []):
            if "source_column" in branch:
                ref_names.add(branch["source_column"])

    for rule in post_process.get("amount_split", []):
        if "source_column" in rule:
            ref_names.add(rule["source_column"])

    for rule in post_process.get("priority_merge", []):
        for src in rule.get("source_columns", []):
            ref_names.add(src)

    header_set = {h.strip(): i for i, h in enumerate(headers)}
    for name in ref_names:
        idx = header_set.get(name)
        if idx is not None:
            cols[name] = idx
    return cols


def _get_col_val(row: List[str], col_idx: int) -> str:
    """安全取列值"""
    val = row[col_idx] if col_idx < len(row) else ""
    return str(val).strip() if val else ""


def _apply_post_process(
    item: Dict[str, str],
    row: List[str],
    post_process: Dict[str, Any],
    cond_cols: Dict[str, int],
) -> None:
    """对单行数据执行后处理规则"""
    import re

    # 1. 金额拆分：单列金额按正负值拆为收入/支出
    for rule in post_process.get("amount_split", []):
        src_col = rule.get("source_column", "")
        col_idx = cond_cols.get(src_col)
        if col_idx is None:
            continue
        raw_val = _get_col_val(row, col_idx)
        amount = normalize_amount(raw_val)
        if amount is None:
            continue
        income_field = rule.get("income_field", "income_amount")
        expense_field = rule.get("expense_field", "expense_amount")
        if amount >= 0:
            item[income_field] = str(amount) if amount > 0 else ""
            item[expense_field] = ""
        else:
            item[expense_field] = str(abs(amount))
            item[income_field] = ""

    # 2. 条件字段：根据条件列的值选择不同的源列
    for rule in post_process.get("conditional_field", []):
        cond_col = rule.get("condition_column", "")
        target_field = rule.get("target_field", "")
        col_idx = cond_cols.get(cond_col)
        if col_idx is None or not target_field:
            continue
        cond_val = _get_col_val(row, col_idx)
        matched = False
        for branch in rule.get("branches", []):
            if not matched:
                pattern = branch.get("match", "")
                if re.search(pattern, cond_val):
                    src_col = branch.get("source_column", "")
                    src_idx = cond_cols.get(src_col)
                    if src_idx is not None:
                        item[target_field] = _get_col_val(row, src_idx)
                    matched = True
        if not matched:
            default_col = rule.get("default_source", "")
            if default_col:
                src_idx = cond_cols.get(default_col)
                if src_idx is not None:
                    item[target_field] = _get_col_val(row, src_idx)

    # 3. 优先级合并：从多个源列按优先级取第一个非空值
    for rule in post_process.get("priority_merge", []):
        target_field = rule.get("target_field", "")
        if not target_field:
            continue
        for src_col in rule.get("source_columns", []):
            src_idx = cond_cols.get(src_col)
            if src_idx is not None:
                val = _get_col_val(row, src_idx)
                if val:
                    item[target_field] = val
                    break

    # 4. 摘要生成：基于 priority_sources 或可用字段生成 fallback 摘要
    sg = post_process.get("summary_generation")
    if sg and not item.get("summary_text", "").strip():
        _generate_summary(item, row, sg, cond_cols)


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


def _generate_summary(
    item: Dict[str, str],
    row: List[str],
    sg: Dict[str, Any],
    cond_cols: Dict[str, int],
) -> None:
    """基于 summary_generation 规则生成 fallback 摘要

    策略：按 logic 中的 priority_sources 顺序，取第一个非空且不在
    encoding_filter / meaningless_values 中的值作为摘要。
    """
    import re

    encoding_patterns = sg.get("encoding_detection", {}).get("patterns", [])
    logic_rules = sg.get("logic", [])

    # 按业务类型匹配摘要规则
    business_type_val = item.get("_business_type", "")
    for rule in logic_rules:
        match_types = rule.get("match_business_type", [])
        if not match_types or any(mt in business_type_val for mt in match_types):
            if rule.get("rule") == "fixed":
                item["summary_text"] = rule.get("fixed_value", "")
                return
            if rule.get("rule") == "fixed_with_type":
                type_mapping = rule.get("type_mapping", {})
                for mt, label in type_mapping.items():
                    if mt in business_type_val:
                        item["summary_text"] = label
                        return
            # priority: 按 priority_sources 顺序找第一个有效值
            for ps in rule.get("priority_sources", []):
                src_field = ps.get("source", "")
                # 先检查 item 中已有的映射值
                val = item.get(src_field, "").strip()
                if not val:
                    # 再从原始行数据中取
                    src_idx = cond_cols.get(src_field)
                    if src_idx is not None:
                        val = _get_col_val(row, src_idx)
                if not val:
                    continue
                # 过滤编码类无意义值
                if encoding_patterns and re.match(encoding_patterns[0], val):
                    continue
                meaningless = rule.get("meaningless_values", [])
                if val in meaningless:
                    continue
                item["summary_text"] = val
                return

    # fallback: 尝试从常用字段取值
    for field in ("_purpose", "_remark", "_reference", "_notes"):
        val = item.get(field, "").strip()
        if not val:
            src_idx = cond_cols.get(field)
            if src_idx is not None:
                val = _get_col_val(row, src_idx)
        if val and not (encoding_patterns and re.match(encoding_patterns[0], val)):
            item["summary_text"] = val
            return

    # 最终兜底
    item["summary_text"] = sg.get("final_fallback", "交易")
