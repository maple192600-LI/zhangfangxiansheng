<template>
  <div class="section">
    <div class="section-title">
      <h3>数据清理</h3>
      <NButton secondary @click="loadPreview" :disabled="loading">
        {{ loading ? '扫描中...' : '扫描残留数据' }}
      </NButton>
    </div>

    <div v-if="error" class="error-bar">{{ error }}</div>
    <div v-if="message" class="warning ok">{{ message }}</div>

    <p class="section-desc">
      清除已删除的智能体、会话及其关联数据（消息、记忆、技能）。开发测试阶段的残留数据会被彻底移除，活跃数据不受影响。
    </p>

    <div v-if="data && !data.summary" class="empty-state">
      <div class="empty-icon">🧹</div>
      <h4>点击"扫描残留数据"开始检查</h4>
      <p>扫描完成后会列出所有可清理的残留数据</p>
    </div>

    <div v-if="data" class="cleanup-result">
      <div v-if="data.summary.deleted_agents === 0 && data.summary.deleted_sessions === 0 && data.summary.draft_skills === 0" class="cleanup-clean">
        <div class="clean-icon">✅</div>
        <div class="clean-text">未发现残留数据，数据库很干净。</div>
      </div>
      <template v-else>
        <div class="cleanup-summary">
          <span v-if="data.summary.deleted_agents" class="sum-tag agent-tag">已删除智能体 {{ data.summary.deleted_agents }} 个</span>
          <span v-if="data.summary.deleted_sessions" class="sum-tag session-tag">已删除会话 {{ data.summary.deleted_sessions }} 个</span>
          <span v-if="data.summary.linked_messages" class="sum-tag msg-tag">关联消息 {{ data.summary.linked_messages }} 条</span>
          <span v-if="data.summary.linked_memories" class="sum-tag mem-tag">关联记忆 {{ data.summary.linked_memories }} 条</span>
          <span v-if="data.summary.draft_skills" class="sum-tag skill-tag">草稿技能 {{ data.summary.draft_skills }} 个</span>
        </div>

        <div class="cleanup-detail">
          <div v-for="a in data.deleted_agents" :key="'a-'+a.id" class="cleanup-item">
            <span class="cleanup-type agent">智能体</span>
            <span class="cleanup-name">{{ a.display_name }} ({{ a.agent_code }})</span>
            <span class="cleanup-info">会话={{ a.sessions }} 消息={{ a.messages }} 记忆={{ a.memories }} 技能={{ a.skills }}</span>
          </div>
          <div v-for="s in data.deleted_sessions" :key="'s-'+s.id" class="cleanup-item">
            <span class="cleanup-type session">会话</span>
            <span class="cleanup-name">{{ s.agent_name }} / {{ s.title || '未命名' }}</span>
            <span class="cleanup-info">消息={{ s.messages }}</span>
          </div>
          <div v-for="sk in data.draft_skills" :key="'sk-'+sk.id" class="cleanup-item">
            <span class="cleanup-type skill">草稿技能</span>
            <span class="cleanup-name">{{ sk.display_name }} ({{ sk.skill_code }})</span>
          </div>
        </div>

        <div class="cleanup-actions">
          <NButton type="warning" @click="confirming = true" :disabled="executing">
            {{ executing ? '清理中...' : '彻底清除以上数据' }}
          </NButton>
        </div>
      </template>
    </div>
  </div>

  <!-- 确认弹窗 -->
  <div v-if="confirming" class="modal-overlay" @click.self="confirming = false">
    <div class="modal-box">
      <h3>确认清理数据</h3>
      <p>将彻底删除以下数据（不可恢复）：</p>
      <ul class="confirm-list">
        <li v-if="data?.summary?.deleted_agents">已删除智能体 {{ data.summary.deleted_agents }} 个（含其会话、消息、记忆、技能）</li>
        <li v-if="data?.summary?.deleted_sessions">已删除会话 {{ data.summary.deleted_sessions }} 个（含其消息）</li>
        <li v-if="data?.summary?.draft_skills">草稿技能 {{ data.summary.draft_skills }} 个</li>
      </ul>
      <p class="confirm-warn">活跃的智能体和数据不受影响。</p>
      <div class="btn-row">
        <NButton secondary @click="confirming = false">取消</NButton>
        <NButton type="warning" @click="doCleanup">确认清理</NButton>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { NButton } from 'naive-ui'
import { getCleanupPreview, executeCleanup } from '@/api/backup'

const data = ref(null)
const loading = ref(false)
const executing = ref(false)
const confirming = ref(false)
const error = ref('')
const message = ref('')

onMounted(loadPreview)

async function loadPreview() {
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    data.value = await getCleanupPreview()
  } catch (e) {
    error.value = e.message || '扫描残留数据失败'
  } finally {
    loading.value = false
  }
}

async function doCleanup() {
  confirming.value = false
  executing.value = true
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
    await loadPreview()
  } catch (e) {
    error.value = e.message || '数据清理失败'
  } finally {
    executing.value = false
  }
}
</script>

<style scoped>
@import './common.css';

.section-desc {
  font-size: 13px; color: var(--text-light, #8c8680); line-height: 1.6;
  margin: 0 0 16px;
}

.cleanup-clean {
  display: flex; align-items: center; gap: 10px;
  padding: 16px 20px; background: #f2f7f0; border-radius: 10px;
  border: 1px solid #d7e5d4;
}
.clean-icon { font-size: 24px; }
.clean-text { font-size: 14px; color: #2f4330; font-weight: 600; }

.cleanup-summary {
  display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 14px;
}
.sum-tag {
  padding: 5px 14px; border-radius: 20px; font-size: 13px; font-weight: 600;
}
.agent-tag { background: #eef3ec; color: #2f4330; }
.session-tag { background: #eef5f8; color: #1a5a6a; }
.msg-tag { background: #f0ede5; color: #6b5d4a; }
.mem-tag { background: #f3f0fa; color: #5a4a7a; }
.skill-tag { background: #f5f0e4; color: #8a7a3a; }

.cleanup-detail {
  display: flex; flex-direction: column; gap: 6px;
}
.cleanup-item {
  display: flex; align-items: center; gap: 10px;
  padding: 10px 16px; background: #fff; border-radius: 8px;
  border: 1px solid var(--border, #ede8df); font-size: 13px;
  transition: border-color .15s;
}
.cleanup-item:hover { border-color: #b8ccb5; }

.cleanup-type {
  display: inline-block; padding: 2px 10px; border-radius: 10px;
  font-size: 11px; font-weight: 600;
}
.cleanup-type.agent { background: #eef3ec; color: #2f4330; }
.cleanup-type.session { background: #eef5f8; color: #1a5a6a; }
.cleanup-type.skill { background: #f5f0e4; color: #8a7a3a; }
.cleanup-name { font-weight: 600; color: var(--text, #333); }
.cleanup-info { color: var(--text-light, #8c8680); margin-left: auto; }

.cleanup-actions { margin-top: 16px; }

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
.confirm-list {
  font-size: 13px; line-height: 1.8; padding-left: 20px;
  color: var(--text-secondary, #666);
}
.confirm-warn {
  color: var(--warn-text, #c0392b); font-weight: 600;
}
.btn-row {
  display: flex; justify-content: flex-end; gap: 8px; margin-top: 20px;
}
</style>
