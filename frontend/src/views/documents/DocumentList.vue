<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      :extra-params="docExtraParams"
      search-placeholder="搜索文件名 / 标题 / 编号..."
      :show-add="false"
      :can-write="auth.canWrite('documents')"
      @edit="onEdit"
      @delete="onDelete"
    >
      <template #toolbar-extra>
        <el-select v-model="docExtraParams.category" placeholder="全部分类" clearable style="width: 150px" @change="onFilterChange">
          <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
        </el-select>
        <el-switch
          v-model="docExtraParams.hide_invalid"
          active-text="隐藏作废"
          inline-prompt
          style="--el-switch-on-color: #67c23a; margin-left: 4px"
          @change="onFilterChange"
        />
        <el-button :icon="Tickets" @click="openLog">更改日志</el-button>
        <el-button v-if="auth.canWrite('documents')" type="primary" :icon="Upload" @click="openUpload">上传文件</el-button>
      </template>

      <template #row-extra="{ row }">
        <el-button link type="info" @click="openDetail(row)">详情</el-button>
        <el-button v-if="row.file_path" link type="success" @click="onPreview(row)">预览</el-button>
        <el-button v-if="row.file_path" link type="primary" @click="onDownload(row)">下载</el-button>
        <el-button v-if="auth.canWrite('documents')" link type="warning" @click="openVersion(row)">新版本</el-button>
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
        <el-table-column prop="version" label="上传版" width="80" />
        <el-table-column prop="doc_version" label="文件版本" width="90" />
        <el-table-column prop="author" label="编写人" width="90" />
        <el-table-column prop="uploader" label="上传人" width="100" />
        <el-table-column prop="note" label="备注" min-width="120" show-overflow-tooltip />
        <el-table-column prop="created_at" label="时间" min-width="150" />
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

    <!-- 编辑 -->
    <el-dialog v-model="editOpen" :title="`编辑 - ${editForm.title || ''}`" width="640px">
      <el-form label-width="100px">
        <el-form-item label="标题">
          <el-input v-model="editForm.title" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="editForm.category" style="width: 100%">
            <el-option v-for="c in categories" :key="c" :label="c" :value="c" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option v-for="s in statuses" :key="s" :label="s" :value="s" />
          </el-select>
        </el-form-item>
        <el-divider>文件头元数据</el-divider>
        <el-form-item label="文件编号">
          <el-input v-model="editForm.doc_number" placeholder="如 BG-KS-CZ-901 / SM-SOP-572" />
        </el-form-item>
        <el-form-item label="文件版本号">
          <el-input v-model="editForm.doc_version" placeholder="如 01" />
        </el-form-item>
        <el-form-item label="修订号">
          <el-input v-model="editForm.revision" />
        </el-form-item>
        <el-form-item label="编写人">
          <el-input v-model="editForm.author" />
        </el-form-item>
        <el-form-item label="审核人">
          <el-input v-model="editForm.reviewer" />
        </el-form-item>
        <el-form-item label="批准人">
          <el-input v-model="editForm.approver" />
        </el-form-item>
        <el-form-item label="发布日期">
          <el-input v-model="editForm.issued_date" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="审核日期">
          <el-input v-model="editForm.audit_date" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="批准日期">
          <el-input v-model="editForm.approve_date" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="实施日期">
          <el-input v-model="editForm.effective_date" placeholder="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="editForm.description" type="textarea" :rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editOpen = false">取消</el-button>
        <el-button type="primary" :loading="editing" @click="onEditSubmit">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情抽屉：展示文件头元数据 + 版本历史 -->
    <el-drawer v-model="detailOpen" :title="detailDoc?.title || '文件详情'" size="580px">
      <template v-if="detailDoc">
        <el-descriptions :column="2" border>
          <el-descriptions-item label="分类">{{ detailDoc.category }}</el-descriptions-item>
          <el-descriptions-item label="子类">{{ recordSubType(detailDoc.doc_number) || '—' }}</el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="statusTag(detailDoc.status)" size="small">{{ detailDoc.status || '-' }}</el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="文件编号">{{ detailDoc.doc_number || '—' }}</el-descriptions-item>
          <el-descriptions-item label="文件版本号">{{ detailDoc.doc_version || '—' }}</el-descriptions-item>
          <el-descriptions-item label="修订号">{{ detailDoc.revision || '—' }}</el-descriptions-item>
          <el-descriptions-item label="编写人">{{ detailDoc.author || '—' }}</el-descriptions-item>
          <el-descriptions-item label="审核人">{{ detailDoc.reviewer || '—' }}</el-descriptions-item>
          <el-descriptions-item label="批准人">{{ detailDoc.approver || '—' }}</el-descriptions-item>
          <el-descriptions-item label="发布日期">{{ detailDoc.issued_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="审核日期">{{ detailDoc.audit_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="批准日期">{{ detailDoc.approve_date || '—' }}</el-descriptions-item>
          <el-descriptions-item label="实施日期">{{ detailDoc.effective_date || '—' }}</el-descriptions-item>
        </el-descriptions>

        <p v-if="detailDoc.description" class="desc-block">说明：{{ detailDoc.description }}</p>
        <p v-if="!hasMeta" class="desc-block tip">
          该文件无可解析的表头元数据（如记录表格、PDF 或旧版 .doc 文档）。修改后重新上传新版本可自动记录。
        </p>

        <el-divider>版本历史</el-divider>
        <el-table :data="detailVersions" border stripe size="small">
          <el-table-column prop="version" label="上传版" width="80" />
          <el-table-column prop="doc_version" label="文件版本" width="90" />
          <el-table-column prop="author" label="编写人" width="90" />
          <el-table-column prop="uploader" label="上传人" width="100" />
          <el-table-column prop="note" label="备注" min-width="110" show-overflow-tooltip />
          <el-table-column prop="created_at" label="时间" min-width="150" />
        </el-table>
      </template>
    </el-drawer>

    <!-- 文档正文预览：docx 由 mammoth 转网页在浏览器内显示；PDF 走浏览器原生阅读器 -->
    <el-dialog v-model="previewOpen" :title="previewTitle" width="82%" top="4vh" append-to-body>
      <div v-loading="previewing" class="doc-preview" v-html="previewHtml"></div>
    </el-dialog>

    <!-- 文件更改日志 -->
    <el-dialog v-model="logOpen" title="文件更改日志" width="860px" @open="onLogOpen">
      <div class="log-toolbar">
        <el-input
          v-model="logQuery.q"
          placeholder="搜索文件名称 / 编码 / 申请人"
          style="width: 260px"
          clearable
          @keyup.enter="fetchLogs"
          @clear="fetchLogs"
        />
        <el-select v-model="logQuery.change_type" placeholder="全部类型" clearable style="width: 140px" @change="fetchLogs">
          <el-option label="新增" value="新增" />
          <el-option label="修改" value="修改" />
          <el-option label="作废" value="作废" />
        </el-select>
        <el-checkbox v-model="logQuery.only_unhandled" @change="fetchLogs" border>仅看未处理</el-checkbox>
        <el-button @click="fetchLogs">查询</el-button>
        <el-button type="primary" :icon="Download" :loading="exporting" @click="onExportLog">导出申请单</el-button>
      </div>
      <el-table :data="logs" border stripe v-loading="logLoading" height="420">
        <el-table-column prop="file_name" label="文件名称" min-width="190" show-overflow-tooltip />
        <el-table-column prop="file_code" label="文件编码" width="140" show-overflow-tooltip />
        <el-table-column prop="change_type" label="更改类型" width="88">
          <template #default="{ row }">
            <el-tag :type="logTypeTag(row.change_type)" size="small">{{ row.change_type }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="change_date" label="日期" width="110" />
        <el-table-column prop="operator" label="申请人" width="96" />
        <el-table-column label="已处理" width="118">
          <template #default="{ row }">
            <el-tag v-if="row.handled" type="success" size="small" effect="dark">已处理</el-tag>
            <el-button v-if="!row.handled" type="success" link size="small" :loading="row._toggling" @click="toggleHandled(row, true)">标记已处理</el-button>
            <el-button v-else type="info" link size="small" :loading="row._toggling" @click="toggleHandled(row, false)">撤销</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination
        class="log-pager"
        layout="total, prev, pager, next"
        :total="logTotal"
        :page-size="logPageSize"
        :current-page="logPage"
        @current-change="(p) => { logPage = p; fetchLogs() }"
      />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Upload, Tickets, Download } from '@element-plus/icons-vue'
import CrudTable from '../../components/CrudTable.vue'
import FileUpload from '../../components/FileUpload.vue'
import {
  listDocuments, getDocument, uploadDocument, updateDocument, newVersion, listVersions,
  deleteDocument, fetchDocumentBlob, downloadBlob, previewBlob,
  listChangeLogs, exportChangeLogs, setChangeLogHandled,
} from '../../api/documents'
import mammoth from 'mammoth'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const categories = ['通用SOP', '项目SOP', '仪器SOP', '记录表格', '项目说明书']
const statuses = ['草稿', '生效', '作废']

const docExtraParams = reactive({ category: '', hide_invalid: false })

const columns = computed(() => {
  const cols = [
    { prop: 'title', label: '标题', minWidth: 220 },
    { prop: 'category', label: '分类', width: 100 },
  ]
  // 仅记录表格显示「子类」列
  if (docExtraParams.category === '记录表格') {
    cols.push({ prop: 'sub_type', label: '子类', width: 100, formatter: (row) => subTypeTag(row.doc_number) })
  }
  cols.push({
    prop: 'status', label: '状态', width: 90,
    formatter: (row) => {
      const map = { 生效: 'success', 草稿: 'info', 作废: 'danger' }
      return `<el-tag type="${map[row.status] || 'info'}" size="small">${row.status || '-'}</el-tag>`
    },
  })
  // 项目说明书不显示编号/版本号/编写人（子类本就不显示）
  if (docExtraParams.category !== '项目说明书') {
    cols.push(
      { prop: 'doc_number', label: '编号', width: 160, ellipsis: true, formatter: (row) => row.doc_number || '—' },
      { prop: 'doc_version', label: '版本号', width: 90, formatter: (row) => row.doc_version || '—' },
      { prop: 'author', label: '编写人', width: 90, formatter: (row) => row.author || '—' },
    )
  }
  cols.push(
    { prop: 'effective_date', label: '实施日期', width: 120, formatter: (row) => row.effective_date || '—' },
  )
  return cols
})

function statusTag(s) {
  return { 生效: 'success', 草稿: 'info', 作废: 'danger' }[s] || 'info'
}

// 记录表格按编号段归类：KS=科室共用，GL=管理类，CZ=操作类，PX=培训类（KS 优先）
function recordSubType(docNumber) {
  if (!docNumber) return ''
  const u = String(docNumber).toUpperCase()
  if (u.includes('KS')) return '科室共用'
  if (u.includes('GL')) return '管理类'
  if (u.includes('CZ')) return '操作类'
  if (u.includes('PX')) return '培训类'
  return ''
}
function subTypeTag(docNumber) {
  const t = recordSubType(docNumber)
  if (!t) return '—'
  const map = { 科室共用: '', 管理类: 'success', 操作类: 'warning', 培训类: 'info' }
  return `<el-tag type="${map[t] || 'info'}" size="small">${t}</el-tag>`
}

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

// 编辑
const editOpen = ref(false)
const editing = ref(false)
const editForm = reactive({
  id: null, title: '', category: '通用SOP', status: '生效',
  doc_number: '', doc_version: '', revision: '', author: '', reviewer: '', approver: '',
  issued_date: '', audit_date: '', approve_date: '', effective_date: '', description: '',
})
function onEdit(row) {
  Object.assign(editForm, {
    id: row.id,
    title: row.title || '',
    category: row.category || '通用SOP',
    status: row.status || '生效',
    doc_number: row.doc_number || '',
    doc_version: row.doc_version || '',
    revision: row.revision || '',
    author: row.author || '',
    reviewer: row.reviewer || '',
    approver: row.approver || '',
    issued_date: row.issued_date || '',
    audit_date: row.audit_date || '',
    approve_date: row.approve_date || '',
    effective_date: row.effective_date || '',
    description: row.description || '',
  })
  editOpen.value = true
}
async function onEditSubmit() {
  if (!editForm.id) return
  editing.value = true
  try {
    const payload = {
      title: editForm.title,
      category: editForm.category,
      status: editForm.status,
      doc_number: editForm.doc_number,
      doc_version: editForm.doc_version,
      revision: editForm.revision,
      author: editForm.author,
      reviewer: editForm.reviewer,
      approver: editForm.approver,
      issued_date: editForm.issued_date,
      audit_date: editForm.audit_date,
      approve_date: editForm.approve_date,
      effective_date: editForm.effective_date,
      description: editForm.description,
    }
    await updateDocument(editForm.id, payload)
    ElMessage.success('已保存')
    editOpen.value = false
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    editing.value = false
  }
}

// 正文预览：docx 用 mammoth 在浏览器内转网页显示；PDF 走浏览器原生；其他回退原行为
const previewOpen = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')
const previewing = ref(false)
async function onPreview(row) {
  if (!row.file_path) {
    ElMessage.warning('该文件无正文可预览')
    return
  }
  const ext = (row.file_path.split('.').pop() || '').toLowerCase()
  // PDF：浏览器内置阅读器可直接渲染
  if (ext === 'pdf') {
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      previewBlob(blob)
    } catch (e) {
      ElMessage.error('文件不存在或预览失败')
    }
    return
  }
  // docx：前端 mammoth 转换为 HTML，在浏览器内显示（不再调用 Word/WPS）
  if (ext === 'docx') {
    previewOpen.value = true
    previewTitle.value = row.title || '预览'
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      const arrayBuffer = await blob.arrayBuffer()
      const res = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = res.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // xlsx/xls：前端用 exceljs 读 arrayBuffer 转 HTML 表格渲染（与 docx 一致），避免二进制被当文本打开乱码
  if (ext === 'xlsx' || ext === 'xls') {
    previewOpen.value = true
    previewTitle.value = row.title || '预览'
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      const buf = await blob.arrayBuffer()
      const head = new Uint8Array(buf.slice(0, 4))
      const isZip = head[0] === 0x50 && head[1] === 0x4B // PK -> xlsx
      const isOle = head[0] === 0xD0 && head[1] === 0xCF && head[2] === 0x11 && head[3] === 0xE0 // 真 .xls(BIFF)
      let html = ''
      if (isZip) {
        const mod = await import('exceljs')
        const ExcelJS = mod.default || mod
        const wb = new ExcelJS.Workbook()
        await wb.xlsx.load(buf)
        wb.eachSheet((sheet) => {
          html += '<h3 style="margin:8px 0">' + (sheet.name || '') + '</h3>'
          html += '<table border="1" cellspacing="0" cellpadding="4" style="border-collapse:collapse;font-size:13px">'
          sheet.eachRow((r, ri) => {
            html += '<tr>'
            r.eachCell({ includeEmpty: true }, (cell) => {
              const tag = ri === 1 ? 'th' : 'td'
              let v = cell.value
              if (v == null) v = ''
              else if (typeof v === 'object') v = v.text != null ? v.text : (v.result != null ? v.result : '')
              v = String(v).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
              html += '<' + tag + '>' + v + '</' + tag + '>'
            })
            html += '</tr>'
          })
          html += '</table><br/>'
        })
      } else if (!isOle) {
        // 非 OLE 的 .xls：多为 GBK 编码 Tab 文本（爱康 LIS 式），按 gbk 解码渲染
        let text
        try { text = new TextDecoder('gbk').decode(buf) } catch (e) { text = new TextDecoder('utf-8').decode(buf) }
        html = '<pre style="white-space:pre-wrap;word-break:break-all;font-size:13px">' + text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;') + '</pre>'
      } else {
        html = '<p style="color:#e6a23c">该 .xls 为旧版二进制格式，浏览器无法在线预览，请下载后查看。</p>'
      }
      previewHtml.value = html || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档格式不支持，请下载后查看') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // 其他（含老 .doc）：回退，由系统用 Word/WPS 打开
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

// 详情抽屉
const detailOpen = ref(false)
const detailDoc = ref(null)
const detailVersions = ref([])
const hasMeta = computed(() => {
  const d = detailDoc.value
  if (!d) return false
  return !!(d.doc_number || d.doc_version || d.author || d.issued_date || d.effective_date)
})
async function openDetail(row) {
  detailOpen.value = true
  detailDoc.value = row
  detailVersions.value = []
  try {
    const [doc, vers] = await Promise.all([getDocument(row.id), listVersions(row.id)])
    detailDoc.value = doc
    detailVersions.value = vers || []
  } catch (e) {
    detailVersions.value = []
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
    ElMessage.success('上传成功（已自动解析文件头元数据）')
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
    ElMessage.success('新版本已提交（已记录文件头元数据）')
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

// 文件更改日志：查看 + 导出「文件更改申请单」
const logOpen = ref(false)
const logLoading = ref(false)
const exporting = ref(false)
const logs = ref([])
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(10)
const logQuery = reactive({ q: '', change_type: '', only_unhandled: false })

function logTypeTag(t) {
  return { 新增: 'success', 修改: 'warning', 作废: 'danger' }[t] || 'info'
}
function openLog() {
  logOpen.value = true
}
function onLogOpen() {
  logPage.value = 1
  fetchLogs()
}
async function fetchLogs() {
  logLoading.value = true
  try {
    const res = await listChangeLogs({
      page: logPage.value,
      page_size: logPageSize.value,
      q: logQuery.q || undefined,
      change_type: logQuery.change_type || undefined,
      handled: logQuery.only_unhandled ? false : undefined,
    })
    logs.value = (res.items || []).map((x) => ({ ...x, _toggling: false }))
    logTotal.value = res.total || 0
  } catch (e) {
    logs.value = []
    logTotal.value = 0
  } finally {
    logLoading.value = false
  }
}
async function onExportLog() {
  exporting.value = true
  try {
    const blob = await exportChangeLogs({
      q: logQuery.q || undefined,
      change_type: logQuery.change_type || undefined,
      handled: logQuery.only_unhandled ? false : undefined,
    })
    const d = new Date()
    const ymd = `${d.getFullYear()}${String(d.getMonth() + 1).padStart(2, '0')}${String(d.getDate()).padStart(2, '0')}`
    downloadBlob(blob, `文件更改申请单_${ymd}.xlsx`)
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exporting.value = false
  }
}
async function toggleHandled(row, handled) {
  row._toggling = true
  try {
    await setChangeLogHandled(row.id, handled)
    row.handled = handled
    ElMessage.success(handled ? '已标记为处理' : '已撤销处理')
    // 若处于「仅看未处理」筛选，撤销后保留、标记后移出列表
    if (logQuery.only_unhandled && handled) {
      fetchLogs()
    }
  } catch (e) {
    ElMessage.error('操作失败')
  } finally {
    row._toggling = false
  }
}
</script>

<style scoped>
.page {
  height: 100%;
}
.desc-block {
  margin: 14px 0 0;
  font-size: 13px;
  color: #606266;
  line-height: 1.6;
}
.desc-block.tip {
  color: #909399;
  background: #f4f4f5;
  border-radius: 4px;
  padding: 8px 12px;
}
.page :deep(.el-table__row) td {
  padding-top: 9px;
  padding-bottom: 9px;
}
.doc-preview {
  max-height: 78vh;
  overflow: auto;
  font-family: -apple-system, 'Microsoft YaHei', 'PingFang SC', sans-serif;
  line-height: 1.7;
  color: #1f2329;
}
.doc-preview :deep(h1),
.doc-preview :deep(h2),
.doc-preview :deep(h3) {
  line-height: 1.4;
  margin: 0.6em 0;
}
.doc-preview :deep(p) {
  margin: 0.4em 0;
}
.doc-preview :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 10px 0;
}
.doc-preview :deep(td),
.doc-preview :deep(th) {
  border: 1px solid #d0d7de;
  padding: 6px 10px;
  vertical-align: top;
}
.doc-preview :deep(img) {
  max-width: 100%;
}
.log-toolbar {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.log-pager {
  margin-top: 12px;
  justify-content: flex-end;
}
</style>
