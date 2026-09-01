<template>
  <div class="staff-education">
    <div class="se-header">
      <h2>人员能力管理</h2>
    </div>

    <el-tabs v-model="active" class="se-tabs">
      <el-tab-pane label="人员档案" name="personnel">
        <PersonnelArchive />
      </el-tab-pane>
      <el-tab-pane label="新员工培训" name="new_employee">
        <NewEmployeeTrain />
      </el-tab-pane>
      <el-tab-pane label="独立上岗认证" name="cert_auth">
        <CertAuth />
      </el-tab-pane>
      <el-tab-pane label="授权表" name="auth_sheet">
        <AuthSheet />
      </el-tab-pane>
      <el-tab-pane label="年度能力评估" name="competency">
        <el-tabs v-model="compTab">
          <el-tab-pane label="能力评估（PX-808）" name="assess">
            <CompetencyAssessment />
          </el-tab-pane>
          <el-tab-pane label="人员比对（CZ-023）" name="compare">
            <PersonnelComparison />
          </el-tab-pane>
        </el-tabs>
      </el-tab-pane>
      <el-tab-pane label="组内培训 / 艾梅乙" name="group">
        <GroupTraining />
      </el-tab-pane>
      <el-tab-pane label="实习进修带教" name="internship">
        <Internship />
      </el-tab-pane>
      <el-tab-pane label="继续教育记录" name="records">
        <TrainingList />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import PersonnelArchive from './staff/PersonnelArchive.vue'
import NewEmployeeTrain from './staff/NewEmployeeTrain.vue'
import CertAuth from './staff/CertAuth.vue'
import AuthSheet from './staff/AuthSheet.vue'
import CompetencyAssessment from './staff/CompetencyAssessment.vue'
import PersonnelComparison from './staff/PersonnelComparison.vue'
import GroupTraining from './staff/GroupTraining.vue'
import Internship from './staff/Internship.vue'
import TrainingList from './TrainingList.vue'

const active = ref('personnel')
const compTab = ref('assess')
</script>

<style scoped>
.staff-education { padding: 4px; }
.se-header { display: flex; align-items: center; gap: 16px; margin-bottom: 8px; }
.se-header h2 { margin: 0; font-size: 20px; }
.se-tabs :deep(.el-tabs__content) { padding-top: 8px; }
</style>
