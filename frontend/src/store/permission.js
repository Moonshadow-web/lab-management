// 模块写权限 store：登录后从后端拉一次"模块→允许角色"映射，
// canWrite 读这里（找不到时回退到硬编码默认）。
import { defineStore } from 'pinia'
import { getModulePermissionsStructure } from '../api/modulePermissions'

// 硬编码 fallback（与后端 DEFAULT_MODULE_PERMISSIONS 一致），用于 store 尚未加载时
const FALLBACK = {
  'test-items':           ['admin'],
  'documents':            ['admin', 'specialty_leader'],
  'instruments':          ['admin', 'specialty_leader'],
  'instrument-families':  ['admin', 'specialty_leader'],
  'qc-monthly':           ['admin', 'qc_manager', 'staff'],
  'qc-monthly_delete':    ['admin', 'qc_manager'],
  'qc-target':            ['admin', 'qc_manager', 'staff'],
  'qc-target_delete':     ['admin', 'qc_manager'],
  'eqa':                  ['admin', 'qc_manager'],
  'eqa_delete':           ['admin', 'qc_manager'],
  'comparison':           ['admin', 'qc_manager', 'technical_support'],
  'comparison-edit':      ['admin', 'qc_manager'],
  'interlab':             ['admin', 'qc_manager', 'technical_support'],
  'interlab-edit':        ['admin', 'qc_manager'],
  'reagents':             ['admin', 'reagent_manager'],
  'reagents_delete':      ['admin', 'reagent_manager'],
  'training':             ['admin', 'training_manager'],
  'training_delete':      ['admin', 'training_manager'],
  'verification':         ['admin', 'specialty_leader'],
  'iso15189':             ['admin', 'quality_manager', 'qc_manager', 'training_manager', 'reagent_manager', 'it_manager', 'specialty_leader'],
  'quality-requirements': ['admin'],
}

export const usePermissionStore = defineStore('permissions', {
  state: () => ({
    // module_key -> [role_code]
    moduleRoles: { ...FALLBACK },
    loaded: false,           // 是否从后端拉过
    loading: false,
    error: null,
  }),

  getters: {
    isLoaded: (s) => s.loaded,
    getModuleRoles: (s) => (moduleKey) => s.moduleRoles[moduleKey] || FALLBACK[moduleKey] || ['admin'],
  },

  actions: {
    async load(force = false) {
      if (this.loading) return
      if (this.loaded && !force) return
      this.loading = true
      this.error = null
      try {
        const r = await getModulePermissionsStructure()
        const map = {}
        for (const m of r.modules) {
          map[m.key] = m.roles
        }
        this.moduleRoles = map
        this.loaded = true
      } catch (e) {
        this.error = e?.response?.data?.detail || e.message
        // 保留 fallback，不阻塞 UI
      } finally {
        this.loading = false
      }
    },

    // 单个模块的写权限判定（与 auth.canWrite 一致；admin 短路）
    canWrite(userRoles, moduleKey) {
      if (userRoles.includes('admin')) return true
      const allowed = this.moduleRoles[moduleKey]
      if (!allowed) return true  // 未配置白名单 = 默认允许
      return userRoles.some((r) => allowed.includes(r))
    },

    // 单个模块的删除权限判定
    // 查找规则：先查 `moduleKey + '_delete'` 专属配置；找不到则回退到写权限
    canDelete(userRoles, moduleKey) {
      if (userRoles.includes('admin')) return true
      const allowed = this.moduleRoles[moduleKey + '_delete'] || this.moduleRoles[moduleKey]
      if (!allowed) return true
      return userRoles.some((r) => allowed.includes(r))
    },

    // admin 在 UI 改了某个模块的角色后，调用此方法同步到本地 store
    setLocal(moduleKey, roles) {
      this.moduleRoles = { ...this.moduleRoles, [moduleKey]: [...roles] }
    },

    // 模块可见性（菜单/页签是否展示）。
    // 角色对该模块的「基础键 / '_delete' 变体 / '-edit' 变体」中任一拥有授权即视为可见。
    // admin 短路为可见；未配置白名单的模块按"可见"兜底，避免误隐藏。
    canAccess(userRoles, moduleKey) {
      if (userRoles.includes('admin')) return true
      const variants = [moduleKey, moduleKey + '_delete', moduleKey + '-edit']
      for (const vk of variants) {
        const allowed = this.moduleRoles[vk]
        if (allowed && userRoles.some((r) => allowed.includes(r))) return true
      }
      return false
    },

    // 多个模块键中任一可见即视为可见（用于"质控管理"这种聚合菜单）
    canAccessAny(userRoles, moduleKeys) {
      return moduleKeys.some((k) => this.canAccess(userRoles, k))
    },
  },
})
