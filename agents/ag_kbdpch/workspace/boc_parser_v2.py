#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
中国银行企业网银流水解析器 v2
【改进版】按照完整规格说明实现，包含摘要生成规则、异常检测。

约束红线：
1. 禁止硬编码列索引，所有字段通过表头名称动态定位
2. 摘要禁止包含金额数字、金额单位
3. 摘要禁止包含敏感词
4. 可疑交易通过"状态"列标记为"待确认"，不在摘要中定性
5. 禁止在摘要中猜测业务性质
6. 单位编码和账户编码必须从外部配置获取
"""

import json
import re
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import pandas as pd
import openpyxl
from openpyxl.styles import Font, PatternFill
from openpyxl.utils import get_column_letter


# ============================================================================
# 工具函数
# ============================================================================

def load_config(config_path: str) -> Dict:
    """读取JSON配置文件"""
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def contains_chinese(text: str) -> bool:
    """检查文本是否包含中文字符"""
    if not text:
        return False
    return bool(re.search(r'[\u4e00-\u9fff]', text))


def simplify_counterparty_name(full_name: str) -> str:
    """
    将对方全称简化为不超过15个字符的简称。
    
    规则：
    1. 去除前缀：山西、太原市、阳曲县
    2. 去除后缀：道路建设养护集团有限公司、集团有限公司、有限公司等
    3. 最终结果不超过15字符
    """
    if not full_name:
        return ''
    
    result = full_name
    
    # 去除前缀
    prefixes = ['山西', '太原市', '阳曲县']
    for prefix in prefixes:
        if result.startswith(prefix):
            result = result[len(prefix):]
            break
    
    # 去除后缀（按长度从长到短匹配）
    suffixes = [
        '道路建设养护集团有限公司',
        '建设养护集团有限公司',
        '集团有限公司',
        '有限责任公司',
        '有限公司',
        '经营部',
        '合伙企业'
    ]
    for suffix in suffixes:
        if result.endswith(suffix):
            result = result[:-len(suffix)]
            break
    
    # 如果结果为空，使用原始全称
    if not result:
        result = full_name
    
    # 截断到15字符
    if len(result) > 15:
        result = result[:15]
    
    return result


def extract_bank_short_name(bank_full_name: str) -> str:
    """从银行全称提取简称"""
    if not bank_full_name:
        return ''
    
    bank_mappings = {
        '中国银行': '中行',
        '中国农业银行': '农行',
        '中国工商银行': '工行',
        '中国建设银行': '建行',
        '中国交通银行': '交行',
        '招商银行': '招行',
        '浦发银行': '浦发',
        '民生银行': '民生',
        '兴业银行': '兴业',
    }
    
    for full_name, short_name in bank_mappings.items():
        if full_name in bank_full_name:
            return short_name
    
    return bank_full_name[:4] if len(bank_full_name) > 4 else bank_full_name


def parse_amount(amount_str: str) -> Optional[float]:
    """解析金额字符串为浮点数"""
    if not amount_str or str(amount_str).strip() == '':
        return None
    try:
        # 去除千分位逗号
        cleaned = str(amount_str).replace(',', '').strip()
        return float(cleaned)
    except ValueError:
        return None


def parse_date(date_str: str) -> str:
    """解析日期字符串为标准格式 YYYY-MM-DD"""
    if not date_str:
        return ''
    
    s = str(date_str).strip()
    
    # 如果是Excel序列号（整数）
    if s.isdigit() and len(s) <= 5:
        try:
            from datetime import datetime, timedelta
            # Excel日期序列号从1900-01-01开始，但需要加1因为Excel从1开始
            d = datetime(1899, 12, 30) + timedelta(days=int(s))
            return d.strftime('%Y-%m-%d')
        except:
            pass
    
    # 尝试各种日期格式
    formats = [
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y%m%d',
        '%Y-%d-%m',
        '%d/%m/%Y',
        '%m/%d/%Y',
    ]
    
    for fmt in formats:
        try:
            from datetime import datetime
            d = datetime.strptime(s[:10], fmt)
            return d.strftime('%Y-%m-%d')
        except:
            continue
    
    return s[:10] if len(s) >= 10 else s


# ============================================================================
# 表头识别与字段映射
# ============================================================================

def find_header_row(df: pd.DataFrame) -> int:
    """
    扫描DataFrame的前N行，找到表头行位置。
    
    判定标准：该行的所有单元格文本合集里，同时包含"交易日期"和"交易金额"。
    """
    for idx in range(min(20, len(df))):
        row_text = ' '.join([str(v) for v in df.iloc[idx].values if pd.notna(v)])
        if '交易日期' in row_text and '交易金额' in row_text:
            return idx
    raise ValueError("无法找到表头行，表头行必须同时包含'交易日期'和'交易金额'")


def build_field_mapping(header_row: List[str]) -> Dict[str, int]:
    """
    根据表头行构建字段名到列索引的映射字典。
    字段名格式为"中文名[ 英文名 ]"，取中文名作为键。
    """
    mapping = {}
    for col_idx, field_name in enumerate(header_row):
        # 提取中文名（去掉方括号及后面的英文名）
        if '[' in field_name and ']' in field_name:
            cn_name = field_name.split('[')[0].strip()
        else:
            cn_name = field_name.strip()
        
        if cn_name:
            mapping[cn_name] = col_idx
    
    return mapping


def get_cell_value(row_data, field_mapping: Dict[str, int], field_name: str) -> str:
    """根据字段名从一行数据中获取值"""
    if field_name not in field_mapping:
        return ''
    col_idx = field_mapping[field_name]
    value = row_data.iloc[col_idx] if col_idx < len(row_data) else None
    if pd.isna(value):
        return ''
    return str(value).strip()


# ============================================================================
# 摘要生成
# ============================================================================

def generate_summary(row: Dict, summary_rules: List[Dict], our_company_name: str) -> Tuple[str, str, str]:
    """
    根据规则生成摘要和对方名称。
    
    优先级：
    1. 配置文件精确匹配（最高）
    2. 内部划转（往账 + 对方是本公司）
    3. 来账（外部收入）
    4. 往账（外部支出）
    5. 兜底
    
    Returns: (摘要, 对方名称, 状态)
    """
    txn_type = row.get('交易类型', '')
    biz_type = row.get('业务类型', '')
    payer_name = row.get('付款人名称', '')
    payee_name = row.get('收款人名称', '')
    purpose = row.get('用途', '')
    remark_field = row.get('交易附言', '')
    original_summary = row.get('摘要', '')
    payee_bank = row.get('收款人开户行名', '')
    counterparty_full = payer_name if txn_type == '来账' else payee_name
    
    is_internal = (counterparty_full == our_company_name)
    
    # 第1级：配置文件精确匹配
    for rule in summary_rules:
        match = rule.get('匹配条件', {})
        field = match.get('字段')
        value = match.get('值')
        sub_field = match.get('子字段')
        contains = match.get('包含')
        
        if field == '业务类型':
            if biz_type != value:
                continue
        
        # 检查子字段（如果有）
        if sub_field and contains:
            sub_value = ''
            if sub_field == '摘要':
                sub_value = original_summary
            elif sub_field == '用途':
                sub_value = purpose
            
            if contains not in sub_value:
                continue
        
        # 命中规则
        config_summary = rule['摘要']
        clear_counterparty = rule.get('对方清空', False)
        
        if clear_counterparty:
            return config_summary, '', '正常'
        else:
            return config_summary, counterparty_full, '正常'
    
    # 第2级：内部划转（往账 + 对方是本公司）
    if txn_type == '往账' and is_internal:
        bank_short = extract_bank_short_name(payee_bank)
        if bank_short:
            summary = f'内部资金划转至{bank_short}'
        else:
            summary = '内部资金划转'
        return summary, '本公司', '正常'
    
    # 第3级：来账（外部收入）
    if txn_type == '来账' and not is_internal:
        counterparty_short = simplify_counterparty_name(counterparty_full)
        summary = f'收{counterparty_short}款项'
        return summary, counterparty_full, '正常'
    
    # 第4级：往账（外部支出）
    if txn_type == '往账' and not is_internal:
        counterparty_short = simplify_counterparty_name(counterparty_full)
        summary = f'付{counterparty_short}款项'
        return summary, counterparty_full, '正常'
    
    # 第5级：兜底
    if txn_type == '来账':
        summary = '收到款项'
    elif txn_type == '往账':
        summary = '付出款项'
    else:
        summary = '未知交易'
    
    return summary, counterparty_full, '正常'


# ============================================================================
# 异常检测
# ============================================================================

def check_same_day_paired(df: pd.DataFrame, min_amount: float, error_ratio: float) -> set:
    """
    同日收付配对检测。
    找出同日同金额（或接近金额）的来账和往账，配对的记录标记为"待确认"。
    """
    suspicious_indices = set()
    
    # 按日期分组
    grouped = df.groupby('交易日期')
    
    for date, group in grouped:
        # 候选收入：来账 + 金额 >= min_amount
        incomes = group[group['交易类型'] == '来账']
        incomes = incomes[incomes['收入金额'] >= min_amount]
        
        # 候选支出：往账 + 金额 >= min_amount
        expenses = group[group['交易类型'] == '往账']
        expenses = expenses[expenses['支出金额'] >= min_amount]
        
        # 两两配对
        for _, income_row in incomes.iterrows():
            for _, expense_row in expenses.iterrows():
                income_amount = income_row['收入金额']
                expense_amount = expense_row['支出金额']
                
                # 金额匹配误差检查
                if income_amount > 0:
                    diff_ratio = abs(income_amount - expense_amount) / income_amount
                    if diff_ratio <= error_ratio:
                        suspicious_indices.add(income_row.name)
                        suspicious_indices.add(expense_row.name)
    
    return suspicious_indices


def check_large_expense_no_purpose(df: pd.DataFrame, min_amount: float, our_company_name: str) -> set:
    """
    大额无用途往账检测。
    
    对满足以下所有条件的往账标记为"待确认"：
    1. 交易类型为往账
    2. 非内部
    3. 金额绝对值 >= min_amount
    4. 用途为空或不包含中文
    5. 交易附言为空或不包含中文
    6. 业务类型不是贷款还款/贷款放款
    """
    suspicious_indices = set()
    
    for idx, row in df.iterrows():
        # 条件1：往账
        if row['交易类型'] != '往账':
            continue
        
        # 条件2：非内部
        counterparty = row.get('对方名称', '')
        if counterparty == our_company_name or counterparty == '本公司':
            continue
        
        # 条件3：金额达标
        if row['支出金额'] < min_amount:
            continue
        
        # 条件4+5：用途和附言都无中文
        purpose = row.get('用途', '') or ''
        remark = row.get('交易附言', '') or ''
        if contains_chinese(purpose) or contains_chinese(remark):
            continue
        
        # 条件6：非贷款类
        biz_type = row.get('业务类型', '') or ''
        if biz_type in ['贷款还款', '贷款放款']:
            continue
        
        suspicious_indices.add(idx)
    
    return suspicious_indices


# ============================================================================
# 主解析流程
# ============================================================================

def parse_boc_statement(input_file: str, config_path: str) -> pd.DataFrame:
    """
    解析中行流水文件的主函数。
    """
    print(f"正在读取输入文件: {input_file}")
    
    # 1. 读取Excel
    df_raw = pd.read_excel(input_file, header=None, engine='openpyxl')
    print(f"原始数据行数: {len(df_raw)}")
    
    # 2. 加载配置
    config = load_config(config_path)
    account_mapping = config.get('账户映射', [])
    summary_rules = config.get('摘要规则', [])
    anomaly_config = config.get('异常检测', {})
    
    # 3. 找到表头行
    header_row_idx = find_header_row(df_raw)
    print(f"表头行位置: 第{header_row_idx + 1}行")
    
    # 4. 构建字段映射
    header_row = df_raw.iloc[header_row_idx].fillna('').astype(str).tolist()
    field_mapping = build_field_mapping(header_row)
    print(f"识别的字段: {list(field_mapping.keys())}")
    
    # 5. 提取账号（从表头行之前的行）
    account_number = ''
    for idx in range(header_row_idx):
        row_text = str(df_raw.iloc[idx, 0]) if idx < len(df_raw) else ''
        if '查询账号' in row_text:
            if len(df_raw.columns) > 1:
                account_number = str(df_raw.iloc[idx, 1]).strip()
            break
    print(f"流水账号: {account_number}")
    
    # 6. 匹配账户配置
    matched_account = None
    for acc in account_mapping:
        if acc.get('流水账号') == account_number:
            matched_account = acc
            break
    
    if matched_account:
        entity_code = matched_account['单位编码']
        account_code = matched_account['账户编码']
        entity_name = matched_account['单位名称']
        account_name = matched_account['账户名称']
        print(f"匹配到账户: {entity_name} - {account_name}")
    else:
        entity_code = 'DW待匹配'
        account_code = 'ZH待匹配'
        entity_name = '待匹配'
        account_name = '待匹配'
        print(f"警告: 账号 {account_number} 未在配置中找到匹配记录！")
    
    # 7. 逐行处理数据
    data_start_idx = header_row_idx + 1
    records = []
    
    for idx in range(data_start_idx, len(df_raw)):
        row_data = df_raw.iloc[idx]
        
        # 获取交易类型
        txn_type = get_cell_value(row_data, field_mapping, '交易类型')
        
        # 跳过无效行（非往账/来账）
        if txn_type not in ['往账', '来账']:
            continue
        
        # 提取所有字段
        biz_date = get_cell_value(row_data, field_mapping, '交易日期')
        biz_time = get_cell_value(row_data, field_mapping, '交易时间')
        biz_type = get_cell_value(row_data, field_mapping, '业务类型')
        payer_name = get_cell_value(row_data, field_mapping, '付款人名称')
        payee_name = get_cell_value(row_data, field_mapping, '收款人名称')
        payee_bank = get_cell_value(row_data, field_mapping, '收款人开户行名')
        purpose = get_cell_value(row_data, field_mapping, '用途')
        remark_field = get_cell_value(row_data, field_mapping, '交易附言')
        remarks = get_cell_value(row_data, field_mapping, '备注')
        original_summary = get_cell_value(row_data, field_mapping, '摘要')
        
        # 解析金额
        amount_str = get_cell_value(row_data, field_mapping, '交易金额')
        amount = parse_amount(amount_str)
        if amount is None:
            print(f"警告: 第{idx + 1}行金额无法解析: '{amount_str}'")
            amount = 0.0
        
        # 解析余额
        balance_str = get_cell_value(row_data, field_mapping, '交易后余额')
        balance = parse_amount(balance_str) or 0.0
        
        # 流水号等
        txn_ref = get_cell_value(row_data, field_mapping, '交易流水号')
        voucher_no = get_cell_value(row_data, field_mapping, '凭证号码')
        
        # 构建行字典
        row_dict = {
            '交易日期': parse_date(biz_date),
            '交易时间': biz_time,
            '交易类型': txn_type,
            '业务类型': biz_type,
            '付款人名称': payer_name,
            '收款人名称': payee_name,
            '收款人开户行名': payee_bank,
            '用途': purpose,
            '交易附言': remark_field,
            '备注': remarks,
            '摘要': original_summary,
            '交易金额_raw': amount,
            '交易流水号': txn_ref,
            '凭证号码': voucher_no,
        }
        
        # 确定收入/支出
        if txn_type == '来账':
            row_dict['收入金额'] = abs(amount)
            row_dict['支出金额'] = 0.0
        else:  # 往账
            row_dict['收入金额'] = 0.0
            row_dict['支出金额'] = abs(amount)
        
        records.append(row_dict)
    
    print(f"有效数据行数: {len(records)}")
    
    # 转换为DataFrame
    df = pd.DataFrame(records)
    
    # 8. 生成摘要和对方名称
    for idx in df.index:
        row = df.loc[idx].to_dict()
        summary, counterparty_name, status = generate_summary(row, summary_rules, entity_name)
        df.loc[idx, '摘要'] = summary
        df.loc[idx, '对方名称'] = counterparty_name
        df.loc[idx, '状态'] = status
    
    # 9. 异常检测
    paired_config = anomaly_config.get('同日收付配对', {})
    if paired_config.get('启用', False):
        min_amount_paired = paired_config.get('最小金额', 1000000)
        error_ratio = paired_config.get('金额匹配误差比例', 0.01)
        paired_indices = check_same_day_paired(df, min_amount_paired, error_ratio)
        if paired_indices:
            print(f"检测到同日收付配对 {len(paired_indices)} 条")
            for idx in paired_indices:
                df.loc[idx, '状态'] = '待确认'
    
    large_config = anomaly_config.get('大额无用途往账', {})
    if large_config.get('启用', False):
        min_amount_large = large_config.get('最小金额', 1000000)
        large_indices = check_large_expense_no_purpose(df, min_amount_large, entity_name)
        if large_indices:
            print(f"检测到大额无用途往账 {len(large_indices)} 条")
            for idx in large_indices:
                df.loc[idx, '状态'] = '待确认'
    
    # 10. 添加单位信息
    df['单位编码'] = entity_code
    df['账户编码'] = account_code
    df['单位名称'] = entity_name
    df['账户名称'] = account_name
    
    # 11. 格式化金额
    df['收入金额'] = df['收入金额'].apply(lambda x: round(float(x), 2) if pd.notna(x) else 0.0)
    df['支出金额'] = df['支出金额'].apply(lambda x: round(float(x), 2) if pd.notna(x) else 0.0)
    df['滚动余额'] = df['交易金额_raw'].apply(lambda x: round(float(x), 2) if pd.notna(x) else 0.0)
    
    # 重新计算正确的滚动余额（累计）
    df = df.sort_values(['交易日期', '交易时间']).reset_index(drop=True)
    running_balance = 0.0
    for idx in df.index:
        amount = df.loc[idx, '交易金额_raw']
        running_balance += amount
        df.loc[idx, '滚动余额'] = round(running_balance, 2)
    
    # 添加序号
    df.insert(0, '序号', range(1, len(df) + 1))
    
    return df


def write_excel_output(df: pd.DataFrame, output_path: str):
    """将处理结果写入Excel文件"""
    
    # Sheet1列定义
    sheet1_columns = [
        '序号', '交易日期', '交易时间', '交易类型', '业务类型',
        '对方名称', '收入金额', '支出金额', '滚动余额',
        '摘要', '状态', '单位编码', '账户编码'
    ]
    
    # Sheet2列定义
    sheet2_columns = sheet1_columns + [
        '交易流水号', '凭证号码', '付款人名称', '收款人名称',
        '收款人开户行名', '用途', '交易附言', '备注', '银行原始摘要'
    ]
    
    wb = openpyxl.Workbook()
    
    # Sheet1: 基础数据表
    ws1 = wb.active
    ws1.title = '基础数据表'
    
    for col_idx, col_name in enumerate(sheet1_columns, 1):
        cell = ws1.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    
    for row_idx, row in df.iterrows():
        for col_idx, col_name in enumerate(sheet1_columns, 1):
            value = row.get(col_name, '')
            cell = ws1.cell(row=row_idx + 2, column=col_idx, value=value)
            
            if col_name == '状态' and value == '待确认':
                cell.font = Font(color='FF0000')
    
    for col_idx in range(1, len(sheet1_columns) + 1):
        ws1.column_dimensions[get_column_letter(col_idx)].width = 15
    
    # Sheet2: 辅助核对明细
    ws2 = wb.create_sheet(title='辅助核对明细')
    
    for col_idx, col_name in enumerate(sheet2_columns, 1):
        cell = ws2.cell(row=1, column=col_idx, value=col_name)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color='D9E1F2', end_color='D9E1F2', fill_type='solid')
    
    for row_idx, row in df.iterrows():
        for col_idx, col_name in enumerate(sheet2_columns, 1):
            value = row.get(col_name, '')
            cell = ws2.cell(row=row_idx + 2, column=col_idx, value=value)
            
            if col_name == '状态' and value == '待确认':
                cell.font = Font(color='FF0000')
    
    for col_idx in range(1, len(sheet2_columns) + 1):
        ws2.column_dimensions[get_column_letter(col_idx)].width = 18
    
    wb.save(output_path)
    print(f"输出文件已保存: {output_path}")


# ============================================================================
# 主入口
# ============================================================================

def main():
    if len(sys.argv) < 3:
        print("用法: python boc_parser_v2.py <输入文件> <配置文件>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    config_path = sys.argv[2]
    
    if not os.path.exists(input_file):
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    if not os.path.exists(config_path):
        print(f"错误: 配置文件不存在: {config_path}")
        sys.exit(1)
    
    # 解析流水
    df = parse_boc_statement(input_file, config_path)
    
    # 生成输出文件名
    input_path = Path(input_file)
    output_file = input_path.stem + '_基础数据表.xlsx'
    output_path = input_path.parent / output_file
    
    # 输出Excel
    write_excel_output(df, str(output_path))
    
    print("\n处理完成！")
    print(f"总记录数: {len(df)}")
    print(f"正常记录: {len(df[df['状态'] == '正常'])}")
    print(f"待确认记录: {len(df[df['状态'] == '待确认'])}")


if __name__ == '__main__':
    main()