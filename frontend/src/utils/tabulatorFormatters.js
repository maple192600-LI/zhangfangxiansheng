/**
 * Tabulator 统一 formatter 集合
 * 注意：这些函数运行在 Tabulator 环境中，不能使用 Vue 组件或 Naive UI。
 */

import { fmtAmt } from '@/utils/format'

export function emptyDashFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '-'
  return String(v)
}

export function dateTextFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '-'
  return String(v)
}

export function tagTextFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '-'
  const text = String(v)
  return `<span class="tabulator-tag tabulator-tag-blue">${escapeHtml(text)}</span>`
}

export function detailFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '-'
  if (typeof v === 'string') return escapeHtml(v)
  if (typeof v === 'object') {
    return Object.entries(v)
      .map(([k, val]) => `${escapeHtml(k)}=${escapeHtml(String(val))}`)
      .join(', ')
  }
  return escapeHtml(String(v))
}

function escapeHtml(str) {
  const s = String(str)
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
}

export function moneyFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '-'
  return escapeHtml(fmtAmt(v))
}

export function directionFormatter(cell) {
  const v = cell.getValue()
  if (v === 'income') return '收入'
  if (v === 'expense') return '支出'
  return escapeHtml(String(v ?? ''))
}

export function abnormalCodeFormatter(cell) {
  const v = cell.getValue()
  if (v == null || v === '') return '<span class="tabulator-tag tabulator-tag-green">正常</span>'
  return `<span class="tabulator-tag tabulator-tag-orange">${escapeHtml(String(v))}</span>`
}
