<template>
  <el-dialog :model-value="visible" :title="`报告管理 · ${plan?.form_code || ''}`" width="960px"
    top="3vh" @update:model-value="(v) => !v && $emit('close')">
    <div v-if="plan">
      <el-descriptions :column="3" border size="small" style="margin-bottom:12px">
        <el-descriptions-item label="分组">{{ groupName }}</el-descriptions-item>
        <el-descriptions-item label="年份/半年">{{ plan.year }} 年 半年 {{ plan.half }}</el-descriptions-item>
        <el-descriptions-item label="比对日期">{{ plan.compared_at || '-' }}</el-descriptions-item>
        <el-descriptions-item label="操作者">{{ plan.operator || '-' }}</el-descriptions-item>
        <el-descriptions-item label="审核者">{{ plan.reviewer || '-' }}</el-descriptions-item>
        <el-descriptions-item label="报告文件">
          <span v-if="plan.report_filename" class="yes">{{ plan.report_filename }}</span>
          <span v-else class="no">未生成</span>
        </el-descriptions-item>
      </el-descriptions>

      <el-alert type="warning" :closable="false" show-icon
        title="生成报告前请先录入结果并填写计划中的「结果分析/结论」。报告将严格保留表格编号。" />

      <div style="margin:14px 0; display:flex; gap:10px; flex-wrap:wrap; align-items:center">
        <el-button type="primary" :loading="genLoading" @click="onGenerate">生成报告（docx）</el-button>
        <el-button :disabled="!plan.report_filename" @click="onDownload">下载</el-button>
        <el-button type="danger" :disabled="!plan.report_filename" :loading="delLoading"
          @click="onDelete">删除报告</el-button>
        <div style="flex:1" />
        <el-upload :auto-upload="false" :show-file-list="false" accept=".docx,.doc,.pdf"
          :on-change="onUploadChange" style="display:inline-block">
          <el-button type="success">既往报告上传</el-button>
        </el-upload>
      </div>

      <!-- 有报告时自动加载预览 -->
      <div v-if="plan.report_filename" style="margin-top:10px">
        <div class="preview-header">
          <span>报告预览（{{ plan.report_filename }}）</span>
          <el-button size="small" text @click="onRefreshPreview" :loading="previewLoading">刷新</el-button>
        </div>
        <div v-if="previewHtml" class="preview-box" v-html="previewHtml" />
        <div v-else-if="previewLoading" class="preview-empty">加载中…</div>
        <div v-else class="preview-empty">点击「刷新」加载预览</div>
      </div>
    </div>
    <template #footer>
      <el-button @click="$emit('close')">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import {
  previewReport, generateReport, downloadReport, uploadReport, deleteReport,
} from '../../api/comparison'

const props = defineProps({
  visible: Boolean,
  plan: { type: Object, default: null },
  groupName: { type: String, default: '' },
})
const emit = defineEmits(['close', 'saved'])

const genLoading = ref(false)
const delLoading = ref(false)
const previewLoading = ref(false)
const previewHtml = ref('')

// 打开时自动加载预览
import { watch } from 'vue'
watch(() => props.visible, async (v) => {
  if (v && props.plan && props.plan.report_filename) {
    await loadPreview()
  } else {
    previewHtml.value = ''
  }
}, { immediate: true })

async function loadPreview() {
  if (!props.plan?.report_filename) return
  previewLoading.value = true
  try {
    const r = await previewReport(props.plan.id)
    previewHtml.value = r.html || ''
  } catch (e) {
    // 预览失败静默处理（可能尚未生成）
    previewHtml.value = ''
  } finally {
    previewLoading.value = false
  }
}
async function onRefreshPreview() {
  await loadPreview()
}

async function onGenerate() {
  genLoading.value = true
  try {
    const p = await generateReport(props.plan.id)
    Object.assign(props.plan, p)
    ElMessage.success('报告已生成')
    await nextTick()
    await loadPreview()
    emit('saved')
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    genLoading.value = false
  }
}
async function onDownload() {
  try {
    const blob = await downloadReport(props.plan.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = props.plan.report_filename || `报告_${props.plan.id}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败：' + (e.response?.data?.detail || e.message))
  }
}
async function onUploadChange(file) {
  try {
    const p = await uploadReport(props.plan.id, file.raw)
    Object.assign(props.plan, p)
    ElMessage.success('报告已上传')
    await nextTick()
    await loadPreview()
    emit('saved')
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  }
}
async function onDelete() {
  delLoading.value = true
  try {
    const p = await deleteReport(props.plan.id)
    Object.assign(props.plan, p)
    previewHtml.value = ''
    ElMessage.success('报告已删除')
    emit('saved')
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  } finally {
    delLoading.value = false
  }
}
</script>

<style scoped>
.preview-box { max-height: 65vh; overflow: auto; border: 1px solid #dcdfe6; border-radius: 4px;
  padding: 12px; background: #fff; }
.preview-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px;
  font-size: 13px; font-weight: 600; color: #333; }
.preview-empty { padding: 30px; text-align: center; color: #999; background: #fafbfc;
  border: 1px dashed #dcdfe6; border-radius: 4px; }
.yes { color: #27ae60; font-weight: 700; }
.no { color: #c0392b; font-weight: 700; }
</style>
