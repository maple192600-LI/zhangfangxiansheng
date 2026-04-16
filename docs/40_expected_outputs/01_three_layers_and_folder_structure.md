# 01｜三层文档体系与文件夹落位规范

## 一、三层是什么

到目前为止，这个项目应该固定为三层文档体系。

### 第一层：上位约束层

作用：锁边界，防止 Claude Code 跑偏。

它解决的是：

- 这个项目服务谁
- 当前阶段只做什么
- 技术栈不能乱换什么
- 用户边界是什么
- 哪些功能不能跨阶段深做

### 第二层：执行与契约层

作用：直接驱动开发。

它解决的是：

- 这个模块这轮到底做什么
- 页面有哪些状态
- 接口怎么定义
- 表怎么建
- 字段怎么校验
- 异常怎么进池
- 做到什么算完成

### 第三层：样本、期望输出与验收层

作用：让开发结果可对照、可测试、可交付。

它解决的是：

- 拿什么样本做开发
- 某个样本跑完应该得到什么结果
- 测试如何通过
- V1 做完到底交什么

---

## 二、这三层分别应该放在哪些文件夹中

建议在项目根目录固定成下面的结构。

```text
zhangfang/
├── docs/
│   ├── 00_governance/          ← 上位约束层
│   ├── 10_product_design/      ← 产品与设计层
│   ├── 20_execution/           ← 模块执行文档
│   ├── 30_contracts/           ← 契约文档（数据库、字段、API）
│   ├── 40_expected_outputs/    ← 期望输出定义
│   ├── 50_tests/               ← 测试与验收
│   └── 60_claude_code_support/ ← 开工手册与协作协议
│
├── references/
│   ├── original_input/         ← 原始需求文档
│   ├── screenshots/            ← 界面截图
│   └── style_and_interaction/  ← 视觉风格与微文案
│
├── samples/
│   ├── bank/
│   ├── manual/
│   ├── reports/
│   └── expected/
│
├── templates/
│   ├── frontend/               ← 前端 HTML 原型参考
│   └── manual/                 ← 手工录入模板
│
├── backend/
├── frontend/
├── build/
└── release/
```

---

## 三、第一层放什么

放在：

```text
docs/00_governance/
```

建议包括：

- 00_project_constitution.md
- 01_v1_scope_and_order.md
- 02_user_constraints.md
- 03_tech_constraints.md
- CLAUDE.md

这些文件的作用只有一个：

**限制 AI coding 工具。**

它们不是讲细节的。
它们是告诉 Claude Code 什么不能做，什么必须先做。

---

## 四、第二层放什么

第二层拆成两个文件夹。

### 1. 模块执行文档

放在：

```text
docs/20_execution/
```

建议包括：

- 10_master_data_execution.md
- 11_home_dashboard_execution.md
- 12_bank_import_execution.md
- 13_manual_flow_execution.md
- 14_base_data_and_report_execution.md
- 15_export_dashboard_backup_execution.md

### 2. 契约文档

放在：

```text
docs/30_contracts/
```

建议包括：

- 20_database_schema.md
- 21_field_dictionary.md
- 22_manual_field_pool.md
- 23_api_contracts.md
- 24_page_states_and_exceptions.md

这两类加起来，才是 Claude Code 真正拿来写代码的主输入。

---

## 五、第三层放什么

第三层再分成两块。

### 1. 期望输出文档

放在：

```text
docs/40_expected_outputs/
```

建议包括：

- 00_expected_output_definition.md
- 01_three_layers_and_folder_structure.md
- 02_v1_expected_outputs_catalog.md
- 03_samples_and_expected_results.md

### 2. 测试与验收文档

放在：

```text
docs/50_tests/
```

建议包括：

- 30_module_test_cases.md
- 31_e2e_acceptance.md
- 32_real_sample_regression.md

---

## 六、样本文件和期望结果放哪

建议固定在：

```text
samples/
├── bank/
├── manual/
├── reports/
└── expected/
```

### bank/
放银行流水脱敏样本。

### manual/
放手工多主体总表样本、快速录入导出样本。

### reports/
放目标输出模板，例如日报、余额表、收入明细表、支出明细表。

### expected/
放“样本对应的期望结果”。

例如：

- `bank_icbc_sample_01.expected.json`
- `manual_multi_subject_sample_01.expected.json`
- `report_interval_case_01.expected.xlsx`

---

## 七、release 里放什么

放最终交付物。

```text
release/
├── v1-alpha/
├── v1-beta/
└── v1-final/
```

每个版本下至少包含：

- 可运行程序
- 初始化数据库脚本
- 版本说明
- 已知问题清单
- 样本测试报告摘要

---

## 八、结论

这三层的核心区别是：

第一层负责“别乱做”。
第二层负责“按什么做”。
第三层负责“做到什么算对”。

这三层分别落到不同文件夹里以后，Claude Code 才不会把说明稿、开发稿、测试稿混成一坨。
