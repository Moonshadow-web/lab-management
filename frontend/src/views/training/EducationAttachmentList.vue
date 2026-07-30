<template>
  <div class="edu-attachment-list">
    <div class="att-toolbar">
      <el-upload
        :show-file-list="false"
        :http-request="onUpload"
        :multiple="true"
        :accept="accept"
      >
        <el-button type="primary" :icon="Upload" :disabled="!canWrite">上传{{ label }}</el-button>
      </el-upload>
      <span class="att-hint" v-if="hint">{{ hint }}</span>
    </div>
    <el-table :data="items" border stripe size="small" v-loading="loading">
      <el-table-column prop="original_name" label="文件名" min-width="180" show-overflow-tooltip />
      <el-table-column prop="file_type" label="类型" width="80" align="center" />
      <el-table-column prop="size_bytes" label="大小" width="100" align="center">
        <template #default="{ row }">{{ formatSize(row.size_bytes) }}</template>
      </el-table-column>
      <el-table-column prop="uploaded_by" label="上传人" width="100" align="center" />
      <el-table-column prop="uploaded_at" label="上传时间" width="160" />
      <el-table-column label="操作" width="180" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="preview(row)">预览</el-button>
          <el-button link type="primary" @click="download(row)">下载</el-button>
          <el-button v-if="canWrite" link type="danger" @click="remove(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { listEduAttachments, uploadEduAttachments, eduAttachmentUrl, deleteEduAttachment } from '../../api/education'

const props = defineProps({
  ownerType: { type: String, required: true },
  ownerId: { type: [Number, String], required: true },
  kind: { type: String, default: 'other' },
  label: { type: String, default: '附件' },
  accept: { type: String, default: '' },
  hint: { type: String, default: '' },
  canWrite: { type: Boolean, default: true },
})

const items = ref([])
const loading = ref(false)

async function refresh() {
  if (!props.ownerId) { items.value = []; return }
  loading.value = true
  try {
    const res = await listEduAttachments(props.ownerType, props.ownerId, props.kind)
    items.value = res.items || []
  } finally {
    loading.value = false
  }
}

async function onUpload(opt) {
  try {
    await uploadEduAttachments(props.ownerType, props.ownerId, props.kind, [opt.file])
    ElMessage.success('上传成功')
    refresh()
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  }
}

function preview(row) { window.open(eduAttachmentUrl(row.id, true), '_blank') }
function download(row) { window.open(eduAttachmentUrl(row.id, false), '_blank') }
async function remove(row) {
  try {
    await ElMessageBox.confirm('确认删除该附件？', '提示', { type: 'warning' })
    await deleteEduAttachment(row.id)
    ElMessage.success('已删除')
    refresh()
  } catch (e) { if (e !== 'cancel') {} }
}

function formatSize(n) {
  if (!n) return '-'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

onMounted(refresh)
watch(() => [props.ownerId, props.ownerType, props.kind], refresh)
defineExpose({ refresh })
</script>

<style scoped>
.edu-attachment-list { padding: 4px 0; }
.att-toolbar { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.att-hint { color: #999; font-size: 12px; }
</style>
