<template>
  <el-select
    :model-value="modelValue"
    @update:model-value="(v) => $emit('update:modelValue', v)"
    filterable
    clearable
    :placeholder="placeholder || '选择人员'"
    :style="{ width: '100%' }"
    :loading="loading"
  >
    <el-option
      v-for="u in users"
      :key="u.id"
      :label="u.full_name || u.username"
      :value="u.full_name || u.username"
    />
  </el-select>
</template>

<script setup>
// 「操作者/审核者」人员下拉组件：复用 /api/v1/users/active。
// 行为：
// - 首次挂载时拉取活跃用户列表（模块级 promise 缓存，所有实例共享一次请求）。
// - v-model 绑定的是用户显示名（full_name 优先，缺省回退 username），与后端 operator/reviewer 字符串字段直接兼容。
// - 支持可清空、可搜索。
defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})
defineEmits(['update:modelValue'])

import { ref, onMounted } from 'vue'
import { listActiveUsers } from '../api/users'

const users = ref([])
const loading = ref(false)

let _promise = null
async function ensureLoaded() {
  if (!_promise) {
    _promise = listActiveUsers().catch((e) => {
      _promise = null  // 失败允许重试
      throw e
    })
  }
  return _promise
}

onMounted(async () => {
  loading.value = true
  try {
    users.value = await ensureLoaded()
  } catch (e) {
    // 静默失败：下拉为空，用户仍可手输（v-model 仍是字符串）
    users.value = []
  } finally {
    loading.value = false
  }
})
</script>
