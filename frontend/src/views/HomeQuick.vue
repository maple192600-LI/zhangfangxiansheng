<template>
  <div v-if="loading" class="loading-state"><div class="loading-spinner"></div><p>加载中...</p></div>
  <template v-else>
  <div class="section">
    <div class="section-title"><h3>快捷入口</h3></div>
    <div class="quick-grid">
      <div v-for="link in links" :key="link.route" class="quick" @click="go(link.route)">
        <strong>{{ link.icon }} {{ link.name }}</strong>
        <span>{{ link.desc }}</span>
      </div>
    </div>
  </div>
  </template>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getQuickLinks } from '@/api/home'

const router = useRouter()
const loading = ref(true)
const links = ref([])

onMounted(async () => {
  try {
    const data = await getQuickLinks()
    links.value = data?.links || []
  } catch (e) {
    console.error('快捷入口加载失败', e)
  } finally {
    loading.value = false
  }
})

function go(route) {
  router.push(route)
}
</script>

<style scoped>
@import './common.css';
</style>
