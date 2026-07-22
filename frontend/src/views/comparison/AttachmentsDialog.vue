<template>
  <el-dialog :model-value="visible" :title="`原始结果 · ${plan?.year || ''} 半年${plan?.half || ''}`"
    width="980px" top="3vh" @update:model-value="(v) => !v && $emit('close')">
    <div v-if="loading" v-loading="true" style="height:300px" />
    <template v-else>
      <div style="margin-bottom:10px;display:flex;align-items:center;gap:12px;flex-wrap:wrap">
        <el-upload :show-file-list="false" accept="image/*,application/pdf,.doc,.docx,.xls,.xlsx"
          :before-upload="onUpload" multiple :disabled="uploading">
          <el-button type="primary" :loading="uploading">上传原始结果（可多选）</el-button>
        </el-upload>
        <span style="color:#888;font-size:12px">支持 图片 / PDF / Word / Excel；上传后可在下方预览、下载或删除</span>
      </div>

      <div v-if="!items.length" class="empty">暂无附件。点击上方按钮上传原始结果扫描件或电子报告。</div>

      <div v-else class="grid">
        <div v-for="a in items" :key="a.id" class="card">
          <div class="thumb">
            <img v-if="a.file_type === 'image'" :src="attachmentUrl(a.id, true)" :alt="a.original_name" @click="openPreview(a)" />
            <div v-else-if="a.file_type === 'pdf'" class="icon pdf" @click="openPreview(a)">
              <el-icon :size="48"><Document /></el-icon>
              <div class="ic-text">PDF</div>
            </div>
            <div v-else class="icon other" @click="openPreview(a)">
              <el-icon :size="48"><Document /></el-icon>
              <div class="ic-text">{{ a.file_type === 'doc' ? '文档' : '文件' }}</div>
            </div>
          </div>
          <div class="meta">
            <div class="name" :title="a.original_name">{{ a.original_name }}</div>
            <div class="sub">{{ formatSize(a.size_bytes) }} · {{ a.uploaded_by || '匿名' }} · {{ formatDate(a.uploaded_at) }}</div>
          </div>
          <div class="ops">
            <el-button size="small" @click="openPreview(a)">预览</el-button>
            <el-button size="small" @click="onDownload(a)">下载</el-button>
            <el-button size="small" type="danger" @click="onDelete(a)">删除</el-button>
          </div>
        </div>
      </div>
    </template>

    <!-- 内嵌预览（支持 图片/PDF/Word/Excel，与文档模块一致） -->
    <AttachmentPreview v-model:visible="previewVisible" :file="previewing" :get-url="attachmentUrl" @download="onDownload" />
  </el-dialog>
</template>

<script setup>
import { ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listAttachments, uploadAttachments, attachmentUrl, deleteAttachment } from '../../api/comparison'
import AttachmentPreview from '../../components/AttachmentPreview.vue'

const props = defineProps({
  visible: Boolean,
  plan: { type: Object, default: null },
})
const emit = defineEmits(['close', 'changed'])

const loading = ref(false)
const uploading = ref(false)
const items = ref([])
const previewVisible = ref(false)
const previewing = ref(null)

watch(() => props.visible, async (v) => { if (v && props.plan) await load() }, { immediate: true })

async function load() {
  loading.value = true
  try {
    const r = await listAttachments(props.plan.id)
    items.value = r.items || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function onUpload(file) {
  // 一次选一个就触发一次；通过多次调用累积上传
  uploading.value = true
  try {
    const r = await uploadAttachments(props.plan.id, [file])
    ElMessage.success(`已上传 ${r.total || 1} 个文件`)
    await load()
    emit('changed')
  } catch (e) {
    ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message))
  } finally {
    uploading.value = false
  }
  return false
}

function openPreview(a) { previewing.value = a; previewVisible.value = true }
function closePreview() { previewVisible.value = false; previewing.value = null }

async function onDownload(a) {
  // 通过 fetch 拿到 blob，再用 <a download> 触发下载
  try {
    const res = await fetch(attachmentUrl(a.id, false), { credentials: 'include' })
    if (!res.ok) throw new Error('下载失败')
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = a.original_name || `attachment_${a.id}`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (e) {
    ElMessage.error('下载失败：' + e.message)
  }
}

async function onDelete(a) {
  try {
    await ElMessageBox.confirm(`确认删除附件「${a.original_name}」？`, '警告', { type: 'warning' })
  } catch { return }
  try {
    await deleteAttachment(a.id)
    ElMessage.success('已删除')
    if (previewing.value && previewing.value.id === a.id) closePreview()
    await load()
    emit('changed')
  } catch (e) {
    ElMessage.error('删除失败：' + (e.response?.data?.detail || e.message))
  }
}

function formatSize(n) {
  if (!n) return '-'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}
function formatDate(s) {
  if (!s) return ''
  return s.replace('T', ' ').slice(0, 16)
}
</script>

<style scoped>
.empty { padding: 40px; text-align: center; color: #999; background: #fafbfc; border-radius: 6px; }
.grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap: 14px; }
.card { border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; background: #fff;
  display: flex; flex-direction: column; }
.thumb { width: 100%; height: 150px; background: #f5f7fa; display: flex; align-items: center; justify-content: center; cursor: pointer; overflow: hidden; }
.thumb img { max-width: 100%; max-height: 100%; object-fit: contain; }
.icon { color: #5e6d82; display: flex; flex-direction: column; align-items: center; gap: 6px; }
.icon.pdf { color: #c0392b; }
.ic-text { font-size: 12px; font-weight: 700; }
.meta { padding: 8px 10px; }
.name { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sub { font-size: 11px; color: #888; margin-top: 2px; }
.ops { display: flex; gap: 4px; padding: 6px 8px 8px; border-top: 1px solid #f0f0f0; }
.preview-wrap { min-height: 300px; }
.preview-wrap img { max-width: 100%; }
.other-preview { text-align: center; padding: 40px; color: #888; }
.other-preview p { margin: 12px 0; }
</style>
