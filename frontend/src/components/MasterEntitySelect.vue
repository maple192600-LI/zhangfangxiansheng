<template>
  <NSelect
    :value="modelValue"
    @update:value="$emit('update:modelValue', $event)"
    :options="options"
    :placeholder="placeholder"
    clearable
    class="filter-select filter-entity-select"
    :consistent-menu-width="false"
    :menu-props="{ class: 'filter-select-menu filter-entity-menu' }"
    :render-label="renderLabel"
  />
</template>

<script setup>
import { computed } from 'vue'
import { NSelect, NTooltip } from 'naive-ui'
import { h } from 'vue'

const props = defineProps({
  modelValue: { default: null },
  entities: { type: Array, default: () => [] },
  showAll: { type: Boolean, default: true },
  placeholder: { type: String, default: '全部单位' },
})

defineEmits(['update:modelValue'])

const options = computed(() => {
  const items = props.entities.map(e => ({
    label: e.entity_display_name || e.entity_name,
    value: e.entity_id,
    entity: e,
  }))
  if (props.showAll) {
    return [{ label: '全部单位', value: null }, ...items]
  }
  return items
})

function renderLabel(option) {
  const e = option.entity
  if (!e) return option.label
  const fullName = e.entity_full_name || ''
  const shortName = e.entity_short_name || e.entity_name || ''
  if (fullName && fullName !== shortName) {
    return h('div', { style: 'display:flex;flex-direction:column;gap:1px;line-height:1.3' }, [
      h('span', { style: 'font-size:13px;color:var(--text)' }, shortName),
      h('span', { style: 'font-size:11px;color:var(--muted);white-space:normal' }, fullName),
    ])
  }
  return shortName || option.label
}
</script>

<style>
/* 全局样式 — 选择器本体固定宽度，不受长名称影响 */
.filter-entity-select {
  flex: 0 0 180px;
  width: 180px;
}
/* 下拉菜单最小宽度，允许显示双行信息 */
.filter-entity-menu {
  min-width: 240px !important;
  max-width: 420px !important;
}
</style>
