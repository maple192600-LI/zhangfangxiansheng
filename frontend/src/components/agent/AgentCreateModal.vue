<template>
  <NModal
    :show="show"
    preset="card"
    title="新建智能体"
    style="width: 580px"
    :mask-closable="false"
    @update:show="handleUpdateShow"
  >
    <template #header>
      <div class="modal-title">
        <span class="modal-icon">🤖</span>
        <h3>新建智能体</h3>
      </div>
      <p class="modal-desc">创建一个专属 AI 智能体，自定义名字、岗位职责和 AI 模型</p>
    </template>

    <NForm label-placement="top">
      <NFormItem label="快速模板">
        <NSelect
          v-model:value="selectedTemplate"
          :options="templateOptions"
          @update:value="applyTemplate"
        />
      </NFormItem>

      <NFormItem label="智能体名称" required>
        <NInput
          v-model:value="form.display_name"
          placeholder="如：财务总监、出纳助手、报表分析师"
          @keyup.enter="handleCreate"
        />
      </NFormItem>

      <NFormItem label="岗位职责">
        <NInput
          v-model:value="form.role_prompt"
          type="textarea"
          :rows="4"
          placeholder="描述这个智能体应该做什么，如：&#10;你是公司的财务总监，负责审核资金日报、分析资金异常，提供专业的财务建议。"
        />
      </NFormItem>

      <NFormItem label="AI 模型配置" required>
        <NSelect
          v-model:value="form.ai_config_id"
          :options="aiConfigOptions"
          placeholder="请选择 AI 配置"
        />
      </NFormItem>
    </NForm>

    <template #footer>
      <NSpace justify="end">
        <NButton @click="emit('close')">取消</NButton>
        <NButton type="primary" :loading="loading" @click="handleCreate">确认创建</NButton>
      </NSpace>
    </template>
  </NModal>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { NModal, NForm, NFormItem, NInput, NSelect, NButton, NSpace, useMessage } from 'naive-ui'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({
  show: { type: Boolean, default: false }
})

const emit = defineEmits(['close', 'created'])
const agentsStore = useAgentsStore()
const message = useMessage()

const form = ref({
  display_name: '',
  role_prompt: '',
  ai_config_id: '',
})
const selectedTemplate = ref('')
const aiConfigs = ref([])
const loading = ref(false)

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

const templateOptions = [
  { label: '自定义（空白）', value: '' },
  { label: '出纳助手', value: 'cashier' },
  { label: '报表分析师', value: 'analyst' },
]

const aiConfigOptions = computed(() =>
  aiConfigs.value.map(cfg => ({
    label: `${cfg.display_name}（${cfg.provider}${cfg.model_name ? ' · ' + cfg.model_name : ''}）`,
    value: cfg.id,
  }))
)

function applyTemplate(value) {
  const tpl = TEMPLATES[value]
  if (tpl) {
    form.value.display_name = tpl.display_name
    form.value.role_prompt = tpl.role_prompt
  }
}

function handleUpdateShow(val) {
  if (!val) emit('close')
}

watch(() => props.show, async (newVal) => {
  if (newVal && aiConfigs.value.length === 0) {
    try {
      aiConfigs.value = await agentsStore.fetchAIConfigs()
      if (aiConfigs.value.length > 0) {
        form.value.ai_config_id = aiConfigs.value[0].id
      }
    } catch (e) {
      message.error('加载 AI 配置失败: ' + (e.message || ''))
    }
  }
})

async function handleCreate() {
  if (!form.value.display_name.trim()) {
    message.error('请填写智能体名称')
    return
  }
  if (!form.value.ai_config_id) {
    message.error('请选择 AI 配置')
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
    message.error(e.message || '创建失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
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
</style>
