<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-brand">
        <h1>账房先生</h1>
        <p>面向中国财务人员的本地部署资金工作台</p>
      </div>
      <div v-if="errorMsg" class="error-bar">{{ errorMsg }}</div>
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label class="form-label">用户名</label>
          <input v-model="username" class="form-input" type="text" placeholder="请输入用户名" autocomplete="username" />
        </div>
        <div class="form-group">
          <label class="form-label">密码</label>
          <input v-model="password" class="form-input" type="password" placeholder="请输入密码" autocomplete="current-password" />
        </div>
        <NButton type="primary" block class="login-btn" attr-type="submit" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </NButton>
      </form>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { NButton } from 'naive-ui'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const username = ref('')
const password = ref('')
const loading = ref(false)
const errorMsg = ref('')

async function handleLogin() {
  if (!username.value || !password.value) {
    errorMsg.value = '请输入用户名和密码'
    return
  }
  loading.value = true
  errorMsg.value = ''
  try {
    const data = await auth.login(username.value, password.value)
    if (data.user?.must_change_password) {
      router.push({ name: 'home', query: { forceChangePwd: '1' } })
    } else {
      router.push('/')
    }
  } catch (e) {
    errorMsg.value = e.message || '登录失败'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-gradient);
}

.login-card {
  width: 400px;
  background: var(--panel-2);
  border-radius: var(--radius-lg, 16px);
  box-shadow: 0 8px 32px rgba(47, 58, 50, 0.08), 0 2px 8px rgba(47, 58, 50, 0.04);
  padding: 48px 40px 40px;
}

.login-brand {
  text-align: center;
  margin-bottom: 36px;
}

.login-brand h1 {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 8px;
  letter-spacing: 2px;
}

.login-brand p {
  font-size: 13px;
  color: var(--text-light);
  margin: 0;
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  height: 42px;
  padding: 0 14px;
  border: 1px solid var(--line);
  border-radius: var(--radius, 8px);
  font-size: 14px;
  color: var(--text);
  background: var(--panel);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus {
  border-color: var(--green);
  box-shadow: 0 0 0 3px var(--green-2);
}

.form-input::placeholder {
  color: var(--muted);
}

.login-btn {
  width: 100%;
  height: 44px;
  margin-top: 8px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.error-bar {
  background: var(--warn-bg);
  border: 1px solid var(--warn-border);
  border-radius: var(--radius, 8px);
  padding: 10px 14px;
  margin-bottom: 20px;
  font-size: 13px;
  color: var(--warn-text);
}
</style>
