import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'
import zhangfangTheme from '../theme/zhangfang.js'
import naiveDefaultTheme from '../theme/naive-default.js'

const SKINS = [
  { key: 'zhangfang', label: '账房风格' },
  { key: 'naive', label: 'Naive 原生' },
]

const THEMES = {
  zhangfang: zhangfangTheme,
  naive: naiveDefaultTheme,
}

const NAIVE_VARS = {
  '--bg': '#ffffff',
  '--bg-gradient': 'none',
  '--panel': '#ffffff',
  '--panel-2': '#ffffff',
  '--line': '#e0e0e6',
  '--line-soft': '#efeff5',
  '--line-table': '#e0e0e6',
  '--line-table-vert': '#e8e8ed',
  '--text': '#333639',
  '--text-secondary': '#55585c',
  '--text-tertiary': '#7c7e82',
  '--text-light': '#999999',
  '--muted': '#999999',
  '--green': '#18a058',
  '--green-hover': '#36ad6a',
  '--green-2': '#e8f5ed',
  '--green-3': '#f0faf3',
  '--accent': '#2080f0',
  '--warn': '#f0a020',
  '--warn-bg': '#fdf6ec',
  '--warn-border': '#f5d0a0',
  '--warn-text': '#9a4e0a',
  '--info': '#2080f0',
  '--info-bg': '#e8f0fe',
  '--info-border': '#bcd4f5',
  '--info-text': '#3a6db5',
  '--ok-bg': '#e8f5ed',
  '--ok-border': '#c0e6cc',
  '--ok-text': '#1a7a3a',
  '--tag-green-bg': '#e8f5ed',
  '--tag-green-text': '#18a058',
  '--tag-green-border': '#b8e6c8',
  '--tag-warn-bg': '#fdf6ec',
  '--tag-warn-text': '#c78520',
  '--tag-warn-border': '#f0d9a0',
  '--tag-gray-bg': '#f5f5f8',
  '--tag-gray-text': '#666666',
  '--tag-gray-border': '#dddde5',
  '--tag-blue-bg': '#e8f0fe',
  '--tag-blue-text': '#2080f0',
  '--tag-blue-border': '#a8c8f0',
  '--thead-bg': '#fafafa',
  '--radius-lg': '6px',
  '--radius': '6px',
  '--radius-md': '4px',
  '--radius-sm': '3px',
  '--radius-pill': '999px',
  '--shadow': '0 1px 4px rgba(0, 0, 0, 0.08)',
  '--shadow-card-subtle': '0 1px 2px rgba(0, 0, 0, 0.04)',
  '--space-xs': '4px',
  '--space-sm': '8px',
  '--space-md': '12px',
  '--space-lg': '16px',
  '--space-xl': '16px',
  '--space-2xl': '20px',
  '--space-3xl': '24px',
  '--space-section': '24px',
  '--font-size-xs': '12px',
  '--font-size-sm': '13px',
  '--font-size-base': '14px',
  '--font-size-md': '14px',
  '--font-size-lg': '16px',
  '--font-size-xl': '18px',
  '--font-size-hero': '24px',
  '--sidebar-width': '240px',
}

function applyCSSVars(skin) {
  const root = document.documentElement
  // 先清除所有 Naive 变量，恢复 theme.css 默认值
  for (const key of Object.keys(NAIVE_VARS)) {
    root.style.removeProperty(key)
  }
  // 只有 Naive 皮肤才覆盖变量
  if (skin === 'naive') {
    for (const [key, value] of Object.entries(NAIVE_VARS)) {
      root.style.setProperty(key, value)
    }
  }
}

export const useThemeStore = defineStore('theme', () => {
  const currentSkin = ref(localStorage.getItem('skin') || 'zhangfang')

  const themeOverrides = computed(() => THEMES[currentSkin.value])

  const skins = SKINS
  const currentSkinLabel = computed(() => SKINS.find(s => s.key === currentSkin.value)?.label || '账房风格')

  watch(currentSkin, (skin) => {
    applyCSSVars(skin)
  }, { immediate: true })

  function switchSkin(key) {
    if (THEMES[key] !== undefined) {
      currentSkin.value = key
      localStorage.setItem('skin', key)
    }
  }

  function toggleSkin() {
    const next = currentSkin.value === 'zhangfang' ? 'naive' : 'zhangfang'
    switchSkin(next)
  }

  return { currentSkin, currentSkinLabel, themeOverrides, skins, switchSkin, toggleSkin }
})
