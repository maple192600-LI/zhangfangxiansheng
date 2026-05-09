<template>
  <div>
    <div class="section">
      <div class="section-title">
        <h3>主数据管理</h3>
        <span>管理核算组织、单位、银行账户等基础数据</span>
      </div>

      <div class="tabs-bar">
        <button class="tab-btn" :class="{ active: activeTab === 'accounts' }" @click="activeTab = 'accounts'">账户列表</button>
        <button class="tab-btn" :class="{ active: activeTab === 'divisions' }" @click="activeTab = 'divisions'">核算管理</button>
        <button class="tab-btn" :class="{ active: activeTab === 'entities' }" @click="activeTab = 'entities'">单位管理</button>
        <button class="tab-btn" :class="{ active: activeTab === 'banks' }" @click="activeTab = 'banks'">账户管理</button>
      </div>

      <AccountList
        v-if="activeTab === 'accounts'"
        :divisions="divisions" :all-entities="allEntities" :accounts="accounts"
        @refresh="loadAll"
      />
      <DivisionList
        v-if="activeTab === 'divisions'"
        :divisions="divisions"
        @refresh="loadAll"
      />
      <EntityList
        v-if="activeTab === 'entities'"
        :divisions="divisions" :all-entities="allEntities"
        @refresh="loadAll"
      />
      <BankAccountList
        v-if="activeTab === 'banks'"
        :divisions="divisions" :all-entities="allEntities" :accounts="accounts"
        @refresh="loadAll"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '@/api/master'
import AccountList from './AccountList.vue'
import DivisionList from './DivisionList.vue'
import EntityList from './EntityList.vue'
import BankAccountList from './BankAccountList.vue'

const activeTab = ref('accounts')
const divisions = ref([])
const allEntities = ref([])
const accounts = ref([])

async function loadAll() {
  try {
    const [divs, ents, accs] = await Promise.all([
      api.getDivisions(),
      api.getEntities({ page: 1, page_size: 200 }),
      api.getAccounts({ page: 1, page_size: 200 }),
    ])
    divisions.value = divs || []
    allEntities.value = ents?.items || []
    accounts.value = accs?.items || []
  } catch (e) { console.error(e) }
}

onMounted(loadAll)
</script>

<style scoped>
@import '../common.css';

.tabs-bar {
  display: flex;
  gap: 0;
  border-bottom: 2px solid var(--line);
  margin-bottom: var(--space-lg);
}
.tab-btn {
  padding: var(--space-sm) var(--space-xl);
  font-size: var(--font-size-base);
  font-family: inherit;
  font-weight: 500;
  color: var(--muted);
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  margin-bottom: -2px;
  cursor: pointer;
  transition: all .18s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active {
  color: var(--green);
  border-bottom-color: var(--green);
  font-weight: 600;
}
</style>
