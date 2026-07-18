import { defineStore } from 'pinia'
import request from '../utils/request'
import { usePermissionStore } from './permission'

// 模块 → 写权限角色映射（启动期 fallback；登录后会从后端拉新值覆盖）
// 与 backend/models/module_permission.py DEFAULT_MODULE_PERMISSIONS 一致
const FALLBACK_MODULE_WRITE_ROLES = {
  'test-items': ['admin'],
  'documents': ['admin', 'specialty_leader'],
  'instruments': ['admin', 'specialty_leader'],
  'instrument-families': ['admin', 'specialty_leader'],
  'qc-monthly': ['admin', 'qc_manager', 'member'],
  'qc-monthly_delete': ['admin', 'qc_manager'],
  'qc-target': ['admin', 'qc_manager', 'member'],
  'qc-target_delete': ['admin', 'qc_manager'],
  'eqa': ['admin', 'qc_manager'],
  'eqa_delete': ['admin', 'qc_manager'],
  'comparison': ['admin', 'qc_manager', 'technical_support'],
  'comparison-edit': ['admin', 'qc_manager'],
  'interlab': ['admin', 'qc_manager', 'technical_support'],
  'interlab-edit': ['admin', 'qc_manager'],
  'reagents': ['admin', 'reagent_manager'],
  'reagents_delete': ['admin', 'reagent_manager'],
  'training': ['admin', 'training_manager'],
  'training_delete': ['admin', 'training_manager'],
  'verification': ['admin', 'specialty_leader'],
  'iso15189': ['admin', 'quality_manager', 'qc_manager', 'training_manager', 'reagent_manager', 'it_manager', 'specialty_leader'],
  'quality-requirements': ['admin'],
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
      // 登录成功后拉一次模块权限映射（用于全站 canWrite 判定）
      try {
        const permStore = usePermissionStore()
        await permStore.load(true)
      } catch (_) { /* 拉失败不阻塞登录 */ }
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
      // 优先读后端拉的最新配置；尚未加载或找不到时用 fallback
      let required
      try {
        const permStore = usePermissionStore()
        required = permStore.moduleRoles[module]
      } catch (_) { /* store 未挂载时退化 */ }
      if (!required) required = FALLBACK_MODULE_WRITE_ROLES[module]
      // 旧版 'qc' 兼容：自动映射到 qc-monthly / qc-target
      if (!required && module === 'qc') required = (permStore?.moduleRoles?.['qc-monthly']) || FALLBACK_MODULE_WRITE_ROLES['qc-monthly']
      if (!required) return true // 未配置的模块默认允许
      return this.myRoles.some(r => required.includes(r))
    },
    // 删除权限（沿用 canWrite 同样的 store 查找，但查找 `xxx_delete` 专属配置）
    canDelete(module) {
      if (this.isAdmin) return true
      let required
      try {
        const permStore = usePermissionStore()
        required = permStore.moduleRoles[module + '_delete'] || permStore.moduleRoles[module]
      } catch (_) { /* store 未挂载时退化 */ }
      if (!required) required = FALLBACK_MODULE_WRITE_ROLES[module + '_delete'] || FALLBACK_MODULE_WRITE_ROLES[module]
      if (!required) return true
      return this.myRoles.some(r => required.includes(r))
    },
  },
})
