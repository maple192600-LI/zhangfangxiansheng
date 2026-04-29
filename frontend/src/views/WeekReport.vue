<template>
  <TemplateReport
    title="资金周报"
    subtitle="按周汇总：期初/收入/支出/净变动/期末"
    reportType="week_report"
    exportType="week_report"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
