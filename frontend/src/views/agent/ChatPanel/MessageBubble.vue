<template>
  <div class="msg-bubble" :class="bubbleClass">
    <div v-if="role === 'user'" v-html="renderedContent"></div>
    <div v-else class="markdown-body" v-html="renderedContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useMarkdown } from '@/composables/useMarkdown'

const props = defineProps({
  content: { type: String, default: '' },
  role: { type: String, required: true },
})

const { renderMarkdown } = useMarkdown()

const bubbleClass = computed(() => ({
  'msg-user-bubble': props.role === 'user',
}))

const renderedContent = computed(() => {
  if (props.role === 'user') {
    return (props.content || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
  }
  return renderMarkdown(props.content)
})
</script>

<style scoped>
.msg-user-bubble {
  background: #7f9b7a;
  color: #fff;
  border-bottom-right-radius: 4px;
}
.msg-bubble:not(.msg-user-bubble) {
  background: #f7f4ee;
  border: 1px solid #e7e0d5;
  border-bottom-left-radius: 4px;
  color: #333;
}

.markdown-body {
  line-height: 1.7;
  word-break: break-word;
}
.markdown-body :deep(p) { margin: 0 0 8px 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(ul), .markdown-body :deep(ol) { margin: 4px 0; padding-left: 20px; }
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(strong) { font-weight: 600; }
.markdown-body :deep(a) { color: #5a8a55; text-decoration: underline; }

.markdown-body :deep(pre) {
  position: relative;
  background: #1e1e2e;
  border-radius: 8px;
  padding: 16px;
  margin: 8px 0;
  overflow-x: auto;
}
.markdown-body :deep(pre code) {
  font-size: 13px;
  line-height: 1.5;
  color: #cdd6f4;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}
.markdown-body :deep(code:not(pre code)) {
  background: #f0ede5;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 13px;
  color: #7f4b32;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
}

.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
  font-size: 13px;
}
.markdown-body :deep(th), .markdown-body :deep(td) {
  border: 1px solid #e7e0d5;
  padding: 6px 10px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: #f7f4ee;
  font-weight: 600;
}

.markdown-body :deep(blockquote) {
  border-left: 3px solid #7f9b7a;
  padding-left: 12px;
  margin: 8px 0;
  color: #5b635e;
}
</style>
