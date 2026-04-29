<template>
  <div class="file-panel">
    <div class="fp-head">
      <span class="fp-title">📁 工作区文件</span>
      <label class="fp-upload-btn" :disabled="uploading">
        {{ uploading ? '上传中...' : '上传' }}
        <input type="file" @change="handleUpload" hidden accept=".xlsx,.xls,.csv,.json,.txt" />
      </label>
    </div>
    <div class="fp-list">
      <div v-if="files.length === 0" class="fp-empty">
        暂无文件，点击上方上传
      </div>
      <div v-for="f in files" :key="f.path" class="fp-item">
        <span class="fp-icon">{{ f.is_dir ? '📂' : icon(f.name) }}</span>
        <span class="fp-name" :title="f.path">{{ f.name }}</span>
        <span v-if="!f.is_dir" class="fp-size">{{ fmtSize(f.size) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({ agentId: Number })
const store = useAgentsStore()

const files = ref([])
const uploading = ref(false)

onMounted(() => load())
watch(() => props.agentId, () => load())

async function load() {
  try {
    files.value = await store.listFiles(props.agentId, 'workspace')
  } catch { files.value = [] }
}

async function handleUpload(e) {
  const file = e.target.files[0]
  if (!file) return
  uploading.value = true
  try {
    await store.uploadFile(props.agentId, file, 'inbox')
    await load()
  } catch (err) {
    alert('上传失败: ' + (err.message || '未知错误'))
  } finally {
    uploading.value = false
    e.target.value = ''
  }
}

function icon(name) {
  const ext = name.split('.').pop().toLowerCase()
  const map = { xlsx: '📊', xls: '📊', csv: '📋', json: '🔧', txt: '📄', pdf: '📕' }
  return map[ext] || '📄'
}

function fmtSize(bytes) {
  if (!bytes) return '0B'
  if (bytes < 1024) return bytes + 'B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + 'K'
  return (bytes / 1024 / 1024).toFixed(1) + 'M'
}
</script>

<style scoped>
.file-panel {
  background: #fff;
  border-radius: 14px;
  border: 1px solid #e7e0d5;
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.fp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #ede8df;
  flex-shrink: 0;
}

.fp-title {
  font-size: 14px;
  font-weight: 700;
  color: #333;
}

.fp-upload-btn {
  padding: 5px 14px;
  border-radius: 8px;
  background: #eef3ec;
  color: #2f4330;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: background .15s;
  font-family: inherit;
}
.fp-upload-btn:hover { background: #d7e5d4; }
.fp-upload-btn[disabled] { opacity: .5; cursor: not-allowed; }

.fp-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.fp-empty {
  text-align: center;
  color: #aaa;
  font-size: 13px;
  padding: 32px 16px;
}

.fp-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 16px;
  font-size: 13px;
  color: #435046;
  transition: background .1s;
}
.fp-item:hover { background: #faf8f3; }

.fp-icon { flex-shrink: 0; font-size: 15px; }
.fp-name {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.fp-size { color: #aaa; font-size: 12px; flex-shrink: 0; }
</style>
