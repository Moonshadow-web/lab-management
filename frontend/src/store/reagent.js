import { defineStore } from 'pinia'

// 试剂管理「责任库」全局状态。
// 多专业组：责任库按当前专业组隔离（storage key 带组编码），避免其他组沿用生免组的"生化凝血/免疫"。
const DEFAULT_SM = '生化凝血'

function groupCode() {
  try { return localStorage.getItem('group_code') || 'sm' } catch (_) { return 'sm' }
}
function storageKey() {
  return `reagent_library_${groupCode()}`
}
function defaultsOf(group) {
  // 生免组固定两类；其他组默认空（其责任库由本组数据决定）
  return group === 'sm' ? ['生化凝血', '免疫'] : []
}

export const LIBRARIES = ['生化凝血', '免疫'] // 兼容旧引用（生免组默认）

export const useReagentStore = defineStore('reagent', {
  state: () => ({
    group: groupCode(),
    library: localStorage.getItem(storageKey()) || (groupCode() === 'sm' ? DEFAULT_SM : ''),
    libs: defaultsOf(groupCode()),
  }),
  actions: {
    // 由页面按本组数据回填可选责任库（生免组至少保留默认两类）
    setLibraries(list) {
      const g = groupCode()
      this.group = g
      const extra = (list || []).filter((x) => x && !defaultsOf(g).includes(x))
      this.libs = [...defaultsOf(g), ...extra]
      if (this.library && !this.libs.includes(this.library)) {
        this.library = defaultsOf(g)[0] || ''
        localStorage.setItem(storageKey(), this.library)
      }
    },
    setLibrary(lib) {
      const g = groupCode()
      if (!lib) {
        this.library = ''
        localStorage.setItem(storageKey(), '')
        return
      }
      if (this.libs.length && !this.libs.includes(lib)) lib = this.libs[0]
      this.library = lib
      localStorage.setItem(storageKey(), lib)
    },
  },
})
