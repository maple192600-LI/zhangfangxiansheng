<template>
  <TemplateReport
    title="资金年报"
    subtitle="按年汇总：期初/收入/支出/净变动/期末"
    reportType="year_report"
    exportType="year_report"
    dateMode="year"
    :defaultHeaders="['单位简称', '期初余额', '收入合计', '支出合计', '净变动', '期末余额']"
    :defaultKeys="['entity_name', 'opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance']"
    :moneyKeys="['opening_balance', 'total_income', 'total_expense', 'net_change', 'ending_balance']"
    :addFrontendTotal="true"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
