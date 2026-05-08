<template>
  <n-config-provider :theme-overrides="themeStore.themeOverrides">
    <n-message-provider>
      <router-view />
    </n-message-provider>
  </n-config-provider>
</template>

<script setup>
import { NConfigProvider, NMessageProvider } from 'naive-ui'
import { useThemeStore } from './stores/theme.js'

const themeStore = useThemeStore()
</script>
