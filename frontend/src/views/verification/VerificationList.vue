<template>
  <div class="page">
    <el-tabs v-model="tab" type="border-card">
      <el-tab-pane label="性能验证记录" name="records">
        <div style="display:flex;gap:8px;align-items:center;margin-bottom:10px">
          <el-button type="warning" plain @click="uncertOpen = true">测量不确定度评估</el-button>
        </div>
        <VerificationRecords />
      </el-tab-pane>
      <el-tab-pane label="验证报告归档" name="archive">
        <VerificationArchive />
      </el-tab-pane>
    </el-tabs>
    <!-- 测量不确定度评估工具 -->
    <el-drawer v-model="uncertOpen" title="测量不确定度评估" size="92%" destroy-on-close>
      <UncertaintyAssessment />
    </el-drawer>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UncertaintyAssessment from './UncertaintyAssessment.vue'
import VerificationArchive from './VerificationArchive.vue'
import VerificationRecords from './VerificationRecords.vue'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const tab = ref('records')
const uncertOpen = ref(false)
</script>

<style scoped>
</style>