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
      <el-table :data="assignments" border size="small" v-loading="loading">
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
            <el-button size="small" :disabled="!row.revised_cloud_key" @click="receive(row)">接收生成版本</el-button>
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
          <el-col :span="12"><el-form-item label="评审时间"><el-input v-model="recordForm.review_date" placeholder="如 2026-08" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="评审组成员">
          <el-input v-model="recordForm.review_members" type="textarea" :rows="2" readonly placeholder="本活动全部被分配成员" />
        </el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="记录人"><el-input v-model="recordForm.recorder" readonly /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="审批人"><el-input v-model="recordForm.approver" placeholder="默认 金子铮" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="记录日期"><el-input v-model="recordForm.record_date" placeholder="YYYY-MM-DD" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="批准日期"><el-input v-model="recordForm.approve_date" placeholder="YYYY-MM-DD" /></el-form-item></el-col>
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

    <!-- 汇总弹窗：按人 A-027 -->
    <el-dialog v-model="summaryVisible" title="文件评审汇总（A-027，按人）" width="960px" top="4vh">
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
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../utils/request'
import {
  listCampaigns, createCampaign, listAssignments, assignBatch, myAssignments,
  uploadRevision, downloadRevisionBlob, submitReview, receiveRevision, reviewSummary,
  downloadDocumentBlob, myRecord, upsertMyRecord,
} from '../../api/review'
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
async function receive(row) {
  await ElMessageBox.confirm(`确认接收「${docTitle(row.document_id)}」的修订并生成新版本？`, '提示', { type: 'warning' })
  const r = await receiveRevision(row.id)
  ElMessage.success(`已生成新版本 ${r.new_version}`)
  await loadAll()
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
  summaryVisible.value = true
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
</style>
