<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      :extra-params="docExtraParams"
      search-placeholder="搜索文件名 / 标题..."
      :show-add="false"
      @delete="onDelete"
    >
      <template #toolbar-extra>
        <el-select v-model="docExtraParams.category" placeholder="全部分类" clearable style="width: 150px" @change="onFilterChange">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-button type="primary" :icon="Upload" @click="openUpload">上传文件</el-button>
      </template>

      <template #row-extra="{ row }">
        <el-button v-if="row.file_path" link type="success" @click="onPreview(row)">预览</el-button>
        <el-button v-if="row.file_path" link type="primary" @click="onDownload(row)">下载</el-button>
        <el-button link type="warning" @click="openVersion(row)">新版本</el-button>
      </template>
    </CrudTable>

    <!-- 上传 -->
    <el-dialog v-model="uploadOpen" title="上传文件" width="620px" @open="onUploadOpen">
      <el-form label-width="90px">
        <el-form-item label="文件" required>
          <FileUpload :key="uploadKey" @change="(f) => (uploadFile = f)" />
        </el-form-item>
        <el-form-item label="标题">
          <el-input v-model="uploadForm.title" placeholder="留空则使用文件名" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="uploadForm.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="uploadForm.status" style="width: 100%">
            <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="uploadForm.description" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="版本备注">
          <el-input v-model="uploadForm.note" placeholder="初始版本" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadOpen = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="onUpload">上传</el-button>
      </template>
    </el-dialog>

    <!-- 新版本 -->
    <el-dialog v-model="versionOpen" :title="`版本管理 - ${versionDoc?.title || ''}`" width="640px" @open="onVersionOpen">
      <el-table :data="versions" border stripe>
        <el-table-column prop="version" label="版本" width="90" />
        <el-table-column prop="uploader" label="上传人" width="110" />
        <el-table-column prop="note" label="备注" min-width="160" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" min-width="160" />
      </el-table>
      <el-divider>上传新版本</el-divider>
      <el-form label-width="90px">
        <el-form-item label="文件" required>
          <FileUpload :key="versionKey" @change="(f) => (versionFile = f)" />
        </el-form-item>
        <el-form-item label="版本备注">
          <el-input v-model="versionNote" placeholder="如：修正错误" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="versionOpen = false">关闭</el-button>
        <el-button type="primary" :loading="versioning" @click="onNewVersion">提交新版本</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import CrudTable from '../../components/CrudTable.vue'
import FileUpload from '../../components/FileUpload.vue'
import {
  listDocuments, uploadDocument, newVersion, listVersions,
  deleteDocument, fetchDocumentBlob, downloadBlob, previewBlob,
} from '../../api/documents'

const crud = ref(null)
const categories = ['通用SOP', '项目SOP', '仪器SOP', '记录表格', '项目说明书']
const statuses = ['草稿', '生效', '作废']

const docExtraParams = reactive({ category: '' })

const columns = [
  { prop: 'title', label: '标题', minWidth: 180 },
  { prop: 'category', label: '分类', width: 110 },
  {
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 生效: 'success', 草稿: 'info', 作废: 'danger' }
      return `<el-tag type="${map[row.status] || 'info'}" size="small">${row.status || '-'}</el-tag>`
    },
  },
  { prop: 'version', label: '版本', width: 80 },
  { prop: 'uploader', label: '上传人', width: 100 },
  {
    prop: 'file_path', label: '文件', width: 90,
    formatter: (row) => (row.file_path ? '<el-tag type="success" size="small">有</el-tag>' : '<el-tag type="info" size="small">无</el-tag>'),
  },
  { prop: 'created_at', label: '上传时间', minWidth: 160 },
]

function fetch(params) {
  return listDocuments(params)
}
function onFilterChange() {
  crud.value?.refresh()
}

async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.title}」？该操作不可恢复。`, '提示', { type: 'warning' })
  await deleteDocument(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}

async function onPreview(row) {
  try {
    const blob = await fetchDocumentBlob(row.id, 'preview')
    previewBlob(blob)
  } catch (e) {
    ElMessage.error('文件不存在或预览失败')
  }
}
async function onDownload(row) {
  try {
    const blob = await fetchDocumentBlob(row.id, 'download')
    downloadBlob(blob, row.original_filename || row.title)
  } catch (e) {
    ElMessage.error('文件不存在或下载失败')
  }
}

// 上传
const uploadOpen = ref(false)
const uploadKey = ref(0)
const uploading = ref(false)
const uploadFile = ref(null)
const uploadForm = reactive({ title: '', category: '通用SOP', status: '生效', description: '', note: '' })

function openUpload() {
  uploadOpen.value = true
}
function onUploadOpen() {
  uploadKey.value++
  uploadFile.value = null
  Object.assign(uploadForm, { title: '', category: '通用SOP', status: '生效', description: '', note: '' })
}
async function onUpload() {
  if (!uploadFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  const fd = new FormData()
  fd.append('file', uploadFile.value)
  fd.append('title', uploadForm.title)
  fd.append('category', uploadForm.category)
  fd.append('status', uploadForm.status)
  fd.append('description', uploadForm.description)
  fd.append('note', uploadForm.note)
  uploading.value = true
  try {
    await uploadDocument(fd)
    ElMessage.success('上传成功')
    uploadOpen.value = false
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

// 版本
const versionOpen = ref(false)
const versionKey = ref(0)
const versioning = ref(false)
const versionDoc = ref(null)
const versions = ref([])
const versionFile = ref(null)
const versionNote = ref('')

function openVersion(row) {
  versionDoc.value = row
  versionOpen.value = true
}
async function onVersionOpen() {
  versionKey.value++
  versionFile.value = null
  versionNote.value = ''
  try {
    versions.value = await listVersions(versionDoc.value.id)
  } catch (e) {
    versions.value = []
  }
}
async function onNewVersion() {
  if (!versionFile.value) {
    ElMessage.warning('请先选择文件')
    return
  }
  const fd = new FormData()
  fd.append('file', versionFile.value)
  fd.append('note', versionNote.value)
  versioning.value = true
  try {
    await newVersion(versionDoc.value.id, fd)
    ElMessage.success('新版本已提交')
    versionFile.value = null
    versionNote.value = ''
    versions.value = await listVersions(versionDoc.value.id)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('提交失败')
  } finally {
    versioning.value = false
  }
}
</script>

<style scoped>
.page {
  height: 100%;
}
</style>
