/**
 * 银行名称关键词映射表 — 供 BankImport / BankRule 等页面共享
 */
export const BANK_KEYWORDS = {
  '招商': '招商银行', '招行': '招商银行',
  '农业': '农业银行', '农行': '农业银行',
  '工商': '工商银行', '工行': '工商银行',
  '建设': '建设银行', '建行': '建设银行',
  '中国银行': '中国银行', '中行': '中国银行',
  '交通': '交通银行', '交行': '交通银行',
  '兴业': '兴业银行', '广发': '广发银行',
  '民生': '民生银行', '浦发': '浦发银行',
  '中信': '中信银行', '光大': '光大银行',
  '华夏': '华夏银行', '邮储': '邮储银行',
  '农商': '农商银行', '信用社': '信用社',
  '网商': '网商银行', '微众': '微众银行',
  '平安': '平安银行',
}

export function guessBank(name) {
  if (!name) return null
  for (const [keyword, bank] of Object.entries(BANK_KEYWORDS)) {
    if (name.includes(keyword)) return bank
  }
  return null
}
