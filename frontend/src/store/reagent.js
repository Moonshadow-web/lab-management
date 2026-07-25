import { defineStore } from 'pinia'

// 试剂管理「责任库」全局状态：生化凝血 / 免疫 两类分管。
// 各试剂页面共享当前选中的责任库，刷新后仍记住选择。
const STORAGE_KEY = 'reagent_library'

export const LIBRARIES = ['生化凝血', '免疫']

export const useReagentStore = defineStore('reagent', {
  state: () => ({
    library: localStorage.getItem(STORAGE_KEY) || '生化凝血',
  }),
  actions: {
    setLibrary(lib) {
      if (!LIBRARIES.includes(lib)) lib = '生化凝血'
      this.library = lib
      localStorage.setItem(STORAGE_KEY, lib)
    },
  },
})
