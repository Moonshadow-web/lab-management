<template>
  <div class="page">
    <CrudTable
      ref="crud"
      :columns="columns"
      :fetch="fetch"
      :extra-params="instrumentExtraParams"
      search-placeholder="搜索名称 / 编号 / 型号 / 负责人..."
      :show-add="auth.canWrite('instruments')"
      :can-write="auth.canWrite('instruments')"
      @add="onAdd"
      @edit="onEdit"
      @delete="onDelete"
    >
      <template #toolbar-extra>
        <el-button v-if="auth.canWrite('instruments')" @click="importVisible = true">批量导入档案</el-button>
        <el-switch
          v-model="hideNonActive"
          active-text="仅看在用"
          inline-prompt
          style="--el-switch-on-color: #67c23a; margin-right: 4px"
          @change="onFilterChange"
        />
      </template>
      <template #row-extra="{ row }">
        <el-button
          link
          :type="row.calib_level === 'danger' ? 'danger' : row.calib_level === 'warning' ? 'warning' : 'primary'"
          @click="openCalib(row)"
        >
          校准记录
          <span v-if="row.calib_level === 'danger'" style="margin-left: 2px">●逾期</span>
          <span v-else-if="row.calib_level === 'warning'" style="margin-left: 2px">●临期</span>
        </el-button>
        <el-button link type="primary" @click="openArchive(row)">档案</el-button>
      </template>
    </CrudTable>

    <EditDialog
      v-model="dialogVisible"
      :title="editingId ? '编辑仪器' : '新增仪器'"
      :form="form"
      :fields="fields"
      :rules="rules"
      :submitting="submitting"
      @submit="onSubmit"
    />

    <!-- 校准记录 -->
    <el-dialog v-model="calibOpen" :title="`校准记录 - ${calibInstrument?.name || ''}`" width="860px">
      <el-table :data="calibs" border stripe>
        <el-table-column prop="calibration_date" label="校准日期" width="120" />
        <el-table-column prop="next_due_date" label="下次到期" width="120" />
        <el-table-column prop="result" label="结果" width="90" show-overflow-tooltip />
        <el-table-column prop="agency" label="检定机构" width="100" show-overflow-tooltip />
        <el-table-column prop="cycle_months" label="周期(月)" width="80" align="center" />
        <el-table-column prop="operator" label="校准人" width="90" />
        <el-table-column label="报告" width="180" align="center">
          <template #default="{ row }">
            <el-button v-if="auth.canWrite('instruments') && !row.report_file_path" link type="primary" :loading="reportUploading && reportTarget.recId === row.id" @click="pickReportFile(row)">上传报告</el-button>
            <template v-else>
              <el-button link type="primary" @click="previewReport(row)">预览</el-button>
              <el-button link type="info" @click="downloadReport(row)">下载</el-button>
            </template>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="70" align="center">
          <template #default="{ row }">
            <el-button v-if="auth.canWrite('instruments')" link type="danger" @click="delCalib(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-divider v-if="auth.canWrite('instruments')">新增校准记录</el-divider>
      <el-form v-if="auth.canWrite('instruments')" :model="calibForm" label-width="100px" inline>
        <el-form-item label="校准日期" required>
          <el-date-picker v-model="calibForm.calibration_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="下次到期" required>
          <el-date-picker v-model="calibForm.next_due_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="检定机构">
          <el-input v-model="calibForm.agency" style="width: 120px" />
        </el-form-item>
        <el-form-item label="周期(月)">
          <el-input v-model="calibForm.cycle_months" style="width: 90px" placeholder="如 12" />
        </el-form-item>
        <el-form-item label="校准人">
          <el-input v-model="calibForm.operator" style="width: 120px" />
        </el-form-item>
        <el-form-item label="结果">
          <el-input v-model="calibForm.result" style="width: 160px" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="calibOpen = false">关闭</el-button>
        <el-button v-if="auth.canWrite('instruments')" type="primary" :loading="calibSubmitting" @click="addCalib">添加记录</el-button>
      </template>
    </el-dialog>

    <!-- 仪器档案详情抽屉（详情 / 预览 / 下载 / 导入 / 替换 / 删除） -->
    <el-drawer v-model="archiveDrawer" :title="`仪器档案 - ${archiveRow?.name || ''}`" :size="drawerSize">
      <el-descriptions title="档案详情" :column="descColumn" border>
        <el-descriptions-item label="设备名称">{{ archiveRow?.name || '—' }}</el-descriptions-item>
        <el-descriptions-item label="型号">{{ archiveRow?.model || '—' }}</el-descriptions-item>
        <el-descriptions-item label="制造商">{{ archiveRow?.manufacturer || '—' }}</el-descriptions-item>
        <el-descriptions-item label="出厂编号">{{ archiveRow?.serial_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="供货商名称">{{ archiveRow?.supplier || '—' }}</el-descriptions-item>
        <el-descriptions-item label="联系人及电话">{{ archiveRow?.contact || '—' }}</el-descriptions-item>
        <el-descriptions-item label="设备编号">{{ archiveRow?.dept_no || '—' }}</el-descriptions-item>
        <el-descriptions-item label="存放地点">{{ archiveRow?.location || '—' }}</el-descriptions-item>
        <el-descriptions-item label="接收日期">{{ archiveRow?.purchase_date || '—' }}</el-descriptions-item>
        <el-descriptions-item label="投入使用日期">{{ archiveRow?.start_date || '—' }}</el-descriptions-item>
        <el-descriptions-item label="设备负责人">{{ archiveRow?.owner || '—' }}</el-descriptions-item>
        <el-descriptions-item label="日常管理人">{{ archiveRow?.daily_manager || '—' }}</el-descriptions-item>
      </el-descriptions>

      <el-divider>仪器档案文件</el-divider>
      <div v-if="archiveInfo.has_archive">
        <el-alert type="success" :closable="false" show-icon>
          <template #title>已建档：{{ archiveInfo.original_filename }}</template>
          <div style="font-size: 12px; color: #888">
            大小：{{ formatSize(archiveInfo.file_size) }} ｜ 导入时间：{{ formatTime(archiveInfo.uploaded_at) }}
          </div>
        </el-alert>
        <div style="margin-top: 12px; display: flex; gap: 8px; flex-wrap: wrap">
          <el-button type="primary" @click="previewArchive">预览</el-button>
          <el-button @click="downloadArchive">下载</el-button>
          <el-button v-if="auth.canWrite('instruments')" type="warning" :loading="uploading" @click="pickArchiveFile">替换</el-button>
          <el-button v-if="auth.canWrite('instruments')" type="danger" @click="removeArchive">删除</el-button>
        </div>
      </div>
      <div v-else>
        <el-alert type="info" :closable="false" show-icon title="尚未导入仪器档案文件">
          <template #default>点击右侧「导入档案」上传该仪器的档案（.docx / .pdf / .doc）。</template>
        </el-alert>
        <div style="margin-top: 12px">
          <el-button v-if="auth.canWrite('instruments')" type="primary" :loading="uploading" @click="pickArchiveFile">导入档案</el-button>
        </div>
      </div>

      <el-divider>操作 / 保养记录（关联本仪器的记录表格）</el-divider>
      <div v-loading="docsLoading">
        <el-table v-if="linkedDocs.length" :data="linkedDocs" border stripe size="small">
          <el-table-column prop="doc_number" label="编号" width="130" show-overflow-tooltip />
          <el-table-column prop="title" label="标题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="version" label="版本" width="70" align="center">
            <template #default="{ row }">{{ row.version || '—' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="130" align="center">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="previewDoc(row)">预览</el-button>
              <el-button link type="primary" size="small" @click="downloadDoc(row)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无操作 / 保养记录关联到此仪器" :image-size="80" />
        <div v-if="linkedDocs.length" class="linked-count">
          共 <b>{{ linkedDocs.length }}</b> 份记录表格
        </div>
      </div>

      <el-divider>对应项目（使用本仪器的检验项目）</el-divider>
      <div v-loading="linkedLoading">
        <el-table v-if="linkedTestItems.length" :data="linkedTestItems" border stripe size="small" @row-click="goTestItem">
          <el-table-column prop="code" label="项目编号" width="110" show-overflow-tooltip />
          <el-table-column prop="name" label="项目名称" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span style="color: #409eff; cursor: pointer">{{ row.name }}</span>
            </template>
          </el-table-column>
          <el-table-column prop="category" label="类别" width="80" align="center" />
          <el-table-column prop="instrument_group" label="仪器组" min-width="120" show-overflow-tooltip>
            <template #default="{ row }">{{ row.instrument_group || row.instrument || '—' }}</template>
          </el-table-column>
        </el-table>
        <el-empty v-else description="暂无项目关联到此仪器" :image-size="80" />
        <div v-if="linkedTestItems.length" class="linked-count">
          共 <b>{{ linkedTestItems.length }}</b> 个检验项目
        </div>
      </div>
    </el-drawer>

    <!-- 档案预览（docx 由 mammoth 转网页在浏览器内显示，无需下载；pdf 走浏览器原生阅读器） -->
    <el-dialog v-model="previewVisible" :title="previewTitle" width="82%" top="4vh" append-to-body>
      <div v-loading="previewing" class="doc-preview" v-html="previewHtml"></div>
    </el-dialog>

    <!-- 批量导入仪器档案 -->
    <el-dialog v-model="importVisible" title="批量导入仪器档案" width="580px">
      <el-form label-width="90px">
        <el-form-item label="档案目录">
          <el-input v-model="importPath" placeholder="如 E:\生免组管理体系文件\生免组仪器档案" />
        </el-form-item>
        <div style="font-size: 12px; color: #888; margin-bottom: 8px">
          程序会扫描该目录下所有 .docx / .pdf / .doc 文件，用文件名中的科室编号（如 MHZYY-JYK-SM-1001）自动匹配仪器。
        </div>
      </el-form>
      <div v-if="importResult">
        <el-alert type="success" :closable="false">
          成功导入 {{ importResult.imported }} 个，共扫描 {{ importResult.total_files }} 个文件。
        </el-alert>
        <div v-if="importResult.skipped.length" style="margin-top: 8px">
          <div style="font-weight: 600; margin-bottom: 4px">未匹配 / 跳过（{{ importResult.skipped.length }}）：</div>
          <ul style="max-height: 200px; overflow: auto; font-size: 12px; color: #666; padding-left: 18px">
            <li v-for="(s, i) in importResult.skipped" :key="i">{{ s }}</li>
          </ul>
        </div>
      </div>
      <template #footer>
        <el-button @click="importVisible = false">关闭</el-button>
        <el-button type="primary" :loading="importing" @click="doImport">开始导入</el-button>
      </template>
    </el-dialog>

    <input ref="fileInput" type="file" accept=".docx,.pdf,.doc" style="display: none" @change="onArchiveFileChange" />
    <input ref="reportInput" type="file" accept=".docx,.pdf,.doc" style="display: none" @change="onReportFileChange" />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import mammoth from 'mammoth'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import {
  listInstruments, getInstrument, createInstrument, updateInstrument, deleteInstrument,
  listCalibrations, createCalibration, deleteCalibration,
  uploadCalibrationReport, downloadCalibrationReport, deleteCalibrationReport, getCalibrationsStatus,
  uploadInstrumentArchive, getInstrumentArchiveInfo, downloadInstrumentArchive,
  deleteInstrumentArchive, getArchivesStatus, importArchivesFolder,
  getInstrumentTestItems, getInstrumentDocuments,
} from '../../api/instruments'
import { fetchDocumentBlob, downloadBlob, previewBlob } from '../../api/documents'
import { useAuthStore } from '../../store/auth'

const crud = ref(null)
const auth = useAuthStore()
const dialogVisible = ref(false)

// 仪器档案描述列表：桌面 2 列，窄屏（≤768px）改 1 列，避免标签/值被挤压
const descColumn = ref(typeof window !== 'undefined' && window.innerWidth <= 768 ? 1 : 2)
// 档案抽屉尺寸：桌面 640px，窄屏占满全屏（size 用内联 !important，CSS 覆盖不生效，故用响应式 prop）
const drawerSize = ref(typeof window !== 'undefined' && window.innerWidth <= 768 ? '100%' : '640px')
function syncMobileLayout() {
  const mobile = typeof window !== 'undefined' && window.innerWidth <= 768
  descColumn.value = mobile ? 1 : 2
  drawerSize.value = mobile ? '100%' : '640px'
}
onMounted(() => window.addEventListener('resize', syncMobileLayout))
onBeforeUnmount(() => window.removeEventListener('resize', syncMobileLayout))

// 一键隐藏非在用：开启时仅显示「在用」状态的仪器（走后端 status 过滤），默认开启
const hideNonActive = ref(true)
const instrumentExtraParams = computed(() => (hideNonActive.value ? { status: '在用' } : {}))
function onFilterChange() {
  crud.value?.refresh()
}

// 从「项目查询」点击关联仪器跳转而来：?focus=<instrument_id> 时自动打开该仪器档案
const route = useRoute()
const router = useRouter()
async function focusInstrument(id) {
  const numId = Number(id)
  if (!numId) return
  try {
    const inst = await getInstrument(numId)
    openArchive(inst)
  } catch (e) {
    ElMessage.warning('未找到对应仪器档案')
  }
}
onMounted(() => {
  const f = route.query.focus
  if (f) focusInstrument(f)
})
watch(
  () => route.query.focus,
  (nf) => {
    if (nf) focusInstrument(nf)
  }
)
const editingId = ref(null)
const submitting = ref(false)

const STATUS_OPTIONS = ['在用', '备用', '维修', '停用'].map((v) => ({ label: v, value: v }))

const fields = [
  { prop: 'name', label: '仪器名称' },
  { prop: 'dept_no', label: '科室编号' },
  { prop: 'model', label: '规格型号' },
  { prop: 'manufacturer', label: '生产厂家' },
  { prop: 'category', label: '类别' },
  { prop: 'serial_no', label: '出厂编号' },
  { prop: 'status', label: '状态', type: 'select', options: STATUS_OPTIONS },
  { prop: 'location', label: '存放位置' },
  { prop: 'owner', label: '设备负责人' },
  { prop: 'daily_manager', label: '日常管理人' },
  { prop: 'supplier', label: '供货商名称' },
  { prop: 'contact', label: '联系人及电话' },
  { prop: 'purchase_date', label: '接收日期', type: 'date' },
  { prop: 'start_date', label: '投入使用日期', type: 'date' },
]

const rules = {
  name: [{ required: true, message: '请填写仪器名称', trigger: 'blur' }],
}

const columns = [
  { prop: 'name', label: '名称', minWidth: 150, tooltip: false },
  { prop: 'dept_no', label: '科室编号', minWidth: 140, tooltip: false },
  { prop: 'model', label: '型号', minWidth: 100, tooltip: false },
  { prop: 'manufacturer', label: '厂家', minWidth: 110, tooltip: false },
  { prop: 'serial_no', label: '出厂编号', minWidth: 100, tooltip: false },
  {
    prop: 'status', label: '状态', minWidth: 70,
    formatter: (row) => {
      const map = { 在用: 'success', 备用: 'info', 维修: 'warning', 停用: 'danger', 已停用: 'danger' }
      const t = map[row.status] || 'info'
      return `<el-tag type="${t}" size="small">${row.status || '-'}</el-tag>`
    },
  },
  { prop: 'start_date', label: '启用时间', minWidth: 80, formatter: (row) => formatYearMonth(row.start_date) },
  { prop: 'owner', label: '负责人', minWidth: 80, tooltip: false },
  { prop: 'daily_manager', label: '日常管理人', minWidth: 80, formatter: (row) => row.daily_manager || '—', tooltip: false },
  { prop: 'calib_next', label: '下次校准', minWidth: 150,
    formatter: (row) => {
      if (!row.calib_next) return '<span style="color:#c0c4cc">—</span>'
      const lvl = row.calib_level
      const color = lvl === 'danger' ? '#f56c6c' : lvl === 'warning' ? '#e6a23c' : '#67c23a'
      const tag = lvl === 'danger' ? '逾期' : lvl === 'warning' ? '即将到期' : ''
      const badge = tag ? ` <span style="color:${color}">(${tag})</span>` : ''
      return `<span style="color:${color}">${row.calib_next}${badge}</span>`
    },
  },
]

// 启用日期取到「年-月」（兼容 YYYY-MM-DD 或已为 YYYY-MM）
function formatYearMonth(v) {
  if (!v) return '—'
  const m = String(v).slice(0, 7)
  return /^\d{4}-\d{2}$/.test(m) ? m : (v || '—')
}

const emptyForm = () => ({
  name: '', dept_no: '', model: '', manufacturer: '', category: '',
  serial_no: '', status: '在用', location: '', owner: '', daily_manager: '',
  supplier: '', contact: '', purchase_date: '', start_date: '', qc_instrument: false,
})

const form = reactive(emptyForm())

// 列表加载时合并建档状态 + 校准预警状态
async function fetch(params) {
  const res = await listInstruments(params)
  try {
    const status = await getArchivesStatus()
    const map = {}
    status.forEach((s) => { map[s.instrument_id] = s })
    ;(res.items || []).forEach((it) => {
      const s = map[it.id]
      it.has_archive = !!(s && s.has_archive)
      it.archive_name = s ? s.original_filename : ''
    })
  } catch (e) { /* 状态接口不可用时忽略，不影响列表 */ }
  try {
    const cstatus = await getCalibrationsStatus()
    const cmap = {}
    cstatus.forEach((c) => { cmap[c.instrument_id] = c })
    ;(res.items || []).forEach((it) => {
      const c = cmap[it.id]
      it.calib_next = c ? c.next_due_date : ''
      it.calib_level = c ? c.level : ''
    })
  } catch (e) { /* 校准状态接口不可用时忽略，不影响列表 */ }
  return res
}
function onAdd() {
  Object.assign(form, emptyForm())
  editingId.value = null
  dialogVisible.value = true
}
function onEdit(row) {
  Object.assign(form, emptyForm(), row)
  // 历史数据 qc_instrument 可能为 null，归一为布尔，避免回传 null 触发后端 422
  form.qc_instrument = row.qc_instrument ?? false
  editingId.value = row.id
  dialogVisible.value = true
}
async function onSubmit() {
  submitting.value = true
  try {
    if (editingId.value) {
      await updateInstrument(editingId.value, { ...form })
    } else {
      await createInstrument({ ...form })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}
async function onDelete(row) {
  await ElMessageBox.confirm(`确认删除「${row.name}」？`, '提示', { type: 'warning' })
  await deleteInstrument(row.id)
  ElMessage.success('已删除')
  crud.value?.refresh()
}

// 校准记录
const calibOpen = ref(false)
const calibInstrument = ref(null)
const calibs = ref([])
const calibSubmitting = ref(false)
const calibForm = reactive({ calibration_date: '', next_due_date: '', result: '', agency: '', cycle_months: '', operator: '' })

// 校准报告：上传 / 预览 / 下载
const reportUploading = ref(false)
const reportInput = ref(null)
const reportTarget = reactive({ recId: null })

function reportExt(row) {
  const name = row.report_filename || row.report_file_path || ''
  const m = /\.[^.]+$/.exec(name)
  return m ? m[0].toLowerCase() : ''
}

async function openCalib(row) {
  calibInstrument.value = row
  calibOpen.value = true
  await loadCalibs(row.id)
}
async function loadCalibs(id) {
  try {
    calibs.value = await listCalibrations(id)
  } catch (e) {
    calibs.value = []
  }
}
async function addCalib() {
  if (!calibForm.calibration_date || !calibForm.next_due_date) {
    ElMessage.warning('请填写校准日期与下次到期日')
    return
  }
  calibSubmitting.value = true
  try {
    await createCalibration(calibInstrument.value.id, { ...calibForm })
    ElMessage.success('已添加')
    Object.assign(calibForm, { calibration_date: '', next_due_date: '', result: '', agency: '', cycle_months: '', operator: '' })
    await loadCalibs(calibInstrument.value.id)
    crud.value?.refresh()
  } finally {
    calibSubmitting.value = false
  }
}
async function delCalib(row) {
  await ElMessageBox.confirm('确认删除该校准记录？', '提示', { type: 'warning' })
  await deleteCalibration(calibInstrument.value.id, row.id)
  ElMessage.success('已删除')
  await loadCalibs(calibInstrument.value.id)
  crud.value?.refresh()
}

function pickReportFile(row) {
  reportTarget.recId = row.id
  reportInput.value?.click()
}
async function onReportFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file || !calibInstrument.value || reportTarget.recId == null) return
  reportUploading.value = true
  const recId = reportTarget.recId
  try {
    await uploadCalibrationReport(calibInstrument.value.id, recId, file)
    ElMessage.success('校准报告已保存')
    await loadCalibs(calibInstrument.value.id)
    crud.value?.refresh()
  } catch (err) {
    ElMessage.error('上传失败')
  } finally {
    reportUploading.value = false
    reportTarget.recId = null
  }
}
async function downloadReport(row) {
  if (!calibInstrument.value) return
  try {
    const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
    triggerDownload(blob, row.report_filename || 'calibration_report')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}
async function previewReport(row) {
  if (!calibInstrument.value || !row.report_file_path) return
  const ext = reportExt(row)
  const fname = row.report_filename || '校准报告预览'
  if (ext === '.pdf') {
    try {
      const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) {
      ElMessage.error('预览失败')
    }
    return
  }
  if (ext === '.docx') {
    previewVisible.value = true
    previewTitle.value = fname
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // 其他格式回退下载
  try {
    const blob = await downloadCalibrationReport(calibInstrument.value.id, row.id)
    triggerDownload(blob, fname)
    ElMessage.info('该格式暂不支持在线预览，已为你下载文件')
  } catch (e) {
    ElMessage.error('预览失败')
  }
}

// ---------------- 仪器档案 ----------------
const archiveDrawer = ref(false)
const archiveRow = ref(null)
const archiveInfo = ref({ has_archive: false })
const uploading = ref(false)
const fileInput = ref(null)
const previewVisible = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')
const previewing = ref(false)

// 反向索引：本仪器对应的项目（与项目查询页「关联仪器」芯片对称）
const linkedTestItems = ref([])
const linkedLoading = ref(false)

// 反向索引：本仪器关联的操作/保养记录（记录表格，归属文件管理模块）
const linkedDocs = ref([])
const docsLoading = ref(false)

async function loadArchiveInfo(id) {
  try {
    archiveInfo.value = await getInstrumentArchiveInfo(id)
  } catch (e) {
    archiveInfo.value = { has_archive: false }
  }
}
async function loadLinkedTestItems(id) {
  linkedLoading.value = true
  try {
    linkedTestItems.value = await getInstrumentTestItems(id)
  } catch (e) {
    linkedTestItems.value = []
  } finally {
    linkedLoading.value = false
  }
}
async function loadLinkedDocs(id) {
  docsLoading.value = true
  try {
    linkedDocs.value = await getInstrumentDocuments(id)
  } catch (e) {
    linkedDocs.value = []
  } finally {
    docsLoading.value = false
  }
}
async function openArchive(row) {
  archiveRow.value = row
  archiveDrawer.value = true
  await loadArchiveInfo(row.id)
  await loadLinkedTestItems(row.id)
  await loadLinkedDocs(row.id)
}
// 操作/保养记录：预览（docx 用 mammoth 内嵌显示；pdf 走浏览器；其他回退）
async function previewDoc(row) {
  const fname = row.original_filename || row.title || ''
  const ext = (fname.split('.').pop() || '').toLowerCase()
  if (ext === 'pdf') {
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      previewBlob(blob)
    } catch (e) {
      ElMessage.error('文件不存在或预览失败')
    }
    return
  }
  if (ext === 'docx') {
    previewVisible.value = true
    previewTitle.value = row.title || fname || '预览'
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await fetchDocumentBlob(row.id, 'preview')
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  try {
    const blob = await fetchDocumentBlob(row.id, 'preview')
    previewBlob(blob)
  } catch (e) {
    ElMessage.error('文件不存在或预览失败')
  }
}
async function downloadDoc(row) {
  try {
    const blob = await fetchDocumentBlob(row.id, 'download')
    downloadBlob(blob, row.original_filename || row.title)
  } catch (e) {
    ElMessage.error('文件不存在或下载失败')
  }
}
// 点击项目跳转项目查询页，并自动按项目名搜索定位
function goTestItem(item) {
  router.push({ path: '/test-items', query: { q: item.name } })
}
function pickArchiveFile() {
  fileInput.value?.click()
}
async function onArchiveFileChange(e) {
  const file = e.target.files?.[0]
  e.target.value = '' // 允许重复选择同一文件
  if (!file || !archiveRow.value) return
  uploading.value = true
  try {
    await uploadInstrumentArchive(archiveRow.value.id, file)
    ElMessage.success('档案已保存')
    await loadArchiveInfo(archiveRow.value.id)
    crud.value?.refresh()
  } catch (err) {
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}
async function downloadArchive() {
  if (!archiveRow.value) return
  try {
    const blob = await downloadInstrumentArchive(archiveRow.value.id)
    triggerDownload(blob, archiveInfo.value.original_filename || 'archive')
  } catch (e) {
    ElMessage.error('下载失败')
  }
}
async function removeArchive() {
  if (!archiveRow.value) return
  try {
    await ElMessageBox.confirm('确认删除该仪器的档案文件？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteInstrumentArchive(archiveRow.value.id)
    ElMessage.success('已删除')
    await loadArchiveInfo(archiveRow.value.id)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}
async function previewArchive() {
  if (!archiveRow.value || !archiveInfo.value.has_archive) return
  const ext = (archiveInfo.value.file_ext || '').toLowerCase()
  const fname = archiveInfo.value.original_filename || '档案预览'
  // PDF：浏览器内置阅读器可直接渲染
  if (ext === '.pdf') {
    try {
      const blob = await downloadInstrumentArchive(archiveRow.value.id)
      const url = URL.createObjectURL(blob)
      window.open(url, '_blank')
      setTimeout(() => URL.revokeObjectURL(url), 60000)
    } catch (e) {
      ElMessage.error('预览失败')
    }
    return
  }
  // docx（含已由 .doc 转换而来的）：前端 mammoth 转 HTML，在浏览器内显示（不下载，与文件管理一致）
  if (ext === '.docx') {
    previewVisible.value = true
    previewTitle.value = fname
    previewHtml.value = ''
    previewing.value = true
    try {
      const blob = await downloadInstrumentArchive(archiveRow.value.id)
      const arrayBuffer = await blob.arrayBuffer()
      const result = await mammoth.convertToHtml({ arrayBuffer })
      previewHtml.value = result.value || '<p style="color:#909399">（文档内容为空）</p>'
    } catch (e) {
      console.error(e)
      previewHtml.value = '<p style="color:#f56c6c">预览失败：' + (e && e.message ? e.message : '该文档可能受保护或格式不支持') + '</p>'
    } finally {
      previewing.value = false
    }
    return
  }
  // 其他格式（极少，如转换失败保留的 .doc）：回退下载
  try {
    const blob = await downloadInstrumentArchive(archiveRow.value.id)
    triggerDownload(blob, fname)
    ElMessage.info('该格式暂不支持在线预览，已为你下载文件')
  } catch (e) {
    ElMessage.error('预览失败')
  }
}
function triggerDownload(blob, name) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name || 'archive'
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

// ---------------- 批量导入 ----------------
const importVisible = ref(false)
const importPath = ref('E:\\生免组管理体系文件\\生免组仪器档案')
const importing = ref(false)
const importResult = ref(null)
async function doImport() {
  if (!importPath.value.trim()) {
    ElMessage.warning('请填写档案目录')
    return
  }
  importing.value = true
  importResult.value = null
  try {
    const res = await importArchivesFolder(importPath.value.trim())
    importResult.value = res
    ElMessage.success(`成功导入 ${res.imported} 个仪器档案`)
    crud.value?.refresh()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    importing.value = false
  }
}

function formatSize(n) {
  if (!n) return '0 B'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(2)} MB`
}
function formatTime(v) {
  if (!v) return '—'
  return String(v).replace('T', ' ').slice(0, 19)
}
</script>

<style scoped>
.page {
  height: 100%;
}
/* 仪器列表：允许单元格内容换行（最多两行），避免横向拖拉 */
.page :deep(.el-table .cell) {
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
}
.page :deep(.el-table__row) td {
  padding-top: 8px;
  padding-bottom: 8px;
}
/* 对应项目数量统计 */
.linked-count {
  margin-top: 10px;
  padding: 8px 12px;
  text-align: right;
  font-size: 13px;
  color: #606266;
  background: #f5f7fa;
  border-radius: 4px;
}
.linked-count b {
  color: #409eff;
  font-size: 15px;
  padding: 0 2px;
}
/* 档案预览：复用的富文本样式 */
.doc-preview {
  max-height: 78vh;
  overflow: auto;
  padding: 8px 12px;
  border: 1px solid #ebeef5;
  border-radius: 4px;
  background: #fff;
  line-height: 1.7;
}
.doc-preview :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin: 8px 0;
}
.doc-preview :deep(td),
.doc-preview :deep(th) {
  border: 1px solid #dcdfe6;
  padding: 4px 8px;
}
.doc-preview :deep(img) {
  max-width: 100%;
}
</style>
