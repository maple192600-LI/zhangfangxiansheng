export const NODE_META = {
  'control.start': { label: '开始', category: '控制', color: '#67c23a' },
  'control.end': { label: '结束', category: '控制', color: '#f56c6c' },
  'control.pause': { label: '暂停确认', category: '控制', color: '#e6a23c' },
  'noop': { label: '空节点', category: '控制', color: '#909399' },
  'data.query_daily': { label: '查询资金日报', category: '数据', color: '#409eff' },
  'data.query_cash_journal': { label: '查询现金日记账', category: '数据', color: '#409eff' },
  'data.query_balance': { label: '查询账户余额', category: '数据', color: '#409eff' },
  'data.query_income': { label: '查询收入明细', category: '数据', color: '#409eff' },
  'data.query_expense': { label: '查询支出明细', category: '数据', color: '#409eff' },
  'data.query_base': { label: '查询基础数据', category: '数据', color: '#409eff' },
  'report.major_balance': { label: '主要账户余额表', category: '报表', color: '#9b59b6' },
  'report.month_check': { label: '月末盘点表', category: '报表', color: '#9b59b6' },
  'export.excel': { label: '导出 Excel', category: '导出', color: '#1abc9c' },
}

export function getNodeMeta(type) {
  return NODE_META[type] || { label: type, category: '未知', color: '#909399' }
}
