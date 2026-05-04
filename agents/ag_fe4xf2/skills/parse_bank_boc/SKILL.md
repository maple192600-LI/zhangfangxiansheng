---
name: parse_bank_boc
description: "中国银行流水专用解析——识别中行 Excel/CSV 流水格式，提取交易字段"
when_to_use: "当用户上传中国银行流水、中行对账单时"
allowed-tools:
  - openpyxl_read
  - file_list
  - file_read
arguments:
  file_path:
    description: "中行流水文件路径"
    required: true
---

# 中国银行流水解析

## 工作流程

1. 接收 file_path 参数，判断文件格式
2. 读取 Excel 或 CSV，提取全部非空行
3. 第一行作为表头，后续行为数据
4. 返回结构化结果：header / row_count / preview

## 输出格式

```json
{
  "ok": true,
  "file": "文件名",
  "bank": "中国银行",
  "header": ["列名1", ...],
  "row_count": 50,
  "preview": [[行1], ...],
  "message": "中行流水解析完成"
}
```

## 规则

- 仅处理中国银行流水格式
- 空行跳过
- 编码统一 utf-8-sig + replace
- 解析完成后提示用户确认字段映射
