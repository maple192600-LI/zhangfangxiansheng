/**
 * 报表模板加载 composable
 *
 * 联动机制：
 *   - onMounted    首次挂载时拉模板
 *   - onActivated  从其他路由切回（keep-alive 缓存）时再拉一次
 *   ↑ 模板管理中心上传/删除模板后，切回业务页面就会自动刷新
 *
 * 加载内容：
 *   - columns：报表字段列定义
 *   - layout：需要保留表格块结构的报表布局
 */
import { ref, onMounted, onActivated } from 'vue'
import { getDefaultTemplate } from '@/api/reportTemplate'

export function useTemplateColumns(reportType) {
  const templateColumns = ref(null)
  const templateLayout = ref(null)
  const templateMeta = ref(null)
  const templateLoaded = ref(false)

  async function loadTemplate() {
    // 每次都重置：保证模板被删除后页面立即回到默认列，不显示陈旧配置。
    templateColumns.value = null
    templateLayout.value = null
    templateMeta.value = null

    try {
      const res = await getDefaultTemplate(reportType)
      templateMeta.value = res
      if (res?.columns?.length) {
        templateColumns.value = res.columns.filter(c => c.visible !== false)
      }
      if (res?.layout?.rows?.length) {
        templateLayout.value = res.layout
      }
    } catch {
      // ignore
    }

    templateLoaded.value = true
  }

  onMounted(loadTemplate)
  onActivated(loadTemplate)

  return {
    templateColumns,
    templateLayout,
    templateMeta,
    templateLoaded,
    loadTemplate,
  }
}
