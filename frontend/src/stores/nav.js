import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useNavStore = defineStore('nav', () => {
  const currentPrimary = ref('首页')
  const currentSecondary = ref(null)
  const currentTab = ref(0)

  const openState = ref({
    资金板块: true,
    系统设置: true
  })

  function navigate(primary, secondary = null, tabIndex = 0) {
    currentPrimary.value = primary
    currentSecondary.value = secondary
    currentTab.value = tabIndex
  }

  function toggleSection(primary) {
    openState.value[primary] = !openState.value[primary]
  }

  return {
    currentPrimary,
    currentSecondary,
    currentTab,
    openState,
    navigate,
    toggleSection
  }
})
