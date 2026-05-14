<template>
  <div class="wf-node" :style="{ borderColor: meta.color }">
    <div class="wf-node__header" :style="{ background: meta.color }">
      <span class="wf-node__cat">{{ meta.category }}</span>
    </div>
    <div class="wf-node__body">
      <span class="wf-node__label">{{ meta.label }}</span>
      <span class="wf-node__id">{{ data.id }}</span>
    </div>
    <Handle type="target" :position="Position.Left" />
    <Handle type="source" :position="Position.Right" />
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { Handle, Position } from '@vue-flow/core'
import { getNodeMeta } from './nodeMeta'

const props = defineProps({
  id: String,
  data: { type: Object, required: true },
})

const meta = computed(() => getNodeMeta(props.data.nodeType))
</script>

<style scoped>
.wf-node {
  background: #fff;
  border: 2px solid #ddd;
  border-radius: 8px;
  min-width: 140px;
  font-size: 12px;
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}
.wf-node__header {
  padding: 2px 8px;
  border-radius: 6px 6px 0 0;
  color: #fff;
  font-size: 10px;
  font-weight: 600;
}
.wf-node__body {
  padding: 6px 10px;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.wf-node__label {
  font-weight: 600;
  font-size: 13px;
  color: #303133;
}
.wf-node__id {
  font-size: 10px;
  color: #909399;
}
</style>
