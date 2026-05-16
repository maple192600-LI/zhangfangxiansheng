import {
  emptyDashFormatter,
  moneyFormatter,
  directionFormatter,
  abnormalCodeFormatter,
} from '@/utils/tabulatorFormatters'

export function adaptTemplateColumns(templateColumns, fallbackColumns, options = {}) {
  const {
    moneyFields = new Set(),
    directionField = null,
    abnormalField = null,
  } = options

  if (!templateColumns?.length) return fallbackColumns

  return templateColumns.map((col) => {
    const def = {
      field: col.field_key,
      title: col.header_name,
      formatter: emptyDashFormatter,
    }
    if (col.width) def.width = col.width
    if (col.align) def.hozAlign = col.align

    if (directionField && col.field_key === directionField) {
      def.formatter = directionFormatter
    } else if (moneyFields.has(col.field_key)) {
      def.formatter = moneyFormatter
      def.hozAlign = def.hozAlign || 'right'
    } else if (abnormalField && col.field_key === abnormalField) {
      def.formatter = abnormalCodeFormatter
    }

    return def
  })
}
