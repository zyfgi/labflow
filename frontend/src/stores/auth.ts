import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { changePassword, login as loginApi, logout as logoutApi, me } from '@/api/auth'
import { TOKEN_KEY, USER_KEY } from '@/api/client'
import type { User } from '@/types'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(localStorage.getItem(TOKEN_KEY))
  const user = ref<User | null>(JSON.parse(localStorage.getItem(USER_KEY) ?? 'null'))

  const isLoggedIn = computed(() => !!token.value)
  const isPI = computed(() => user.value?.role === 'PI')
  const isTeacher = computed(() => user.value?.role === 'TEACHER')
  const isStudent = computed(() => user.value?.role === 'STUDENT')
  const isEquipmentAdmin = computed(() => user.value?.role === 'EQUIPMENT_ADMIN')
  const canManage = computed(() => isPI.value || isTeacher.value)

  async function login(username: string, password: string) {
    const { data } = await loginApi(username, password)
    token.value = data.data.access_token
    user.value = data.data.user
    localStorage.setItem(TOKEN_KEY, data.data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.data.user))
    if (data.data.must_change_password) {
      const { ElMessage } = await import('element-plus')
      ElMessage.warning('首次登录请修改初始密码')
    }
  }

  async function fetchMe() {
    const { data } = await me()
    user.value = data.data
    localStorage.setItem(USER_KEY, JSON.stringify(data.data))
  }

  async function resetPassword(oldPwd: string, newPwd: string) {
    await changePassword(oldPwd, newPwd)
    await fetchMe()
  }

  async function logout() {
    try {
      await logoutApi()
    } catch {
      /* token may already be invalid */
    }
    token.value = null
    user.value = null
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
  }

  return {
    token,
    user,
    isLoggedIn,
    isPI,
    isTeacher,
    isStudent,
    isEquipmentAdmin,
    canManage,
    login,
    fetchMe,
    resetPassword,
    logout,
  }
})
