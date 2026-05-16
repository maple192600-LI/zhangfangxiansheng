<template>
  <TemplateReport
    title="月末盘点表"
    subtitle="按月汇总各账户余额"
    reportType="month_check"
    exportType="month_check"
    dateMode="month"
    :defaultHeaders="['单位简称', '账户名称', '期初余额', '本期收入', '本期支出', '期末余额']"
    :defaultKeys="['entity_name', 'account_name', 'opening_balance', 'period_income', 'period_expense', 'ending_balance']"
    :moneyKeys="['opening_balance', 'period_income', 'period_expense', 'ending_balance']"
  />
</template>

<script setup>
import TemplateReport from '@/composables/TemplateReport.vue'
</script>
