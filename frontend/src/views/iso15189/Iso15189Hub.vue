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
      <el-tab-pane label="认可能力范围" name="scope">
        <AccreditedScope />
      </el-tab-pane>
      <el-tab-pane label="规范文件" name="standards">
        <StandardsTab />
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import ReviewTab from './ReviewTab.vue'
import SelfInspectionTab from './SelfInspectionTab.vue'
import InternalAuditTab from './InternalAuditTab.vue'
import AccreditedScope from './AccreditedScope.vue'
import StandardsTab from './StandardsTab.vue'

const activeTab = ref('review')
</script>

<style scoped>
.page { height: 100%; }
</style>
