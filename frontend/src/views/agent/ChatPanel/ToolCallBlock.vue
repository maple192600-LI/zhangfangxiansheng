<template>
  <div class="tool-block" @click="$emit('toggle')">
    <div class="tool-head" :class="statusClass">
      <span class="tool-icon">{{ icon }}</span>
      <span class="tool-name">{{ name }}</span>
      <span class="tool-toggle">{{ expanded ? '收起 ▴' : '展开 ▸' }}</span>
    </div>
    <div v-if="expanded" class="tool-detail">
      <div class="tool-section">
        <div class="tool-section-title">参数</div>
        <pre>{{ fmtArgs }}</pre>
      </div>
      <div v-if="toolResult" class="tool-section">
        <div class="tool-section-title">结果</div>
        <pre>{{ fmtResult }}</pre>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  toolCallJson: { type: String, required: true },
  toolResult: { type: String, default: null },
  expanded: { type: Boolean, default: false },
})
defineEmits(['toggle'])

const parsedCall = computed(() => {
  try { return JSON.parse(props.toolCallJson) } catch { return {} }
})

const name = computed(() => parsedCall.value.name || '?')

const icon = computed(() => {
  if (props.toolResult) {
    try { return JSON.parse(props.toolResult).ok ? '✅' : '❌' } catch {}
  }
  return '🔧'
})

const statusClass = computed(() => {
  if (props.toolResult) {
    try { return JSON.parse(props.toolResult).ok ? 'tool-ok' : 'tool-err' } catch {}
  }
  return 'tool-running'
})

const fmtArgs = computed(() => {
  try { return JSON.stringify(parsedCall.value.arguments || parsedCall.value, null, 2) } catch { return props.toolCallJson }
})

const fmtResult = computed(() => {
  try { return JSON.stringify(JSON.parse(props.toolResult).result || JSON.parse(props.toolResult), null, 2) } catch { return props.toolResult }
})
</script>

<style scoped>
.tool-block {
  margin-top: 6px;
  border-radius: 10px;
  overflow: hidden;
  font-size: 13px;
  cursor: pointer;
}
.tool-head {
  display: flex; align-items: center; gap: 6px;
  padding: 8px 12px;
  transition: background .15s;
}
.tool-head.tool-running { background: #eef5f8; border: 1px solid #d0e4ea; }
.tool-head.tool-ok { background: #eef3ec; border: 1px solid #d7e5d4; }
.tool-head.tool-err { background: #fdf2ef; border: 1px solid #e0b8ad; }
.tool-block:hover .tool-head { filter: brightness(.97); }

.tool-icon { font-size: 14px; }
.tool-name { font-weight: 600; flex: 1; }
.tool-running .tool-name { color: #1a7a8a; }
.tool-ok .tool-name { color: #2f5e2e; }
.tool-err .tool-name { color: #9b3d2f; }
.tool-toggle { color: #8c8680; font-size: 12px; }

.tool-detail {
  border-top: 1px solid #ede8df;
  background: #faf8f3;
}
.tool-section { padding: 8px 12px; }
.tool-section + .tool-section { border-top: 1px dashed #e7e0d5; }
.tool-section-title {
  font-size: 11px; font-weight: 600; color: #8c8680;
  margin-bottom: 4px; text-transform: uppercase;
}
.tool-detail pre {
  margin: 0; padding: 6px 8px;
  background: #fff; border-radius: 6px;
  font-size: 12px; overflow: auto;
  max-height: 200px; line-height: 1.5;
  border: 1px solid #ede8df;
}
</style>
