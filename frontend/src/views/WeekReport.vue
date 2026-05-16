<template>
  <TemplateReport
    title="资金周报"
    subtitle="按周汇总：期初/收入/支出/净变动/期末"
    reportType="week_report"
    exportType="week_report"
    :defaultHeaders="['单位简称', '期初余额', '收入合计', '支出合计', '净变动', '期末余额']"
    :defaultKeys="['entity_name', 'opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance']"
    :moneyKeys="['opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance']"
    :addFrontendTotal="true"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
