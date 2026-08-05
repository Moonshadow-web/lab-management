<template>
  <div class="page">
    <div class="bar">
      <span class="hint">CNAS / 行标 / 申请书附件等医学实验室认可规范文件，可在线预览或下载。</span>
      <div class="cat-filter">
        <button class="cat-pill" :class="{ active: catFilter === '' }" @click="catFilter = ''">
          全部 <span class="num">{{ rows.length }}</span>
        </button>
        <button
          v-for="c in categories"
          :key="c"
          class="cat-pill"
          :class="[catCls(c), { active: catFilter === c }]"
          @click="catFilter = (catFilter === c ? '' : c)"
        >
          {{ c }} <span class="num">{{ countOf(c) }}</span>
        </button>
      </div>
    </div>
    <el-table v-loading="loading" :data="displayRows" border stripe>
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column prop="code" label="代号" width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.code">{{ row.code }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="280" show-overflow-tooltip />
      <el-table-column prop="category" label="类别" width="140">
        <template #default="{ row }">
          <el-tag size="small" :type="catTagType(row.category)">{{ row.category || '其他' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="大小" width="110" align="right">
        <template #default="{ row }">{{ fmtSize(row.file_size) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="170" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="success" :icon="View" :loading="row._previewing" @click="onPreview(row)">预览</el-button>
          <el-button link type="primary" :icon="Download" @click="onDownload(row)">下载</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog
      :model-value="previewVisible"
      :title="previewTitle"
      width="90%" top="2vh" append-to-body
      @update:model-value="(v) => { if (!v) closePreview() }"
    >
      <div v-if="previewLoading" v-loading="true" style="height: 75vh" />
      <template v-else>
        <iframe v-if="previewMode === 'pdf'" :src="previewSrc" style="width: 100%; height: 75vh; border: 0" />
        <div v-else-if="previewMode === 'html'" class="preview-html" v-html="previewHtml" />
        <div v-else class="other-preview">
          <el-icon :size="64"><Document /></el-icon>
          <p>{{ previewMsg }}</p>
          <el-button type="primary" @click="onDownload(previewFile)">下载 {{ previewFile?.original_filename }}</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { View, Download, Document } from '@element-plus/icons-vue'
import { listCnasStandards, fetchCnasStandardBlob, downloadStandard } from '../../api/cnasStandards'
import mammoth from 'mammoth'

const rows = ref([])
const loading = ref(false)
const catFilter = ref('')

const categories = computed(() => {
  const seen = []
  for (const r of rows.value) {
    const c = r.category || '其他'
    if (!seen.includes(c)) seen.push(c)
  }
  return seen
})

const displayRows = computed(() =>
  catFilter.value ? rows.value.filter((r) => r.category === catFilter.value) : rows.value
)

function countOf(c) {
  return rows.value.filter((r) => (r.category || '其他') === c).length
}

function catCls(c) {
  if (c === 'CNAS认可规范') return 'c-danger'
  if (c === 'CNAS附件表') return 'c-warning'
  if (c === '行标') return 'c-success'
  return 'c-info'
}

function catTagType(c) {
  if (c === 'CNAS认可规范') return 'danger'
  if (c === 'CNAS附件表') return 'warning'
  if (c === '行标') return 'success'
  return 'info'
}

function fmtSize(n) {
  n = Number(n) || 0
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
}

// ===== 预览（dialog）：pdf 内联、docx 用 mammoth 渲染、其余下载 =====
const previewVisible = ref(false)
const previewLoading = ref(false)
const previewMode = ref('other') // pdf | html | other
const previewSrc = ref('')
const previewHtml = ref('')
const previewMsg = ref('')
const previewFile = ref(null)
const previewTitle = computed(() => previewFile.value?.original_filename || '预览')

function extOf(name) {
  const m = (name || '').toLowerCase().match(/\.([a-z0-9]+)$/)
  return m ? m[1] : ''
}

async function onPreview(row) {
  previewFile.value = row
  previewVisible.value = true
  previewLoading.value = true
  previewMode.value = 'other'
  previewSrc.value = ''
  previewHtml.value = ''
  const ext = extOf(row.original_filename)
  try {
    if (ext === 'pdf') {
      const blob = await fetchCnasStandardBlob(row.id, 'preview')
      previewSrc.value = URL.createObjectURL(blob)
      previewMode.value = 'pdf'
    } else if (ext === 'docx') {
      const blob = await fetchCnasStandardBlob(row.id, 'preview')
      const buf = await blob.arrayBuffer()
      const res = await mammoth.convertToHtml({ arrayBuffer: buf })
      previewHtml.value = res.value || '<p style="color:#909399">（文档内容为空）</p>'
      previewMode.value = 'html'
    } else {
      previewMsg.value = '该类型文件无法在浏览器内直接预览，请点击下载查看。'
      previewMode.value = 'other'
    }
  } catch (e) {
    console.error(e)
    previewMsg.value = '预览失败：' + (e && e.message ? e.message : '请下载后查看')
    previewMode.value = 'other'
  } finally {
    previewLoading.value = false
  }
}

function closePreview() {
  if (previewSrc.value) {
    URL.revokeObjectURL(previewSrc.value)
    previewSrc.value = ''
  }
  previewVisible.value = false
}

async function onDownload(row) {
  try {
    await downloadStandard(row.id, row.original_filename || `${row.code || row.name}.pdf`)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function load() {
  loading.value = true
  try {
    rows.value = await listCnasStandards()
  } catch (e) {
    ElMessage.error('加载规范文件失败')
    rows.value = []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.page {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.bar {
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.hint {
  font-size: 13px;
  color: #909399;
}
.muted {
  color: #c0c4cc;
}
.cat-filter {
  display: flex;
  gap: 8px;
  margin-left: 12px;
  flex-wrap: wrap;
}
.cat-pill {
  border: 1px solid #dcdfe6;
  background: #fff;
  color: #606266;
  padding: 5px 14px;
  border-radius: 16px;
  cursor: pointer;
  font-size: 13px;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  transition: all 0.15s;
}
.cat-pill:hover {
  border-color: #c0c4cc;
}
.cat-pill .num {
  font-size: 12px;
  opacity: 0.75;
}
.cat-pill.active {
  color: #fff;
  border-color: transparent;
}
.cat-pill.active.c-danger {
  background: #f56c6c;
}
.cat-pill.active.c-warning {
  background: #e6a23c;
}
.cat-pill.active.c-success {
  background: #67c23a;
}
.cat-pill.active.c-info {
  background: #909399;
}
.preview-html {
  max-height: 75vh;
  overflow: auto;
  background: #fff;
  padding: 16px;
  line-height: 1.7;
}
.preview-html :deep(table) {
  border-collapse: collapse;
}
.preview-html :deep(th),
.preview-html :deep(td) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.preview-html :deep(th) {
  background: #f5f7fa;
}
.preview-html :deep(pre) {
  white-space: pre-wrap;
  word-break: break-all;
}
.preview-html :deep(img) {
  max-width: 100%;
}
.other-preview {
  text-align: center;
  padding: 40px;
  color: #888;
}
.other-preview p {
  margin: 12px 0;
}
</style>
