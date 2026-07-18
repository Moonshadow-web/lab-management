import { defineStore } from 'pinia'
import request from '../utils/request'

// 模块 → 写权限角色映射（与后端 write_roles 一致）
const MODULE_WRITE_ROLES = {
  'test-items': ['admin'],
  'documents': ['admin', 'specialty_leader'],
  'instruments': ['admin', 'specialty_leader'],
  'instrument-families': ['admin', 'specialty_leader'],
  'qc': ['admin', 'qc_manager'],
  'eqa': ['admin', 'qc_manager'],
  'reagents': ['admin', 'reagent_manager'],
  'training': ['admin', 'training_manager'],
  'verification': ['admin', 'specialty_leader'],
  'iso15189': ['admin', 'quality_manager', 'qc_manager', 'training_manager', 'reagent_manager', 'it_manager', 'specialty_leader'],
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refreshToken: localStorage.getItem('refresh_token') || '',
    user: JSON.parse(localStorage.getItem('user') || 'null'),
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
    // 用户拥有的全部角色码列表
    myRoles: (state) => {
      if (!state.user) return []
      const set = new Set()
      if (state.user.role) set.add(state.user.role)
      if (state.user.roles) state.user.roles.split(',').filter(Boolean).forEach(r => set.add(r))
      return [...set]
    },
    // 是否管理员（admin 始终有全部权限）
    isAdmin: (state) => {
      if (!state.user) return false
      return state.user.role === 'admin' || (state.user.roles || '').includes('admin')
    },
  },
  actions: {
    async login(username, password) {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const data = await request.post('/api/v1/auth/login', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      this.token = data.access_token
      localStorage.setItem('token', this.token)
      if (data.refresh_token) {
        this.refreshToken = data.refresh_token
        localStorage.setItem('refresh_token', data.refresh_token)
      }
      const me = await request.get('/api/v1/auth/me')
      this.user = me
      localStorage.setItem('user', JSON.stringify(this.user))
      return data
    },
    async changePassword(oldPassword, newPassword) {
      return request.post('/api/v1/auth/change-password', {
        old_password: oldPassword,
        new_password: newPassword,
      })
    },
    logout() {
      const refreshToken = localStorage.getItem('refresh_token')
      if (refreshToken) {
        // 尽力吊销服务端 refresh token（失败不影响本地退出）
        request.post('/api/v1/auth/logout', { refresh_token: refreshToken }).catch(() => {})
      }
      this.token = ''
      this.refreshToken = ''
      this.user = null
      localStorage.removeItem('token')
      localStorage.removeItem('refresh_token')
      localStorage.removeItem('user')
    },
    // 判断当前用户对某模块是否有写权限
    canWrite(module) {
      if (this.isAdmin) return true
      const required = MODULE_WRITE_ROLES[module]
      if (!required) return true // 未配置的模块默认允许
      return this.myRoles.some(r => required.includes(r))
    },
  },
})
