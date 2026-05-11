<template>
  <div class="section">
    <div class="section-title">
      <h3>系统维护</h3>
    </div>

    <div class="tabs-bar">
      <button class="tab-btn" :class="{ active: activeTab === 'backup' }" @click="activeTab = 'backup'">备份恢复</button>
      <button class="tab-btn" :class="{ active: activeTab === 'cleanup' }" @click="activeTab = 'cleanup'">数据清理</button>
    </div>

    <!-- 备份恢复 -->
    <div v-show="activeTab === 'backup'">
      <div v-if="backupError" class="error-bar">{{ backupError }}</div>
      <div v-if="backupMsg" class="warning ok">{{ backupMsg }}</div>

      <div class="backup-header">
        <NButton type="primary" size="small" @click="doCreate" :disabled="creating">
          {{ creating ? '创建中...' : '创建备份' }}
        </NButton>
      </div>

      <table v-if="backups.length" class="backup-table">
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
              <NButton type="warning" size="small" @click="confirmRestore(b.filename)" :disabled="restoring">
                {{ restoring === b.filename ? '恢复中...' : '恢复' }}
              </NButton>
            </td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty-state-sm">暂无备份，点击"创建备份"生成第一份</div>

      <div class="factory-section">
        <h4>恢复出厂设置</h4>
        <p>清空所有业务数据（流水、报表、日志），保留主数据配置。执行前自动创建备份。</p>
        <NButton type="warning" size="small" @click="confirmingFactory = true" :disabled="resetting">
          {{ resetting ? '执行中...' : '恢复出厂设置' }}
        </NButton>
      </div>
    </div>

    <!-- 数据清理 -->
    <div v-show="activeTab === 'cleanup'">
      <div v-if="cleanupError" class="error-bar">{{ cleanupError }}</div>
      <div v-if="cleanupMsg" class="warning ok">{{ cleanupMsg }}</div>

      <p class="section-desc">清除已删除的智能体、会话及其关联数据（消息、记忆、技能）。活跃数据不受影响。</p>

      <NButton secondary size="small" @click="loadPreview" :disabled="cleanupLoading" style="margin-bottom: 16px;">
        {{ cleanupLoading ? '扫描中...' : '扫描残留数据' }}
      </NButton>

      <div v-if="cleanupData">
        <div v-if="!cleanupData.summary.deleted_agents && !cleanupData.summary.deleted_sessions && !cleanupData.summary.draft_skills" class="cleanup-clean">
          <span>✅</span> 未发现残留数据，数据库很干净。
        </div>
        <template v-else>
          <div class="cleanup-summary">
            <span v-if="cleanupData.summary.deleted_agents" class="sum-tag agent-tag">已删除智能体 {{ cleanupData.summary.deleted_agents }} 个</span>
            <span v-if="cleanupData.summary.deleted_sessions" class="sum-tag session-tag">已删除会话 {{ cleanupData.summary.deleted_sessions }} 个</span>
            <span v-if="cleanupData.summary.linked_messages" class="sum-tag msg-tag">关联消息 {{ cleanupData.summary.linked_messages }} 条</span>
            <span v-if="cleanupData.summary.linked_memories" class="sum-tag mem-tag">关联记忆 {{ cleanupData.summary.linked_memories }} 条</span>
            <span v-if="cleanupData.summary.draft_skills" class="sum-tag skill-tag">草稿技能 {{ cleanupData.summary.draft_skills }} 个</span>
          </div>

          <div class="cleanup-detail">
            <div v-for="a in cleanupData.deleted_agents" :key="'a-'+a.id" class="cleanup-item">
              <span class="cleanup-type agent">智能体</span>
              <span class="cleanup-name">{{ a.display_name }} ({{ a.agent_code }})</span>
              <span class="cleanup-info">会话={{ a.sessions }} 消息={{ a.messages }} 记忆={{ a.memories }} 技能={{ a.skills }}</span>
            </div>
            <div v-for="s in cleanupData.deleted_sessions" :key="'s-'+s.id" class="cleanup-item">
              <span class="cleanup-type session">会话</span>
              <span class="cleanup-name">{{ s.agent_name }} / {{ s.title || '未命名' }}</span>
              <span class="cleanup-info">消息={{ s.messages }}</span>
            </div>
            <div v-for="sk in cleanupData.draft_skills" :key="'sk-'+sk.id" class="cleanup-item">
              <span class="cleanup-type skill">草稿技能</span>
              <span class="cleanup-name">{{ sk.display_name }} ({{ sk.skill_code }})</span>
            </div>
          </div>

          <NButton type="warning" size="small" @click="confirmingCleanup = true" style="margin-top: 12px;" :disabled="executing">
            {{ executing ? '清理中...' : '彻底清除以上数据' }}
          </NButton>
        </template>
      </div>
    </div>
  </div>

  <!-- 恢复确认 -->
  <div v-if="confirming" class="modal-overlay" @click.self="confirming = null">
    <div class="modal-box">
      <h3>确认恢复</h3>
      <p>将从 <strong>{{ confirming }}</strong> 恢复数据，当前数据库将被替换。</p>
      <p style="color: var(--warn-text); font-weight: 600;">此操作不可撤销！</p>
      <div class="btn-row">
        <NButton secondary @click="confirming = null">取消</NButton>
        <NButton type="warning" @click="doRestore(confirming)">确认恢复</NButton>
      </div>
    </div>
  </div>

  <!-- 恢复出厂确认 -->
  <div v-if="confirmingFactory" class="modal-overlay" @click.self="confirmingFactory = false">
    <div class="modal-box">
      <h3>确认恢复出厂设置</h3>
      <p>将清空以下业务数据：</p>
      <ul class="confirm-list">
        <li>资金流水记录</li>
        <li>导入批次记录</li>
        <li>日报生成记录</li>
        <li>操作日志</li>
      </ul>
      <p style="color: var(--warn-text); font-weight: 600;">主数据将被保留。执行前自动创建备份。</p>
      <div class="btn-row">
        <NButton secondary @click="confirmingFactory = false">取消</NButton>
        <NButton type="warning" @click="doFactoryReset">确认恢复出厂</NButton>
      </div>
    </div>
  </div>

  <!-- 清理确认 -->
  <div v-if="confirmingCleanup" class="modal-overlay" @click.self="confirmingCleanup = false">
    <div class="modal-box">
      <h3>确认清理数据</h3>
      <p>将彻底删除以下数据（不可恢复）：</p>
      <ul class="confirm-list">
        <li v-if="cleanupData?.summary?.deleted_agents">已删除智能体 {{ cleanupData.summary.deleted_agents }} 个（含其会话、消息、记忆、技能）</li>
        <li v-if="cleanupData?.summary?.deleted_sessions">已删除会话 {{ cleanupData.summary.deleted_sessions }} 个（含其消息）</li>
        <li v-if="cleanupData?.summary?.draft_skills">草稿技能 {{ cleanupData.summary.draft_skills }} 个</li>
      </ul>
      <p style="color: var(--warn-text, #c0392b); font-weight: 600;">活跃的智能体和数据不受影响。</p>
      <div class="btn-row">
        <NButton secondary @click="confirmingCleanup = false">取消</NButton>
        <NButton type="warning" @click="doCleanup">确认清理</NButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import { listBackups, createBackup, restoreBackup, factoryReset, getCleanupPreview, executeCleanup } from '@/api/backup'

const activeTab = ref('backup')

// --- 备份恢复 ---
const backups = ref([])
const creating = ref(false)
const restoring = ref(null)
const confirming = ref(null)
const confirmingFactory = ref(false)
const resetting = ref(false)
const backupError = ref('')
const backupMsg = ref('')

// --- 数据清理 ---
const cleanupData = ref(null)
const cleanupLoading = ref(false)
const executing = ref(false)
const confirmingCleanup = ref(false)
const cleanupError = ref('')
const cleanupMsg = ref('')

onMounted(fetchList)

async function fetchList() {
  try {
    const data = await listBackups()
    backups.value = data?.items || []
  } catch (e) {
    backupError.value = '获取备份列表失败'
  }
}

async function doCreate() {
  creating.value = true; backupError.value = ''; backupMsg.value = ''
  try {
    const data = await createBackup()
    backupMsg.value = `备份已创建：${data.filename} (${data.size_mb} MB)`
    await fetchList()
  } catch (e) { backupError.value = e.message || '创建备份失败' }
  finally { creating.value = false }
}

function confirmRestore(filename) { confirming.value = filename }

async function doRestore(filename) {
  confirming.value = null; restoring.value = filename; backupError.value = ''; backupMsg.value = ''
  try {
    await restoreBackup(filename)
    backupMsg.value = `已从 ${filename} 恢复成功`
  } catch (e) { backupError.value = e.message || '恢复备份失败' }
  finally { restoring.value = null }
}

async function doFactoryReset() {
  confirmingFactory.value = false; resetting.value = true; backupError.value = ''; backupMsg.value = ''
  try {
    const data = await factoryReset()
    backupMsg.value = `恢复出厂完成。已自动备份：${data.backup_file || '无'}`
    await fetchList()
  } catch (e) { backupError.value = e.message || '恢复出厂设置失败' }
  finally { resetting.value = false }
}

async function loadPreview() {
  cleanupLoading.value = true; cleanupError.value = ''; cleanupMsg.value = ''
  try { cleanupData.value = await getCleanupPreview() }
  catch (e) { cleanupError.value = e.message || '扫描残留数据失败' }
  finally { cleanupLoading.value = false }
}

async function doCleanup() {
  confirmingCleanup.value = false; executing.value = true; cleanupError.value = ''; cleanupMsg.value = ''
  try {
    const result = await executeCleanup()
    const parts = []
    if (result.agents) parts.push(`智能体 ${result.agents} 个`)
    if (result.sessions) parts.push(`会话 ${result.sessions} 个`)
    if (result.messages) parts.push(`消息 ${result.messages} 条`)
    if (result.memories) parts.push(`记忆 ${result.memories} 条`)
    if (result.skills || result.draft_skills) parts.push(`技能 ${(result.skills || 0) + (result.draft_skills || 0)} 个`)
    cleanupMsg.value = `清理完成：已清除 ${parts.join('、')}`
    await loadPreview()
  } catch (e) { cleanupError.value = e.message || '数据清理失败' }
  finally { executing.value = false }
}
</script>

<style scoped>
@import './common.css';

.tabs-bar {
  display: flex; gap: 0; margin-bottom: 20px;
  border-bottom: 2px solid var(--border, #ede8df);
}
.tab-btn {
  padding: 10px 24px; border: none; background: transparent;
  font-size: 14px; font-weight: 600; color: var(--text-light, #8c8680);
  cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px;
  transition: color .15s, border-color .15s; font-family: inherit;
}
.tab-btn:hover { color: var(--text, #333); }
.tab-btn.active {
  color: #7f9b7a; border-bottom-color: #7f9b7a;
}

.backup-header { margin-bottom: 16px; }
.backup-table { width: 100%; }
.backup-table th { text-align: left; }
.empty-state-sm {
  padding: 20px; text-align: center; color: var(--text-light, #8c8680);
  font-size: 13px; background: #faf8f3; border-radius: 8px; margin-bottom: 16px;
}

.factory-section {
  margin-top: 24px; padding: 16px 20px;
  border: 1px dashed var(--warn-border, #e8c9a0); border-radius: 8px;
  background: var(--warn-bg, #fef6ed);
}
.factory-section h4 { margin: 0 0 6px; font-size: 14px; color: var(--text); }
.factory-section p { margin: 0 0 12px; font-size: 13px; color: var(--text-light); }

.section-desc {
  font-size: 13px; color: var(--text-light, #8c8680); line-height: 1.6; margin: 0 0 16px;
}

.cleanup-clean {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 18px; background: #f2f7f0; border-radius: 8px;
  border: 1px solid #d7e5d4; font-size: 13px; color: #2f4330; font-weight: 600;
}
.cleanup-summary { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 12px; }
.sum-tag { padding: 4px 12px; border-radius: 16px; font-size: 12px; font-weight: 600; }
.agent-tag { background: #eef3ec; color: #2f4330; }
.session-tag { background: #eef5f8; color: #1a5a6a; }
.msg-tag { background: #f0ede5; color: #6b5d4a; }
.mem-tag { background: #f3f0fa; color: #5a4a7a; }
.skill-tag { background: #f5f0e4; color: #8a7a3a; }

.cleanup-detail { display: flex; flex-direction: column; gap: 6px; }
.cleanup-item {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 14px; background: #fff; border-radius: 6px;
  border: 1px solid var(--border, #ede8df); font-size: 13px;
}
.cleanup-item:hover { border-color: #b8ccb5; }
.cleanup-type { display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 11px; font-weight: 600; }
.cleanup-type.agent { background: #eef3ec; color: #2f4330; }
.cleanup-type.session { background: #eef5f8; color: #1a5a6a; }
.cleanup-type.skill { background: #f5f0e4; color: #8a7a3a; }
.cleanup-name { font-weight: 600; color: var(--text, #333); }
.cleanup-info { color: var(--text-light, #8c8680); margin-left: auto; }

.modal-overlay {
  position: fixed; inset: 0; background: rgba(0,0,0,.35);
  display: flex; align-items: center; justify-content: center; z-index: 100;
}
.modal-box {
  background: #fff; border-radius: var(--radius-lg); padding: 28px;
  max-width: 440px; width: 90%; box-shadow: 0 12px 40px rgba(0,0,0,.15);
}
.modal-box h3 { margin: 0 0 12px; }
.modal-box p { font-size: 13px; line-height: 1.8; margin: 6px 0; }
.confirm-list { font-size: 13px; line-height: 1.8; padding-left: 20px; color: var(--text-secondary, #666); }
.btn-row { display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px; }
</style>
