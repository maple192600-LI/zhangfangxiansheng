<template>
  <TemplateReport
    title="资金年报"
    subtitle="按年汇总：期初/收入/支出/净变动/期末"
    reportType="year_report"
    exportType="year_report"
    dateMode="year"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
