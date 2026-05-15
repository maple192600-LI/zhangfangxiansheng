import { ref, watch, onMounted, onUnmounted, onActivated, onDeactivated, nextTick } from 'vue'
import { TabulatorFull as Tabulator } from 'tabulator-tables'

export function useTabulatorTable(containerRef, options) {
  const table = ref(null)
  const isReady = ref(false)
  let initialized = false

  function createTable() {
    if (!containerRef.value || initialized) return

    const defaultConfig = {
      pagination: options.pagination !== false ? 'local' : false,
      paginationSize: options.paginationSize || 50,
      paginationCounter: 'rows',
      layout: 'fitColumns',
      placeholder: '暂无数据',
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

    const instance = new Tabulator(containerRef.value, {
      ...defaultConfig,
      ...options,
      columns: options.columns || [],
      data: options.data || [],
    })

    instance.on('tableBuilt', () => {
      isReady.value = true
    })

    table.value = instance
    initialized = true
  }

  function destroyTable() {
    if (table.value) {
      table.value.destroy()
      table.value = null
      isReady.value = false
      initialized = false
    }
  }

  function updateData(newData) {
    if (table.value && isReady.value) {
      table.value.replaceData(newData || [])
    }
  }

  function updateColumns(newColumns) {
    if (table.value && isReady.value) {
      table.value.setColumns(newColumns || [])
    }
  }

  onMounted(() => {
    nextTick(createTable)
  })

  onUnmounted(() => {
    destroyTable()
  })

  onActivated(() => {
    if (!initialized && containerRef.value) {
      nextTick(createTable)
    }
  })

  onDeactivated(() => {
    // keep-alive 离开时不销毁，避免重入时重复创建
  })

  return { table, isReady, updateData, updateColumns, destroyTable }
}
