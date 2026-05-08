<template>
  <div class="section">
    <div class="top-bar">
      <h2 style="margin:0;font-size:18px">规则中心</h2>
    </div>

    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: activeTab === t.key }" @click="activeTab = t.key">
        {{ t.label }}
      </button>
    </div>

    <div v-if="loadError" class="load-error">{{ loadError }}</div>

    <!-- Tab: 银行 Parser -->
    <template v-if="activeTab === 'bank'">
      <div v-if="bankParsers.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>规则名称</th><th>来源银行</th><th>创建者</th>
              <th>样本校验</th><th>状态</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in bankParsers" :key="p.id">
              <td><strong>{{ p.name || p.kind }}</strong></td>
              <td>
                <span class="bank-tag" v-if="p.account_code">{{ p.account_code }}</span>
                <span class="tag tag-gray" v-else>通用</span>
              </td>
              <td>{{ p.created_by || '-' }}</td>
              <td>
                <span class="tag" :class="sampleCheckClass(p.sample_check_log)">
                  {{ sampleCheckText(p.sample_check_log) }}
                </span>
              </td>
              <td><span class="tag" :class="statusClass(p.status)">{{ statusText(p.status) }}</span></td>
              <td class="time-cell">{{ shortDate(p.created_at) }}</td>
              <td>
                <div class="btn-row">
                  <button class="btn btn-secondary btn-sm" @click="viewParser(p)">查看</button>
                  <button class="btn btn-primary btn-sm" v-if="p.status === 'draft'" @click="doApprove('parser', p.id)">审核通过</button>
                  <button class="btn btn-secondary btn-sm" v-if="p.status === 'active'" @click="doStatusChange('parser', p.id, 'retired')">停用</button>
                  <button class="btn btn-primary btn-sm" v-if="p.status === 'retired'" @click="doStatusChange('parser', p.id, 'active')">启用</button>
                  <button class="btn btn-danger btn-sm" @click="doDelete('parser', p.id, p.name)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-hint">暂无银行解析规则。请在「网银导入」页面上传文件后，由 AI 智能体创建解析器。</p>
    </template>

    <!-- Tab: 手工 Parser -->
    <template v-if="activeTab === 'manual'">
      <div v-if="manualParsers.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>规则名称</th><th>适用账户</th><th>创建者</th><th>样本校验</th><th>状态</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in manualParsers" :key="p.id">
              <td><strong>{{ p.name || '手工解析器' }}</strong></td>
              <td>{{ p.account_code || '通用' }}</td>
              <td>{{ p.created_by || '-' }}</td>
              <td>
                <span class="tag" :class="sampleCheckClass(p.sample_check_log)">
                  {{ sampleCheckText(p.sample_check_log) }}
                </span>
              </td>
              <td><span class="tag" :class="statusClass(p.status)">{{ statusText(p.status) }}</span></td>
              <td class="time-cell">{{ shortDate(p.created_at) }}</td>
              <td>
                <div class="btn-row">
                  <button class="btn btn-secondary btn-sm" @click="viewParser(p)">查看</button>
                  <button class="btn btn-primary btn-sm" v-if="p.status === 'draft'" @click="doApprove('parser', p.id)">审核通过</button>
                  <button class="btn btn-secondary btn-sm" v-if="p.status === 'active'" @click="doStatusChange('parser', p.id, 'retired')">停用</button>
                  <button class="btn btn-primary btn-sm" v-if="p.status === 'retired'" @click="doStatusChange('parser', p.id, 'active')">启用</button>
                  <button class="btn btn-danger btn-sm" @click="doDelete('parser', p.id, p.name)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-hint">暂无手工流水解析规则。</p>
    </template>

    <!-- Tab: 报表 Rule -->
    <template v-if="activeTab === 'report'">
      <div v-if="rules.length" class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>规则名称</th><th>关联模板</th><th>创建者</th><th>占位符绑定</th><th>状态</th><th>创建时间</th><th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="r in rules" :key="r.id">
              <td><strong>{{ r.name || '报表规则' }}</strong></td>
              <td>{{ r.template_id || '-' }}</td>
              <td>{{ r.created_by || '-' }}</td>
              <td>{{ bindingCount(r) }} 个</td>
              <td><span class="tag" :class="statusClass(r.status)">{{ statusText(r.status) }}</span></td>
              <td class="time-cell">{{ shortDate(r.created_at) }}</td>
              <td>
                <div class="btn-row">
                  <button class="btn btn-secondary btn-sm" @click="viewRule(r)">查看</button>
                  <button class="btn btn-primary btn-sm" v-if="r.status === 'draft'" @click="doApprove('rule', r.id)">审核通过</button>
                  <button class="btn btn-secondary btn-sm" v-if="r.status === 'active'" @click="doStatusChange('rule', r.id, 'retired')">停用</button>
                  <button class="btn btn-primary btn-sm" v-if="r.status === 'retired'" @click="doStatusChange('rule', r.id, 'active')">启用</button>
                  <button class="btn btn-danger btn-sm" @click="doDelete('rule', r.id, r.name)">删除</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <p v-else class="empty-hint">暂无报表规则。</p>
    </template>

    <!-- 详情弹窗 -->
    <div class="modal-mask" v-if="showDetail" @click.self="showDetail=false">
      <div class="modal detail-modal">
        <h3>{{ detailData.name || detailData.kind || '规则详情' }}</h3>
        <div class="detail-grid">
          <div class="field"><span class="label">类型</span><span>{{ detailData._type === 'parser' ? '解析器 (Parser)' : '报表规则 (Rule)' }}</span></div>
          <div class="field"><span class="label">状态</span><span class="tag" :class="statusClass(detailData.status)">{{ statusText(detailData.status) }}</span></div>
          <div class="field" v-if="detailData.account_code"><span class="label">关联账户</span><span>{{ detailData.account_code }}</span></div>
          <div class="field"><span class="label">创建时间</span><span>{{ detailData.created_at || '-' }}</span></div>
        </div>

        <div class="detail-section" v-if="detailData.kind">
          <h4>解析器类别</h4>
          <p>{{ detailData.kind === 'bank' ? '银行流水解析' : '手工流水解析' }}</p>
        </div>

        <div class="detail-section" v-if="detailData.sample_check_log">
          <h4>样本校验结果</h4>
          <div class="check-log">
            <div v-for="(v, k) in detailData.sample_check_log" :key="k" class="check-item">
              <span class="check-key">{{ k }}</span>
              <span class="check-val">{{ v }}</span>
            </div>
          </div>
        </div>

        <div class="detail-section" v-if="detailData.code">
          <h4>解析器代码</h4>
          <pre class="code-block">{{ detailData.code }}</pre>
        </div>

        <div class="detail-section" v-if="detailData.placeholder_bindings">
          <h4>占位符绑定 ({{ Object.keys(detailData.placeholder_bindings).length }} 个)</h4>
          <div class="mapping-table-wrap">
            <table class="mapping-table">
              <thead><tr><th>占位符</th><th>绑定值</th></tr></thead>
              <tbody>
                <tr v-for="(v, k) in detailData.placeholder_bindings" :key="k">
                  <td class="col-name">{{ k }}</td>
                  <td>{{ typeof v === 'object' ? JSON.stringify(v) : v }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showDetail=false">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as fundApi from '@/api/fund'

const tabs = [
  { key: 'bank', label: '银行解析器' },
  { key: 'manual', label: '手工解析器' },
  { key: 'report', label: '报表规则' },
]
const activeTab = ref('bank')

const bankParsers = ref([])
const manualParsers = ref([])
const rules = ref([])
const showDetail = ref(false)
const detailData = ref({})

function statusClass(s) {
  return { draft: 'tag-yellow', active: 'tag-green', retired: 'tag-gray' }[s] || 'tag-gray'
}
function statusText(s) {
  return { draft: '待审核', active: '已启用', retired: '已停用' }[s] || s
}
function sampleCheckClass(log) {
  if (!log) return 'tag-gray'
  if (log.errors === 0 || log.canonical_rows > 0) return 'tag-green'
  return 'tag-yellow'
}
function sampleCheckText(log) {
  if (!log) return '未校验'
  const rows = log.canonical_rows || 0
  const errs = log.errors || 0
  return `${rows} 行 / ${errs} 异常`
}
function shortDate(d) {
  if (!d) return '-'
  return d.slice(0, 10)
}
function bindingCount(r) {
  if (!r.placeholder_bindings) return 0
  return Object.keys(r.placeholder_bindings).length
}

const loadError = ref('')

async function loadBankParsers() {
  try {
    bankParsers.value = await fundApi.listParserArtifacts({ kind: 'bank' }) || []
  } catch (e) { bankParsers.value = []; loadError.value = '加载银行解析器失败：' + (e.message || '接口不可用') }
}
async function loadManualParsers() {
  try {
    manualParsers.value = await fundApi.listParserArtifacts({ kind: 'manual' }) || []
  } catch (e) { manualParsers.value = []; loadError.value = '加载手工解析器失败：' + (e.message || '接口不可用') }
}
async function loadRules() {
  try {
    rules.value = await fundApi.listRuleArtifacts({}) || []
  } catch (e) { rules.value = []; loadError.value = '加载报表规则失败：' + (e.message || '接口不可用') }
}

async function viewParser(p) {
  try {
    const detail = await fundApi.getParserArtifact(p.id)
    detailData.value = { ...detail, _type: 'parser' }
    showDetail.value = true
  } catch (e) { alert('获取详情失败: ' + e.message) }
}

async function viewRule(r) {
  try {
    const detail = await fundApi.getRuleArtifact(r.id)
    detailData.value = { ...detail, _type: 'rule' }
    showDetail.value = true
  } catch (e) { alert('获取详情失败: ' + e.message) }
}

async function doApprove(type, id) {
  if (!confirm('确定审核通过？审核后该规则将用于日常工作流程。')) return
  try {
    if (type === 'parser') await fundApi.approveParserArtifact(id)
    else await fundApi.approveRuleArtifact(id)
    await Promise.all([loadBankParsers(), loadManualParsers(), loadRules()])
  } catch (e) { alert('审核失败: ' + e.message) }
}

async function doStatusChange(type, id, newStatus) {
  const label = newStatus === 'retired' ? '停用' : '启用'
  if (!confirm(`确定${label}该规则？`)) return
  try {
    if (type === 'parser') await fundApi.updateParserStatus(id, newStatus)
    else await fundApi.updateRuleStatus(id, newStatus)
    await Promise.all([loadBankParsers(), loadManualParsers(), loadRules()])
  } catch (e) { alert(`${label}失败: ` + e.message) }
}

async function doDelete(type, id, name) {
  if (!confirm(`确定要删除「${name || '此规则'}」吗？\n此操作不可恢复。`)) return
  try {
    if (type === 'parser') await fundApi.deleteParserArtifact(id)
    else await fundApi.deleteRuleArtifact(id)
    await Promise.all([loadBankParsers(), loadManualParsers(), loadRules()])
  } catch (e) { alert('删除失败: ' + e.message) }
}

onMounted(() => {
  loadBankParsers()
  loadManualParsers()
  loadRules()
})
</script>

<style scoped>
@import './common.css';

.tab-bar {
  display: flex; gap: 0; border-bottom: 2px solid #e7e0d5; margin-bottom: 16px;
}
.tab-btn {
  padding: 8px 20px; border: none; background: transparent; cursor: pointer;
  font-size: 14px; color: var(--muted); border-bottom: 2px solid transparent;
  margin-bottom: -2px; transition: all 0.2s;
}
.tab-btn:hover { color: var(--text); }
.tab-btn.active { color: var(--primary); border-bottom-color: var(--primary); font-weight: 600; }

.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th { text-align: left; padding: 10px 12px; background: #f5f0e8; border-bottom: 2px solid #e7e0d5; white-space: nowrap; }
td { padding: 10px 12px; border-bottom: 1px solid #f0ebe3; }
.time-cell { color: var(--muted); font-size: 13px; white-space: nowrap; }

.bank-tag {
  display: inline-block; padding: 3px 10px; border-radius: var(--radius-sm); font-size: 13px;
  background: var(--tag-green-bg); color: var(--tag-green-text); font-weight: 500;
}

.tag { padding: 3px 10px; border-radius: var(--radius-sm); font-size: 12px; display: inline-block; }
.tag-green { background: var(--tag-green-bg); color: var(--tag-green-text); }
.tag-yellow { background: #fff8e1; color: #f57f17; }
.tag-gray { background: #f0ebe3; color: var(--muted); }

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: var(--radius-lg); padding: 24px; width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; }
.modal h3 { margin: 0 0 16px 0; }

.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.field { background: #fff; border: 1px solid #e7e0d5; border-radius: var(--radius-sm); padding: 10px 12px; }
.field .label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }

.detail-section { margin-top: 14px; }
.detail-section h4 { margin: 0 0 6px; font-size: 14px; color: var(--text); font-weight: 600; }
.detail-section p { margin: 0; font-size: 14px; color: var(--text-secondary); }

.check-log { display: flex; flex-direction: column; gap: 6px; background: #fff; border: 1px solid #e7e0d5; border-radius: var(--radius-sm); padding: 10px; }
.check-item { display: flex; justify-content: space-between; font-size: 13px; }
.check-key { color: var(--muted); }
.check-val { font-weight: 500; }

.code-block {
  background: #1e1e2e; color: #cdd6f4; padding: 14px 16px; border-radius: var(--radius-sm);
  font-size: 12px; line-height: 1.6; font-family: 'Consolas', 'Monaco', monospace;
  max-height: 320px; overflow: auto; white-space: pre; margin: 0;
}

.mapping-table-wrap {
  max-height: 260px; overflow-y: auto; border: 1px solid #e7e0d5; border-radius: var(--radius-sm);
}
.mapping-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.mapping-table th { position: sticky; top: 0; background: #f5f0e8; padding: 6px 10px; text-align: left; font-weight: 600; border-bottom: 1px solid #e7e0d5; }
.mapping-table td { padding: 5px 10px; border-bottom: 1px solid #f0ebe3; }
.mapping-table .col-name { max-width: 280px; word-break: break-all; }

.empty-hint {
  color: var(--muted); font-size: 14px; padding: 20px 0; margin: 0;
}
.load-error {
  background: #fdf2ef; border: 1px solid #e0b8ad; color: #9b3d2f;
  padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 12px;
}
</style>
