/**
 * 报表模板加载 composable
 *
 * 联动机制：
 *   - onMounted    首次挂载时拉模板
 *   - onActivated  从其他路由切回（keep-alive 缓存）时再拉一次
 *   ↑ 模板管理中心上传/删除模板后，切回业务页面就会自动刷新
 *
 * 加载顺序：
 *   1. 优先 excel-html：原 Excel 完整渲染（合并单元格/对齐/背景/字体），用户上传啥就显示啥
 *   2. fallback 到 columns / layout：旧版字段抽取
 */
import { ref, onMounted, onActivated } from 'vue'
import http from '@/api'
import { getDefaultTemplate } from '@/api/reportTemplate'

export function useTemplateColumns(reportType) {
  const templateColumns = ref(null)
  const templateLayout = ref(null)
  const templateExcelHtml = ref(null)
  const templateMeta = ref(null)
  const templateLoaded = ref(false)

  async function loadTemplate() {
    // 每次都重置：保证模板被删除后页面立即回到空状态，不显示陈旧 HTML
    templateExcelHtml.value = null
    templateColumns.value = null
    templateLayout.value = null
    templateMeta.value = null

    // dev-only: ?debug_no_template=1 强制跳过模板，走 AdvancedDataTable fallback
    if (import.meta.env.DEV) {
      const params = new URLSearchParams(window.location.search)
      if (params.get('debug_no_template') === '1') {
        templateLoaded.value = true
        return
      }
    }

    try {
      const res = await http.get(`/report-templates/default/${reportType}/excel-html`)
      if (res?.html) {
        templateExcelHtml.value = res.html
        templateMeta.value = {
          template_id: res.template_id,
          template_code: res.template_code,
          template_name: res.template_name,
        }
      }
    } catch {
      // 没有原 Excel 文件就降级
    }

    try {
      const res = await getDefaultTemplate(reportType)
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
    templateExcelHtml,
    templateMeta,
    templateLoaded,
    loadTemplate,
  }
}
