<template>
  <div class="page">
    <div class="bar">
      <span class="hint">CNAS / 卫生行业（WS/T）医学实验室认可规范文件，可在线预览或下载。</span>
    </div>
    <el-table v-loading="loading" :data="rows" border stripe>
      <el-table-column type="index" label="#" width="50" align="center" />
      <el-table-column prop="code" label="代号" width="180" show-overflow-tooltip>
        <template #default="{ row }">
          <span v-if="row.code">{{ row.code }}</span>
          <span v-else class="muted">—</span>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="名称" min-width="280" show-overflow-tooltip />
      <el-table-column prop="category" label="类别" width="170">
        <template #default="{ row }">
          <el-tag size="small" :type="catTag(row.category)">{{ row.category || '其他' }}</el-tag>
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
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { View, Download } from '@element-plus/icons-vue'
import { listCnasStandards, previewStandard, downloadStandard } from '../../api/cnasStandards'

const rows = ref([])
const loading = ref(false)

function catTag(c) {
  if (c === 'CNAS认可规范') return 'danger'
  if (c === '卫生行业标准(WS/T)') return 'success'
  return 'info'
}

function fmtSize(n) {
  n = Number(n) || 0
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(2) + ' MB'
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

async function onPreview(row) {
  row._previewing = true
  try {
    await previewStandard(row.id)
  } catch (e) {
    ElMessage.error('预览失败，文件可能不存在')
  } finally {
    row._previewing = false
  }
}

async function onDownload(row) {
  try {
    await downloadStandard(row.id, row.original_filename || `${row.code || row.name}.pdf`)
  } catch (e) {
    ElMessage.error('下载失败')
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
}
.hint {
  font-size: 13px;
  color: #909399;
}
.muted {
  color: #c0c4cc;
}
</style>
