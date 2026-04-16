<template>
  <div class="section">
    <div class="section-title">
      <h3>{{ pageTitle }}</h3>
      <span>V2 阶段实现</span>
    </div>
    <div class="placeholder">此模块将在后续版本中开发，敬请期待。</div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const pageTitle = computed(() => route.meta?.title || route.name || '功能开发中')
</script>

<style scoped>
@import './common.css';
</style>
