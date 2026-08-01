<template>
  <div>
    <!-- 活动选择 / 新建 -->
    <div class="bar">
      <el-select v-model="campaignId" placeholder="选择评审活动" filterable style="width: 280px" @change="loadAll">
        <el-option v-for="c in campaigns" :key="c.id" :label="`${c.title}（${c.year}）`" :value="c.id" />
      </el-select>
      <el-button v-if="auth.canWrite('iso15189')" type="primary" @click="onNewCampaign">新建活动</el-button>
      <el-button v-if="auth.canWrite('iso15189')" :disabled="!campaignId" @click="onAssign">批量分配文件</el-button>
      <el-button v-if="auth.canWrite('iso15189')" :disabled="!campaignId" @click="onSummary">汇总 A-027</el-button>
    </div>

    <!-- 管理员：全部分配与接收 -->
    <template v-if="auth.canWrite('iso15189')">
      <el-divider content-position="left">分配与接收（管理员）</el-divider>
      <div class="reviewer-filter-bar">
        <el-select v-model="reviewerFilter" placeholder="按审核人筛选" clearable style="width:180px" @change="loadStats">
          <el-option v-for="opt in reviewerOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <div class="progress-chips">
          <el-tag v-for="s in progressStats" :key="s.reviewer" size="small" type="info">
            {{ s.reviewer }}：共{{ s.total }} / 已提交{{ s.submitted }} / 已接收{{ s.received }} / A-027已交{{ s.a027_submitted ? '是' : '否' }}
          </el-tag>
        </div>
      </div>
      <el-table :data="filteredAssignments" border size="small" v-loading="loading">
        <el-table-column prop="document_id" label="文档" min-width="220">
          <template #default="{ row }">{{ docTitle(row.document_id) }} <el-tag type="info" size="small">{{ docCat(row.document_id) }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="reviewer" label="审核人" width="100" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="revised_filename" label="修订文件" min-width="160" />
        <el-table-column prop="document_new_version" label="生成版本" width="100" />
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :disabled="!row.revised_cloud_key" type="primary" @click="openReceive(row)">接收生成版本</el-button>
            <el-button size="small" text @click="viewAssignRecord(row)">记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 成员：我的任务 -->
    <el-divider content-position="left">我的评审任务</el-divider>
    <div v-if="myTasks.length" class="my-record-bar">
      <span>文件评审记录（A-027）：</span>
      <el-tag size="small" :type="recordStatusType(myRecordStatus)">{{ myRecordStatus || '待提交' }}</el-tag>
      <el-button size="small" type="primary" @click="openRecord">填写 / 编辑</el-button>
    </div>
    <el-table :data="myTasks" border size="small" v-loading="loadingMy">
      <el-table-column prop="document_id" label="文档" min-width="240">
        <template #default="{ row }">{{ docTitle(row.document_id) }} <el-tag type="info" size="small">{{ docCat(row.document_id) }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="status" label="修订状态" width="120">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="320" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="downloadDoc(row.document_id)">下载原文件</el-button>
          <el-upload
            :show-file-list="false" :auto-upload="true"
            :http-request="(o) => doUpload(o, row)"
            style="display:inline-block;margin:0 6px"
          >
            <el-button size="small" type="primary">上传修订</el-button>
          </el-upload>
          <el-button size="small" type="success" :disabled="row.status !== '待评审' && row.status !== '已提交'" @click="submitRevision(row)">提交修订</el-button>
          <el-button v-if="row.revised_cloud_key" size="small" text @click="downloadRevised(row)">下载修订</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!myTasks.length" description="当前活动暂无分配给您的文件" :image-size="60" />

    <!-- 批量分配弹窗（可视化：勾选表格 + 单人/多人均分） -->
    <el-dialog v-model="assignVisible" title="批量分配评审文件" width="820px" top="5vh">
      <el-form label-width="120px" size="small">
        <el-form-item label="分配模式">
          <el-radio-group v-model="assignMode">
            <el-radio value="single">指定单个审核人</el-radio>
            <el-radio value="multi">分配给多人（自动均分）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="assignMode === 'single'" label="审核人">
          <el-select v-model="assignReviewer" filterable placeholder="选择成员" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item v-else label="审核人（多人）">
          <el-select v-model="assignReviewers" multiple filterable placeholder="选择多名成员，文件将自动均分" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <div class="assign-toolbar">
        <el-input v-model="assignSearch" placeholder="搜索文件名" clearable style="width:220px" />
        <el-button size="small" @click="selectAllDocs">全选</el-button>
        <el-button size="small" @click="clearDocSelection">清空</el-button>
        <span class="sel-count">已选 {{ assignSelection.length }} 份</span>
      </div>
      <el-table
        ref="assignTableRef" :data="reviewDocsFiltered" border size="small" height="360"
        @selection-change="onAssignSelect"
      >
        <el-table-column type="selection" width="46" />
        <el-table-column prop="title" label="文件名称" min-width="280" />
        <el-table-column prop="category" label="类别" width="110" />
        <el-table-column prop="version" label="版本" width="80" />
      </el-table>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" :disabled="!assignSelection.length" @click="submitAssign">批量分配（{{ assignSelection.length }} 份）</el-button>
      </template>
    </el-dialog>

    <!-- 文件评审记录（A-027）弹窗：每人一份 -->
    <el-dialog v-model="recordVisible" :title="`文件评审记录（A-027）— ${myRecordStatus}`" width="860px" top="4vh">
      <el-form :model="recordForm" label-width="110px" size="small">
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="专业组"><el-input v-model="recordForm.review_group" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="评审日期">
              <el-date-picker v-model="recordForm.review_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-form-item label="评审组成员">
          <el-input v-model="recordForm.review_members" type="textarea" :rows="2" readonly placeholder="本活动全部被分配成员" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="记录人"><el-input v-model="recordForm.recorder" readonly /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="审批人"><el-input v-model="recordForm.approver" placeholder="默认 金子铮" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="记录日期">
              <el-date-picker v-model="recordForm.record_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="批准日期">
              <el-date-picker v-model="recordForm.approve_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-divider content-position="left">评审文件（本人被分配范围）</el-divider>
        <el-table :data="recordForm.files" border size="small">
          <el-table-column prop="title" label="文件名称" min-width="200" />
          <el-table-column prop="doc_number" label="文件编号" width="130" />
          <el-table-column prop="version" label="版本" width="80" />
          <el-table-column label="评审意见" min-width="200">
            <template #default="{ row }"><el-input v-model="row.comment" type="textarea" :rows="2" /></template>
          </el-table-column>
          <el-table-column label="评审结论" width="140">
            <template #default="{ row }">
              <el-select v-model="row.conclusion" placeholder="选择" style="width:100%">
                <el-option label="适宜" value="适宜" />
                <el-option label="修改后适宜" value="修改后适宜" />
                <el-option label="作废" value="作废" />
              </el-select>
            </template>
          </el-table-column>
        </el-table>
        <el-form-item label="主要存在问题" style="margin-top:10px">
          <el-input v-model="recordForm.problems" type="textarea" :rows="3" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordVisible = false">关闭</el-button>
        <el-button @click="saveRecord(false)">保存</el-button>
        <el-button type="primary" @click="saveRecord(true)">提交</el-button>
      </template>
    </el-dialog>

    <!-- 接收前审阅弹窗 -->
    <el-dialog v-model="receiveVisible" title="审阅修订并生成新版本" width="620px" top="5vh">
      <el-form :model="receiveForm" label-width="120px" size="small">
        <el-form-item label="文档">{{ receiveForm.doc_title }}</el-form-item>
        <el-form-item label="成员修订文件">
          <div v-if="receiveForm.revised_filename">
            {{ receiveForm.revised_filename }}
            <el-button size="small" text type="primary" @click="previewRevision">预览</el-button>
            <el-button size="small" text @click="downloadRevisedFromReceive">下载</el-button>
          </div>
          <span v-else class="text-muted">无修订文件</span>
        </el-form-item>
        <el-form-item label="接受所有修订">
          <el-switch v-model="receiveForm.accept_revisions" active-text="是" inactive-text="否" />
          <div class="form-tip">成员上传的是「修订模式」文档时，勾选此项可在生成版本前自动接受全部修订。</div>
        </el-form-item>
        <el-form-item label="或上传终稿">
          <el-upload
            :auto-upload="false" :limit="1"
            :on-change="(f) => { receiveForm.final_file = f.raw }"
            :on-remove="() => { receiveForm.final_file = null }"
          >
            <el-button size="small">选择文件</el-button>
          </el-upload>
          <div class="form-tip">如管理员已在外部审阅并定稿，可直接上传终稿覆盖成员修订版。</div>
        </el-form-item>
        <el-divider content-position="left">生成版本信息</el-divider>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="版本号"><el-input v-model="receiveForm.new_version" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="修订号"><el-input v-model="receiveForm.revision_no" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="审核日期">
              <el-date-picker v-model="receiveForm.audit_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="批准者"><el-input v-model="receiveForm.approver" placeholder="默认保留原文档批准者" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="批准日期">
              <el-date-picker v-model="receiveForm.approve_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="实施日期">
              <el-date-picker v-model="receiveForm.effective_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" style="width:100%" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="receiveVisible = false">取消</el-button>
        <el-button type="primary" @click="submitReceive">确认接收并生成 {{ receiveForm.new_version }}</el-button>
      </template>
    </el-dialog>

    <!-- 汇总弹窗：按人 A-027 -->
    <el-dialog v-model="summaryVisible" title="文件评审汇总（A-027，按人）" width="960px" top="4vh">
      <div class="summary-bar">
        <el-tag v-if="summaryArchived" type="success">已存档</el-tag>
        <el-tag v-else type="info">未存档</el-tag>
        <el-button size="small" type="success" :disabled="summaryArchived" @click="archiveSummary">确认存档</el-button>
        <el-button size="small" type="primary" @click="previewSummary">预览</el-button>
        <el-button size="small" @click="printSummary">打印</el-button>
        <el-button size="small" @click="downloadSummary">下载（Word）</el-button>
      </div>
      <el-table :data="summaryData" border size="small" max-height="520">
        <el-table-column type="expand">
          <template #default="{ row }">
            <div style="padding:6px 12px">
              <div><b>评审文件（本人范围）：</b></div>
              <el-table :data="row.review_files || []" size="small" border style="margin:6px 0">
                <el-table-column prop="title" label="文件名称" min-width="200" />
                <el-table-column prop="doc_number" label="编号" width="120" />
                <el-table-column prop="version" label="版本" width="70" />
                <el-table-column prop="comment" label="评审意见" min-width="160" />
                <el-table-column prop="conclusion" label="结论" width="100" />
              </el-table>
              <div><b>实际分配与接收：</b></div>
              <el-table :data="row.assign_files || []" size="small" border>
                <el-table-column prop="title" label="文件" min-width="200" />
                <el-table-column prop="status" label="状态" width="110" />
                <el-table-column prop="new_version" label="生成版本" width="100" />
              </el-table>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="reviewer" label="记录人" width="100" />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }"><el-tag size="small" :type="recordStatusType(row.status)">{{ row.status }}</el-tag></template>
        </el-table-column>
        <el-table-column prop="review_members" label="评审组成员" min-width="180" />
        <el-table-column prop="approver" label="审批人" width="90" />
        <el-table-column prop="problems" label="主要存在问题" min-width="180" />
        <el-table-column prop="record_date" label="记录日期" width="110" />
      </el-table>
    </el-dialog>
  </div>

  <!-- 修订文件在线预览 -->
  <el-dialog v-model="revisionPreviewVisible" title="修订文件预览" width="90%" top="2vh" append-to-body>
    <div v-if="revisionPreviewLoading" v-loading="true" style="height: 70vh" />
    <div v-else class="revision-preview-html" v-html="revisionPreviewHtml" />
    <template #footer>
      <el-button @click="revisionPreviewVisible = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 文件评审汇总报告预览 -->
  <el-dialog v-model="summaryReportVisible" title="文件评审汇总报告预览" width="92%" top="2vh" append-to-body>
    <div class="report-bar">
      <el-button type="primary" @click="printHtml(summaryReportHtml)">打印</el-button>
      <el-button @click="downloadDoc(summaryReportHtml, `文件评审汇总_${campaigns.find(c=>c.id===campaignId)?.title||''}.doc`)">下载（Word）</el-button>
      <span class="report-hint">预览为只读；下载得到 .doc 文件，可用 Word 打开。</span>
    </div>
    <div class="summary-report-html" v-html="summaryReportHtml" />
  </el-dialog>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../utils/request'
import {
  listCampaigns, createCampaign, updateCampaign, listAssignments, assignBatch, myAssignments,
  uploadRevision, downloadRevisionBlob, submitReview, receiveRevision, reviewerStats, reviewSummary,
  downloadDocumentBlob, myRecord, upsertMyRecord,
} from '../../api/review'
import mammoth from 'mammoth'
import { buildReviewSummaryHtml, printHtml, downloadDoc as downloadReportDoc } from '../../utils/reportExport'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const campaignId = ref(null)
const campaigns = ref([])
const assignments = ref([])
const myTasks = ref([])
const users = ref([])
const docs = ref([])
const loading = ref(false)
const loadingMy = ref(false)

const docMap = ref({})
const docCatMap = ref({})
const docFileMap = ref({})  // id -> original_filename
const userMap = ref({})

const assignVisible = ref(false)
const assignMode = ref('single')
const assignReviewer = ref(null)
const assignReviewers = ref([])
const assignSelection = ref([])
const assignSearch = ref('')
const assignTableRef = ref(null)

const recordVisible = ref(false)
const recordForm = reactive({ files: [] })
const myRecordStatus = ref('')

const summaryVisible = ref(false)
const summaryData = ref([])
const summaryArchived = ref(false)
const summaryReportVisible = ref(false)
const summaryReportHtml = ref('')

// 管理员：按人筛选 + 进度
const reviewerFilter = ref('')
const progressStats = ref([])

// 接收生成版本审阅弹窗
const receiveVisible = ref(false)
const receiveForm = reactive({
  assignment_id: null,
  doc_title: '',
  revised_filename: '',
  accept_revisions: true,
  new_version: '2.0',
  revision_no: '0',
  audit_date: '',
  approve_date: '2026-09-01',
  effective_date: '2026-09-01',
  approver: '',
  final_file: null,
})

// 修订文件在线预览
const revisionPreviewVisible = ref(false)
const revisionPreviewHtml = ref('')
const revisionPreviewLoading = ref(false)

// 仅允许三类 SOP 参与文件评审（范围：通用SOP / 项目SOP / 仪器SOP）
const ALLOWED_CATS = ['通用SOP', '项目SOP', '仪器SOP']
const reviewDocs = computed(() =>
  docs.value.filter(
    (d) => ALLOWED_CATS.includes(d.category) && (!d.status || !['作废', '停用', '废弃'].includes(d.status))
  )
)
const reviewDocsFiltered = computed(() => {
  const k = assignSearch.value.trim()
  if (!k) return reviewDocs.value
  return reviewDocs.value.filter((d) => (d.title || '').includes(k))
})

const reviewerOptions = computed(() => {
  const names = new Set(assignments.value.map(a => a.reviewer).filter(Boolean))
  return [{ label: '全部审核人', value: '' }, ...Array.from(names).map(n => ({ label: n, value: n }))]
})

const filteredAssignments = computed(() => {
  if (!reviewerFilter.value) return assignments.value
  return assignments.value.filter(a => a.reviewer === reviewerFilter.value)
})

function statusType(s) {
  return { 待评审: 'info', 已提交: 'warning', 管理员已接收: 'success', 已完成: 'success' }[s] || 'info'
}
function recordStatusType(s) {
  return { 待提交: 'info', 已填写: 'warning', 已提交: 'success' }[s] || 'info'
}
function docTitle(id) {
  return docMap.value[id] || `文档#${id}`
}
function docCat(id) {
  return docCatMap.value[id] || ''
}

async function loadDict() {
  try {
    const d = await request.get('/api/v1/documents', { params: { page_size: 500, hide_invalid: true } })
    docs.value = d.items || []
    const m = {}, cm = {}, fm = {}
    d.items.forEach((x) => {
      m[x.id] = x.title
      cm[x.id] = x.category
      fm[x.id] = x.original_filename || ''
    })
    docMap.value = m
    docCatMap.value = cm
    docFileMap.value = fm
  } catch (e) {}
  try {
    const u = await request.get('/api/v1/users', { params: { page_size: 500 } })
    const arr = u.items || u || []
    users.value = arr
    const um = {}
    arr.forEach((x) => (um[x.id] = x))
    userMap.value = um
  } catch (e) {}
}
async function loadCampaigns() {
  const r = await listCampaigns({ page_size: 100 })
  campaigns.value = r.items || []
  if (!campaignId.value && campaigns.value.length) campaignId.value = campaigns.value[0].id
}
async function loadAll() {
  if (!campaignId.value) return
  loading.value = true
  try {
    const r = await listAssignments({ campaign_id: campaignId.value, page_size: 500 })
    assignments.value = r.items || []
  } finally { loading.value = false }
  await loadStats()
  await loadMy()
}
async function loadMy() {
  if (!campaignId.value) return
  loadingMy.value = true
  try {
    const r = await myAssignments(campaignId.value)
    myTasks.value = r || []
    if (myTasks.value.length) {
      try {
        const rec = await myRecord(campaignId.value)
        myRecordStatus.value = rec.status || '待提交'
        if (rec.files) recordForm.files = rec.files
      } catch (e) { myRecordStatus.value = '待提交' }
    } else {
      myRecordStatus.value = ''
    }
  } finally { loadingMy.value = false }
}

function onNewCampaign() {
  ElMessageBox.prompt('活动名称', '新建评审活动', { inputValue: '文件评审（第二次内审）' })
    .then(async ({ value }) => {
      await createCampaign({ title: value, year: String(new Date().getFullYear()) })
      ElMessage.success('已创建')
      await loadCampaigns()
    }).catch(() => {})
}
function onAssign() {
  assignMode.value = 'single'
  assignReviewer.value = null
  assignReviewers.value = []
  assignSelection.value = []
  assignSearch.value = ''
  assignVisible.value = true
}
function onAssignSelect(rows) {
  assignSelection.value = rows
}
function selectAllDocs() {
  assignTableRef.value?.toggleAllSelection()
}
function clearDocSelection() {
  assignTableRef.value?.clearSelection()
  assignSelection.value = []
}
async function submitAssign() {
  if (!assignSelection.value.length) {
    ElMessage.warning('请勾选至少一份文件'); return
  }
  const docsSel = assignSelection.value
  let reviewers = []
  if (assignMode.value === 'single') {
    if (!assignReviewer.value) { ElMessage.warning('请选择审核人'); return }
    const u = userMap.value[assignReviewer.value]
    reviewers = docsSel.map(() => ({ id: assignReviewer.value, name: u?.full_name || u?.username || '' }))
  } else {
    if (!assignReviewers.value.length) { ElMessage.warning('请选择至少一名审核人'); return }
    reviewers = docsSel.map((_, i) => {
      const rid = assignReviewers.value[i % assignReviewers.value.length]
      const u = userMap.value[rid]
      return { id: rid, name: u?.full_name || u?.username || '' }
    })
  }
  const items = docsSel.map((d, i) => ({ document_id: d.id, reviewer: reviewers[i].name, reviewer_id: reviewers[i].id }))
  await assignBatch(campaignId.value, items)
  ElMessage.success(`已分配 ${items.length} 份文件`)
  assignVisible.value = false
  await loadAll()
}
function openReceive(row) {
  const a = assignments.value.find(x => x.id === row.id) || row
  Object.assign(receiveForm, {
    assignment_id: a.id,
    doc_title: docTitle(a.document_id),
    revised_filename: a.revised_filename || '',
    accept_revisions: true,
    new_version: '2.0',
    revision_no: '0',
    audit_date: a.submitted_at ? a.submitted_at.slice(0, 10) : '',
    approve_date: '2026-09-01',
    effective_date: '2026-09-01',
    approver: '',
    final_file: null,
  })
  receiveVisible.value = true
}
async function previewRevision() {
  const row = assignments.value.find(a => a.id === receiveForm.assignment_id)
  if (!row) return
  revisionPreviewLoading.value = true
  revisionPreviewVisible.value = true
  revisionPreviewHtml.value = ''
  try {
    const blob = await downloadRevisionBlob(row.id)
    const arrayBuffer = await blob.arrayBuffer()
    const res = await mammoth.convertToHtml({ arrayBuffer })
    revisionPreviewHtml.value = res.value || '<p style="color:#909399">（文档内容为空）</p>'
  } catch (e) {
    revisionPreviewHtml.value = `<p style="color:#f56c6c">预览失败：${e && e.message ? e.message : '无法解析文档'}</p>`
  } finally {
    revisionPreviewLoading.value = false
  }
}

async function downloadRevisedFromReceive() {
  const row = assignments.value.find(a => a.id === receiveForm.assignment_id)
  if (!row) return
  const blob = await downloadRevisionBlob(row.id)
  triggerDownload(blob, row.revised_filename || `revised-${row.id}`)
}
async function submitReceive() {
  const row = assignments.value.find(a => a.id === receiveForm.assignment_id)
  if (!row) return
  const fd = new FormData()
  fd.append('new_version', receiveForm.new_version)
  fd.append('revision_no', receiveForm.revision_no)
  fd.append('audit_date', receiveForm.audit_date || '')
  fd.append('approve_date', receiveForm.approve_date)
  fd.append('effective_date', receiveForm.effective_date)
  fd.append('accept_revisions', receiveForm.accept_revisions ? 'true' : 'false')
  fd.append('approver', receiveForm.approver || '')
  if (receiveForm.final_file) {
    fd.append('file', receiveForm.final_file)
  }
  const r = await receiveRevision(row.id, fd)
  ElMessage.success(`已生成新版本 ${r.new_version}`)
  receiveVisible.value = false
  await loadAll()
}
async function loadStats() {
  if (!campaignId.value) return
  try {
    progressStats.value = await reviewerStats(campaignId.value)
  } catch (e) { progressStats.value = [] }
}
async function downloadDoc(docId) {
  const blob = await downloadDocumentBlob(docId)
  const name = docFileMap.value[docId] || docMap.value[docId] || `doc-${docId}`
  triggerDownload(blob, name)
}
async function downloadRevised(row) {
  const blob = await downloadRevisionBlob(row.id)
  triggerDownload(blob, row.revised_filename || `revised-${row.id}`)
}
async function doUpload(opt, row) {
  try {
    await uploadRevision(row.id, opt.file)
    ElMessage.success('修订文件已上传')
    await loadMy()
  } catch (e) { ElMessage.error('上传失败') }
}
async function submitRevision(row) {
  await submitReview(row.id, {})
  ElMessage.success('修订已提交')
  await loadMy()
}
async function viewAssignRecord(row) {
  const rec = row.record_json && typeof row.record_json === 'object' ? row.record_json : {}
  ElMessageBox.alert(
    `<div>专业组：${rec.review_group || '-'}</div>
     <div>评审时间：${rec.review_date || '-'}</div>
     <div>评审组成员：${rec.review_members || '-'}</div>
     <div>评审文件：${rec.review_files || '-'}</div>
     <div>主要存在问题：${rec.problems || '-'}</div>
     <div>记录人：${rec.recorder || '-'}　审批人：${rec.approver || '-'}</div>`,
    'A-027 评审记录', { dangerouslyUseHTMLString: true }
  )
}
async function openRecord() {
  try {
    const rec = await myRecord(campaignId.value)
    Object.assign(recordForm, {
      review_group: rec.review_group || '生免组',
      review_date: rec.review_date || '',
      review_members: rec.review_members || '',
      recorder: rec.recorder || '',
      approver: rec.approver || '金子铮',
      record_date: rec.record_date || '',
      approve_date: rec.approve_date || '',
      problems: rec.problems || '',
      files: rec.files || [],
    })
    myRecordStatus.value = rec.status || '待提交'
    recordVisible.value = true
  } catch (e) { ElMessage.error('加载评审记录失败') }
}
async function saveRecord(submit) {
  await upsertMyRecord(campaignId.value, { ...recordForm }, submit)
  ElMessage.success(submit ? '已提交文件评审记录' : '已保存')
  recordVisible.value = false
  myRecordStatus.value = submit ? '已提交' : '已填写'
  await loadMy()
}
async function onSummary() {
  const r = await reviewSummary(campaignId.value)
  summaryData.value = r || []
  const camp = campaigns.value.find(c => c.id === campaignId.value)
  summaryArchived.value = camp?.status === '已存档'
  summaryVisible.value = true
}
async function archiveSummary() {
  await updateCampaign(campaignId.value, { status: '已存档' })
  summaryArchived.value = true
  ElMessage.success('已确认存档')
  await loadCampaigns()
}
function buildSummaryHtml() {
  const camp = campaigns.value.find(c => c.id === campaignId.value)
  return buildReviewSummaryHtml({ campaignTitle: camp?.title || '', year: camp?.year || '', rows: summaryData.value })
}
function previewSummary() {
  summaryReportHtml.value = buildSummaryHtml()
  summaryReportVisible.value = true
}
function printSummary() { printHtml(buildSummaryHtml()) }
function downloadSummary() {
  const camp = campaigns.value.find(c => c.id === campaignId.value)
  downloadReportDoc(buildSummaryHtml(), `文件评审汇总_${camp?.title || ''}.doc`)
}
function triggerDownload(blob, name) {
  const url = window.URL.createObjectURL(new Blob([blob]))
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  window.URL.revokeObjectURL(url)
}

onMounted(async () => {
  await loadDict()
  await loadCampaigns()
  await loadAll()
})
</script>

<style scoped>
.bar { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; flex-wrap: wrap; }
.el-divider { margin: 12px 0; }
.my-record-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.assign-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.sel-count { color: #888; font-size: 13px; }
.reviewer-filter-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; flex-wrap: wrap; }
.progress-chips { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.form-tip { color: #909399; font-size: 12px; line-height: 1.4; margin-top: 4px; }
.text-muted { color: #909399; }
.revision-preview-html { max-height: 70vh; overflow: auto; background: #fff; padding: 4px; }
.revision-preview-html :deep(table) { border-collapse: collapse; }
.revision-preview-html :deep(th),
.revision-preview-html :deep(td) { border: 1px solid #dcdfe6; padding: 4px 8px; }
.revision-preview-html :deep(th) { background: #f5f7fa; }
.revision-preview-html :deep(pre) { white-space: pre-wrap; word-break: break-all; }
.summary-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; flex-wrap: wrap; }
.report-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.report-hint { color: #909399; font-size: 12px; }
.summary-report-html { max-height: 72vh; overflow: auto; background: #fff; padding: 8px; border: 1px solid #ebeef5; border-radius: 4px; }
.summary-report-html :deep(table) { border-collapse: collapse; width: 100%; font-size: 12px; }
.summary-report-html :deep(th), .summary-report-html :deep(td) { border: 1px solid #333; padding: 5px 7px; vertical-align: top; text-align: left; }
.summary-report-html :deep(h2) { text-align: center; font-size: 18px; }
</style>
