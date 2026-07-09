<template>
  <div class="placeholder">
    <el-icon class="ph-icon"><Tools /></el-icon>
    <h2>{{ title }}（建设中）</h2>
    <p>该模块属于 ISO 15189 实验室管理系统第二阶段功能，将在后续迭代中实现。</p>
    <el-tag type="info">规划中</el-tag>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Tools } from '@element-plus/icons-vue'

const route = useRoute()
const title = computed(() => route.meta.title || '模块')
</script>

<style scoped>
.placeholder {
  height: 100%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #666;
  gap: 10px;
}
.ph-icon {
  font-size: 64px;
  color: #c0c4cc;
}
</style>
