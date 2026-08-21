<template>
  <div class="page">
    <el-tabs v-model="tab" type="border-card">
      <el-tab-pane label="性能验证记录" name="records">
        <VerificationRecords />
      </el-tab-pane>
      <el-tab-pane label="项目验证档案" name="archive">
        <VerificationArchive />
      </el-tab-pane>
      <el-tab-pane label="验证报告归档" name="reports">
        <ProjectVerificationArchive />
      </el-tab-pane>
      <el-tab-pane label="测量不确定度评定" name="uncertainty">
        <UncertaintyAssessment />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import UncertaintyAssessment from './UncertaintyAssessment.vue'
import VerificationArchive from './VerificationArchive.vue'
import VerificationRecords from './VerificationRecords.vue'
import ProjectVerificationArchive from './ProjectVerificationArchive.vue'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const tab = ref('records')
</script>

<style scoped>
</style>