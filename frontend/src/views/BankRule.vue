<template>
  <div class="section">
    <div class="top-bar">
      <button class="btn btn-primary" @click="showForm=true">+ 新建规则模板</button>
    </div>

    <table class="data-table" v-if="templates.length">
      <thead>
        <tr>
          <th>规则名称</th><th>识别银行</th><th>文件格式</th><th>表头行</th><th>跳过行</th>
          <th>样本表头</th><th>映射字段数</th><th>状态</th><th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="t in templates" :key="t.id">
          <td><strong>{{ t.template_name }}</strong></td>
          <td>
            <div class="bank-tag" v-if="guessBank(t.template_name)">
              {{ guessBank(t.template_name) }}
            </div>
          </td>
          <td>{{ t.file_format }}</td>
          <td>{{ t.header_row }}</td>
          <td>{{ t.skip_rows }}</td>
          <td>
            <div class="tag-list">
              <span class="tag" v-for="h in (t.sample_headers || []).slice(0, 5)" :key="h">{{ h }}</span>
              <span class="tag more" v-if="(t.sample_headers || []).length > 5">+{{ t.sample_headers.length - 5 }}</span>
            </div>
          </td>
          <td>{{ Object.keys(t.mapping_json || {}).length }}</td>
          <td><span class="badge" :class="t.status">{{ t.status === 'active' ? '启用' : '停用' }}</span></td>
          <td>
            <div class="btn-row">
              <button class="btn btn-secondary btn-sm" @click="viewDetail(t)">查看</button>
              <button class="btn btn-secondary btn-sm" v-if="t.status==='active'" @click="toggleStatus(t, 'disabled')">停用</button>
              <button class="btn btn-secondary btn-sm" v-else @click="toggleStatus(t, 'active')">启用</button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
    <p v-else style="color:var(--muted);font-size:14px;padding:20px 0">
      暂无银行流水规则。请在「网银导入」页面上传文件后创建模板，或手动新建。
    </p>

    <!-- 详情弹窗 -->
    <div class="modal-mask" v-if="showDetail" @click.self="showDetail=false">
      <div class="modal" style="max-width:640px">
        <h3>{{ detailData.template_name }} — 规则详情</h3>
        <div class="detail-grid">
          <div class="field"><span class="label">文件格式</span><span>{{ detailData.file_format }}</span></div>
          <div class="field"><span class="label">表头行号</span><span>{{ detailData.header_row }}</span></div>
          <div class="field"><span class="label">跳过行数</span><span>{{ detailData.skip_rows }}</span></div>
          <div class="field"><span class="label">状态</span><span class="badge" :class="detailData.status">{{ detailData.status }}</span></div>
        </div>
        <div style="margin-top:14px">
          <h4 style="margin:0 0 8px;font-size:14px">样本表头</h4>
          <div class="tag-list">
            <span class="tag" v-for="h in (detailData.sample_headers || [])" :key="h">{{ h }}</span>
          </div>
        </div>
        <div style="margin-top:14px">
          <h4 style="margin:0 0 8px;font-size:14px">字段映射</h4>
          <table class="data-table" style="font-size:12px">
            <thead><tr><th>银行列名</th><th>→ 标准字段</th></tr></thead>
            <tbody>
              <tr v-for="(v, k) in (detailData.mapping_json || {})" :key="k">
                <td>{{ k }}</td><td style="color:var(--green)">{{ v }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showDetail=false">关闭</button>
        </div>
      </div>
    </div>

    <!-- 新建弹窗 -->
    <div class="modal-mask" v-if="showForm" @click.self="showForm=false">
      <div class="modal" style="max-width:560px">
        <h3>新建银行流水规则</h3>
        <div class="form-group">
          <label>模板名称</label>
          <input v-model="form.template_name" class="filter" placeholder="如：招商银行标准模板" />
        </div>
        <div class="form-row">
          <div class="form-group" style="flex:1">
            <label>文件格式</label>
            <select v-model="form.file_format" class="filter">
              <option value="xlsx">xlsx</option>
              <option value="xls">xls</option>
              <option value="csv">csv</option>
            </select>
          </div>
          <div class="form-group" style="width:80px">
            <label>表头行</label>
            <input v-model.number="form.header_row" type="number" class="filter" min="0" />
          </div>
          <div class="form-group" style="width:80px">
            <label>跳过行</label>
            <input v-model.number="form.skip_rows" type="number" class="filter" min="0" />
          </div>
        </div>
        <div class="form-group">
          <label>样本表头（每行一个列名）</label>
          <textarea v-model="form.sample_headers_text" class="filter" rows="3" placeholder="交易日期&#10;收入金额&#10;支出金额&#10;对方户名&#10;摘要"></textarea>
        </div>
        <div class="form-group">
          <label>映射 JSON（银行列名 → 标准字段）</label>
          <textarea v-model="form.mapping_text" class="filter" rows="5" placeholder='{"交易日期":"business_date","收入金额":"income_amount","支出金额":"expense_amount","对方户名":"counterparty_name","摘要":"summary_text"}'></textarea>
        </div>
        <div class="btn-row" style="justify-content:flex-end;margin-top:16px">
          <button class="btn btn-secondary" @click="showForm=false">取消</button>
          <button class="btn btn-primary" @click="doCreate">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import * as api from '@/api/bank'

const templates = ref([])
const showDetail = ref(false)
const showForm = ref(false)
const detailData = ref({})

const form = ref({
  template_name: '',
  file_format: 'xlsx',
  header_row: 0,
  skip_rows: 0,
  sample_headers_text: '',
  mapping_text: '',
})

async function loadTemplates() {
  try {
    templates.value = await api.getParserTemplates({ template_type: 'bank' })
  } catch { /* ignore */ }
}

// 从规则名称中猜测对应的银行
const BANK_KEYWORDS = {
  '招商': '招商银行', '招行': '招商银行',
  '农业': '农业银行', '农行': '农业银行',
  '工商': '工商银行', '工行': '工商银行',
  '建设': '建设银行', '建行': '建设银行',
  '中国银行': '中国银行', '中行': '中国银行',
  '交通': '交通银行', '交行': '交通银行',
  '兴业': '兴业银行',
  '广发': '广发银行',
  '民生': '民生银行',
  '浦发': '浦发银行',
  '中信': '中信银行',
  '光大': '光大银行',
  '华夏': '华夏银行',
  '邮储': '邮储银行',
  '农商': '农商银行',
  '信用社': '信用社',
  '网商': '网商银行',
  '微众': '微众银行',
  '平安': '平安银行',
}

function guessBank(name) {
  if (!name) return null
  for (const [keyword, bank] of Object.entries(BANK_KEYWORDS)) {
    if (name.includes(keyword)) return bank
  }
  return null
}

function viewDetail(t) {
  detailData.value = t
  showDetail.value = true
}

async function toggleStatus(tpl, status) {
  // 目前 template 没有 update API，这里通过后端预留
  alert('模板状态切换功能将在后续版本实现')
}

async function doCreate() {
  const f = form.value
  if (!f.template_name.trim()) { alert('请输入模板名称'); return }
  let mapping = {}
  try { mapping = JSON.parse(f.mapping_text || '{}') } catch { alert('映射 JSON 格式错误'); return }
  const sampleHeaders = f.sample_headers_text.split('\n').map(s => s.trim()).filter(Boolean)
  try {
    await api.createParserTemplate({
      template_name: f.template_name,
      template_type: 'bank',
      file_format: f.file_format,
      header_row: f.header_row,
      skip_rows: f.skip_rows,
      sample_headers: sampleHeaders,
      mapping_json: mapping,
    })
    showForm.value = false
    form.value = { template_name: '', file_format: 'xlsx', header_row: 0, skip_rows: 0, sample_headers_text: '', mapping_text: '' }
    await loadTemplates()
  } catch (e) { alert('创建失败: ' + e.message) }
}

onMounted(loadTemplates)
</script>

<style scoped>
@import './common.css';
.data-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.data-table th { text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--line); color: var(--muted); font-weight: 500; }
.data-table td { padding: 8px 10px; border-bottom: 1px solid #f0ede6; }
.badge { display: inline-block; padding: 2px 8px; border-radius: 8px; font-size: 11px; }
.badge.active { background: #edf4ea; color: #3f5b3d; }
.badge.disabled { background: #f5ece5; color: #8a6e52; }
.btn-sm { padding: 5px 10px; font-size: 12px; }

.tag-list { display: flex; flex-wrap: wrap; gap: 4px; }
.tag {
  display: inline-block; padding: 2px 8px; border-radius: 6px; font-size: 11px;
  background: #f0ede6; color: #5b635e;
}
.tag.more { background: #e2ded4; color: #8a6e52; }

.bank-tag {
  display: inline-block; padding: 3px 10px; border-radius: 8px; font-size: 12px;
  background: #edf4ea; color: #3f5b3d; font-weight: 500;
}

.modal-mask { position: fixed; inset: 0; background: rgba(0,0,0,0.35); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #faf8f3; border-radius: 16px; padding: 24px; width: 90%; max-width: 520px; box-shadow: 0 8px 32px rgba(0,0,0,0.18); }
.modal h3 { margin: 0 0 16px 0; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 13px; color: var(--muted); margin-bottom: 4px; }
.form-group .filter { width: 100%; box-sizing: border-box; }
.form-row { display: flex; gap: 12px; }
textarea.filter { font-family: inherit; resize: vertical; line-height: 1.6; }

.detail-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }
.field { background: #fff; border: 1px solid #e7e0d5; border-radius: 10px; padding: 10px 12px; }
.field .label { display: block; font-size: 12px; color: var(--muted); margin-bottom: 4px; }
</style>
