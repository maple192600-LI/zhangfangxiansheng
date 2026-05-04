<template>
  <div class="memory-page">
    <div class="memory-main">
      <div class="memory-block">
        <div class="block-head">
          <h3>长期记忆</h3>
          <div class="block-actions">
            <span class="block-count">{{ memories.length }} 条记忆</span>
            <button class="btn-new" @click="startAdd">添加记忆</button>
          </div>
        </div>

        <!-- 新增/编辑表单 -->
        <div v-if="editForm.show" class="memory-add">
          <input v-model="editForm.key" class="add-input" placeholder="记忆标题" />
          <textarea v-model="editForm.content" class="add-textarea" rows="4" placeholder="记忆内容" />
          <div class="add-actions">
            <button class="btn-save" @click="handleSave" :disabled="saving">
              {{ saving ? '保存中...' : '保存' }}
            </button>
            <button class="btn-cancel" @click="cancelEdit">取消</button>
          </div>
        </div>

        <div v-if="memories.length === 0 && !editForm.show" class="memory-empty">
          <div class="empty-icon">🧠</div>
          <div class="empty-text">暂无记忆</div>
          <div class="empty-hint">智能体在对话中会自动积累记忆，也可手动添加</div>
        </div>

        <div v-for="m in memories" :key="m.id" class="memory-card">
          <div class="memory-head">
            <span class="memory-key">{{ m.key }}</span>
            <div class="memory-meta">
              <span v-if="m.source" class="tag">{{ m.source }}</span>
              <span class="memory-time">{{ fmtTime(m.last_used_at || m.created_at) }}</span>
              <button class="btn-edit" @click="startEdit(m)" title="编辑">✏️</button>
              <button class="btn-del" @click="handleDelete(m)" title="删除">🗑</button>
            </div>
          </div>
          <div class="memory-content">{{ m.content }}</div>
        </div>
      </div>
    </div>

    <div class="memory-side">
      <div class="info-card">
        <div class="info-head">记忆说明</div>
        <div class="tips">
          <p><strong>长期记忆</strong>是智能体跨会话保留的知识。</p>
          <p>智能体在对话中可自动保存重要信息，也可由用户手动添加。</p>
          <p>记忆会在每次对话时被智能体检索和参考。</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, watch } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({ agentId: Number })
const store = useAgentsStore()
const memories = ref([])
const saving = ref(false)

const editForm = reactive({
  show: false,
  id: null,
  key: '',
  content: '',
  isNew: false,
})

onMounted(() => load())
watch(() => props.agentId, () => load())

async function load() {
  try { memories.value = await store.listMemories(props.agentId) }
  catch { memories.value = [] }
}

function startAdd() {
  editForm.show = true
  editForm.id = null
  editForm.key = ''
  editForm.content = ''
  editForm.isNew = true
}

function startEdit(m) {
  editForm.show = true
  editForm.id = m.id
  editForm.key = m.key
  editForm.content = m.content
  editForm.isNew = false
}

function cancelEdit() {
  editForm.show = false
  editForm.id = null
  editForm.key = ''
  editForm.content = ''
  editForm.isNew = false
}

async function handleSave() {
  const key = editForm.key.trim()
  const content = editForm.content.trim()
  if (!key || !content) return
  saving.value = true
  try {
    if (editForm.isNew) {
      await store.saveMemory(props.agentId, key, content)
    } else {
      await store.updateMemory(props.agentId, editForm.id, key, content)
    }
    cancelEdit()
    await load()
  } catch (err) { alert('保存失败: ' + (err.message || '未知错误')) }
  finally { saving.value = false }
}

async function handleDelete(m) {
  if (!confirm(`确定删除记忆「${m.key}」？`)) return
  try { await store.deleteMemory(props.agentId, m.id); await load() }
  catch { }
}

function fmtTime(ts) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = n => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}
</script>

<style scoped>
.memory-page {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 20px;
  height: 100%;
  overflow-y: auto;
}

.memory-block {
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

.btn-new {
  padding: 6px 16px; border-radius: 8px; background: #eef3ec; color: #2f4330;
  font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid #d7e5d4;
  font-family: inherit; transition: background .15s;
}
.btn-new:hover { background: #d7e5d4; }

.memory-add {
  background: #faf8f3; border-radius: 12px; border: 1px solid #e7e0d5;
  padding: 16px; margin-bottom: 16px;
}
.add-input {
  width: 100%; box-sizing: border-box; padding: 8px 12px;
  border: 1px solid #e7e0d5; border-radius: 8px; font-size: 14px;
  font-family: inherit; margin-bottom: 8px; outline: none;
}
.add-input:focus { border-color: #b8ccb5; }
.add-textarea {
  width: 100%; box-sizing: border-box; padding: 8px 12px;
  border: 1px solid #e7e0d5; border-radius: 8px; font-size: 13px;
  font-family: inherit; resize: vertical; outline: none;
}
.add-textarea:focus { border-color: #b8ccb5; }
.add-actions { display: flex; gap: 8px; margin-top: 10px; justify-content: flex-end; }
.btn-save {
  padding: 6px 16px; border-radius: 8px; background: #7f9b7a; color: #fff;
  font-size: 13px; font-weight: 600; cursor: pointer; border: none; font-family: inherit;
}
.btn-save:hover:not(:disabled) { background: #3d6b3a; }
.btn-save:disabled { opacity: .5; cursor: not-allowed; }
.btn-cancel {
  padding: 6px 16px; border-radius: 8px; background: #fff; color: #8c8680;
  font-size: 13px; cursor: pointer; border: 1px solid #e7e0d5; font-family: inherit;
}
.btn-cancel:hover { background: #faf8f3; }

.memory-empty { text-align: center; padding: 40px 20px; color: #8c8680; }
.empty-icon { font-size: 36px; opacity: .35; margin-bottom: 10px; }
.empty-text { font-size: 15px; font-weight: 600; color: #555; margin-bottom: 6px; }
.empty-hint { font-size: 13px; color: #aaa; }

.memory-card {
  padding: 14px 16px; border: 1px solid #ede8df; border-radius: 12px; margin-bottom: 10px;
}
.memory-head {
  display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px;
}
.memory-key { font-size: 14px; font-weight: 600; color: #333; }
.memory-meta { display: flex; align-items: center; gap: 8px; }

.tag {
  display: inline-block; padding: 2px 8px; border-radius: 20px;
  font-size: 11px; font-weight: 600; background: #eef3ec; color: #2f4330;
}
.memory-time { font-size: 12px; color: #aaa; }

.btn-edit, .btn-del {
  padding: 2px 6px; border: none; border-radius: 4px; background: transparent;
  font-size: 13px; cursor: pointer; opacity: 0; transition: opacity .15s;
}
.memory-card:hover .btn-edit,
.memory-card:hover .btn-del { opacity: 1; }
.btn-edit:hover { background: #f0ede5; }
.btn-del { color: #c0392b; }
.btn-del:hover { background: #fdf2ef; }

.memory-content {
  font-size: 13px; color: #6b726c; line-height: 1.6;
  white-space: pre-wrap; word-break: break-word;
}

/* 右侧 */
.memory-side { display: flex; flex-direction: column; }
.info-card {
  background: #fff; border-radius: 14px; border: 1px solid #e7e0d5; padding: 22px 24px;
}
.info-head {
  font-size: 14px; font-weight: 700; color: #333; margin-bottom: 16px;
  padding-bottom: 10px; border-bottom: 1px solid #ede8df;
}
.tips { font-size: 13px; color: #6b726c; line-height: 1.8; }
.tips p { margin: 0 0 10px; }
.tips strong { color: #333; }

@media (max-width: 900px) { .memory-page { grid-template-columns: 1fr; } }
</style>
