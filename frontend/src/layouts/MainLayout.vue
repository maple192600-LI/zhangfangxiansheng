<template>
  <div class="app-layout">
    <!-- 左侧导航 -->
    <aside class="sidebar">
      <div class="brand">
        <h1>账房先生</h1>
        <div class="subtitle">面向中国财务人员的本地部署资金工作台</div>
      </div>

      <div class="nav-group">
        <div class="nav-list">
          <template v-for="(item, key) in navData" :key="key">
            <!-- AI智能体动态导航 -->
            <template v-if="item._dynamic && key === 'AI智能体'">
              <button
                class="nav-main"
                :class="{ active: nav.currentPrimary === key }"
                @click="toggleSection(key)"
              >
                <span class="nav-icon">{{ item.icon }}</span>
                <span class="nav-label">{{ key }}</span>
                <span class="caret">{{ openState[key] ? '▾' : '▸' }}</span>
              </button>
              <div class="subnav" :class="{ open: openState[key] }">
                <button
                  v-for="agent in agentsStore.list"
                  :key="agent.id"
                  class="subnav-item"
                  :class="{ active: nav.currentPrimary === key && Number(route.params.id) === agent.id }"
                  @click="goToAgent(agent)"
                >
                  {{ agent.display_name }}
                </button>
                <button
                  class="subnav-item add-agent-btn"
                  @click="showCreateAgentModal = true"
                >
                  ＋ 新建 agent
                </button>
              </div>
            </template>
            <!-- 有二级导航 -->
            <template v-else-if="item.secondary">
              <button
                class="nav-main"
                :class="{ active: nav.currentPrimary === key }"
                @click="toggleSection(key)"
              >
                <span class="nav-icon">{{ item.icon }}</span>
                <span class="nav-label">{{ key }}</span>
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
                <span class="nav-icon">{{ item.icon }}</span>
                <span class="nav-label">{{ key }}</span>
              </button>
            </template>
          </template>
        </div>
      </div>

      <!-- 用户区域 -->
      <div class="user-area">
        <div class="user-info">
          <span class="user-avatar">{{ (auth.user?.username || '?')[0].toUpperCase() }}</span>
          <span class="user-name">{{ auth.user?.username || '未知用户' }}</span>
        </div>
        <div class="user-actions">
          <button class="user-btn" @click="showPwdDialog = true">修改密码</button>
          <button class="user-btn user-btn-logout" @click="handleLogout">退出登录</button>
        </div>
      </div>
    </aside>

    <!-- 修改密码弹窗 -->
    <div v-if="showPwdDialog" class="modal-overlay" @click.self="showPwdDialog = false">
      <div class="modal-box">
        <h3>修改密码</h3>
        <div v-if="pwdError" class="error-bar" style="margin-bottom: 12px;">{{ pwdError }}</div>
        <div v-if="pwdOk" class="warning ok" style="margin-bottom: 12px;">密码修改成功，请重新登录</div>
        <div class="form-group">
          <label class="form-label">当前密码</label>
          <input v-model="oldPwd" type="password" class="form-input" placeholder="请输入当前密码" />
        </div>
        <div class="form-group">
          <label class="form-label">新密码</label>
          <input v-model="newPwd" type="password" class="form-input" placeholder="请输入新密码" />
        </div>
        <div class="form-group">
          <label class="form-label">确认新密码</label>
          <input v-model="confirmPwd" type="password" class="form-input" placeholder="再次输入新密码" />
        </div>
        <div class="btn-row" style="justify-content: flex-end; margin-top: 16px;">
          <button class="btn btn-secondary" @click="showPwdDialog = false">取消</button>
          <button class="btn btn-primary" :disabled="pwdLoading" @click="handleChangePwd">
            {{ pwdLoading ? '保存中...' : '确认修改' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 新建 Agent 弹窗 -->
    <AgentCreateModal
      v-if="showCreateAgentModal"
      @close="showCreateAgentModal = false"
      @created="onAgentCreated"
    />

    <!-- 右侧内容区 -->
    <main class="main-area" :class="{ 'main-area--full': isAgentPage }">
      <!-- Agent 页面：无 shell 包裹，直接全屏 -->
      <div v-if="isAgentPage" class="agent-page-wrap">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>
      <!-- 普通 页面：有 shell + tabs -->
      <div v-else class="shell">
        <div class="right-tabs" v-if="currentTabs.length">
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
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onActivated } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useNavStore } from '@/stores/nav'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'
import { changePassword } from '@/api/auth'
import AgentCreateModal from '@/components/agent/AgentCreateModal.vue'

const nav = useNavStore()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const agentsStore = useAgentsStore()

// 首次登录强制改密码检测
onMounted(() => {
  if (route.query.forceChangePwd === '1' || auth.user?.must_change_password) {
    showPwdDialog.value = true
  }
  // 加载 agent 列表
  agentsStore.fetchAll()
})

// 修改密码相关
const showPwdDialog = ref(false)
const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdLoading = ref(false)
const pwdError = ref('')
const pwdOk = ref(false)

async function handleChangePwd() {
  if (!oldPwd.value || !newPwd.value || !confirmPwd.value) {
    pwdError.value = '请填写所有字段'
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    pwdError.value = '两次输入的新密码不一致'
    return
  }
  if (newPwd.value.length < 6) {
    pwdError.value = '新密码至少6位'
    return
  }
  pwdLoading.value = true
  pwdError.value = ''
  try {
    await changePassword({ old_password: oldPwd.value, new_password: newPwd.value })
    pwdOk.value = true
    setTimeout(() => {
      showPwdDialog.value = false
      pwdOk.value = false
      oldPwd.value = ''
      newPwd.value = ''
      confirmPwd.value = ''
      auth.logout()
      router.push({ name: 'login' })
    }, 1500)
  } catch (e) {
    pwdError.value = e.message || '修改密码失败'
  } finally {
    pwdLoading.value = false
  }
}

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}

// 导航数据 — 严格复刻 preview_v4_confirmed.html 的 navData
const navData = {
  '首页': {
    icon: '🏠',
    tabs: [
      { name: '工作总览', explain: '首页默认页。打开软件先看今天的处理进度、待办、异常、快捷入口和关键状态。', route: 'home' },
      { name: '待办追踪', explain: '首页待办追踪页。集中看待导入、待确认、待生成和待处理项。', route: 'home-tasks' },
      { name: '快捷入口', explain: '首页快捷入口页。放高频动作，不放一堆低频配置。', route: 'home-quick' },
      { name: '系统提醒', explain: '首页系统提醒页。看最近生成时间、备份时间、OCR 状态和规则更新时间。', route: 'home-system' }
    ]
  },
  '资金板块': {
    icon: '💰',
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
    icon: '📷',
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
    icon: '🏦',
    tabs: [
      { name: '贷款台账', explain: '贷款管理下的贷款台账页。', route: 'loan-ledger' },
      { name: '利息支出', explain: '贷款管理下的利息支出页。', route: 'loan-interest' },
      { name: '贷款其他信息台账', explain: '贷款管理下的贷款其他信息台账页。', route: 'loan-other-ledger' },
      { name: '其他信息', explain: '贷款管理下的其他信息页。', route: 'loan-other' }
    ]
  },
  '预算管理': {
    icon: '📋',
    tabs: [
      { name: '资金计划', explain: '预算管理下的资金计划页。', route: 'budget-plan' }
    ]
  },
  'AI智能体': {
    icon: '🤖',
    _dynamic: true  // 标记为动态渲染
  },
  '系统设置': {
    icon: '⚙️',
    secondary: {
      '数据中心': {
        tabs: [
          { name: '账户数据管理', explain: '管理账户及其所属核算组织、单位、银行信息', route: 'account-manage' },
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
          { name: 'API KEY配置', explain: 'AI 配置下的 API KEY 配置页。', route: 'ai-config' }
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

// Agent 页面检测 — 不套 shell，全屏渲染
const isAgentPage = computed(() => route.name === 'agent-detail')

// Agent 相关
const showCreateAgentModal = ref(false)

function goToAgent(agent) {
  nav.navigate('AI智能体', agent.display_name, 0)
  router.push({ name: 'agent-detail', params: { id: agent.id } })
}

async function onAgentCreated(agent) {
  showCreateAgentModal.value = false
  // store 已在 createAgent 中刷新
  goToAgent(agent)
}
const currentTabs = computed(() => {
  const node = navData[nav.currentPrimary]
  if (!node) return []
  if (node.secondary && nav.currentSecondary && node.secondary[nav.currentSecondary]) {
    return node.secondary[nav.currentSecondary].tabs
  }
  return node.tabs || []
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
  display: flex;
  flex-direction: column;
}

.brand {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px 18px 14px;
  margin-bottom: 8px;
}

.brand h1 {
  font-size: var(--font-size-xl);
  margin: 0;
  font-weight: 700;
  letter-spacing: 0.5px;
}

.brand .subtitle {
  color: var(--muted);
  font-size: var(--font-size-xs);
  line-height: 1.7;
}

.nav-group {
  margin-top: 10px;
}

.nav-main {
  display: flex;
  align-items: center;
  width: 100%;
  border: none;
  background: transparent;
  border-radius: var(--radius-md);
  padding: var(--space-md);
  cursor: pointer;
  color: var(--text);
  font-size: var(--font-size-md);
  text-align: left;
  transition: background .18s ease, box-shadow .18s ease;
  font-family: inherit;
}

.nav-icon {
  width: 20px;
  text-align: center;
  flex: 0 0 20px;
  font-size: 15px;
  margin-right: 8px;
  opacity: .7;
}

.nav-main.active .nav-icon { opacity: 1; }

.nav-label { flex: 1; }

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

.add-agent-btn {
  color: var(--green) !important;
  font-weight: 500;
  border-top: 1px dashed #ddd8ce;
  margin-top: 4px;
  padding-top: 12px;
}

.add-agent-btn:hover {
  background: #eef3ec;
}

/* ── 右侧内容区 ── */
.main-area {
  padding: 18px 20px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.main-area--full {
  padding: 0;
  gap: 0;
  overflow: hidden;
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
  padding: var(--space-xl);
}

@media (max-width: 1200px) {
  .app-layout {
    grid-template-columns: 1fr;
  }
  .sidebar {
    height: auto;
    position: relative;
  }
}

/* ── 用户区域 ── */
.user-area {
  margin-top: auto;
  padding: 16px 14px 8px;
  border-top: 1px solid var(--line);
}

.user-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.user-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--green-2);
  color: #30422f;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 14px;
  flex-shrink: 0;
}

.user-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}

.user-actions {
  display: flex;
  gap: 8px;
}

.user-btn {
  flex: 1;
  padding: 6px 0;
  border: 1px solid var(--line);
  border-radius: var(--radius, 8px);
  background: #fff;
  font-size: 12px;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .15s;
}

.user-btn:hover {
  background: #f4f1ea;
}

.user-btn-logout {
  color: var(--warn-text);
  border-color: var(--warn-border);
}

.user-btn-logout:hover {
  background: var(--warn-bg);
}

/* ── 弹窗 ── */
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: #faf8f3; border-radius: var(--radius-lg, 16px); padding: 28px;
  max-width: 420px; width: 90%; box-shadow: 0 12px 40px rgba(0,0,0,.15);
}
.modal-box h3 { margin: 0 0 16px; font-size: var(--font-size-lg); }

.form-group { margin-bottom: 14px; }
.form-label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.form-input {
  width: 100%; height: 38px; padding: 0 12px; border: 1px solid var(--line);
  border-radius: var(--radius-sm, 8px); font-size: 14px; color: var(--text);
  background: var(--panel-2, #f7f4ee); outline: none; box-sizing: border-box;
}
.form-input:focus { border-color: var(--green); box-shadow: 0 0 0 3px var(--green-2); }
</style>
