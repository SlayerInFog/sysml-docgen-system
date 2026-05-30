import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { authApi, type User } from '@/api'

// 定义登录状态和权限判断的全局 Store。
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('sysml_docgen_token') || '')
  const user = ref<User | null>(JSON.parse(localStorage.getItem('sysml_docgen_user') || 'null'))

  const isAuthenticated = computed(() => Boolean(token.value && user.value))
  const isAdmin = computed(() => user.value?.role === 'admin')
  const canEdit = computed(() => user.value?.role === 'admin' || user.value?.role === 'author')

  // 校验账号密码并签发访问令牌。
  async function login(username: string, password: string) {
    const result = await authApi.login({ username, password })
    token.value = result.access_token
    user.value = result.user
    localStorage.setItem('sysml_docgen_token', result.access_token)
    localStorage.setItem('sysml_docgen_user', JSON.stringify(result.user))
  }

  // 创建新用户并保存账号信息。
  async function register(data: Record<string, unknown>) {
    return authApi.register(data)
  }

  // 刷新当前登录用户信息。
  async function refresh() {
    if (!token.value) return
    user.value = await authApi.me()
    localStorage.setItem('sysml_docgen_user', JSON.stringify(user.value))
  }

  // 清空本地登录状态并退出系统。
  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('sysml_docgen_token')
    localStorage.removeItem('sysml_docgen_user')
  }

  return { token, user, isAuthenticated, isAdmin, canEdit, login, register, refresh, logout }
})
