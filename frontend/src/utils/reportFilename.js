const REPORT_NAMES = {
  daily_report: '资金日报',
  account_balance: '账户余额表',
  income_list: '收入明细表',
  expense_list: '支出明细表',
  cash_journal: '现金日记账',
  base_data: '基础数据表',
  major_balance: '资金余额表',
  month_check: '月度对账表',
  week_report: '周报',
  month_report: '月报',
  year_report: '年报',
}

export function getReportFilename(exportType, { startDate, endDate, year, month } = {}) {
  const name = REPORT_NAMES[exportType] || exportType

  if (year && month) return `${name}_${year}年${month}月.xlsx`
  if (year) return `${name}_${year}年.xlsx`

  const hasStart = !!startDate
  const hasEnd = !!endDate

  if (hasStart && hasEnd) return `${name}_${startDate}_${endDate}.xlsx`
  if (hasStart && !hasEnd) return `${name}_${startDate}起.xlsx`
  if (!hasStart && hasEnd) return `${name}_截至${endDate}.xlsx`
  return `${name}_全部.xlsx`
}
