const STORAGE_PREFIX = 'zfxs:advanced-table'
const VERSION = 1

function emptyPreferences() {
  return { version: VERSION, density: 'default', widths: {}, visibility: {}, order: [] }
}

export function getPreferenceKey(tableKey) {
  return `${STORAGE_PREFIX}:${tableKey}:current`
}

export function getPreferences(tableKey) {
  if (!tableKey) return emptyPreferences()
  try {
    const raw = localStorage.getItem(getPreferenceKey(tableKey))
    if (!raw) return emptyPreferences()
    const parsed = JSON.parse(raw)
    if (!parsed || typeof parsed !== 'object') return emptyPreferences()
    return {
      version: VERSION,
      density: parsed.density || 'default',
      widths: parsed.widths && typeof parsed.widths === 'object' ? parsed.widths : {},
      visibility: parsed.visibility && typeof parsed.visibility === 'object' ? parsed.visibility : {},
      order: Array.isArray(parsed.order) ? parsed.order : [],
    }
  } catch {
    return emptyPreferences()
  }
}

function writePreferences(tableKey, prefs) {
  if (!tableKey) return
  try {
    localStorage.setItem(getPreferenceKey(tableKey), JSON.stringify(prefs))
  } catch { /* quota exceeded or private browsing — silently ignore */ }
}

export function savePreferences(tableKey, patch) {
  if (!tableKey) return
  const prefs = getPreferences(tableKey)
  Object.assign(prefs, patch)
  writePreferences(tableKey, prefs)
}

export function applyPreferences(columns, preferences) {
  if (!preferences || !columns?.length) return columns

  const widths = preferences.widths || {}
  const visibility = preferences.visibility || {}
  const order = preferences.order || []

  const fieldSet = new Set(columns.filter(c => c.field).map(c => c.field))

  // Apply widths and clone columns
  const cols = columns.map(col => {
    if (!col.field) return { ...col }
    const patched = { ...col }
    if (widths[col.field] != null) patched.width = widths[col.field]
    return patched
  })

  // Separate system cols (no field) from data cols
  const systemCols = cols.filter(c => !c.field)
  const dataCols = cols.filter(c => c.field)

  // Build ordered data cols
  const orderedDataCols = []
  const placed = new Set()

  for (const field of order) {
    if (!fieldSet.has(field)) continue
    const col = dataCols.find(c => c.field === field)
    if (col) {
      orderedDataCols.push(col)
      placed.add(field)
    }
  }

  // Append new columns not in saved order
  for (const col of dataCols) {
    if (!placed.has(col.field)) {
      orderedDataCols.push(col)
    }
  }

  // Apply visibility
  const visibleDataCols = orderedDataCols.filter(col => {
    if (visibility[col.field] != null) return visibility[col.field]
    return true
  })

  // Must keep at least 1 data column
  const finalDataCols = visibleDataCols.length > 0 ? visibleDataCols : orderedDataCols

  return [...systemCols, ...finalDataCols]
}

export function saveColumnWidth(tableKey, field, width) {
  if (!tableKey || !field) return
  const prefs = getPreferences(tableKey)
  prefs.widths[field] = width
  writePreferences(tableKey, prefs)
}

export function saveColumnVisibility(tableKey, field, visible) {
  if (!tableKey || !field) return
  const prefs = getPreferences(tableKey)
  prefs.visibility[field] = visible
  writePreferences(tableKey, prefs)
}

export function saveColumnOrder(tableKey, order) {
  if (!tableKey || !Array.isArray(order)) return
  const prefs = getPreferences(tableKey)
  prefs.order = order
  writePreferences(tableKey, prefs)
}

export function saveDensity(tableKey, density) {
  if (!tableKey) return
  const prefs = getPreferences(tableKey)
  prefs.density = density
  writePreferences(tableKey, prefs)
}

export function resetPreferences(tableKey) {
  if (!tableKey) return
  try {
    localStorage.removeItem(getPreferenceKey(tableKey))
  } catch { /* ignore */ }
}
