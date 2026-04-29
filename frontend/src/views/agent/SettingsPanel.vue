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
          <select v-model="form.ai_config_id" class="inp">
            <option v-for="cfg in aiConfigs" :key="cfg.id" :value="cfg.id">
              {{ cfg.display_name }}（{{ cfg.provider }}{{ cfg.model_name ? ' · ' + cfg.model_name : '' }}）
            </option>
          </select>
          <span class="hint">可在「系统设置 → AI配置」中添加新的模型配置</span>
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
          <input v-model.number="form.llm_max_tokens" type="number" class="inp" min="256" max="65536" placeholder="4096" />
          <span class="hint">AI 单次回复的最大 token 数。较大的值允许更长的回复，但会增加耗时。</span>
        </div>

        <div class="sep"></div>

        <div class="actions">
          <button class="btn btn-del" @click="handleDelete">🗑 删除此智能体</button>
          <div style="flex:1"></div>
          <button class="btn btn-ghost" @click="resetForm">重置</button>
          <button class="btn btn-ok" :disabled="saving" @click="handleSave">
            {{ saving ? '保存中...' : '保存修改' }}
          </button>
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
import { ref, onMounted } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({ agent: Object })
const emit = defineEmits(['updated', 'deleted'])
const store = useAgentsStore()

const form = ref({ display_name: '', role_prompt: '', ai_config_id: '', llm_timeout: 300, llm_max_tokens: 4096 })
const aiConfigs = ref([])
const saving = ref(false)
const errMsg = ref('')
const okMsg = ref('')

onMounted(async () => {
  form.value = {
    display_name: props.agent.display_name,
    role_prompt: props.agent.role_prompt || '',
    ai_config_id: props.agent.ai_config_id,
    llm_timeout: props.agent.llm_timeout ?? 300,
    llm_max_tokens: props.agent.llm_max_tokens ?? 4096,
  }
  try { aiConfigs.value = await store.fetchAIConfigs() } catch {}
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
</style>
