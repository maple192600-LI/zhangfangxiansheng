<template>
  <TemplateReport
    title="资金月报"
    subtitle="按月汇总：期初/收入/支出/净变动/期末"
    reportType="month_report"
    exportType="month_report"
    dateMode="month"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
