/**
 * 金额格式化 — 千分位 + 2位小数
 */
export function fmtAmt(v) {
  if (v == null) return '-'
  return Number(v).toLocaleString('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })
}
