<template>
  <div class="modal-mask" @click.self="$emit('close')">
    <div class="modal" style="max-width:520px">
      <div class="modal-header">
        <div class="modal-title">
          <span class="modal-icon">🤖</span>
          <h3>新建智能体</h3>
        </div>
        <p class="modal-desc">创建一个专属 AI 智能体，自定义名字、岗位职责和 AI 模型</p>
      </div>

      <div v-if="errMsg" class="error-bar">{{ errMsg }}</div>

      <div class="form-group">
        <label class="form-label">快速模板</label>
        <select v-model="selectedTemplate" class="filter" style="display:block" @change="applyTemplate">
          <option value="">自定义（空白）</option>
          <option value="cashier">出纳助手</option>
          <option value="analyst">报表分析师</option>
        </select>
        <p class="field-tip">选择模板自动填充名称和岗位职责</p>
      </div>

      <div class="form-group">
        <label class="form-label">智能体名称 <span class="required">*</span></label>
        <input
          v-model="form.display_name"
          class="filter"
          placeholder="如：财务总监、出纳助手、报表分析师"
          @keyup.enter="handleCreate"
        />
        <p class="field-tip">中文名称，将显示在左侧导航栏</p>
      </div>

      <div class="form-group">
        <label class="form-label">岗位职责</label>
        <textarea
          v-model="form.role_prompt"
          class="filter"
          style="height:90px;resize:vertical;display:block"
          placeholder="描述这个智能体应该做什么，如：&#10;你是公司的财务总监，负责审核资金日报、分析资金异常，提供专业的财务建议。"
        ></textarea>
        <p class="field-tip">作为智能体的系统提示词，决定其行为和回复风格</p>
      </div>

      <div class="form-group">
        <label class="form-label">AI 模型配置 <span class="required">*</span></label>
        <select v-model="form.ai_config_id" class="filter" style="display:block">
          <option value="">— 请选择 AI 配置 —</option>
          <option v-for="cfg in aiConfigs" :key="cfg.id" :value="cfg.id">
            {{ cfg.display_name }}（{{ cfg.provider }}{{ cfg.model_name ? ' · ' + cfg.model_name : '' }}）
          </option>
        </select>
        <p class="field-tip">选择已配置的 AI 模型，可在「系统设置 → 模型配置」中添加</p>
      </div>

      <div class="modal-footer">
        <button class="btn btn-secondary" @click="$emit('close')">取消</button>
        <button class="btn btn-primary" :disabled="loading" @click="handleCreate">
          {{ loading ? '创建中...' : '确认创建' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const emit = defineEmits(['close', 'created'])
const agentsStore = useAgentsStore()

const form = ref({
  display_name: '',
  role_prompt: '',
  ai_config_id: '',
})
const selectedTemplate = ref('')
const aiConfigs = ref([])
const loading = ref(false)
const errMsg = ref('')

const TEMPLATES = {
  cashier: {
    display_name: '出纳助手',
    role_prompt: '你是账房先生系统里的出纳助手，服务对象是普通财务人员（出纳、资金岗）。你擅长识别和解析各种银行的 Excel 流水文件，将它们转化为标准格式的资金流水数据。你还擅长根据流水数据生成现金日记账、资金日报等标准报表。\n\n工作方式：\n- 用户上传银行流水 → 你识别字段映射 → 生成预览 → 确认入库\n- 用户请求报表 → 你从业务数据中取数 → 按模板格式生成\n- 对不确定的信息主动提问，不猜测\n- 回复简洁专业，用财务语言沟通',
  },
  analyst: {
    display_name: '报表分析师',
    role_prompt: '你是账房先生系统里的报表分析师。你擅长分析资金流水数据，生成各类财务报表（资金日报、现金日记账、收支明细等），发现数据异常和趋势。\n\n工作方式：\n- 根据用户需求查询和分析 fund_events 数据\n- 按指定格式生成报表并导出 Excel\n- 主动指出数据中的异常和关注点\n- 回复简洁专业，突出关键数据',
  },
}

function applyTemplate() {
  const tpl = TEMPLATES[selectedTemplate.value]
  if (tpl) {
    form.value.display_name = tpl.display_name
    form.value.role_prompt = tpl.role_prompt
  }
}

onMounted(async () => {
  try {
    aiConfigs.value = await agentsStore.fetchAIConfigs()
    if (aiConfigs.value.length > 0) {
      form.value.ai_config_id = aiConfigs.value[0].id
    }
  } catch (e) {
    errMsg.value = '加载 AI 配置失败: ' + (e.message || '')
  }
})

async function handleCreate() {
  errMsg.value = ''
  if (!form.value.display_name.trim()) {
    errMsg.value = '请填写智能体名称'
    return
  }
  if (!form.value.ai_config_id) {
    errMsg.value = '请选择 AI 配置'
    return
  }
  loading.value = true
  try {
    const agent = await agentsStore.createAgent({
      display_name: form.value.display_name.trim(),
      role_prompt: form.value.role_prompt.trim(),
      ai_config_id: form.value.ai_config_id,
    })
    emit('created', agent)
  } catch (e) {
    errMsg.value = e.message || '创建失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
@import '@/views/common.css';

.modal-mask {
  position: fixed; inset: 0;
  background: rgba(0,0,0,0.35);
  display: flex; align-items: center; justify-content: center;
  z-index: 1000;
}
.modal {
  background: #faf8f3;
  border-radius: var(--radius-lg, 16px);
  padding: 28px 32px;
  width: 90%;
  max-width: 520px;
  box-shadow: 0 8px 32px rgba(0,0,0,0.18);
}
.modal-header {
  margin-bottom: 20px;
}
.modal-title {
  display: flex; align-items: center; gap: 10px;
}
.modal-title h3 {
  margin: 0;
  font-size: var(--font-size-lg, 18px);
  font-weight: 700;
}
.modal-icon {
  font-size: 24px;
}
.modal-desc {
  margin: 6px 0 0;
  font-size: var(--font-size-sm, 13px);
  color: var(--muted);
  line-height: 1.6;
}
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: var(--font-size-sm, 13px);
  color: var(--text-secondary);
  font-weight: 600;
  margin-bottom: 6px;
}
.form-group .filter {
  width: 100%;
  box-sizing: border-box;
}
.required {
  color: var(--warn-text, #9b3d2f);
}
.field-tip {
  margin: 5px 0 0;
  color: var(--muted);
  font-size: 12px;
  line-height: 1.5;
}
.modal-footer {
  display: flex; gap: 10px;
  justify-content: flex-end;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--line-soft, #e7e0d5);
}
</style>
