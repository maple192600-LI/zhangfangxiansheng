<template>
  <div class="skills-page">
    <div class="skills-main">
      <div class="skills-block">
        <div class="block-head">
          <h3>技能列表</h3>
          <div class="block-actions">
            <span class="block-count">{{ skills.length }} 个技能</span>
            <button class="btn-teach" @click="showTeachModal = true">教 agent 学新手艺</button>
          </div>
        </div>

        <!-- 教 agent 学新手艺弹窗 -->
        <div v-if="showTeachModal" class="result-overlay" @click.self="showTeachModal = false">
          <div class="teach-box">
            <div class="teach-head">
              <span>教 agent 学新手艺</span>
              <button class="btn-close" @click="showTeachModal = false">关闭</button>
            </div>
            <div class="teach-body">
              <div class="teach-field">
                <label>上传样本文件</label>
                <label class="teach-upload">
                  {{ teachFile ? teachFile.name : '点击选择文件（Excel/CSV）' }}
                  <input type="file" @change="onTeachFile" hidden accept=".xlsx,.xls,.csv" />
                </label>
              </div>
              <div class="teach-field">
                <label>描述目标</label>
                <textarea v-model="teachDesc" class="teach-textarea" rows="3"
                  placeholder="例如：识别中行流水的字段，输出标准 fund_event 行" />
              </div>
              <div class="teach-actions">
                <button class="btn-save" @click="startTeach" :disabled="!teachFile || !teachDesc.trim()">开始学习</button>
              </div>
            </div>
          </div>
        </div>

        <div v-if="skills.length === 0" class="skills-empty">
          <div class="empty-icon">⚡</div>
          <div class="empty-text">暂无可用技能</div>
          <div class="empty-hint">系统预置技能将自动出现在这里</div>
        </div>

        <div v-for="sk in skills" :key="sk.id" class="skill-card-wrapper">
          <div class="skill-card">
            <div class="skill-left" @click="toggleDetail(sk.skill_code)" style="cursor:pointer">
              <span class="skill-icon">⚡</span>
              <div class="skill-info">
                <div class="skill-name">
                  {{ sk.display_name }}
                  <span v-if="sk.is_global" class="tag tag-blue">全局</span>
                  <span :class="['tag', sk.status === 'verified' ? 'tag-green' : 'tag-yellow']">
                    {{ sk.status === 'verified' ? '已验证' : '草稿' }}
                  </span>
                  <span class="detail-toggle">{{ expandedDetail[sk.skill_code] ? '▴' : '▾' }}</span>
                </div>
                <div class="skill-desc">{{ sk.description || '无描述' }}</div>
              </div>
            </div>
            <div class="skill-meta">
              <span class="skill-code">{{ sk.skill_code }}</span>
              <div class="skill-btns">
                <button class="btn-run" @click="handleRun(sk)" :disabled="runningCode === sk.skill_code">运行</button>
                <button class="btn-test" @click="handleTest(sk)" :disabled="testingCode === sk.skill_code">测试</button>
              </div>
            </div>
          </div>
          <!-- 展开的详情 -->
          <div v-if="expandedDetail[sk.skill_code]" class="skill-detail">
            <div v-if="detailLoading[sk.skill_code]" class="detail-loading">加载中...</div>
            <div v-else-if="detailData[sk.skill_code]" class="detail-content">
              <div class="detail-meta">
                <span>测试通过: {{ detailData[sk.skill_code].test_pass_count || 0 }}</span>
                <span>测试失败: {{ detailData[sk.skill_code].test_fail_count || 0 }}</span>
              </div>
              <div v-if="detailData[sk.skill_code].run_py" class="detail-section">
                <div class="detail-label">源码 (run.py)</div>
                <pre class="detail-code">{{ detailData[sk.skill_code].run_py }}</pre>
              </div>
              <div v-if="detailData[sk.skill_code].manifest" class="detail-section">
                <div class="detail-label">配置 (manifest.yaml)</div>
                <pre class="detail-code">{{ detailData[sk.skill_code].manifest }}</pre>
              </div>
            </div>
          </div>
        </div>

        <!-- 运行/测试结果弹窗 -->
        <div v-if="resultModal" class="result-overlay" @click.self="resultModal = null">
          <div class="result-box">
            <div class="result-head">
              <span>{{ resultModal.title }}</span>
              <button class="btn-close" @click="resultModal = null">关闭</button>
            </div>
            <pre class="result-body" :class="{ 'result-ok': resultModal.ok, 'result-err': !resultModal.ok }">{{ resultModal.content }}</pre>
          </div>
        </div>
      </div>
    </div>

    <div class="skills-side">
      <div class="info-card">
        <div class="info-head">技能说明</div>
        <div class="tips">
          <p><strong>全局技能</strong>由系统预置，所有智能体均可使用。</p>
          <p><strong>自定义技能</strong>可由智能体在对话中自动创建，也可手动编写。</p>
          <p>技能通过 <code>skill_run</code> 工具执行。在聊天中输入类似指令即可触发：</p>
          <pre class="code-hint">"用招行解析技能解析 inbox 里的文件"</pre>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAgentsStore } from '@/stores/agents'
import http from '@/api'

const props = defineProps({ agentId: Number })
const emit = defineEmits(['start-teach'])
const store = useAgentsStore()
const skills = ref([])
const runningCode = ref('')
const testingCode = ref('')
const resultModal = ref(null)
const showTeachModal = ref(false)
const teachFile = ref(null)
const teachDesc = ref('')
const expandedDetail = ref({})
const detailData = ref({})
const detailLoading = ref({})

onMounted(() => load())
watch(() => props.agentId, () => load())

async function load() {
  try {
    skills.value = await store.listSkills(props.agentId)
  } catch { skills.value = [] }
}

async function handleRun(sk) {
  runningCode.value = sk.skill_code
  try {
    const res = await http.post(`/agent/agents/${props.agentId}/skill-run`, {
      skill_code: sk.skill_code,
    })
    const data = res
    resultModal.value = {
      title: `运行 ${sk.display_name}`,
      ok: data.ok !== false,
      content: JSON.stringify(data, null, 2),
    }
  } catch (e) {
    resultModal.value = {
      title: `运行 ${sk.display_name}`,
      ok: false,
      content: e.message || '运行失败',
    }
  }
  runningCode.value = ''
}

async function handleTest(sk) {
  testingCode.value = sk.skill_code
  try {
    const res = await http.post(`/agent/agents/${props.agentId}/skill-test`, {
      skill_code: sk.skill_code,
    })
    const data = res
    resultModal.value = {
      title: `测试 ${sk.display_name}`,
      ok: data.ok !== false,
      content: JSON.stringify(data, null, 2),
    }
  } catch (e) {
    resultModal.value = {
      title: `测试 ${sk.display_name}`,
      ok: false,
      content: e.message || '测试失败',
    }
  }
  testingCode.value = ''
}

function onTeachFile(e) {
  teachFile.value = e.target.files[0] || null
}

async function startTeach() {
  if (!teachFile.value || !teachDesc.value.trim()) return
  // 先上传样本文件到 inbox
  try {
    await store.uploadFile(props.agentId, teachFile.value, 'inbox')
  } catch {}
  // 通知父组件切换到聊天 tab 并发送学习指令
  const prompt = `请学习一个新的技能。我已经上传了样本文件 "${teachFile.value.name}" 到 inbox 目录。请先用 openpyxl_read 读取它，分析结构后编写一个解析技能。\n\n目标：${teachDesc.value.trim()}\n\n请用 skill_create 工具创建技能，并用 skill_test 验证。`
  showTeachModal.value = false
  teachFile.value = null
  teachDesc.value = ''
  emit('start-teach', prompt)
}

async function toggleDetail(skillCode) {
  expandedDetail.value = { ...expandedDetail.value, [skillCode]: !expandedDetail.value[skillCode] }
  if (expandedDetail.value[skillCode] && !detailData.value[skillCode]) {
    detailLoading.value = { ...detailLoading.value, [skillCode]: true }
    try {
      const data = await http.get(`/agent/agents/${props.agentId}/skills/${skillCode}`)
      detailData.value = { ...detailData.value, [skillCode]: data }
    } catch {
      detailData.value = { ...detailData.value, [skillCode]: { error: '加载失败' } }
    }
    detailLoading.value = { ...detailLoading.value, [skillCode]: false }
  }
}
</script>

<style scoped>
.skills-page {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  height: 100%;
  overflow-y: auto;
}

.skills-main { min-width: 0; }

.skills-block {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  padding: 24px 28px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid #ede8df;
}
.block-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #333; }
.block-actions {
  display: flex;
  align-items: center;
  gap: 14px;
}
.block-count { font-size: 13px; color: #aaa; }

.btn-teach {
  padding: 6px 16px;
  border-radius: 8px;
  background: #eef3ec;
  color: #2f4330;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #d7e5d4;
  font-family: inherit;
  transition: background .15s;
}
.btn-teach:hover { background: #d7e5d4; }

/* 教手艺弹窗 */
.teach-box {
  background: #fff;
  border-radius: 14px;
  padding: 24px;
  width: 480px;
  max-width: 90vw;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.teach-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 700;
  color: #333;
  margin-bottom: 20px;
}
.teach-field {
  margin-bottom: 16px;
}
.teach-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}
.teach-upload {
  display: block;
  padding: 10px 14px;
  border: 2px dashed #d7e5d4;
  border-radius: 10px;
  text-align: center;
  color: #6b726c;
  font-size: 13px;
  cursor: pointer;
  transition: border-color .15s;
}
.teach-upload:hover { border-color: #b8ccb5; color: #2f4330; }
.teach-textarea {
  width: 100%;
  box-sizing: border-box;
  padding: 10px 14px;
  border: 1px solid #e7e0d5;
  border-radius: 10px;
  font-size: 13px;
  font-family: inherit;
  resize: vertical;
  outline: none;
}
.teach-textarea:focus { border-color: #b8ccb5; }
.teach-actions {
  display: flex;
  justify-content: flex-end;
}
.teach-actions .btn-save {
  padding: 8px 24px;
  border-radius: 10px;
  background: #eef3ec;
  color: #2f4330;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid #d7e5d4;
  font-family: inherit;
}
.teach-actions .btn-save:hover { background: #d7e5d4; }
.teach-actions .btn-save[disabled] { opacity: .5; cursor: not-allowed; }

.skills-empty {
  text-align: center;
  padding: 40px 20px;
  color: #8c8680;
}
.empty-icon { font-size: 36px; opacity: .35; margin-bottom: 10px; }
.empty-text { font-size: 15px; font-weight: 600; color: #555; margin-bottom: 6px; }
.empty-hint { font-size: 13px; color: #aaa; }

.skill-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border: 1px solid #ede8df;
  border-radius: 12px;
  margin-bottom: 10px;
  transition: background .15s;
}
.skill-card:hover { background: #faf8f3; }

.skill-card-wrapper {
  margin-bottom: 10px;
}

.skill-detail {
  background: #faf8f3;
  border: 1px solid #ede8df;
  border-top: none;
  border-radius: 0 0 12px 12px;
  padding: 16px;
  margin-top: -2px;
}
.detail-loading { color: #aaa; font-size: 13px; text-align: center; padding: 12px; }
.detail-meta {
  display: flex;
  gap: 16px;
  font-size: 12px;
  color: #8c8680;
  margin-bottom: 12px;
}
.detail-section { margin-bottom: 12px; }
.detail-label {
  font-size: 12px;
  font-weight: 600;
  color: #555;
  margin-bottom: 6px;
}
.detail-code {
  background: #fff;
  border: 1px solid #e7e0d5;
  border-radius: 8px;
  padding: 12px;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  overflow-x: auto;
  max-height: 300px;
  overflow-y: auto;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.detail-toggle {
  font-size: 11px;
  color: #aaa;
  margin-left: 4px;
}

.skill-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.skill-icon {
  width: 38px; height: 38px;
  border-radius: 10px;
  background: #eef3ec;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}

.skill-info { min-width: 0; }
.skill-name {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  display: flex;
  align-items: center;
  gap: 6px;
}
.skill-desc {
  font-size: 13px;
  color: #8c8680;
  margin-top: 3px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 400px;
}

.skill-meta { flex-shrink: 0; display: flex; align-items: center; gap: 10px; }
.skill-code {
  font-family: monospace;
  font-size: 12px;
  color: #aaa;
  background: #f7f4ee;
  padding: 3px 10px;
  border-radius: 6px;
}
.skill-btns {
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity .15s;
}
.skill-card:hover .skill-btns { opacity: 1; }
.btn-run, .btn-test {
  padding: 4px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: 1px solid;
  font-family: inherit;
  transition: background .15s;
}
.btn-run {
  background: #eef3ec;
  color: #2f4330;
  border-color: #d7e5d4;
}
.btn-run:hover { background: #d7e5d4; }
.btn-run[disabled] { opacity: .5; cursor: not-allowed; }
.btn-test {
  background: #f5f0e4;
  color: #8a7a3a;
  border-color: #e0d8c5;
}
.btn-test:hover { background: #e0d8c5; }
.btn-test[disabled] { opacity: .5; cursor: not-allowed; }

/* 结果弹窗 */
.result-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}
.result-box {
  background: #fff;
  border-radius: 14px;
  padding: 24px;
  width: 520px;
  max-width: 90vw;
  max-height: 70vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 8px 32px rgba(0, 0, 0, 0.12);
}
.result-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 15px;
  font-weight: 700;
  color: #333;
  margin-bottom: 16px;
}
.btn-close {
  padding: 4px 12px;
  border-radius: 6px;
  background: #f7f4ee;
  color: #6b726c;
  font-size: 13px;
  cursor: pointer;
  border: 1px solid #e7e0d5;
  font-family: inherit;
}
.btn-close:hover { background: #ede8df; }
.result-body {
  flex: 1;
  overflow: auto;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  padding: 14px;
  border-radius: 8px;
  margin: 0;
  white-space: pre-wrap;
  word-break: break-word;
}
.result-ok { background: #f0f7ef; color: #2f4330; }
.result-err { background: #fdf2f2; color: #9b3b30; }

.tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
}
.tag-blue { background: #eef5f8; color: #1a7a8a; }
.tag-green { background: #eef3ec; color: #2f4330; }
.tag-yellow { background: #f5f0e4; color: #8a7a3a; }

/* 右侧信息 */
.skills-side {
  display: flex;
  flex-direction: column;
}

.info-card {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  padding: 22px 24px;
}

.info-head {
  font-size: 14px;
  font-weight: 700;
  color: #333;
  margin-bottom: 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #ede8df;
}

.tips {
  font-size: 13px;
  color: #6b726c;
  line-height: 1.8;
}
.tips p { margin: 0 0 10px; }
.tips strong { color: #333; }
.tips code {
  background: #f7f4ee;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}

.code-hint {
  background: #f7f4ee;
  border: 1px solid #e7e0d5;
  border-radius: 8px;
  padding: 8px 12px;
  font-size: 12px;
  color: #435046;
  margin-top: 6px;
}

@media (max-width: 900px) {
  .skills-page { grid-template-columns: 1fr; }
}
</style>
