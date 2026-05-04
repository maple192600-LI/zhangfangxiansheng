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

    <!-- 恢复出厂设置 -->
    <div class="factory-section">
      <h4 style="margin: 0 0 6px; color: var(--text);">恢复出厂设置</h4>
      <p style="margin: 0 0 12px; font-size: 13px; color: var(--text-light);">清空所有业务数据（流水、报表、日志），保留主数据配置。执行前自动创建备份。</p>
      <button class="btn btn-warn" @click="confirmingFactory = true" :disabled="resetting">
        {{ resetting ? '执行中...' : '恢复出厂设置' }}
      </button>
    </div>

    <!-- 数据清理 -->
    <div class="cleanup-section">
      <h4 style="margin: 0 0 6px; color: var(--text);">数据清理</h4>
      <p style="margin: 0 0 12px; font-size: 13px; color: var(--text-light);">清除已删除的智能体、会话及其关联数据（消息、记忆、技能）。开发测试阶段的残留数据会被彻底移除。</p>
      <button class="btn btn-secondary" @click="loadCleanupPreview" :disabled="loadingCleanup">
        {{ loadingCleanup ? '扫描中...' : '扫描残留数据' }}
      </button>

      <div v-if="cleanupData" class="cleanup-result">
        <div v-if="cleanupData.summary.deleted_agents === 0 && cleanupData.summary.deleted_sessions === 0 && cleanupData.summary.draft_skills === 0" class="cleanup-empty">
          未发现残留数据，数据库很干净。
        </div>
        <template v-else>
          <div class="cleanup-summary">
            <span v-if="cleanupData.summary.deleted_agents">已删除智能体: {{ cleanupData.summary.deleted_agents }} 个</span>
            <span v-if="cleanupData.summary.deleted_sessions">已删除会话: {{ cleanupData.summary.deleted_sessions }} 个</span>
            <span v-if="cleanupData.summary.linked_messages">关联消息: {{ cleanupData.summary.linked_messages }} 条</span>
            <span v-if="cleanupData.summary.linked_memories">关联记忆: {{ cleanupData.summary.linked_memories }} 条</span>
            <span v-if="cleanupData.summary.draft_skills">草稿技能: {{ cleanupData.summary.draft_skills }} 个</span>
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

          <button class="btn btn-warn" @click="confirmingCleanup = true" style="margin-top: 12px;">
            彻底清除以上数据
          </button>
        </template>
      </div>
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

  <!-- 恢复出厂确认弹窗 -->
  <div v-if="confirmingFactory" class="modal-overlay" @click.self="confirmingFactory = false">
    <div class="modal-box">
      <h3>确认恢复出厂设置</h3>
      <p>将清空以下业务数据：</p>
      <ul style="font-size: 13px; line-height: 1.8; padding-left: 20px; color: var(--text-secondary);">
        <li>资金流水记录（fund_events）</li>
        <li>导入批次记录（import_batches）</li>
        <li>日报生成记录（daily_report_runs）</li>
        <li>操作日志（operation_logs）</li>
      </ul>
      <p style="color: var(--warn-text); font-weight: 600;">主数据（单位、账户、模板等）将被保留。执行前自动创建备份。</p>
      <div class="btn-row" style="justify-content: flex-end; margin-top: 20px;">
        <button class="btn btn-secondary" @click="confirmingFactory = false">取消</button>
        <button class="btn btn-warn" @click="doFactoryReset">确认恢复出厂</button>
      </div>
    </div>
  </div>

  <!-- 数据清理确认弹窗 -->
  <div v-if="confirmingCleanup" class="modal-overlay" @click.self="confirmingCleanup = false">
    <div class="modal-box">
      <h3>确认清理数据</h3>
      <p>将彻底删除以下数据（不可恢复）：</p>
      <ul style="font-size: 13px; line-height: 1.8; padding-left: 20px; color: var(--text-secondary, #666);">
        <li v-if="cleanupData?.summary?.deleted_agents">已删除智能体 {{ cleanupData.summary.deleted_agents }} 个（含其会话、消息、记忆、技能）</li>
        <li v-if="cleanupData?.summary?.deleted_sessions">已删除会话 {{ cleanupData.summary.deleted_sessions }} 个（含其消息）</li>
        <li v-if="cleanupData?.summary?.draft_skills">草稿技能 {{ cleanupData.summary.draft_skills }} 个</li>
      </ul>
      <p style="color: var(--warn-text, #c0392b); font-weight: 600;">活跃的智能体和数据不受影响。</p>
      <div class="btn-row" style="justify-content: flex-end; margin-top: 20px;">
        <button class="btn btn-secondary" @click="confirmingCleanup = false">取消</button>
        <button class="btn btn-warn" @click="doCleanup">确认清理</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { listBackups, createBackup, restoreBackup, factoryReset, getCleanupPreview, executeCleanup } from '@/api/backup'

const backups = ref([])
const creating = ref(false)
const restoring = ref(null)
const confirming = ref(null)
const confirmingFactory = ref(false)
const confirmingCleanup = ref(false)
const resetting = ref(false)
const error = ref('')
const message = ref('')
const cleanupData = ref(null)
const loadingCleanup = ref(false)

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

async function doFactoryReset() {
  confirmingFactory.value = false
  resetting.value = true
  error.value = ''
  message.value = ''
  try {
    const data = await factoryReset()
    message.value = `恢复出厂完成。已自动备份：${data.backup_file || '无'}`
    await fetchList()
  } catch (e) {
    error.value = e.message || '恢复出厂设置失败'
  } finally {
    resetting.value = false
  }
}

async function loadCleanupPreview() {
  loadingCleanup.value = true
  error.value = ''
  try {
    cleanupData.value = await getCleanupPreview()
  } catch (e) {
    error.value = e.message || '扫描残留数据失败'
  } finally {
    loadingCleanup.value = false
  }
}

async function doCleanup() {
  confirmingCleanup.value = false
  resetting.value = true
  error.value = ''
  message.value = ''
  try {
    const result = await executeCleanup()
    const parts = []
    if (result.agents) parts.push(`智能体 ${result.agents} 个`)
    if (result.sessions) parts.push(`会话 ${result.sessions} 个`)
    if (result.messages) parts.push(`消息 ${result.messages} 条`)
    if (result.memories) parts.push(`记忆 ${result.memories} 条`)
    if (result.skills || result.draft_skills) parts.push(`技能 ${(result.skills || 0) + (result.draft_skills || 0)} 个`)
    message.value = `清理完成：已清除 ${parts.join('、')}`
    cleanupData.value = null
  } catch (e) {
    error.value = e.message || '数据清理失败'
  } finally {
    resetting.value = false
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

.factory-section {
  margin-top: 24px;
  padding: 18px 20px;
  border: 1px dashed var(--warn-border, #e8c9a0);
  border-radius: var(--radius, 8px);
  background: var(--warn-bg, #fef6ed);
}

.cleanup-section {
  margin-top: 24px;
  padding: 18px 20px;
  border: 1px dashed #b8ccb5;
  border-radius: var(--radius, 8px);
  background: #f2f7f0;
}
.cleanup-result { margin-top: 12px; }
.cleanup-empty { font-size: 13px; color: #5a7a55; padding: 8px 0; }
.cleanup-summary {
  display: flex; flex-wrap: wrap; gap: 12px;
  font-size: 13px; color: #333; margin-bottom: 10px;
  padding: 8px 12px; background: #fff; border-radius: 6px; border: 1px solid #d7e5d4;
}
.cleanup-detail { display: flex; flex-direction: column; gap: 6px; }
.cleanup-item {
  display: flex; align-items: center; gap: 8px;
  padding: 6px 12px; background: #fff; border-radius: 6px; border: 1px solid #ede8df;
  font-size: 13px;
}
.cleanup-type {
  display: inline-block; padding: 1px 8px; border-radius: 10px;
  font-size: 11px; font-weight: 600;
}
.cleanup-type.agent { background: #eef3ec; color: #2f4330; }
.cleanup-type.session { background: #eef5f8; color: #1a5a6a; }
.cleanup-type.skill { background: #f5f0e4; color: #8a7a3a; }
.cleanup-name { font-weight: 600; color: #333; }
.cleanup-info { color: #8c8680; margin-left: auto; }
</style>
