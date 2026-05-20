<template>
  <NLayout has-sider class="app-layout">
    <!-- 左侧导航 -->
    <NLayoutSider
      bordered
      :width="280"
      :collapsed-width="0"
      :collapsed="false"
      class="sidebar"
    >
      <div class="brand">
        <h1>账房先生</h1>
        <div class="subtitle">面向中国财务人员的本地部署资金工作台</div>
      </div>

      <div class="nav-scroll">
        <NMenu
          :options="menuOptions"
          :value="menuActiveKey"
          :default-expand-all="false"
          :expanded-keys="menuExpandedKeys"
          :indent="24"
          :root-indent="16"
          @update:value="onMenuSelect"
          @update:expanded-keys="onMenuExpandedKeysChange"
        />
      </div>

      <!-- 用户区域 -->
      <div class="user-area">
        <div class="user-info">
          <span class="user-avatar">{{ (auth.user?.username || '?')[0].toUpperCase() }}</span>
          <span class="user-name">{{ auth.user?.username || '未知用户' }}</span>
        </div>
        <div class="user-actions">
          <NButton class="user-btn skin-btn" quaternary @click="toggleSkin" :title="'当前皮肤: ' + skinLabel">{{ skinLabel }}</NButton>
          <NButton class="user-btn" quaternary @click="showPwdDialog = true">修改密码</NButton>
          <NButton class="user-btn user-btn-logout" quaternary @click="handleLogout">退出登录</NButton>
        </div>
      </div>
    </NLayoutSider>

    <!-- 修改密码弹窗 -->
    <NModal
      v-model:show="showPwdDialog"
      preset="card"
      title="修改密码"
      style="width: 460px"
      :mask-closable="!isForceChangePwd"
    >
      <NForm label-placement="top">
        <NFormItem label="当前密码">
          <NInput v-model:value="oldPwd" type="password" show-password-on="click" placeholder="请输入当前密码" />
        </NFormItem>
        <NFormItem label="新密码">
          <NInput v-model:value="newPwd" type="password" show-password-on="click" placeholder="请输入新密码" />
        </NFormItem>
        <NFormItem label="确认新密码">
          <NInput v-model:value="confirmPwd" type="password" show-password-on="click" placeholder="再次输入新密码" />
        </NFormItem>
      </NForm>
      <template #footer>
        <NSpace justify="end">
          <NButton @click="showPwdDialog = false">取消</NButton>
          <NButton type="primary" :loading="pwdLoading" @click="handleChangePwd">确认修改</NButton>
        </NSpace>
      </template>
    </NModal>

    <!-- 新建 Agent 弹窗 -->
    <AgentCreateModal
      :show="showCreateAgentModal"
      @close="showCreateAgentModal = false"
      @created="onAgentCreated"
    />

    <!-- 右侧内容区 -->
    <NLayoutContent class="main-area" :class="{ 'main-area--full': isAgentPage || isFullPage }">
      <!-- Agent 页面：无 shell 包裹，直接全屏 -->
      <div v-if="isAgentPage" class="agent-page-wrap">
        <router-view v-slot="{ Component }">
          <component :is="Component" />
        </router-view>
      </div>
      <!-- 全屏页面：有 tabs 无 shell -->
      <template v-else-if="isFullPage">
        <div class="right-tabs" v-if="currentTabs.length">
          <NButton
            v-for="(tab, idx) in currentTabs"
            :key="idx"
            class="right-tab"
            :class="{ active: nav.currentTab === idx }"
            quaternary
            @click="selectTab(idx)"
          >
            {{ tab.name }}
          </NButton>
        </div>
        <div class="content-full">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </template>
      <!-- 普通 页面：有 shell + tabs -->
      <div v-else class="shell">
        <div class="right-tabs" v-if="currentTabs.length">
          <NButton
            v-for="(tab, idx) in currentTabs"
            :key="idx"
            class="right-tab"
            :class="{ active: nav.currentTab === idx }"
            quaternary
            @click="selectTab(idx)"
          >
            {{ tab.name }}
          </NButton>
        </div>
        <div class="content">
          <router-view v-slot="{ Component }">
            <keep-alive>
              <component :is="Component" />
            </keep-alive>
          </router-view>
        </div>
      </div>
    </NLayoutContent>
  </NLayout>
</template>

<script setup>
import { ref, computed, watch, onMounted, h } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { NLayout, NLayoutSider, NLayoutContent, NMenu, NModal, NForm, NFormItem, NInput, NButton, NSpace, useMessage } from 'naive-ui'
import { useNavStore } from '@/stores/nav'
import { useAuthStore } from '@/stores/auth'
import { useAgentsStore } from '@/stores/agents'
import { changePassword } from '@/api/auth'
import AgentCreateModal from '@/components/agent/AgentCreateModal.vue'
import { useSkin, SKINS } from '@/styles/skins'

const nav = useNavStore()
const router = useRouter()
const route = useRoute()
const auth = useAuthStore()
const agentsStore = useAgentsStore()
const { setSkin, getSkinName, getSkinLabel } = useSkin()
const message = useMessage()

const skinLabel = computed(() => getSkinLabel())
const skinNames = Object.keys(SKINS)

function toggleSkin() {
  const current = getSkinName()
  const idx = skinNames.indexOf(current)
  const next = skinNames[(idx + 1) % skinNames.length]
  setSkin(next)
}

// 首次登录强制改密码检测
const isForceChangePwd = computed(() => route.query.forceChangePwd === '1' || !!auth.user?.must_change_password)

onMounted(() => {
  if (isForceChangePwd.value) {
    showPwdDialog.value = true
  }
  agentsStore.fetchAll()
})

// 修改密码相关
const showPwdDialog = ref(false)
const oldPwd = ref('')
const newPwd = ref('')
const confirmPwd = ref('')
const pwdLoading = ref(false)

async function handleChangePwd() {
  if (!oldPwd.value || !newPwd.value || !confirmPwd.value) {
    message.error('请填写所有字段')
    return
  }
  if (newPwd.value !== confirmPwd.value) {
    message.error('两次输入的新密码不一致')
    return
  }
  if (newPwd.value.length < 6) {
    message.error('新密码至少6位')
    return
  }
  pwdLoading.value = true
  try {
    await changePassword({ old_password: oldPwd.value, new_password: newPwd.value })
    message.success('密码修改成功，请重新登录')
    setTimeout(() => {
      showPwdDialog.value = false
      oldPwd.value = ''
      newPwd.value = ''
      confirmPwd.value = ''
      auth.logout()
      router.push({ name: 'login' })
    }, 1500)
  } catch (e) {
    message.error(e.message || '修改密码失败')
  } finally {
    pwdLoading.value = false
  }
}

function handleLogout() {
  auth.logout()
  router.push({ name: 'login' })
}

// 导航数据 — 严格复刻 preview_confirmed.html 的 navData
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
          { name: '上传结果预览', explain: '工作台中的上传结果预览页。查看处理状态、未处理项和异常数据。', route: 'upload-preview' },
          { name: '工作流编排', explain: '用可视化节点编排资金导入、查询、报表生成和导出流程。', route: 'workflow-list' }
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
  '票据中心': {
    icon: '📷',
    tabs: [
      { name: '票据上传', explain: '上传发票、合同、回单等票据，自动识别类型和内容。', route: 'ocr-upload' },
      { name: '发票管理', explain: '发票台账管理，查看识别结果和历史记录。', route: 'invoice-ledger' },
      { name: '合同管理', explain: '合同台账管理，查看识别结果和历史记录。', route: 'contract-ledger' },
      { name: '识别设置', explain: '配置识别模板、分类规则和识别参数。', route: 'ocr-settings' }
    ]
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
    _dynamic: true
  },
  '系统设置': {
    icon: '⚙️',
    secondary: {
      '数据中心': {
        tabs: [
          { name: '主数据管理', explain: '管理核算组织、单位、银行账户等基础数据', route: 'account-manage' },
          { name: '报表模板管理', explain: '数据中心下的报表模板管理页。', route: 'data-report-tpl' },
          { name: '部门信息管理', explain: '数据中心下的部门信息管理页。', route: 'data-department' }
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
      '模型配置': {
        tabs: [
          { name: '模型配置', explain: '配置 AI 模型供应商和 API Key。', route: 'ai-config' }
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
      '系统维护': {
        tabs: [
          { name: '系统维护', explain: '系统备份恢复与数据清理。', route: 'system-maintenance' }
        ]
      },
      '操作日志': {
        tabs: [{ name: '操作日志', explain: '系统操作日志。', route: 'operation-log' }]
      }
    }
  }
}

// 默认展开的菜单
const defaultExpandedKeys = ['资金板块', 'AI智能体', '系统设置']
const menuExpandedKeys = ref([...defaultExpandedKeys])

// Agent 页面检测
const isAgentPage = computed(() => route.name === 'agent-detail')
const isFullPage = computed(() => route.name === 'ai-config' || route.name === 'workflow-editor')

// Agent 相关
const showCreateAgentModal = ref(false)

function goToAgent(agent) {
  nav.navigate('AI智能体', agent.display_name, 0)
  router.push({ name: 'agent-detail', params: { id: agent.id } })
}

async function onAgentCreated(agent) {
  showCreateAgentModal.value = false
  goToAgent(agent)
}

// 当前 tabs
const currentTabs = computed(() => {
  const node = navData[nav.currentPrimary]
  if (!node) return []
  if (node.secondary && nav.currentSecondary && node.secondary[nav.currentSecondary]) {
    return node.secondary[nav.currentSecondary].tabs
  }
  return node.tabs || []
})

// n-menu 的 active key：优先用 agent 的 key，否则用当前路由反查
const menuActiveKey = computed(() => {
  // 如果在 agent 页面，用 agent nav key
  if (isAgentPage.value) {
    return `agent-${route.params.id}`
  }
  // 否则用 primary-secondary 或 primary
  if (nav.currentSecondary) {
    return `${nav.currentPrimary}-${nav.currentSecondary}`
  }
  return nav.currentPrimary
})

// 将 navData 转换为 n-menu options
const menuOptions = computed(() => {
  const options = []
  for (const [key, node] of Object.entries(navData)) {
    // AI智能体 — 动态
    if (node._dynamic) {
      const children = agentsStore.list.map(agent => ({
        key: `agent-${agent.id}`,
        label: agent.display_name,
        __agentId: agent.id
      }))
      children.push({
        key: 'agent-create',
        label: '＋ 新建 agent',
        __isCreate: true
      })
      options.push({
        key,
        label: () => h('span', {}, [
          h('span', { class: 'nav-icon-inline' }, node.icon + ' '),
          h('span', {}, key)
        ]),
        children
      })
    } else if (node.secondary) {
      // 有二级导航
      options.push({
        key,
        label: () => h('span', {}, [
          h('span', { class: 'nav-icon-inline' }, node.icon + ' '),
          h('span', {}, key)
        ]),
        children: Object.entries(node.secondary).map(([secKey, secData]) => ({
          key: `${key}-${secKey}`,
          label: secKey
        }))
      })
    } else {
      // 无二级导航
      options.push({
        key,
        label: () => h('span', {}, [
          h('span', { class: 'nav-icon-inline' }, node.icon + ' '),
          h('span', {}, key)
        ])
      })
    }
  }
  return options
})

// n-menu 选中处理
function onMenuSelect(key) {
  // 新建 agent
  if (key === 'agent-create') {
    showCreateAgentModal.value = true
    return
  }

  // agent 子项
  if (key.startsWith('agent-')) {
    const agentId = Number(key.replace('agent-', ''))
    const agent = agentsStore.list.find(a => a.id === agentId)
    if (agent) {
      goToAgent(agent)
    }
    return
  }

  // 二级导航项：格式 "primary-secondary"
  for (const [primary, node] of Object.entries(navData)) {
    if (node.secondary) {
      for (const sec of Object.keys(node.secondary)) {
        if (key === `${primary}-${sec}`) {
          nav.navigate(primary, sec, 0)
          const tabs = navData[primary]?.secondary[sec]?.tabs || []
          if (tabs.length > 0) {
            router.push({ name: tabs[0].route })
          }
          return
        }
      }
    }
  }

  // 一级导航
  if (navData[key]) {
    nav.navigate(key, null, 0)
    const tabs = navData[key]?.tabs || []
    if (tabs.length > 0) {
      router.push({ name: tabs[0].route })
    }
  }
}

function onMenuExpandedKeysChange(keys) {
  menuExpandedKeys.value = keys
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
          if (!menuExpandedKeys.value.includes(key)) {
            menuExpandedKeys.value = [...menuExpandedKeys.value, key]
          }
          return
        }
      }
    }
  }
}, { immediate: true })
</script>

<style scoped>
/* n-layout 外层锁定视口高度，禁止 body 级滚动 */
.app-layout {
  height: 100vh;
  overflow: hidden;
}

/* 禁用 NLayout 根级滚动容器，它是 sidebar 和 main-area 的共同父级 */
.app-layout > :deep(.n-layout-scroll-container) {
  overflow: hidden !important;
  height: 100%;
}

/* ── 左侧导航 Sider ── */
.sidebar {
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: rgba(251, 250, 247, 0.92);
  backdrop-filter: blur(8px);
}

/* NLayoutSider 内部滚动容器：禁止其滚动，让 nav-scroll 独立滚动 */
.sidebar :deep(.n-layout-sider-scroll-container) {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  height: 100%;
}

.nav-scroll {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
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

/* n-menu icon 内联样式 */
.nav-icon-inline {
  margin-right: 6px;
  font-size: 15px;
  opacity: 0.7;
}

/* 让 n-menu 在 nav-scroll 中正常渲染 */
.nav-scroll :deep(.n-menu) {
  --n-item-text-color: var(--text-secondary);
  --n-item-text-color-hover: var(--text);
  --n-item-text-color-active: var(--text);
  --n-item-text-color-child-active: var(--text);
  --n-item-color-active: var(--green-2);
  --n-item-color-hover: var(--bg, #f3f0e8);
  --n-item-color-active-hover: var(--green-2);
  --n-item-icon-color: var(--text-tertiary);
  --n-item-icon-color-hover: var(--text);
  --n-item-icon-color-active: var(--text);
  --n-item-icon-color-child-active: var(--text);
  --n-arrow-color: var(--muted);
  --n-font-size: var(--font-size-base);
  --n-item-height: 42px;
  --n-border-radius: var(--radius-md);
  --n-divider-color: transparent;
}

/* agent 新建按钮特殊样式 */
.nav-scroll :deep(.n-menu .n-menu-item-content--child-active),
.nav-scroll :deep(.n-menu .n-menu-item-content--selected) {
  font-weight: 600;
}

/* ── 右侧内容区 ── */
.main-area {
  padding: 18px 20px;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 14px;
  overflow: hidden;
  height: 100%;
}

/* 禁用 Naive UI NLayoutContent 内部滚动容器 */
.main-area :deep(.n-scroll-content),
.main-area :deep(.n-layout-scroll-container) {
  overflow: hidden !important;
  height: 100%;
  display: flex;
  flex-direction: column;
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
  height: 100%;
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
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
  flex: 1;
  min-height: 0;
  overflow: auto;
  position: relative;
}

.content-full {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

@media (max-width: 1200px) {
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
  gap: 6px;
  flex-wrap: wrap;
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

.skin-btn {
  color: var(--green);
  border-color: var(--green-2);
  font-weight: 500;
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
</style>
