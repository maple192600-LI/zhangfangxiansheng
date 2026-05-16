<template>
  <TemplateReport
    title="主要账户余额表"
    subtitle="按单位汇总各账户期初/本期收支/期末余额"
    reportType="major_balance"
    exportType="major_balance"
    :defaultHeaders="['单位简称', '账户名称', '期初余额', '本期收入', '本期支出', '期末余额']"
    :defaultKeys="['entity_name', 'account_name', 'opening_balance', 'period_income', 'period_expense', 'ending_balance']"
    :moneyKeys="['opening_balance', 'period_income', 'period_expense', 'ending_balance']"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
