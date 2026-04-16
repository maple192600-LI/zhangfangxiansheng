<template>
  <div class="app-layout">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <h1>资金报表系统</h1>
        <p>首页独立置顶，首页风格改为多维表格仪表盘风格。其余目录关系不变。</p>
      </div>

      <div class="nav-group">
        <div class="nav-title">主导航</div>
        <div class="nav-list">
          <template v-for="(item, key) in navData" :key="key">
            <!-- 有二级导航 -->
            <template v-if="item.secondary">
              <button
                class="nav-main"
                :class="{ active: nav.currentPrimary === key }"
                @click="toggleSection(key)"
              >
                {{ key }}
                <span class="caret">{{ openState[key] ? '▾' : '▸' }}</span>
              </button>
              <div class="subnav" :class="{ open: openState[key] }">
                <button
                  v-for="(_, sec) in item.secondary"
                  :key="sec"
                  class="subnav-item"
                  :class="{ active: nav.currentPrimary === key && nav.currentSecondary === sec }"
                  @click="selectSecondary(key, sec)"
                >
                  {{ sec }}
                </button>
              </div>
            </template>
            <!-- 无二级导航 -->
            <template v-else>
              <button
                class="nav-main"
                :class="{ active: nav.currentPrimary === key }"
                @click="selectPrimary(key)"
              >
                {{ key }}
              </button>
            </template>
          </template>
        </div>
      </div>
    </aside>

    <!-- 右侧内容区 -->
    <main class="main-area">
      <!-- 顶栏 -->
      <div class="topbar">
        <div class="sys">
          <div class="pill">当前法人范围：全部法人</div>
          <div class="pill">当前口径：资金报表系统</div>
        </div>
        <div class="search">全局搜索：账户 / 摘要 / 对方名称 / 模块名</div>
        <div class="pill">本地备份入口</div>
      </div>

      <!-- 面包屑 -->
      <div class="crumb">
        当前路径：<strong>{{ breadcrumb }}</strong>
      </div>

      <!-- 内容壳 -->
      <div class="shell">
        <div class="right-tabs">
          <button
            v-for="(tab, idx) in currentTabs"
            :key="idx"
            class="right-tab"
            :class="{ active: nav.currentTab === idx }"
            @click="selectTab(idx)"
          >
            {{ tab.name }}
          </button>
        </div>
        <div class="content">
          <router-view />
        </div>
      </div>

      <div class="footer-note">
        这版已经把首页独立到左侧置顶位置，并改成工作导向的仪表盘样式。不是汇报台，是出纳打开软件后的总控台。
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useNavStore } from '@/stores/nav'

const nav = useNavStore()
const router = useRouter()

// 导航数据 — 严格复刻 preview_v4_confirmed.html 的 navData
const navData = {
  '首页': {
    tabs: [
      { name: '工作总览', explain: '首页默认页。打开软件先看今天的处理进度、待办、异常、快捷入口和关键状态。', route: 'home' },
      { name: '待办追踪', explain: '首页待办追踪页。集中看待导入、待确认、待生成和待处理项。', route: 'home-tasks' },
      { name: '快捷入口', explain: '首页快捷入口页。放高频动作，不放一堆低频配置。', route: 'home-quick' },
      { name: '系统提醒', explain: '首页系统提醒页。看最近生成时间、备份时间、OCR 状态和规则更新时间。', route: 'home-system' }
    ]
  },
  '资金板块': {
    secondary: {
      '工作台': {
        tabs: [
          { name: '网银导入', explain: '工作台中的网银导入页。用于上传银行流水文件。', route: 'bank-import' },
          { name: '手工流水', explain: '工作台中的手工流水页。用于录入或导入手工流水。', route: 'manual-flow' },
          { name: '手动维护', explain: '工作台中的手动维护页。用于修正记录、补录信息和维护。', route: 'manual-maintenance' },
          { name: '上传结果预览', explain: '工作台中的上传结果预览页。查看处理状态、未处理项和异常数据。', route: 'upload-preview' }
        ]
      },
      '资金日报表': {
        tabs: [
          { name: '基础数据表', explain: '基础数据表是所有后续报表的统一底座。', route: 'base-data' },
          { name: '现金日记账', explain: '资金日报表下的现金日记账。', route: 'cash-journal' },
          { name: '账户余额表', explain: '资金日报表下的账户余额表。', route: 'account-balance' },
          { name: '收入明细表', explain: '资金日报表下的收入明细表。', route: 'income-list' },
          { name: '支出明细表', explain: '资金日报表下的支出明细表。', route: 'expense-list' }
        ]
      },
      '资金综合报表': {
        tabs: [
          { name: '主要账户余额表', explain: '资金综合报表下的主要账户余额表。', route: 'major-balance' },
          { name: '月末盘点表', explain: '资金综合报表下的月末盘点表。', route: 'month-check' },
          { name: '资金周报', explain: '资金综合报表下的周报。', route: 'week-report' },
          { name: '资金月报', explain: '资金综合报表下的月报。', route: 'month-report' },
          { name: '资金年报', explain: '资金综合报表下的年报。', route: 'year-report' }
        ]
      }
    }
  },
  'OCR识别': {
    secondary: {
      '识别': {
        tabs: [
          { name: '发票识别', explain: 'OCR 识别中的发票识别页。', route: 'invoice-ocr' },
          { name: '合同识别', explain: 'OCR 识别中的合同识别页。', route: 'contract-ocr' },
          { name: '回单识别', explain: 'OCR 识别中的回单识别页。', route: 'receipt-ocr' },
          { name: '付款凭证识别', explain: 'OCR 识别中的付款凭证识别页。', route: 'payment-ocr' }
        ]
      },
      '台账': {
        tabs: [
          { name: '发票台账', explain: 'OCR 下的发票台账页。', route: 'invoice-ledger' },
          { name: '合同台账', explain: 'OCR 下的合同台账页。', route: 'contract-ledger' }
        ]
      }
    }
  },
  '贷款管理': {
    tabs: [
      { name: '贷款台账', explain: '贷款管理下的贷款台账页。', route: 'loan-ledger' },
      { name: '利息支出', explain: '贷款管理下的利息支出页。', route: 'loan-interest' },
      { name: '贷款其他信息台账', explain: '贷款管理下的贷款其他信息台账页。', route: 'loan-other-ledger' },
      { name: '其他信息', explain: '贷款管理下的其他信息页。', route: 'loan-other' }
    ]
  },
  '预算管理': {
    tabs: [
      { name: '资金计划', explain: '预算管理下的资金计划页。', route: 'budget-plan' }
    ]
  },
  'AI智能体': {
    secondary: {
      '规则agent': { tabs: [{ name: '负责解析新上传的各种新文件和模板规则解析', explain: '规则 agent 页面。', route: 'agent-social' }] },
      '日报agent': { tabs: [{ name: '负责日记账流水识别', explain: '日报 agent 页面。', route: 'agent-daily' }] },
      '费用agent': { tabs: [{ name: '生成费用类会计凭证', explain: '费用 agent 页面。', route: 'agent-cost' }] },
      '收入agent': { tabs: [{ name: '生成收入类会计凭证', explain: '收入 agent 页面。', route: 'agent-income' }] },
      '材料agent': { tabs: [{ name: '生成材料类收入凭证', explain: '材料 agent 页面。', route: 'agent-material' }] },
      '工资、税费agent': { tabs: [{ name: '工资税费类凭证生成', explain: '工资、税费 agent 页面。', route: 'agent-tax' }] },
      '自定义agent': { tabs: [{ name: '自定义智能体', explain: '自定义 agent 页面。', route: 'agent-custom' }] }
    }
  },
  '系统设置': {
    secondary: {
      '数据中心': {
        tabs: [
          { name: '账户数据管理', explain: '数据中心下的账户数据管理页。', route: 'account-manage' },
          { name: '报表模板管理', explain: '数据中心下的报表模板管理页。', route: 'data-report-tpl' },
          { name: '部门信息管理', explain: '数据中心下的部门信息管理页。', route: 'data-department' },
          { name: '合同台账管理', explain: '数据中心下的合同台账管理页。', route: 'data-contract' },
          { name: '发票台账管理', explain: '数据中心下的发票台账管理页。', route: 'data-invoice' },
          { name: '凭证模板管理', explain: '数据中心下的凭证模板管理页。', route: 'data-voucher-tpl' }
        ]
      },
      '规则中心': {
        tabs: [
          { name: '银行流水规则', explain: '规则中心下的银行流水规则页。', route: 'rule-bank' },
          { name: '收支规则', explain: '规则中心下的收支规则页。', route: 'rule-io' },
          { name: '原始凭证规则', explain: '规则中心下的原始凭证规则页。', route: 'rule-origin' },
          { name: '凭证生成规则', explain: '规则中心下的凭证生成规则页。', route: 'rule-voucher' },
          { name: '其他待拓展规则', explain: '规则中心下的其他待拓展规则页。', route: 'rule-other' }
        ]
      },
      '异常中心': {
        tabs: [
          { name: '收付款凭证缺失及补录信息', explain: '异常中心下的收付款凭证缺失及补录信息页。', route: 'exception-receipt' },
          { name: '其他可能出现的异常', explain: '异常中心下的其他异常页。', route: 'exception-other' }
        ]
      },
      'AI配置': {
        tabs: [
          { name: 'API KEY配置', explain: 'AI 配置下的 API KEY 配置页。', route: 'ai-config' },
          { name: 'agent配置', explain: 'AI 配置下的 agent 配置页。', route: 'agent-config' },
          { name: 'skill文件夹', explain: 'AI 配置下的 skill 文件夹页。', route: 'ai-skill' },
          { name: '记忆配置区', explain: 'AI 配置下的记忆配置区。', route: 'ai-memory' },
          { name: '定时任务区', explain: 'AI 配置下的定时任务区。', route: 'ai-task' },
          { name: 'OCR配置', explain: 'AI 配置下的 OCR 配置页。', route: 'ai-ocr' }
        ]
      },
      '用户和权限': {
        tabs: [
          { name: '超级管理员', explain: '用户和权限下的超级管理员视图。', route: 'perm-admin' },
          { name: '出纳', explain: '用户和权限下的出纳视图。', route: 'perm-cashier' },
          { name: '财务总监/经理', explain: '用户和权限下的财务总监/经理视图。', route: 'perm-manager' },
          { name: '老板', explain: '用户和权限下的老板视图。', route: 'perm-boss' },
          { name: '各不同会计', explain: '用户和权限下的不同会计视图。', route: 'perm-accountant' }
        ]
      },
      '备份恢复': {
        tabs: [{ name: '备份恢复', explain: '系统备份和恢复。', route: 'backup-restore' }]
      },
      '操作日志': {
        tabs: [{ name: '操作日志', explain: '系统操作日志。', route: 'operation-log' }]
      }
    }
  }
}

const openState = ref({
  '资金板块': true,
  'OCR识别': true,
  'AI智能体': true,
  '系统设置': true
})
const currentTabs = computed(() => {
  const node = navData[nav.currentPrimary]
  if (!node) return []
  if (node.secondary && nav.currentSecondary && node.secondary[nav.currentSecondary]) {
    return node.secondary[nav.currentSecondary].tabs
  }
  return node.tabs || []
})

// 说明文字
const explainText = computed(() => {
  const tabs = currentTabs.value
  if (tabs.length === 0) return ''
  const idx = Math.min(nav.currentTab, tabs.length - 1)
  return tabs[idx]?.explain || ''
})

// 面包屑
const breadcrumb = computed(() => {
  const sec = nav.currentSecondary ? ` / ${nav.currentSecondary}` : ''
  const tabs = currentTabs.value
  const idx = Math.min(nav.currentTab, tabs.length - 1)
  const tabName = tabs[idx]?.name || ''
  return `${nav.currentPrimary}${sec} / ${tabName}`
})

function toggleSection(key) {
  openState.value[key] = !openState.value[key]
}

function selectPrimary(key) {
  nav.navigate(key, null, 0)
  const node = navData[key]
  const tabs = node?.tabs || []
  if (tabs.length > 0) {
    router.push({ name: tabs[0].route })
  }
}

function selectSecondary(key, sec) {
  nav.navigate(key, sec, 0)
  const tabs = navData[key]?.secondary[sec]?.tabs || []
  if (tabs.length > 0) {
    router.push({ name: tabs[0].route })
  }
}

function selectTab(idx) {
  nav.currentTab = idx
  const tabs = currentTabs.value
  if (tabs[idx]?.route) {
    router.push({ name: tabs[idx].route })
  }
}

// 路由变化时同步导航状态
watch(() => router.currentRoute.value, (route) => {
  // 根据路由名反查导航位置
  const name = route.name
  for (const [key, node] of Object.entries(navData)) {
    if (node.tabs) {
      const idx = node.tabs.findIndex(t => t.route === name)
      if (idx >= 0) {
        nav.navigate(key, null, idx)
        return
      }
    }
    if (node.secondary) {
      for (const [sec, secData] of Object.entries(node.secondary)) {
        const idx = secData.tabs.findIndex(t => t.route === name)
        if (idx >= 0) {
          nav.navigate(key, sec, idx)
          return
        }
      }
    }
  }
}, { immediate: true })
</script>

<style scoped>
.app-layout {
  display: grid;
  grid-template-columns: 280px 1fr;
  min-height: 100vh;
}

/* ── 左侧导航 ── */
.sidebar {
  background: rgba(251, 250, 247, 0.92);
  border-right: 1px solid var(--line);
  backdrop-filter: blur(8px);
  padding: 18px 16px;
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: auto;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px 18px 14px;
  margin-bottom: 8px;
}

.brand h1 {
  font-size: 20px;
  margin: 0;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand p {
  margin: 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.7;
}

.nav-group {
  margin-top: 10px;
}

.nav-title {
  font-size: 12px;
  color: #7a7f79;
  padding: 8px 12px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.nav-main {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;
  border: none;
  background: transparent;
  border-radius: 14px;
  padding: 12px 12px;
  cursor: pointer;
  color: var(--text);
  font-size: 15px;
  text-align: left;
}

.nav-main:hover {
  background: #f3f0e8;
}

.nav-main.active {
  background: var(--green-2);
  color: #30422f;
  box-shadow: inset 0 0 0 1px rgba(127, 155, 122, 0.22);
  font-weight: 600;
}

.caret {
  font-size: 12px;
  color: #889286;
  width: 14px;
  text-align: center;
  flex: 0 0 14px;
}

.subnav {
  display: none;
  margin: 6px 0 4px 10px;
  padding-left: 10px;
  border-left: 2px solid #e5e0d6;
}

.subnav.open {
  display: block;
}

.subnav-item {
  width: 100%;
  background: transparent;
  border: none;
  padding: 10px 12px;
  margin: 2px 0;
  border-radius: 12px;
  text-align: left;
  cursor: pointer;
  color: #465048;
  font-size: 14px;
}

.subnav-item:hover {
  background: #f4f1ea;
}

.subnav-item.active {
  background: #eef3ec;
  color: #2f4330;
  font-weight: 600;
}

/* ── 右侧内容区 ── */
.main-area {
  padding: 18px 20px 28px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.topbar {
  display: grid;
  grid-template-columns: 1fr auto auto;
  gap: 14px;
  align-items: center;
  background: rgba(251, 250, 247, 0.82);
  border: 1px solid var(--line);
  border-radius: 18px;
  padding: 14px 16px;
  box-shadow: var(--shadow);
}

.sys {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.pill {
  padding: 8px 12px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: #465048;
  font-size: 13px;
  white-space: nowrap;
}

.search {
  padding: 10px 14px;
  min-width: 280px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 999px;
  color: #6a706c;
  font-size: 14px;
}

.crumb {
  background: rgba(251, 250, 247, 0.95);
  border: 1px solid var(--line);
  border-radius: 14px;
  padding: 10px 14px;
  color: var(--muted);
  font-size: 13px;
}

.crumb strong {
  color: var(--text);
}

.shell {
  background: rgba(251, 250, 247, 0.95);
  border: 1px solid var(--line);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.right-tabs {
  padding: 12px;
  border-bottom: 1px solid var(--line);
  background: #f7f4ee;
  overflow-x: auto;
  white-space: nowrap;
}

.right-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  margin-right: 8px;
  padding: 0 14px;
  border-radius: 12px;
  border: 1px solid var(--line);
  background: #fff;
  cursor: pointer;
  font-size: 14px;
  color: #465048;
}

.right-tab.active {
  background: var(--green-2);
  border-color: #d7e5d4;
  color: #2f4330;
  font-weight: 600;
}

.content {
  padding: 16px;
}

.footer-note {
  margin-top: 10px;
  color: #7a7f79;
  font-size: 12px;
  line-height: 1.8;
}

@media (max-width: 1200px) {
  .app-layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    height: auto;
    position: relative;
  }
  .topbar {
    grid-template-columns: 1fr;
  }
}
</style>
