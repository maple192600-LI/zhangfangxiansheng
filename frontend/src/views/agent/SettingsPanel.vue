<template>
  <div class="settings-page">
    <!-- 左侧：表单 -->
    <div class="settings-main">
      <div class="settings-block">
        <div class="block-head">
          <h3>基本设置</h3>
        </div>

        <div v-if="errMsg" class="msg-bar err">{{ errMsg }}</div>
        <div v-if="okMsg" class="msg-bar ok">{{ okMsg }}</div>

        <div class="row">
          <label>智能体名称</label>
          <input v-model="form.display_name" class="inp" placeholder="如：财务总监" />
        </div>

        <div class="row">
          <label>岗位职责（System Prompt）</label>
          <textarea v-model="form.role_prompt" class="inp textarea" placeholder="描述这个智能体应该做什么，它的专业领域、行为风格、擅长的任务..."></textarea>
          <span class="hint">作为系统提示词注入，决定智能体的回复风格和能力边界</span>
        </div>

        <div class="row">
          <label>AI 模型配置</label>
          <NSelect v-model:value="form.ai_config_id" :options="aiConfigOptions" placeholder="选择模型配置" class="inp" />
          <span class="hint">可在「系统设置 → 模型配置」中添加新的模型配置</span>
        </div>

        <div class="sep"></div>

        <div class="block-head">
          <h3>运行参数</h3>
        </div>

        <div class="row">
          <label>LLM 超时时间（秒）</label>
          <input v-model.number="form.llm_timeout" type="number" class="inp" min="10" max="3600" placeholder="300" />
          <span class="hint">单次 AI 调用的最大等待时间，建议 120~600 秒。本地大模型推理较慢时可适当调大。</span>
        </div>

        <div class="row">
          <label>最大输出 Token</label>
          <div class="token-presets">
            <NButton v-for="p in tokenPresets" :key="p.value"
              class="preset-btn" :class="{ active: form.llm_max_tokens === p.value }"
              quaternary @click="form.llm_max_tokens = p.value" :title="p.desc">
              {{ p.label }}
            </NButton>
          </div>
          <input v-model.number="form.llm_max_tokens" type="number" class="inp" min="1024" max="524288" />
          <span class="hint">单次回复的最大输出 token 数（非上下文窗口）。值太小会导致回复被截断（Agent 半路断掉）。请根据所选用模型的支持范围合理设置。</span>
        </div>

        <div class="sep"></div>

        <div class="block-head">
          <h3>工具权限</h3>
        </div>

        <div v-if="toolsetsLoading" style="color:#aaa;font-size:13px">加载中...</div>
        <div v-else class="tool-grid">
          <div v-for="(tools, group) in toolsets" :key="group" class="tool-group">
            <div class="tool-group-head">
              <span class="tool-group-name">{{ groupLabel(group) }}</span>
              <label class="toggle-label">
                <input type="checkbox" :checked="isGroupEnabled(group)" @change="toggleGroup(group, $event.target.checked)" />
                <span>{{ isGroupEnabled(group) ? '已启用' : '已禁用' }}</span>
              </label>
            </div>
            <div class="tool-list">
              <div v-for="tool in tools" :key="tool" class="tool-item" :class="getToolClass(tool)">
                <span class="tool-name">{{ tool }}</span>
                <NSelect :value="getToolPerm(tool)" :options="toolPermOptions" size="tiny" style="width:80px" @update:value="v => setToolPerm(tool, v)" />
              </div>
            </div>
          </div>
        </div>

        <div class="sep"></div>

        <div class="actions">
          <NButton class="btn btn-del" quaternary @click="handleDelete">🗑 删除此智能体</NButton>
          <div style="flex:1"></div>
          <NButton class="btn btn-ghost" quaternary @click="resetForm">重置</NButton>
          <NButton class="btn btn-ok" quaternary :disabled="saving" @click="handleSave">
            {{ saving ? '保存中...' : '保存修改' }}
          </NButton>
        </div>
      </div>
    </div>

    <!-- 右侧：信息卡 -->
    <div class="settings-side">
      <div class="info-card">
        <div class="info-head">智能体信息</div>
        <div class="info-rows">
          <div class="info-row">
            <span class="info-label">创建时间</span>
            <span class="info-val">{{ fmtTime(agent?.created_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">最近更新</span>
            <span class="info-val">{{ fmtTime(agent?.updated_at) }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">编码</span>
            <span class="info-val mono">{{ agent?.agent_code }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">AI 提供商</span>
            <span class="info-val">{{ agent?.ai_config?.provider || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">模型</span>
            <span class="info-val">{{ agent?.ai_config?.model_name || '-' }}</span>
          </div>
          <div class="info-row">
            <span class="info-label">状态</span>
            <span class="tag tag-green">启用</span>
          </div>
        </div>
      </div>

      <div class="info-card" style="margin-top:16px">
        <div class="info-head">快速说明</div>
        <div class="tips">
          <p><strong>岗位职责</strong>是智能体最核心的配置——它决定了 AI 的专业方向和回复风格。</p>
          <p><strong>AI 模型</strong>决定智能体的推理能力。本地 Ollama 免费且隐私安全，云端模型通常更聪明。</p>
          <p>删除智能体后，相关会话记录将一并删除且不可恢复。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { NSelect, NButton } from 'naive-ui'
import { useAgentsStore } from '@/stores/agents'
import http from '@/api'

const props = defineProps({ agent: Object })
const emit = defineEmits(['updated', 'deleted'])
const store = useAgentsStore()

const form = ref({ display_name: '', role_prompt: '', ai_config_id: '', llm_timeout: 300, llm_max_tokens: 4096 })
const aiConfigs = ref([])
const aiConfigOptions = computed(() => aiConfigs.value.map(cfg => ({
  label: `${cfg.display_name}（${cfg.provider}${cfg.model_name ? ' · ' + cfg.model_name : ''}）`,
  value: cfg.id
})))
const toolPermOptions = [
  { label: '允许', value: 'allowed' },
  { label: '需确认', value: 'confirm' },
  { label: '禁用', value: 'disabled' },
]
const saving = ref(false)
const errMsg = ref('')
const okMsg = ref('')
const toolsets = ref({})
const toolsetsLoading = ref(true)
const permissions = ref({ allowed_tools: [], needs_user_confirm: [], disabled_toolsets: [] })

const GROUP_LABELS = {
  file: '文件操作', parse: '文件解析', shell: '脚本执行',
  database: '数据库', excel: 'Excel', skill: '技能管理',
  memory: '记忆', agent: '交互',
}

function groupLabel(g) { return GROUP_LABELS[g] || g }

function getToolPerm(tool) {
  if (permissions.value.allowed_tools?.includes(tool)) return 'allowed'
  if (permissions.value.needs_user_confirm?.includes(tool)) return 'confirm'
  return 'disabled'
}

function getToolClass(tool) {
  const p = getToolPerm(tool)
  return p === 'allowed' ? 'tool-allowed' : p === 'confirm' ? 'tool-confirm' : 'tool-disabled'
}

function setToolPerm(tool, val) {
  const perms = { ...permissions.value }
  perms.allowed_tools = (perms.allowed_tools || []).filter(t => t !== tool)
  perms.needs_user_confirm = (perms.needs_user_confirm || []).filter(t => t !== tool)
  if (val === 'allowed') perms.allowed_tools = [...perms.allowed_tools, tool]
  else if (val === 'confirm') perms.needs_user_confirm = [...perms.needs_user_confirm, tool]
  permissions.value = perms
  savePermissions()
}

function isGroupEnabled(group) {
  const tools = toolsets.value[group] || []
  if (permissions.value.disabled_toolsets?.includes(group)) return false
  return tools.some(t => getToolPerm(t) !== 'disabled')
}

function toggleGroup(group, enabled) {
  const perms = { ...permissions.value }
  perms.disabled_toolsets = (perms.disabled_toolsets || []).filter(g => g !== group)
  const tools = toolsets.value[group] || []
  if (enabled) {
    tools.forEach(t => {
      if (!perms.allowed_tools.includes(t) && !perms.needs_user_confirm.includes(t)) {
        perms.allowed_tools = [...perms.allowed_tools, t]
      }
    })
  } else {
    perms.allowed_tools = perms.allowed_tools.filter(t => !tools.includes(t))
    perms.needs_user_confirm = perms.needs_user_confirm.filter(t => !tools.includes(t))
    perms.disabled_toolsets = [...(perms.disabled_toolsets || []), group]
  }
  permissions.value = perms
  savePermissions()
}

async function savePermissions() {
  try {
    await http.put(`/agent/agents/${props.agent.id}/permissions`, permissions.value)
  } catch {}
}

const tokenPresets = [
  { label: '4K', value: 4096, desc: '本地部署模型适用' },
  { label: '16K', value: 16384, desc: '日常简单对话够用' },
  { label: '32K', value: 32768, desc: '复杂任务，Agent 多轮工具调用推荐' },
  { label: '64K', value: 65536, desc: '长文生成、复杂 Agent 任务' },
  { label: '128K', value: 131072, desc: '超长生成' },
  { label: '384K', value: 393216, desc: '极限输出' },
]

onMounted(async () => {
  form.value = {
    display_name: props.agent.display_name,
    role_prompt: props.agent.role_prompt || '',
    ai_config_id: props.agent.ai_config_id,
    llm_timeout: props.agent.llm_timeout ?? 300,
    llm_max_tokens: props.agent.llm_max_tokens ?? 4096,
  }
  try { aiConfigs.value = await store.fetchAIConfigs() } catch {}
  try {
    const [toolsData, permData] = await Promise.all([
      http.get('/agent/tools/list'),
      http.get(`/agent/agents/${props.agent.id}/permissions`),
    ])
    toolsets.value = toolsData.toolsets || {}
    permissions.value = permData || { allowed_tools: [], needs_user_confirm: [], disabled_toolsets: [] }
  } catch {}
  toolsetsLoading.value = false
})

function resetForm() {
  form.value = {
    display_name: props.agent.display_name,
    role_prompt: props.agent.role_prompt || '',
    ai_config_id: props.agent.ai_config_id,
    llm_timeout: props.agent.llm_timeout ?? 300,
    llm_max_tokens: props.agent.llm_max_tokens ?? 4096,
  }
  errMsg.value = ''; okMsg.value = ''
}

async function handleSave() {
  errMsg.value = ''; okMsg.value = ''
  if (!form.value.display_name.trim()) { errMsg.value = '名称不能为空'; return }
  saving.value = true
  try {
    await store.updateAgent(props.agent.id, {
      display_name: form.value.display_name.trim(),
      role_prompt: form.value.role_prompt,
      ai_config_id: form.value.ai_config_id,
      llm_timeout: form.value.llm_timeout,
      llm_max_tokens: form.value.llm_max_tokens,
    })
    okMsg.value = '保存成功'; emit('updated')
    setTimeout(() => { okMsg.value = '' }, 2000)
  } catch (e) { errMsg.value = e.message || '保存失败' }
  finally { saving.value = false }
}

async function handleDelete() {
  if (!confirm(`确定要删除智能体「${props.agent.display_name}」吗？\n此操作不可恢复。`)) return
  try { await store.deleteAgent(props.agent.id); emit('deleted') }
  catch (e) { errMsg.value = e.message || '删除失败' }
}

function fmtTime(iso) {
  if (!iso) return '-'
  return iso.replace('T', ' ').slice(0, 19)
}
</script>

<style scoped>
.settings-page {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 20px;
  height: 100%;
  overflow-y: auto;
  padding: 0;
}

/* 左侧表单 */
.settings-main {
  min-width: 0;
}

.settings-block {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  padding: 28px 32px;
}

.block-head {
  margin-bottom: 22px;
  padding-bottom: 14px;
  border-bottom: 1px solid #ede8df;
}
.block-head h3 { margin: 0; font-size: 16px; font-weight: 700; color: #333; }

.msg-bar {
  padding: 10px 14px; border-radius: 10px; font-size: 13px; margin-bottom: 16px;
}
.msg-bar.err { background: #fdf2ef; border: 1px solid #e0b8ad; color: #9b3d2f; }
.msg-bar.ok { background: #f0faf0; border: 1px solid #d4e8d4; color: #2f5e2e; }

.row { margin-bottom: 20px; }
.row label {
  display: block; font-size: 13px; font-weight: 600; color: #6b726c; margin-bottom: 8px;
}
.inp {
  width: 100%; padding: 10px 16px;
  border: 1px solid #e7e0d5; border-radius: 10px;
  font-size: 14px; color: #333; background: #f7f4ee;
  outline: none; font-family: inherit; box-sizing: border-box;
  transition: border-color .2s, box-shadow .2s;
}
.inp:focus { border-color: #7f9b7a; box-shadow: 0 0 0 3px rgba(127,155,122,.12); }
.textarea { min-height: 140px; max-height: 300px; resize: vertical; line-height: 1.6; }

.hint { display: block; font-size: 12px; color: #aaa; margin-top: 6px; line-height: 1.5; }

.token-presets {
  display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px;
}
.preset-btn {
  padding: 5px 14px; border: 1px solid #e7e0d5; border-radius: 8px;
  background: #f7f4ee; color: #435046; font-size: 12px; cursor: pointer;
  font-family: inherit; transition: all .15s;
}
.preset-btn:hover { border-color: #7f9b7a; background: #eef3ec; }
.preset-btn.active { background: #7f9b7a; color: #fff; border-color: #7f9b7a; font-weight: 600; }

.sep { height: 1px; background: #ede8df; margin: 24px 0; }

.actions { display: flex; gap: 10px; align-items: center; }

.btn {
  border: none; border-radius: 10px; padding: 9px 22px;
  cursor: pointer; font-size: 14px; font-family: inherit; transition: all .15s;
}
.btn-ghost { background: #f7f4ee; color: #435046; border: 1px solid #e7e0d5; }
.btn-ghost:hover { background: #f0ede5; }
.btn-ok { background: #7f9b7a; color: #fff; font-weight: 600; }
.btn-ok:hover:not(:disabled) { background: #3d6b3a; }
.btn-ok:disabled { opacity: .45; cursor: not-allowed; }
.btn-del {
  border: 1px solid #e0b8ad; border-radius: 10px; padding: 9px 18px;
  background: transparent; color: #9b3d2f; font-size: 14px; cursor: pointer;
  font-family: inherit; transition: all .15s;
}
.btn-del:hover { background: #fdf2ef; }

/* 右侧信息 */
.settings-side {
  display: flex;
  flex-direction: column;
  gap: 0;
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

.info-rows {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}
.info-label { color: #8c8680; }
.info-val { color: #333; font-weight: 500; }
.mono { font-family: monospace; font-size: 12px; }

.tag {
  display: inline-block; padding: 3px 10px; border-radius: 20px;
  font-size: 12px; font-weight: 600;
}
.tag-green { background: #eef3ec; color: #2f4330; }

.tips {
  font-size: 13px;
  color: #6b726c;
  line-height: 1.8;
}
.tips p { margin: 0 0 10px; }
.tips strong { color: #333; }

@media (max-width: 900px) {
  .settings-page {
    grid-template-columns: 1fr;
  }
}

.tool-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
}
.tool-group {
  border: 1px solid #ede8df;
  border-radius: 10px;
  padding: 12px;
}
.tool-group-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid #ede8df;
}
.tool-group-name {
  font-size: 13px;
  font-weight: 600;
  color: #333;
}
.toggle-label {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #8c8680;
  cursor: pointer;
}
.toggle-label input { cursor: pointer; }
.tool-list { display: flex; flex-direction: column; gap: 4px; }
.tool-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 12px;
}
.tool-allowed { background: #eef3ec; color: #2f4330; }
.tool-confirm { background: #f5f0e4; color: #8a7a3a; }
.tool-disabled { background: #f7f4ee; color: #aaa; }
.tool-name { font-family: monospace; font-size: 11px; }
.tool-perm-select {
  border: 1px solid #e7e0d5;
  border-radius: 4px;
  font-size: 11px;
  padding: 2px 4px;
  background: #fff;
  cursor: pointer;
  font-family: inherit;
}

@media (max-width: 900px) {
  .tool-grid { grid-template-columns: 1fr; }
}
</style>
