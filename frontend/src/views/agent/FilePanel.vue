<template>
  <div
    class="file-panel"
    :class="{ 'fp-drag-over': dragOver }"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <!-- 文件列表视图 -->
    <div v-if="!editingFile" class="fp-browser">
      <div class="fp-head">
        <span class="fp-title">📁 工作区</span>
        <div class="fp-actions">
          <label class="fp-btn" :disabled="uploading">
            {{ uploading ? '上传中...' : '上传' }}
            <input type="file" @change="handleUpload" hidden multiple :accept="ACCEPT_EXTS" />
          </label>
        </div>
      </div>

      <!-- 拖拽提示层 -->
      <div v-if="dragOver" class="fp-drop-zone">
        <div class="drop-hint">
          <span class="drop-icon">📥</span>
          <span>释放文件以上传到工作区</span>
        </div>
      </div>

      <div class="fp-list">
        <div v-if="treeItems.length === 0" class="fp-empty">
          暂无文件，拖拽或点击上传
        </div>
        <div v-for="item in treeItems" :key="item.path">
          <div
            class="fp-item"
            :class="{ 'fp-draggable': !item.is_dir }"
            :style="{ paddingLeft: (item.depth * 16 + 12) + 'px' }"
            :draggable="!item.is_dir"
            @click="handleItemClick(item)"
            @dragstart="onDragStart($event, item)"
          >
            <span v-if="item.is_dir" class="fp-toggle">{{ expanded[item.path] ? '▾' : '▸' }}</span>
            <span v-else class="fp-toggle-space"></span>
            <span class="fp-icon">{{ item.is_dir ? (expanded[item.path] ? '📂' : '📁') : icon(item.name) }}</span>
            <span class="fp-name" :title="item.path">{{ item.name }}</span>
            <span v-if="!item.is_dir" class="fp-size">{{ fmtSize(item.size) }}</span>
            <div class="fp-item-btns" v-if="!item.is_dir">
              <NButton class="fp-btn-sm" quaternary @click.stop="openEditor(item)" title="编辑">✏️</NButton>
              <NButton class="fp-btn-sm fp-btn-del" quaternary @click.stop="handleDelete(item)" title="删除">🗑</NButton>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 文件编辑器视图 -->
    <div v-else class="fp-editor">
      <div class="fp-head">
        <NButton class="fp-btn" quaternary @click="closeEditor">← 返回</NButton>
        <span class="fp-path">{{ editingFile.path }}</span>
        <div class="fp-actions">
          <NButton class="fp-btn fp-btn-save" quaternary @click="handleSave" :disabled="saving">
            {{ saving ? '保存中...' : '💾 保存' }}
          </NButton>
        </div>
      </div>
      <textarea
        class="fp-textarea"
        v-model="editContent"
        spellcheck="false"
        placeholder="文件内容..."
      ></textarea>
      <div class="fp-status">
        {{ editDirty ? '● 有未保存的修改' : '✓ 已保存' }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { NButton } from 'naive-ui'
import { useAgentsStore } from '@/stores/agents'

const props = defineProps({ agentId: Number })
const store = useAgentsStore()

const ACCEPT_EXTS = '.xlsx,.xls,.csv,.pdf,.txt,.json,.yaml,.yml,.py,.md,.doc,.docx,.png,.jpg,.jpeg,.gif,.bmp,.webp,.tiff,.tif,.ppt,.pptx,.zip,.rar,.7z'

const files = ref([])
const expanded = ref({})
const uploading = ref(false)
const editingFile = ref(null)
const editContent = ref('')
const originalContent = ref('')
const saving = ref(false)
const editDirty = ref(false)
const dragOver = ref(false)

onMounted(() => load())
watch(() => props.agentId, () => { closeEditor(); load() })
watch(editContent, (v) => { editDirty.value = v !== originalContent.value })

const BINARY_EXTS = new Set(['xls', 'xlsx', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'bmp', 'ico', 'zip', 'rar', '7z', 'gz', 'tar', 'exe', 'dll', 'doc', 'docx', 'ppt', 'pptx'])

function isBinary(name) {
  const ext = name.split('.').pop().toLowerCase()
  return BINARY_EXTS.has(ext)
}

const treeItems = computed(() => {
  const dirPaths = new Set(files.value.filter(f => f.is_dir).map(f => f.path))
  const items = []
  for (const f of files.value) {
    const parts = f.path.split('/')
    if (parts.length <= 1) {
      items.push({ ...f, depth: 0 })
      continue
    }
    let visible = true
    let depth = 0
    for (let i = 0; i < parts.length - 1; i++) {
      const prefix = parts.slice(0, i + 1).join('/')
      if (dirPaths.has(prefix)) {
        if (!expanded.value[prefix]) {
          visible = false
          break
        }
        depth++
      }
    }
    if (visible) {
      items.push({ ...f, depth })
    }
  }
  return items
})

async function load() {
  try { files.value = await store.listFiles(props.agentId, 'workspace') }
  catch { files.value = [] }
}

async function uploadFiles(fileList) {
  if (!fileList || fileList.length === 0) return
  uploading.value = true
  let ok = 0
  let fail = 0
  for (const file of fileList) {
    try {
      await store.uploadFile(props.agentId, file, 'inbox')
      ok++
    } catch { fail++ }
  }
  uploading.value = false
  await load()
  if (fail > 0) alert(`${ok} 个文件上传成功，${fail} 个失败`)
}

function handleUpload(e) {
  uploadFiles(e.target.files)
  e.target.value = ''
}

let dragTimer = null
function onDragOver() {
  dragOver.value = true
  clearTimeout(dragTimer)
}
function onDragLeave() {
  clearTimeout(dragTimer)
  dragTimer = setTimeout(() => { dragOver.value = false }, 100)
}
function onDrop(e) {
  dragOver.value = false
  uploadFiles(e.dataTransfer.files)
}

async function openEditor(f) {
  if (isBinary(f.name)) {
    alert(`「${f.name}」是二进制文件，不支持文本编辑。请通过对话让 Agent 处理。`)
    return
  }
  try {
    const data = await store.readFile(props.agentId, f.path)
    editingFile.value = f
    editContent.value = data.content || ''
    originalContent.value = data.content || ''
    editDirty.value = false
  } catch (err) { alert('读取失败: ' + (err.message || '未知错误')) }
}

function closeEditor() {
  if (editDirty.value && !confirm('有未保存的修改，确定返回？')) return
  editingFile.value = null
  editContent.value = ''
  originalContent.value = ''
  editDirty.value = false
}

async function handleSave() {
  if (!editingFile.value) return
  saving.value = true
  try {
    await store.writeFile(props.agentId, editingFile.value.path, editContent.value)
    originalContent.value = editContent.value
    editDirty.value = false
    await load()
  } catch (err) { alert('保存失败: ' + (err.message || '未知错误')) }
  finally { saving.value = false }
}

async function handleDelete(f) {
  if (!confirm(`确定删除「${f.name}」？`)) return
  try {
    await store.deleteFile(props.agentId, f.path)
    await load()
  } catch (err) { alert('删除失败: ' + (err.message || '未知错误')) }
}

function onDragStart(e, item) {
  if (item.is_dir) return
  e.dataTransfer.setData('application/x-workspace-file', JSON.stringify({
    path: item.path,
    name: item.name
  }))
  e.dataTransfer.effectAllowed = 'copy'
}

function handleItemClick(item) {
  if (item.is_dir) {
    expanded.value = { ...expanded.value, [item.path]: !expanded.value[item.path] }
  } else {
    openEditor(item)
  }
}

function icon(name) {
  const ext = name.split('.').pop().toLowerCase()
  const map = { xlsx: '📊', xls: '📊', csv: '📋', pdf: '📕', json: '🔧', txt: '📄', py: '🐍', yaml: '⚙️', yml: '⚙️', md: '📝', doc: '📘', docx: '📘', png: '🖼', jpg: '🖼', jpeg: '🖼', gif: '🖼', bmp: '🖼', webp: '🖼', tiff: '🖼', tif: '🖼', ppt: '📊', pptx: '📊', zip: '📦', rar: '📦', '7z': '📦' }
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
  transition: border-color .2s, box-shadow .2s;
}
.file-panel.fp-drag-over {
  border-color: #7f9b7a;
  box-shadow: 0 0 0 3px rgba(127,155,122,.15);
}

.fp-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid #ede8df;
  flex-shrink: 0;
}
.fp-title { font-size: 14px; font-weight: 700; color: #333; }
.fp-path { font-size: 12px; color: #8c8680; font-family: monospace; flex: 1; margin: 0 12px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

.fp-actions { display: flex; gap: 8px; }

.fp-btn {
  padding: 5px 14px; border-radius: 8px; background: #eef3ec; color: #2f4330;
  font-size: 13px; font-weight: 600; cursor: pointer; border: 1px solid #d7e5d4;
  font-family: inherit; transition: background .15s;
}
.fp-btn:hover { background: #d7e5d4; }
.fp-btn[disabled] { opacity: .5; cursor: not-allowed; }
.fp-btn-save { background: #7f9b7a; color: #fff; border-color: #7f9b7a; }
.fp-btn-save:hover:not([disabled]) { background: #3d6b3a; }

/* 拖拽区域 */
.fp-drop-zone {
  position: absolute;
  inset: 0;
  background: rgba(238, 243, 236, 0.92);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  border-radius: 14px;
}
.drop-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  color: #2f4330;
  font-size: 14px;
  font-weight: 600;
}
.drop-icon { font-size: 32px; }

.fp-list { flex: 1; overflow-y: auto; padding: 4px 0; }
.fp-empty { text-align: center; color: #aaa; font-size: 13px; padding: 32px 16px; }

.fp-item {
  display: flex; align-items: center; gap: 6px; padding: 7px 12px;
  font-size: 13px; color: #435046; transition: background .1s; cursor: pointer;
}
.fp-item:hover { background: #faf8f3; }
.fp-item.fp-draggable { cursor: grab; }
.fp-item.fp-draggable:active { cursor: grabbing; }

.fp-toggle {
  flex-shrink: 0; width: 14px; text-align: center;
  font-size: 10px; color: #8c8680; cursor: pointer;
  user-select: none;
}
.fp-toggle-space { flex-shrink: 0; width: 14px; }

.fp-icon { flex-shrink: 0; font-size: 14px; }
.fp-name { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.fp-size { color: #aaa; font-size: 11px; flex-shrink: 0; }

.fp-item-btns { display: flex; gap: 4px; opacity: 0; transition: opacity .15s; }
.fp-item:hover .fp-item-btns { opacity: 1; }

.fp-btn-sm {
  padding: 2px 6px; border: none; border-radius: 4px; background: transparent;
  cursor: pointer; font-size: 13px; transition: background .15s;
}
.fp-btn-sm:hover { background: #f0ede5; }
.fp-btn-del:hover { background: #fdf2ef; }

/* 编辑器 */
.fp-editor { display: flex; flex-direction: column; height: 100%; }

.fp-textarea {
  flex: 1; padding: 16px; border: none; outline: none; resize: none;
  font-family: 'Consolas', 'Monaco', monospace; font-size: 13px; line-height: 1.6;
  color: #333; background: #faf8f3; tab-size: 2;
}

.fp-status {
  padding: 6px 16px; font-size: 12px; color: #8c8680; border-top: 1px solid #ede8df;
  background: #f7f4ee;
}
</style>
