import { ref, onMounted, onUnmounted, onActivated, nextTick } from 'vue'
import { TabulatorFull as Tabulator } from 'tabulator-tables'

export function useTabulatorTable(containerRef, options) {
  const table = ref(null)
  const isReady = ref(false)
  let initialized = false
  let destroyed = false

  function createTable() {
    if (!containerRef.value || initialized || destroyed) return

    try {
      const editable = options.editable || false
      const clipboard = options.clipboard || false

      const defaultConfig = {
        pagination: options.pagination !== false ? 'local' : false,
        paginationSize: options.paginationSize || 50,
        paginationCounter: 'rows',
        layout: 'fitColumns',
        placeholder: options.emptyText || '暂无数据',
        locale: 'zh-cn',
        langs: {
          'zh-cn': {
            pagination: {
              first: '首页',
              first_title: '首页',
              last: '末页',
              last_title: '末页',
              prev: '上一页',
              prev_title: '上一页',
              next: '下一页',
              next_title: '下一页',
              all: '全部',
              page_size: '每页条数',
            },
          },
        },
      }

      const editableOverrides = editable ? {
        keybindings: {
          navLeft: 'arrowleft',
          navRight: 'arrowright',
          navUp: 'arrowup',
          navDown: 'arrowdown',
          navNext: 'tab',
          navPrev: 'shift+tab',
        },
        editTriggerEvent: 'click',
      } : {}

      const clipboardOverrides = clipboard ? {
        clipboard: true,
        clipboardPasteAction: 'insert',
      } : {}

      const instance = new Tabulator(containerRef.value, {
        ...defaultConfig,
        ...editableOverrides,
        ...clipboardOverrides,
        ...(options.tabulatorOverrides || {}),
        columns: options.columns || [],
        data: options.data || [],
      })

      instance.on('tableBuilt', () => {
        if (destroyed) return
        isReady.value = true
        options.onTableReady?.()
      })

      if (options.rowClick) {
        instance.on('rowClick', (e, row) => options.rowClick(e, row.getData()))
      }

      if (options.rowDblClick) {
        instance.on('rowDblClick', (e, row) => options.rowDblClick(e, row.getData()))
      }

      if (options.onSelectionChange) {
        instance.on('rowSelectionChanged', (data) => {
          options.onSelectionChange(data)
        })
      }

      if (options.onColumnResized) {
        instance.on('columnResized', (column) => {
          const field = column.getField?.()
          const width = column.getWidth?.()
          if (field) options.onColumnResized({ field, width })
        })
      }

      if (options.onColumnMoved) {
        instance.on('columnMoved', () => {
          const order = instance
            .getColumns()
            .map(col => col.getField?.())
            .filter(Boolean)
          options.onColumnMoved(order)
        })
      }

      if (options.onColumnVisibilityChanged) {
        instance.on('columnVisibilityChanged', (column, visible) => {
          const field = column.getField?.()
          if (field) options.onColumnVisibilityChanged({ field, visible })
        })
      }

      if (options.cellClick) {
        instance.on('cellClick', (e, cell) => options.cellClick(e, cell))
      }

      if (options.onCellEdited) {
        instance.on('cellEdited', (cell) => {
          const field = cell.getColumn()?.getField()
          const value = cell.getValue()
          const rowData = cell.getRow()?.getData()
          options.onCellEdited({ field, value, rowData })
        })
      }

      if (options.onPaste) {
        instance.on('clipboardPasted', (rows, rowsData) => {
          options.onPaste(rowsData || [])
        })
      }

      table.value = instance
      initialized = true
    } catch (err) {
      options.onTableError?.(err.message || '表格初始化失败')
    }
  }

  function destroyTable() {
    destroyed = true
    if (table.value) {
      try { table.value.destroy() } catch (e) { console.warn('[useTabulatorTable] destroy failed:', e) }
      table.value = null
    }
    isReady.value = false
    initialized = false
  }

  function updateData(newData) {
    if (!table.value || !isReady.value || destroyed) return
    try {
      table.value.replaceData(newData || [])
    } catch (e) { console.warn('[useTabulatorTable] updateData failed:', e) }
  }

  function updateColumns(newColumns) {
    if (!table.value || !isReady.value || destroyed) return
    try {
      table.value.setColumns(newColumns || [])
    } catch (e) { console.warn('[useTabulatorTable] updateColumns failed:', e) }
  }

  function getSelectedRows() {
    if (!table.value || !isReady.value || destroyed) return []
    try {
      return table.value.getSelectedData()
    } catch (e) {
      console.warn('[useTabulatorTable] getSelectedRows failed:', e)
      return []
    }
  }

  function clearSelection() {
    if (!table.value || !isReady.value || destroyed) return
    try {
      table.value.deselectRow()
    } catch (e) { console.warn('[useTabulatorTable] clearSelection failed:', e) }
  }

  function addRow(rowData, pos = 'bottom') {
    if (!table.value || !isReady.value || destroyed) return
    try {
      return table.value.addRow(rowData || {}, pos)
    } catch (e) { console.warn('[useTabulatorTable] addRow failed:', e) }
  }

  function addRows(rowsData, pos = 'bottom') {
    if (!table.value || !isReady.value || destroyed) return
    try {
      for (const row of (rowsData || [])) {
        table.value.addRow(row, pos)
      }
    } catch (e) { console.warn('[useTabulatorTable] addRows failed:', e) }
  }

  function deleteRow(rowId) {
    if (!table.value || !isReady.value || destroyed) return
    try {
      table.value.deleteRow(rowId)
    } catch (e) { console.warn('[useTabulatorTable] deleteRow failed:', e) }
  }

  function getData() {
    if (!table.value || !isReady.value || destroyed) return []
    try {
      return table.value.getData()
    } catch (e) {
      console.warn('[useTabulatorTable] getData failed:', e)
      return []
    }
  }

  function clearData() {
    if (!table.value || !isReady.value || destroyed) return
    try {
      table.value.clearData()
    } catch (e) { console.warn('[useTabulatorTable] clearData failed:', e) }
  }

  onMounted(() => {
    destroyed = false
    nextTick(createTable)
  })

  onUnmounted(() => {
    destroyTable()
  })

  onActivated(() => {
    if (!initialized && !destroyed && containerRef.value) {
      nextTick(createTable)
    }
  })

  return {
    table,
    isReady,
    updateData,
    updateColumns,
    destroyTable,
    getSelectedRows,
    clearSelection,
    addRow,
    addRows,
    deleteRow,
    getData,
    clearData,
  }
}
