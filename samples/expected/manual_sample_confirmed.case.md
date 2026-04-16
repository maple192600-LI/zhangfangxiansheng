# 手工样本 case

## 样本编号
manual_sample_confirmed

## 样本用途
用于验证手工多主体总表上传这条主链路是否跑通。

## 输入来源
- `manual_sample_confirmed.xlsx`

## 预期处理路径
1. 进入“手工流水”
2. 上传 Excel 总表
3. 模板命中“多主体总表标准版”
4. 在“上传结果预览”中看到 12 条记录全部可入库
5. 进入“基础数据表”
6. 生成以下结果视图：
   - 基础数据表
   - 账户余额表
   - 收入明细表
   - 支出明细表

## 关键校验点
- 同一份总表中允许多法人、多账户、多资金类型并存
- 每行都可被拆成标准资金事件
- 无异常池记录
- 无重复拦截记录
- 期末余额与样本填写值一致
- 账户余额表按账户编码汇总后的期末余额正确

## 期望结果文件
- `samples/expected/manual_sample_confirmed.expected.json`
- `samples/reports/manual_sample_confirmed__基础数据表.csv`
- `samples/reports/manual_sample_confirmed__账户余额表.csv`
- `samples/reports/manual_sample_confirmed__收入明细表.csv`
- `samples/reports/manual_sample_confirmed__支出明细表.csv`
- `samples/reports/manual_sample_confirmed__报表示例.xlsx`
