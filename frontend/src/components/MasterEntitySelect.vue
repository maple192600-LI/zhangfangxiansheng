<template>
  <NSelect
    :value="modelValue"
    @update:value="$emit('update:modelValue', $event)"
    :options="options"
    :placeholder="placeholder"
    clearable
    filterable
    :filter="entityFilter"
    clear-filter-after-select
    class="filter-select filter-entity-select"
    :consistent-menu-width="false"
    :menu-props="{ class: 'filter-select-menu filter-entity-menu' }"
  />
</template>

<script setup>
import { computed } from 'vue'
import { NSelect } from 'naive-ui'

const props = defineProps({
  modelValue: { default: null },
  entities: { type: Array, default: () => [] },
  showAll: { type: Boolean, default: true },
  placeholder: { type: String, default: '全部单位' },
})

defineEmits(['update:modelValue'])

const options = computed(() => {
  const items = props.entities.map(e => ({
    label: e.entity_full_name || e.entity_display_name || e.entity_name,
    value: e.entity_id,
    entity: e,
  }))
  if (props.showAll) {
    return [{ label: '全部单位', value: null }, ...items]
  }
  return items
})

function entityFilter(pattern, option) {
  if (!pattern) return true
  const p = pattern.toLowerCase()
  const e = option.entity
  if (!e) return true
  return (
    (e.entity_full_name || '').toLowerCase().includes(p) ||
    (e.entity_display_name || '').toLowerCase().includes(p) ||
    (e.entity_name || '').toLowerCase().includes(p) ||
    (e.entity_short_name || '').toLowerCase().includes(p)
  )
}
</script>

<style>
/* 全局样式 — 选择器本体固定宽度，不受长名称影响 */
.filter-entity-select {
  flex: 0 0 180px;
  width: 180px;
}
/* 下拉菜单最小宽度，允许显示完整单位全称 */
.filter-entity-menu {
  min-width: 280px !important;
  max-width: 480px !important;
}
</style>
