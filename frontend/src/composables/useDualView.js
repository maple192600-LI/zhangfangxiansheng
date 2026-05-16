import { computed, ref, watch } from 'vue'

export function useDualView(templateExcelHtml) {
  const viewMode = ref('data')
  const userTouchedView = ref(false)

  const hasTemplate = computed(() => !!templateExcelHtml.value)

  watch(
    hasTemplate,
    (exists) => {
      if (!exists) {
        viewMode.value = 'data'
        userTouchedView.value = false
      }
    },
    { immediate: true }
  )

  function setView(mode) {
    if (mode === 'template' && !hasTemplate.value) return
    if (mode !== 'template' && mode !== 'data') return
    userTouchedView.value = true
    viewMode.value = mode
  }

  function switchView() {
    setView(viewMode.value === 'template' ? 'data' : 'template')
  }

  const isTemplateView = computed(() => viewMode.value === 'template' && hasTemplate.value)
  const isDataView = computed(() => !isTemplateView.value)

  return { viewMode, hasTemplate, isTemplateView, isDataView, setView, switchView }
}
