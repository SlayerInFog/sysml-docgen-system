import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi, type User } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sysml_docgen_token') || '')
  const user = ref<User | null>(JSON.parse(localStorage.getItem('sysml_docgen_user') || 'null'))

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'author')

  async function login(username: string, password: string) {
    const result = await authApi.login({ username, password })
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('sysml_docgen_token', result.access_token)
    localStorage.setItem('sysml_docgen_user', JSON.stringify(result.user))
  }

  async function register(data: Record<string, unknown>) {
    return authApi.register(data)
  }

  async function refresh() {
    if (!token.value) return
    user.value = await authApi.me()
    localStorage.setItem('sysml_docgen_user', JSON.stringify(user.value))
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('sysml_docgen_token')
    localStorage.removeItem('sysml_docgen_user')
  }

  return { token, user, isAuthenticated, isAdmin, canEdit, login, register, refresh, logout }
})
