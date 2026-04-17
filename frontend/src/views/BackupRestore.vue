<template>
  <div class="section">
    <div class="section-title">
      <h3>备份恢复</h3>
      <button class="btn btn-primary" @click="doCreate" :disabled="creating">
        {{ creating ? '创建中...' : '创建备份' }}
      </button>
    </div>

    <div v-if="error" class="error-bar">{{ error }}</div>
    <div v-if="message" class="warning ok">{{ message }}</div>

    <table v-if="backups.length">
      <thead>
        <tr>
          <th>文件名</th>
          <th>大小</th>
          <th>创建时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="b in backups" :key="b.filename">
          <td>{{ b.filename }}</td>
          <td>{{ b.size_mb }} MB</td>
          <td>{{ b.created_at }}</td>
          <td>
            <button class="btn btn-warn btn-sm" @click="confirmRestore(b.filename)" :disabled="restoring">
              {{ restoring === b.filename ? '恢复中...' : '恢复' }}
            </button>
          </td>
        </tr>
      </tbody>
    </table>
    <div v-else class="empty-state">
      <div class="empty-icon">💾</div>
      <h4>暂无备份</h4>
      <p>点击"创建备份"生成第一份系统备份</p>
    </div>
  </div>

  <!-- 恢复确认弹窗 -->
  <div v-if="confirming" class="modal-overlay" @click.self="confirming = null">
    <div class="modal-box">
      <h3>确认恢复</h3>
      <p>将从 <strong>{{ confirming }}</strong> 恢复数据，当前数据库将被替换。</p>
      <p style="color: var(--warn-text); font-weight: 600;">此操作不可撤销，请确认！</p>
      <div class="btn-row" style="justify-content: flex-end; margin-top: 20px;">
        <button class="btn btn-secondary" @click="confirming = null">取消</button>
        <button class="btn btn-warn" @click="doRestore(confirming)">确认恢复</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listBackups, createBackup, restoreBackup } from '@/api/backup'

const backups = ref([])
const creating = ref(false)
const restoring = ref(null)
const confirming = ref(null)
const error = ref('')
const message = ref('')

onMounted(fetchList)

async function fetchList() {
  try {
    const data = await listBackups()
    backups.value = data?.items || []
  } catch (e) {
    error.value = '获取备份列表失败'
  }
}

async function doCreate() {
  creating.value = true
  error.value = ''
  message.value = ''
  try {
    const data = await createBackup()
    message.value = `备份已创建：${data.filename} (${data.size_mb} MB)`
    await fetchList()
  } catch (e) {
    error.value = e.message || '创建备份失败'
  } finally {
    creating.value = false
  }
}

function confirmRestore(filename) {
  confirming.value = filename
}

async function doRestore(filename) {
  confirming.value = null
  restoring.value = filename
  error.value = ''
  message.value = ''
  try {
    await restoreBackup(filename)
    message.value = `已从 ${filename} 恢复成功`
  } catch (e) {
    error.value = e.message || '恢复备份失败'
  } finally {
    restoring.value = null
  }
}
</script>

<style scoped>
@import './common.css';
.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: #fff; border-radius: var(--radius-lg); padding: 28px;
  max-width: 440px; width: 90%; box-shadow: 0 12px 40px rgba(0,0,0,.15);
}
.modal-box h3 { margin: 0 0 12px; font-size: var(--font-size-lg); }
.modal-box p { font-size: var(--font-size-sm); line-height: 1.8; margin: 6px 0; }
</style>
