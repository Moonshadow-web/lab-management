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
    <div v-if="uploading" style="margin:6px 0 10px;">
      <el-progress :percentage="uploadPct" :status="uploadPct === 100 ? 'success' : ''" />
      <div style="font-size:12px;color:#909399;margin-top:2px;">正在上传：{{ uploadingName }}（{{ uploadPct }}%）</div>
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
    <AttachmentPreview
      :visible="previewVisible"
      :file="previewFile"
      :get-url="(id, inline) => eduAttachmentUrl(id, inline)"
      @update:visible="(v) => (previewVisible = v)"
      @download="download"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import { listEduAttachments, uploadEduAttachments, eduAttachmentUrl, deleteEduAttachment, initChunkUpload, uploadChunk, completeChunkUpload } from '../../api/education'
import AttachmentPreview from '../../components/AttachmentPreview.vue'

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
const previewVisible = ref(false)
const previewFile = ref(null)
const emit = defineEmits(['uploaded'])

// 大文件分片上传状态
const uploading = ref(false)
const uploadPct = ref(0)
const uploadingName = ref('')
const CHUNK_SIZE = 4 * 1024 * 1024     // 4MB / 片
const CHUNK_THRESHOLD = 8 * 1024 * 1024 // >8MB 走分片

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

async function uploadInChunks(file) {
  const init = await initChunkUpload({
    owner_type: props.ownerType,
    owner_id: props.ownerId,
    kind: props.kind,
    filename: file.name,
    size: file.size,
  })
  const uploadId = init.upload_id
  const total = Math.ceil(file.size / CHUNK_SIZE)
  for (let i = 0; i < total; i++) {
    const start = i * CHUNK_SIZE
    const blob = file.slice(start, Math.min(file.size, start + CHUNK_SIZE))
    await uploadChunk(uploadId, i, blob, `${file.name}.part${i}`)
    uploadPct.value = Math.round(((i + 1) * 100) / total)
  }
  return completeChunkUpload(uploadId)
}

async function onUpload(opt) {
  const file = opt.file
  try {
    if (file.size > 200 * 1024 * 1024) {
      ElMessage.error('文件超过 200MB 上限')
      return
    }
    if (file.size > CHUNK_THRESHOLD) {
      uploading.value = true
      uploadPct.value = 0
      uploadingName.value = file.name
      await uploadInChunks(file)
      uploadPct.value = 100
      ElMessage.success(`上传成功：${file.name}（${(file.size / 1024 / 1024).toFixed(1)} MB）`)
    } else {
      await uploadEduAttachments(props.ownerType, props.ownerId, props.kind, [file])
      ElMessage.success('上传成功')
    }
    refresh()
    emit('uploaded')
  } catch (e) {
    let msg = e.response?.data?.detail || e.message
    if (e.response?.status === 413) msg = '文件过大被服务器拒绝（413），请确认后端已更新'
    ElMessage.error('上传失败：' + msg)
  } finally {
    uploading.value = false
    uploadPct.value = 0
    uploadingName.value = ''
  }
}

function preview(row) { previewFile.value = row; previewVisible.value = true }
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
