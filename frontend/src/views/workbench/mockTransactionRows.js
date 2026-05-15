const ENTITIES = ['总公司', '华东分公司', '华南分公司', '华北分公司', '西南分公司']
const ACCOUNTS = ['工商银行-基本户', '建设银行-一般户', '农业银行-专用户', '中国银行-基本户', '招商银行-一般户']
const SUMMARIES = ['货款收入', '供应商付款', '工资发放', '社保缴纳', '税费缴纳', '水电费', '租金', '利息收入', '转账', '退款']
const COUNTERPARTIES = ['甲方有限公司', '乙方有限公司', '丙方有限公司', '丁方有限公司', '戊方有限公司', null, null]
const ABNORMAL_CODES = [null, null, null, null, null, null, null, null, null, 'MISS_ENTITY', 'DUPLICATE_DATE', 'AMOUNT_MISMATCH', 'MISS_ACCOUNT']

function randomDate(start, end) {
  const s = new Date(start).getTime()
  const e = new Date(end).getTime()
  const d = new Date(s + Math.random() * (e - s))
  return d.toISOString().split('T')[0]
}

function randomAmount(min, max) {
  const v = min + Math.random() * (max - min)
  return Math.round(v * 100) / 100
}

export function generateRows(count) {
  const rows = []
  for (let i = 0; i < count; i++) {
    const hasIncome = Math.random() > 0.5
    const hasAbnormal = Math.random() < 0.1
    const missingAmount = Math.random() < 0.05
    const missingDate = Math.random() < 0.02
    const missingAccount = Math.random() < 0.03

    const income = hasIncome && !missingAmount ? randomAmount(1000, 500000) : null
    const expense = !hasIncome && !missingAmount ? randomAmount(500, 200000) : null

    rows.push({
      _row_no: i + 1,
      business_date: missingDate ? null : randomDate('2026-01-01', '2026-05-15'),
      entity_name: ENTITIES[Math.floor(Math.random() * ENTITIES.length)],
      account_name: missingAccount ? null : ACCOUNTS[Math.floor(Math.random() * ACCOUNTS.length)],
      summary_text: SUMMARIES[Math.floor(Math.random() * SUMMARIES.length)],
      counterparty_name: COUNTERPARTIES[Math.floor(Math.random() * COUNTERPARTIES.length)],
      income_amount: income,
      expense_amount: expense,
      balance: randomAmount(10000, 5000000),
      abnormal_code: hasAbnormal ? ABNORMAL_CODES[9 + Math.floor(Math.random() * 5)] : null,
    })
  }
  return rows
}
