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
  'qc':                   ['admin', 'qc_manager'],
  'eqa':                  ['admin', 'qc_manager'],
  'reagents':             ['admin', 'reagent_manager'],
  'training':             ['admin', 'training_manager'],
  'verification':         ['admin', 'specialty_leader'],
  'iso15189':             ['admin', 'quality_manager', 'qc_manager', 'training_manager', 'reagent_manager', 'it_manager', 'specialty_leader'],
  'quality-requirements':['admin'],
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
        for (const m of r.data.modules) {
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

    // admin 在 UI 改了某个模块的角色后，调用此方法同步到本地 store
    setLocal(moduleKey, roles) {
      this.moduleRoles = { ...this.moduleRoles, [moduleKey]: [...roles] }
    },
  },
})
