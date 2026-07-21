<template>
  <div class="att-wrap">
    <div class="att-head">
      <span class="att-title">原始报告存档 <el-tag size="small" type="info">{{ items.length }}</el-tag></span>
      <el-upload
        v-if="canWrite"
        :auto-upload="true"
        :show-file-list="false"
        :multiple="true"
        :http-request="onUpload"
        :accept="accept"
        :disabled="uploading"
      >
        <el-button size="small" type="primary" :icon="Upload" :loading="uploading">上传原始报告</el-button>
      </el-upload>
    </div>

    <el-table v-if="items.length" :data="items" border size="small" style="margin-top:8px">
      <el-table-column prop="original_name" label="文件名" min-width="200" show-overflow-tooltip />
      <el-table-column label="类型" width="76">
        <template #default="{ row }">
          <el-tag size="small" :type="typeTag(row.file_type)">{{ row.file_type }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="96">
        <template #default="{ row }">{{ fmtSize(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="uploaded_by" label="上传人" width="96" />
      <el-table-column label="上传时间" width="150">
        <template #default="{ row }">{{ fmtTime(row.uploaded_at) }}</template>
      </el-table-column>
      <el-table-column label="操作" min-width="230">
        <template #default="{ row }">
          <el-button size="small" :icon="View" @click="onPreview(row)">预览</el-button>
          <el-button size="small" :icon="Download" @click="onDownload(row)">下载</el-button>
          <el-button size="small" :icon="Printer" @click="onPrint(row)" :disabled="!canPrint(row)">打印</el-button>
          <el-button size="small" type="danger" :icon="Delete" @click="onDelete(row)" v-if="canWrite">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
    <div v-else class="att-empty">暂无原始报告存档</div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, View, Download, Printer, Delete } from '@element-plus/icons-vue'
import {
  listAttachments, uploadAttachments, attachmentUrl, deleteAttachment,
} from '../api/comparison'
import {
  listInterlabAttachments, uploadInterlabAttachments, interlabAttachmentUrl, deleteInterlabAttachment,
} from '../api/interlab'

const props = defineProps({
  // 计划/比对 id
  planId: { type: [Number, String], required: true },
  // 'comparison' | 'interlab'
  module: { type: String, default: 'comparison' },
  // 是否允许上传/删除（由父组件按权限传入）
  canWrite: { type: Boolean, default: true },
  // 接受的文件类型，默认不限制
  accept: { type: String, default: '' },
})

const items = ref([])
const uploading = ref(false)

const api = computed(() => {
  if (props.module === 'interlab') {
    return {
      list: listInterlabAttachments,
      upload: uploadInterlabAttachments,
      url: interlabAttachmentUrl,
      del: deleteInterlabAttachment,
    }
  }
  return {
    list: listAttachments,
    upload: uploadAttachments,
    url: attachmentUrl,
    del: deleteAttachment,
  }
})

async function load() {
  if (!props.planId) { items.value = []; return }
  try {
    const r = await api.value.list(props.planId)
    items.value = r.items || []
  } catch (e) {
    items.value = []
  }
}

watch(() => props.planId, () => load(), { immediate: true })

async function onUpload(option) {
  uploading.value = true
  try {
    await api.value.upload(props.planId, [option.file])
    ElMessage.success('已上传：' + option.file.name)
    await load()
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
    option.onSuccess?.()
  }
}

function onPreview(row) {
  window.open(api.value.url(row.id, true), '_blank')
}

function onDownload(row) {
  window.open(api.value.url(row.id, false), '_blank')
}

function onPrint(row) {
  const w = window.open(api.value.url(row.id, true), '_blank')
  if (!w) return
  w.onload = () => { setTimeout(() => { try { w.print() } catch (_) {} }, 400) }
}

async function onDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除附件「${row.original_name}」？`, '删除', { type: 'warning' })
    await api.value.del(row.id)
    ElMessage.success('已删除')
    await load()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

function fmtSize(b) {
  if (b == null) return '-'
  if (b < 1024) return b + ' B'
  if (b < 1024 * 1024) return (b / 1024).toFixed(1) + ' KB'
  return (b / 1024 / 1024).toFixed(2) + ' MB'
}
function fmtTime(t) {
  if (!t) return '-'
  return String(t).replace('T', ' ').slice(0, 19)
}
function canPrint(row) {
  return row.file_type === 'image' || row.file_type === 'pdf'
}
function typeTag(t) {
  if (t === 'image') return 'success'
  if (t === 'pdf') return 'danger'
  if (t === 'doc') return 'primary'
  return 'info'
}

defineExpose({ load })
</script>

<style scoped>
.att-wrap { border: 1px solid #ebeef5; border-radius: 6px; padding: 10px 12px; background: #fafbfc; }
.att-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.att-title { font-size: 13px; font-weight: 600; color: #333; }
.att-empty { padding: 18px; text-align: center; color: #999; font-size: 13px; }
</style>
