<template>
  <div class="page">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="文件评审" name="review">
        <ReviewTab />
      </el-tab-pane>
      <el-tab-pane label="自查（条款内审）" name="self">
        <SelfInspectionTab />
      </el-tab-pane>
      <el-tab-pane label="科室内审" name="internal">
        <InternalAuditTab />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ReviewTab from './ReviewTab.vue'
import SelfInspectionTab from './SelfInspectionTab.vue'
import InternalAuditTab from './InternalAuditTab.vue'

const activeTab = ref('review')
</script>

<style scoped>
.page { height: 100%; }
</style>
