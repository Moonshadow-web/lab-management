<template>
  <div>
    <!-- 活动选择 / 新建 -->
    <div class="bar">
      <el-select v-model="campaignId" placeholder="选择评审活动" filterable style="width: 280px" @change="loadAll">
        <el-option v-for="c in campaigns" :key="c.id" :label="`${c.title}（${c.year}）`" :value="c.id" />
      </el-select>
      <el-button v-if="auth.canWrite('iso15189')" type="primary" @click="onNewCampaign">新建活动</el-button>
      <el-button v-if="auth.canWrite('iso15189')" :disabled="!campaignId" @click="onAssign">分配文件</el-button>
      <el-button v-if="auth.canWrite('iso15189')" :disabled="!campaignId" @click="onSummary">汇总 A-027</el-button>
    </div>

    <!-- 管理员：全部分配 -->
    <template v-if="auth.canWrite('iso15189')">
      <el-divider content-position="left">分配与接收（管理员）</el-divider>
      <el-table :data="assignments" border size="small" v-loading="loading">
        <el-table-column prop="document_id" label="文档" min-width="220">
          <template #default="{ row }">{{ docTitle(row.document_id) }}</template>
        </el-table-column>
        <el-table-column prop="reviewer" label="审核人" width="100" />
        <el-table-column prop="status" label="状态" width="110">
          <template #default="{ row }">
            <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="revised_filename" label="修订文件" min-width="160" />
        <el-table-column prop="document_new_version" label="生成版本" width="100" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" :disabled="!row.revised_cloud_key" @click="receive(row)">接收生成版本</el-button>
            <el-button size="small" text @click="viewRecord(row)">记录</el-button>
          </template>
        </el-table-column>
      </el-table>
    </template>

    <!-- 成员：我的任务 -->
    <el-divider content-position="left">我的评审任务</el-divider>
    <el-table :data="myTasks" border size="small" v-loading="loadingMy">
      <el-table-column prop="document_id" label="文档" min-width="220">
        <template #default="{ row }">{{ docTitle(row.document_id) }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="110">
        <template #default="{ row }">
          <el-tag size="small" :type="statusType(row.status)">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="300" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="downloadDoc(row.document_id)">下载原文件</el-button>
          <el-upload
            :show-file-list="false" :auto-upload="true"
            :http-request="(o) => doUpload(o, row)"
            style="display:inline-block;margin:0 6px"
          >
            <el-button size="small" type="primary">上传修订</el-button>
          </el-upload>
          <el-button size="small" @click="fillRecord(row)">填写A-027</el-button>
          <el-button size="small" type="success" :disabled="row.status !== '待评审' && row.status !== '已提交'" @click="submit(row)">提交</el-button>
          <el-button v-if="row.revised_cloud_key" size="small" text @click="downloadRevised(row)">下载修订</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分配弹窗 -->
    <el-dialog v-model="assignVisible" title="分配评审文件" width="640px">
      <el-form label-width="90px">
        <el-form-item label="审核人">
          <el-select v-model="assignForm.reviewer_id" filterable placeholder="选择成员" style="width:100%">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="评审文件">
          <el-select v-model="assignForm.doc_ids" multiple filterable placeholder="选择在用文件" style="width:100%">
            <el-option v-for="d in docs" :key="d.id" :label="d.title" :value="d.id" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="assignVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAssign">确定分配</el-button>
      </template>
    </el-dialog>

    <!-- A-027 填写弹窗 -->
    <el-dialog v-model="recordVisible" title="A-027 文件评审记录表" width="620px">
      <el-form :model="recordForm" label-width="100px">
        <el-form-item label="专业组"><el-input v-model="recordForm.review_group" /></el-form-item>
        <el-form-item label="评审时间"><el-input v-model="recordForm.review_date" placeholder="如 2026-08" /></el-form-item>
        <el-form-item label="评审组成员"><el-input v-model="recordForm.review_members" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="评审文件"><el-input v-model="recordForm.review_files" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="主要存在问题"><el-input v-model="recordForm.problems" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="记录人"><el-input v-model="recordForm.recorder" /></el-form-item>
        <el-form-item label="审批人"><el-input v-model="recordForm.approver" /></el-form-item>
        <el-form-item label="记录日期"><el-input v-model="recordForm.record_date" placeholder="YYYY-MM-DD" /></el-form-item>
        <el-form-item label="批准日期"><el-input v-model="recordForm.approve_date" placeholder="YYYY-MM-DD" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRecord">保存记录</el-button>
      </template>
    </el-dialog>

    <!-- 汇总弹窗 -->
    <el-dialog v-model="summaryVisible" title="文件评审汇总（A-027）" width="900px">
      <el-table :data="summaryData" border size="small" max-height="500">
        <el-table-column prop="document_title" label="评审文件" min-width="200" />
        <el-table-column prop="reviewer" label="审核人" width="90" />
        <el-table-column prop="status" label="状态" width="100" />
        <el-table-column prop="document_new_version" label="生成版本" width="90" />
        <el-table-column label="主要存在问题 / 记录" min-width="280">
          <template #default="{ row }">
            <div><b>问题：</b>{{ row.record?.problems || '-' }}</div>
            <div><b>记录人：</b>{{ row.record?.recorder || '-' }} <b>审批：</b>{{ row.record?.approver || '-' }}</div>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../utils/request'
import {
  listCampaigns, createCampaign, listAssignments, assignBatch, myAssignments,
  uploadRevision, downloadRevisionBlob, submitReview, receiveRevision, reviewSummary,
  downloadDocumentBlob,
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
const userMap = ref({})

const assignVisible = ref(false)
const assignForm = reactive({ reviewer_id: null, doc_ids: [] })
const recordVisible = ref(false)
const recordForm = reactive({})
const currentAid = ref(null)
const summaryVisible = ref(false)
const summaryData = ref([])

function statusType(s) {
  return { 待评审: 'info', 已提交: 'warning', 管理员已接收: 'success', 已完成: 'success' }[s] || 'info'
}
function docTitle(id) {
  return docMap.value[id] || `文档#${id}`
}
function userName(id) {
  const u = userMap.value[id]
  return u ? (u.full_name || u.username) : `用户#${id}`
}

async function loadDict() {
  try {
    const d = await request.get('/api/v1/documents', { params: { page_size: 500, hide_invalid: true } })
    docs.value = d.items || []
    const m = {}
    d.items.forEach((x) => (m[x.id] = x.title))
    docMap.value = m
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
  assignForm.reviewer_id = null
  assignForm.doc_ids = []
  assignVisible.value = true
}
async function submitAssign() {
  if (!assignForm.reviewer_id || !assignForm.doc_ids.length) {
    ElMessage.warning('请选择审核人与至少一份文件'); return
  }
  const u = userMap.value[assignForm.reviewer_id]
  const items = assignForm.doc_ids.map((did) => ({
    document_id: did, reviewer: u?.full_name || u?.username || '', reviewer_id: assignForm.reviewer_id,
  }))
  await assignBatch(campaignId.value, items)
  ElMessage.success('已分配')
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
  triggerDownload(blob, docMap.value[docId] || `doc-${docId}`)
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
function fillRecord(row) {
  currentAid.value = row.id
  const rec = row.record_json && typeof row.record_json === 'object' ? row.record_json : {}
  Object.assign(recordForm, {
    review_group: rec.review_group || '生免组',
    review_date: rec.review_date || '',
    review_members: rec.review_members || '',
    review_files: rec.review_files || '',
    problems: rec.problems || '',
    recorder: rec.recorder || '',
    approver: rec.approver || '',
    record_date: rec.record_date || '',
    approve_date: rec.approve_date || '',
  })
  recordVisible.value = true
}
async function saveRecord() {
  await submitReview(currentAid.value, { ...recordForm })
  ElMessage.success('已保存 A-027 记录')
  recordVisible.value = false
  await loadMy()
}
async function submit(row) {
  await submitReview(row.id, row.record_json && typeof row.record_json === 'object' ? row.record_json : {})
  ElMessage.success('已提交')
  await loadMy()
}
async function viewRecord(row) {
  const rec = row.record_json && typeof row.record_json === 'object' ? row.record_json : {}
  ElMessageBox.alert(
    `<div>专业组：${rec.review_group || '-'}</div>
     <div>评审时间：${rec.review_date || '-'}</div>
     <div>评审组成员：${rec.review_members || '-'}</div>
     <div>评审文件：${rec.review_files || '-'}</div>
     <div>主要存在问题：${rec.problems || '-'}</div>
     <div>记录人：${rec.recorder || '-'}　审批人：${rec.approver || '-'}</div>
     <div>记录日期：${rec.record_date || '-'}　批准日期：${rec.approve_date || '-'}</div>`,
    'A-027 评审记录', { dangerouslyUseHTMLString: true }
  )
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
</style>
