<template>
  <NSelect
    :value="modelValue"
    @update:value="$emit('update:modelValue', $event)"
    :options="options"
    :placeholder="placeholder"
    clearable
    filterable
    :filter="accountFilter"
    clear-filter-after-select
    class="filter-select filter-account-select"
    :consistent-menu-width="false"
    :menu-props="{ class: 'filter-select-menu filter-account-menu' }"
  />
</template>

<script setup>
import { computed } from 'vue'
import { NSelect } from 'naive-ui'

const props = defineProps({
  modelValue: { default: null },
  entities: { type: Array, default: () => [] },
  placeholder: { type: String, default: '全部账户' },
})

defineEmits(['update:modelValue'])

const options = computed(() => {
  return props.entities.map(e => ({
    type: 'group',
    label: e.entity_full_name || e.entity_display_name || e.entity_name,
    key: e.entity_id,
    entity: e,
    children: (e.accounts || []).map(a => ({
      label: `${a.account_code} ${a.account_alias}`,
      value: a.id,
      account: a,
      entity: e,
    })),
  }))
})

function accountFilter(pattern, option) {
  if (!pattern) return true
  const p = pattern.toLowerCase()
  if (option.type === 'group') {
    const e = option.entity
    if (!e) return true
    return (
      (e.entity_full_name || '').toLowerCase().includes(p) ||
      (e.entity_display_name || '').toLowerCase().includes(p) ||
      (e.entity_name || '').toLowerCase().includes(p)
    )
  }
  const a = option.account
  const e = option.entity
  if (!a) return true
  return (
    (a.account_code || '').toLowerCase().includes(p) ||
    (a.account_alias || '').toLowerCase().includes(p) ||
    (a.account_type || '').toLowerCase().includes(p) ||
    (a.bank_name || '').toLowerCase().includes(p) ||
    (e && (e.entity_full_name || '').toLowerCase().includes(p))
  )
}
</script>

<style>
.filter-account-select {
  min-width: 200px;
}
.filter-account-menu {
  min-width: 320px !important;
  max-width: 520px !important;
}
</style>
