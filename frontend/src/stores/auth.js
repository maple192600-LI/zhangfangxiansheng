import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as loginApi, getMe } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('zf_token') || '')
  const user = ref(JSON.parse(localStorage.getItem('zf_user') || 'null'))

  const isLoggedIn = computed(() => !!token.value)

  async function login(username, password) {
    const data = await loginApi({ username, password })
    token.value = data.token
    user.value = data.user
    localStorage.setItem('zf_token', data.token)
    localStorage.setItem('zf_user', JSON.stringify(data.user))
    return data
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('zf_token')
    localStorage.removeItem('zf_user')
  }

  async function checkAuth() {
    if (!token.value) return false
    try {
      const data = await getMe()
      user.value = data
      localStorage.setItem('zf_user', JSON.stringify(data))
      return true
    } catch {
      logout()
      return false
    }
  }

  return { token, user, isLoggedIn, login, logout, checkAuth }
})
