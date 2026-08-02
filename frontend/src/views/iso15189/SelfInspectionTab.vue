<template>
  <div>
    <!-- 管理员：条款字典 + 活动 + 分配 -->
    <template v-if="auth.canManageIso15189">
      <el-divider content-position="left">条款字典（CNAS-AL02-07 附表3）</el-divider>
      <div class="bar">
        <el-button type="primary" @click="onImportClauses">批量导入条款</el-button>
      </div>
      <CrudTable
        ref="clauseCrud"
        :columns="clauseColumns"
        :fetch="fetchClauses"
        search-placeholder="搜索条款号 / 章节 / 标题..."
        :show-add="true"
        :can-write="true"
        @add="onAddClause"
        @edit="onEditClause"
        @delete="onDeleteClause"
      />
      <EditDialog
        v-model="clauseVisible"
        :title="clauseEditingId ? '编辑条款' : '新增条款'"
        :form="clauseForm"
        :fields="clauseFields"
        :submitting="clauseSubmitting"
        @submit="onSubmitClause"
      />

      <el-divider content-position="left">自查活动</el-divider>
      <CrudTable
        ref="campCrud"
        :columns="campColumns"
        :fetch="fetchCampaigns"
        search-placeholder="搜索活动..."
        :show-add="true"
        :can-write="true"
        @add="onAddCamp"
        @edit="onEditCamp"
        @delete="onDeleteCamp"
      />
      <EditDialog
        v-model="campVisible"
        :title="campEditingId ? '编辑活动' : '新建自查活动'"
        :form="campForm"
        :fields="campFields"
        :submitting="campSubmitting"
        @submit="onSubmitCamp"
      />

      <el-divider content-position="left">分配条款给员工</el-divider>
      <el-form :inline="true" class="bar">
        <el-form-item label="活动">
          <el-select v-model="assignForm.campaign_id" placeholder="选择活动" style="width:220px" @change="loadAssignDetail">
            <el-option v-for="c in campaigns" :key="c.id" :label="`${c.title}（${c.year}）`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="员工">
          <el-select v-model="assignForm.assignee_id" filterable placeholder="选择员工" style="width:160px">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="条款（可多选）">
          <el-select
            v-model="assignForm.clause_ids"
            multiple filterable collapse-tags
            placeholder="下拉选择多个具体条款（如 8.9.1）"
            style="width:420px"
          >
            <el-option v-for="c in clauseOptions" :key="c.id" :label="`${c.clause_no} ${c.title}`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!canAssign" @click="onAssignClauses">分配选中条款</el-button>
        </el-form-item>
      </el-form>

      <!-- 分配明细（谁分了什么、是否提交） -->
      <div v-if="assignForm.campaign_id" class="assign-detail">
        <div class="assign-detail-bar">
          <b>分配明细</b>
          <el-button size="small" type="primary" plain @click="reportCampaign">预览 / 下载 / 打印 全部</el-button>
        </div>
        <el-table :data="assignDetails" border size="small" v-loading="loadingDetail">
          <el-table-column prop="assignee" label="员工" width="110" />
          <el-table-column label="分配条款" min-width="280">
            <template #default="{ row }">{{ clauseNosOf(row).join('、') }}</template>
          </el-table-column>
          <el-table-column label="条数" width="70">
            <template #default="{ row }">{{ (row.clause_ids || []).length }}</template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag size="small" :type="row.status === '已提交' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <el-button size="small" text @click="printEmptySheet(row)">打印空表</el-button>
              <el-button size="small" text type="primary" @click="openReassign(row)">重新分配</el-button>
              <el-button size="small" text type="primary" @click="reportAssignment(row)">预览</el-button>
              <el-button size="small" text @click="printAssignment(row)">打印</el-button>
              <el-button size="small" text @click="downloadAssignment(row)">下载</el-button>
            </template>
          </el-table-column>
        </el-table>
        <el-empty v-if="!assignDetails.length" description="该活动尚未分配条款" :image-size="50" />
      </div>
    </template>

    <!-- 成员：我的条款分配 -->
    <el-divider content-position="left">我的自查分配</el-divider>
    <el-table :data="myAssigns" border size="small" v-loading="loadingMy">
      <el-table-column prop="assignee" label="员工" width="100" />
      <el-table-column label="分配条款" min-width="260">
        <template #default="{ row }">{{ clauseNosOf(row).join('、') }}</template>
      </el-table-column>
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === '已提交' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openFill(row)">逐条填写</el-button>
          <el-button size="small" :disabled="row.status === '已提交'" @click="submitAssign(row)">提交</el-button>
          <el-button size="small" @click="printEmptySheet(row)">打印空表</el-button>
          <el-button size="small" @click="reportAssignment(row)">报告</el-button>
        </template>
      </el-table-column>
    </el-table>
    <el-empty v-if="!myAssigns.length" description="当前活动暂无分配给您的条款" :image-size="50" />

    <!-- 逐条填写弹窗 -->
    <el-dialog v-model="fillVisible" :title="fillTitle" width="900px" top="3vh">
      <div v-for="item in fillClauses" :key="item.clause.id" class="clause-card" :class="{ 'clause-na': isNoRequirementClause(item.clause) }">
        <div class="clause-head">
          <b>{{ item.clause.clause_no }}</b>　{{ item.clause.title }}
          <span class="clause-chapter">（{{ item.clause.chapter }}）</span>
          <el-tag v-if="isNoRequirementClause(item.clause)" size="small" type="info" style="margin-left:8px">无具体应用要求 / 无需填写</el-tag>
        </div>
        <div class="clause-content">{{ item.clause?.content || '（无内容）' }}</div>
        <div v-if="item.clause?.application_requirement || item.clause?.check_point" class="clause-checkpoint">
          <b>应用要求：</b>{{ item.clause?.application_requirement || item.clause.check_point }}
        </div>
        <el-form v-if="!isNoRequirementClause(item.clause)" label-width="92px" size="small">
          <el-form-item label="核查内容">
            <el-input v-model="item.form.check_content" type="textarea" :rows="2" placeholder="如：查看程序文件 / 查看相关记录 / 现场查看……" />
          </el-form-item>
          <el-form-item label="核查结果">
            <el-select v-model="item.form.result" style="width:220px">
              <el-option v-for="r in resultOptions" :key="r" :label="r" :value="r" />
            </el-select>
          </el-form-item>
          <el-form-item label="问题描述"><el-input v-model="item.form.finding" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="采取措施"><el-input v-model="item.form.action" type="textarea" :rows="2" /></el-form-item>
        </el-form>
        <div v-else class="na-notice">该条款无具体应用要求，已自动标记为「不适用」。</div>
      </div>
      <template #footer>
        <el-button @click="fillVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveFill">保存全部条款</el-button>
      </template>
    </el-dialog>

    <!-- 报告预览弹窗（预览 / 下载 / 打印） -->
    <el-dialog v-model="reportVisible" :title="reportTitle" width="92%" top="2vh" append-to-body>
      <div class="report-bar">
        <el-button type="primary" @click="printCurrentReport">打印</el-button>
        <el-button @click="downloadCurrentReport">下载（Word）</el-button>
        <span class="report-hint">预览为只读；下载得到 .doc 文件，可用 Word 打开。</span>
      </div>
      <div class="report-html" v-html="reportHtml" />
    </el-dialog>

    <!-- 批量导入条款弹窗 -->
    <el-dialog v-model="importVisible" title="批量导入条款（每行一条）" width="720px">
      <el-alert type="info" :closable="false" show-icon
        title="格式：条款号|章节|标题|条款内容。可省略章节/内容，用空字段占位。多条换行。" />
      <el-input v-model="importText" type="textarea" :rows="12" placeholder="6.4.1|第六章 资源要求|人员|...\n6.4.2|第六章 资源要求|设施..." style="margin-top:10px" />
      <template #footer>
        <el-button @click="importVisible = false">取消</el-button>
        <el-button type="primary" @click="doImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 重新分配弹窗 -->
    <EditDialog
      v-model="reassignVisible"
      title="重新分配条款"
      :form="reassignForm"
      :fields="reassignFields"
      :submitting="reassignSubmitting"
      @submit="onSubmitReassign"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import request from '../../utils/request'
import {
  listClauses, createClause, updateClause, deleteClause, batchImportClauses,
  listCampaigns, createCampaign, updateCampaign, deleteCampaign, deleteCampaignCascade,
  assignClausesBatch, updateAssignment, myAssignments, assignmentClauses, upsertRecord, submitAssignment,
  listAssignments,
} from '../../api/selfInspection'
import { useAuthStore } from '../../store/auth'
import { buildSelfInspectionHtml, buildEmptySelfInspectionHtml, printHtml, downloadDoc } from '../../utils/reportExport'

const auth = useAuthStore()
const users = ref([])
const campaigns = ref([])
const myAssigns = ref([])
const loadingMy = ref(false)
const resultOptions = ['符合', '不符合', '观察项', '不适用']
const DEFAULT_CHECK = '查看程序文件\n查看相关记录\n现场查看：'
const NA_MARKS = ['', '（无）', '(无)']
function isNoRequirementClause(c) {
  if (!c) return false
  const contentEmpty = NA_MARKS.includes((c.content || '').trim())
  const appEmpty = NA_MARKS.includes((c.application_requirement || '').trim()) && NA_MARKS.includes((c.check_point || '').trim())
  return contentEmpty && appEmpty
}

// 条款字典 CRUD
const clauseCrud = ref(null)
const clauseVisible = ref(false)
const clauseEditingId = ref(null)
const clauseSubmitting = ref(false)
const clauseFields = [
  { prop: 'clause_no', label: '条款号' },
  { prop: 'chapter', label: '章节' },
  { prop: 'title', label: '标题' },
  { prop: 'content', label: '条款内容', type: 'textarea' },
  { prop: 'check_point', label: '核查要点', type: 'textarea' },
]
const clauseColumns = [
  { prop: 'clause_no', label: '条款号', width: 100 },
  { prop: 'chapter', label: '章节', width: 160 },
  { prop: 'title', label: '标题', minWidth: 200 },
  { prop: 'content', label: '条款内容', minWidth: 260 },
]
const emptyClause = () => ({ clause_no: '', chapter: '', title: '', content: '', check_point: '' })
const clauseForm = reactive(emptyClause())
function fetchClauses(params) { return listClauses(params) }
function onAddClause() { Object.assign(clauseForm, emptyClause()); clauseEditingId.value = null; clauseVisible.value = true }
function onEditClause(row) { Object.assign(clauseForm, emptyClause(), row); clauseEditingId.value = row.id; clauseVisible.value = true }
async function onSubmitClause() {
  clauseSubmitting.value = true
  try {
    if (clauseEditingId.value) await updateClause(clauseEditingId.value, { ...clauseForm })
    else await createClause({ ...clauseForm })
    ElMessage.success('已保存'); clauseVisible.value = false; clauseCrud.value?.refresh()
  } catch (e) { ElMessage.error('保存失败') } finally { clauseSubmitting.value = false }
}
async function onDeleteClause(row) {
  await ElMessageBox.confirm('确认删除该条款？', '提示', { type: 'warning' })
  await deleteClause(row.id); ElMessage.success('已删除'); clauseCrud.value?.refresh()
}

// 活动 CRUD
const campCrud = ref(null)
const campVisible = ref(false)
const campEditingId = ref(null)
const campSubmitting = ref(false)
const campFields = [
  { prop: 'title', label: '活动名称' },
  { prop: 'year', label: '年度' },
  { prop: 'due_date', label: '截止日期' },
  { prop: 'status', label: '状态' },
  { prop: 'note', label: '备注', type: 'textarea' },
]
const campColumns = [
  { prop: 'title', label: '活动名称', minWidth: 200 },
  { prop: 'year', label: '年度', width: 80 },
  { prop: 'due_date', label: '截止', width: 110 },
  { prop: 'status', label: '状态', width: 90 },
]
const emptyCamp = () => ({ title: '', year: String(new Date().getFullYear()), due_date: '', status: '进行中', note: '' })
const campForm = reactive(emptyCamp())
function fetchCampaigns(params) { return listCampaigns(params) }
function onAddCamp() { Object.assign(campForm, emptyCamp()); campEditingId.value = null; campVisible.value = true }
function onEditCamp(row) { Object.assign(campForm, emptyCamp(), row); campEditingId.value = row.id; campVisible.value = true }
async function onSubmitCamp() {
  campSubmitting.value = true
  try {
    if (campEditingId.value) await updateCampaign(campEditingId.value, { ...campForm })
    else await createCampaign({ ...campForm })
    ElMessage.success('已保存'); campVisible.value = false; campCrud.value?.refresh()
    await loadCampaigns()
  } catch (e) { ElMessage.error('保存失败') } finally { campSubmitting.value = false }
}
async function onDeleteCamp(row) {
  try {
    await ElMessageBox.confirm('确认删除该活动？其下的分配与自查记录将一并删除。', '提示', { type: 'warning' })
    await deleteCampaignCascade(row.id)
    ElMessage.success('已删除')
    campCrud.value?.refresh()
    await loadAssignDetail(); await loadMy()
  } catch (e) {
    if (e !== 'cancel' && e?.type !== 'cancel' && !(e?.toString?.().includes('cancel'))) {
      ElMessage.error('删除失败：' + (e?.response?.data?.detail || e?.message || e))
    }
  }
}

// 全部条款（用于下拉多选分配）
const allClauses = ref([])
const allClausesMap = computed(() => {
  const map = {}
  for (const c of allClauses.value) map[c.id] = c
  return map
})
async function loadAllClauses() {
  // 条款字典为公开配置信息，任何登录用户都需读取（成员视图也要显示条款号），故不以 canWrite 收口
  if (!auth.isLoggedIn) return
  try {
    const r = await listClauses({ page_size: 1000 })
    allClauses.value = r.items || []
  } catch (e) {}
}
const clauseOptions = computed(() => {
  return [...allClauses.value].sort((a, b) => natCmp(a.clause_no, b.clause_no))
})
function clauseNosOf(row) {
  const ids = row.clause_ids || []
  return ids.map(id => allClausesMap.value[id]?.clause_no).filter(Boolean).sort(natCmp)
}

// 分配条款（下拉多选 -> 具体条款）
const assignForm = reactive({ campaign_id: null, assignee_id: null, clause_ids: [] })
const assignDetails = ref([])
const loadingDetail = ref(false)
const canAssign = computed(() => assignForm.campaign_id && assignForm.assignee_id && assignForm.clause_ids.length)
async function onAssignClauses() {
  if (!canAssign.value) { ElMessage.warning('请选择活动、员工与至少一个条款'); return }
  const selected = assignForm.clause_ids.map(id => allClausesMap.value[id]).filter(Boolean)
  const ids = selected.map(c => c.id)
  if (!ids.length) { ElMessage.warning('未匹配到条款'); return }
  const u = users.value.find(x => x.id === assignForm.assignee_id)
  await assignClausesBatch(assignForm.campaign_id, [{
    assignee: u?.full_name || u?.username || '',
    assignee_id: assignForm.assignee_id,
    clause_ids: ids,
    clause_range: selected.map(c => c.clause_no).sort(natCmp).join('、'),
  }])
  ElMessage.success('已分配')
  assignForm.clause_ids = []
  await loadAssignDetail()
  await loadMy()
}
async function loadAssignDetail() {
  if (!assignForm.campaign_id) { assignDetails.value = []; return }
  loadingDetail.value = true
  try {
    const r = await listAssignments({ campaign_id: assignForm.campaign_id, page_size: 500 })
    assignDetails.value = r.items || []
  } catch (e) { assignDetails.value = [] } finally { loadingDetail.value = false }
}

// 重新分配
const reassignVisible = ref(false)
const reassignSubmitting = ref(false)
const reassignId = ref(null)
const reassignForm = reactive({ assignee_id: null, clause_ids: [] })
const userOptions = computed(() => users.value.map(u => ({ label: u.full_name || u.username, value: u.id })))
const reassignFields = computed(() => [
  { prop: 'assignee_id', label: '员工', type: 'select', options: userOptions.value },
  { prop: 'clause_ids', label: '条款', type: 'select', multiple: true,
    options: clauseOptions.value.map(c => ({ label: `${c.clause_no} ${c.title}`, value: c.id })) },
])
function openReassign(row) {
  reassignId.value = row.id
  reassignForm.assignee_id = row.assignee_id || null
  reassignForm.clause_ids = Array.isArray(row.clause_ids) ? [...row.clause_ids] : []
  reassignVisible.value = true
}
async function onSubmitReassign() {
  if (!reassignForm.assignee_id || !reassignForm.clause_ids.length) {
    ElMessage.warning('请选择员工与至少一个条款'); return
  }
  reassignSubmitting.value = true
  try {
    const selected = reassignForm.clause_ids.map(id => allClausesMap.value[id]).filter(Boolean)
    const u = users.value.find(x => x.id === reassignForm.assignee_id)
    await updateAssignment(reassignId.value, {
      assignee: u?.full_name || u?.username || '',
      assignee_id: reassignForm.assignee_id,
      clause_ids: reassignForm.clause_ids,
      clause_range: selected.map(c => c.clause_no).sort(natCmp).join('、'),
    })
    ElMessage.success('已重新分配')
    reassignVisible.value = false
    await loadAssignDetail()
    await loadMy()
  } catch (e) { ElMessage.error('重新分配失败') } finally { reassignSubmitting.value = false }
}

// 批量导入条款
const importVisible = ref(false)
const importText = ref('')
function onImportClauses() { importText.value = ''; importVisible.value = true }
async function doImport() {
  const lines = importText.value.split('\n').map(l => l.trim()).filter(Boolean)
  const items = []
  for (const line of lines) {
    const [clause_no, chapter, title, content] = line.split('|').map(s => (s || '').trim())
    if (!clause_no && !title) continue
    items.push({ clause_no: clause_no || '', chapter: chapter || '', title: title || '', content: content || '' })
  }
  if (!items.length) { ElMessage.warning('没有可导入的条款'); return }
  await batchImportClauses(items)
  ElMessage.success(`已导入 ${items.length} 条`)
  importVisible.value = false
  clauseCrud.value?.refresh()
  await loadAllClauses()
}

// 成员：我的分配 + 逐条填写
const fillVisible = ref(false)
const fillTitle = ref('')
const fillClauses = ref([])
const fillAssign = ref(null)
async function openFill(row) {
  fillAssign.value = row
  fillTitle.value = `逐条填写 — ${row.assignee}（${row.clause_range || ''}）`
  const data = await assignmentClauses(row.id)
  fillClauses.value = (data || [])
    .map(x => {
      const na = isNoRequirementClause(x.clause)
      return {
        clause: x.clause,
        form: reactive({
          check_content: x.record?.check_content || (na ? '' : DEFAULT_CHECK),
          result: x.record?.result || (na ? '不适用' : ''),
          finding: x.record?.finding || '',
          action: x.record?.action || '',
        }),
      }
    })
    .sort((a, b) => natCmp(a.clause?.clause_no, b.clause?.clause_no))
  fillVisible.value = true
}
async function saveFill() {
  const a = fillAssign.value
  for (const item of fillClauses.value) {
    await upsertRecord({
      campaign_id: a.campaign_id, assignment_id: a.id, clause_id: item.clause.id,
      check_content: item.form.check_content, result: item.form.result,
      finding: item.form.finding, action: item.form.action,
    })
  }
  ElMessage.success('已保存全部条款')
  await loadMy()
}
async function submitAssign(row) {
  await submitAssignment(row.id)
  ElMessage.success('已提交')
  await loadMy()
}

// 报告（预览 / 下载 / 打印）
const reportVisible = ref(false)
const reportTitle = ref('')
const reportHtml = ref('')
const reportName = ref('自查报告.doc')
function normalizeRows(items) {
  return (items || [])
    .map(x => ({
      clause_no: x.clause?.clause_no || x.clause_no || '',
      title: x.clause?.title || x.title || '',
      content: x.clause?.content || x.content || '',
      check_point: x.clause?.check_point || x.check_point || '',
      application_requirement: x.clause?.application_requirement || x.application_requirement || '',
      check_content: x.record?.check_content || x.check_content || '',
      result: x.record?.result || x.result || '',
      finding: x.record?.finding || x.finding || '',
      action: x.record?.action || x.action || '',
    }))
    .sort((a, b) => natCmp(a.clause_no, b.clause_no))
}
async function buildAssignmentReport(row) {
  const data = await assignmentClauses(row.id)
  const rows = normalizeRows(data)
  const name = row.assignee || '员工'
  const camp = campaigns.value.find(c => c.id === row.campaign_id)
  reportTitle.value = `自查报告 — ${name}`
  reportName.value = `自查报告_${name}_${camp?.title || ''}.doc`
  reportHtml.value = buildSelfInspectionHtml({
    campaignTitle: camp?.title || '', year: camp?.year || '', assignee: name,
    rows, generatedAt: new Date().toLocaleString('zh-CN'),
  })
  reportVisible.value = true
}
function reportAssignment(row) { buildAssignmentReport(row) }
function printAssignment(row) { buildAssignmentReport(row).then(() => printCurrentReport()) }
function downloadAssignment(row) { buildAssignmentReport(row).then(() => downloadCurrentReport()) }
async function printEmptySheet(row) {
  const data = await assignmentClauses(row.id)
  const rows = normalizeRows(data).map(r => ({ ...r, check_content: r.check_content || DEFAULT_CHECK }))
  const camp = campaigns.value.find(c => c.id === row.campaign_id)
  const html = buildEmptySelfInspectionHtml({
    campaignTitle: camp?.title || '', year: camp?.year || '', assignee: row.assignee || '', rows,
  })
  printHtml(html)
}
async function reportCampaign() {
  if (!assignForm.campaign_id) return
  const summary = await selfInspectionSummaryLocal(assignForm.campaign_id)
  const camp = campaigns.value.find(c => c.id === assignForm.campaign_id)
  const allRows = []
  for (const a of summary) {
    for (const c of (a.clauses || [])) allRows.push(c)
  }
  reportTitle.value = `自查汇总 — ${camp?.title || ''}`
  reportName.value = `自查汇总_${camp?.title || ''}.doc`
  reportHtml.value = buildSelfInspectionHtml({
    campaignTitle: camp?.title || '', year: camp?.year || '', assignee: '全部分配人',
    rows: normalizeRows(allRows), generatedAt: new Date().toLocaleString('zh-CN'),
  })
  reportVisible.value = true
}
function printCurrentReport() { if (reportHtml.value) printHtml(reportHtml.value) }
function downloadCurrentReport() { if (reportHtml.value) downloadDoc(reportHtml.value, reportName.value) }

// 取活动级汇总（用于全部导出）
async function selfInspectionSummaryLocal(cid) {
  return request.get('/api/v1/self-inspection/campaigns/' + cid + '/summary').then(r => r || [])
}

async function loadUsers() {
  try {
    const u = await request.get('/api/v1/users', { params: { page_size: 500 } })
    users.value = u.items || u || []
  } catch (e) {}
}
async function loadCampaigns() {
  const r = await listCampaigns({ page_size: 100 })
  campaigns.value = r.items || []
}
async function loadMy() {
  loadingMy.value = true
  try {
    const r = await myAssignments()
    myAssigns.value = r || []
  } finally { loadingMy.value = false }
}
onMounted(async () => {
  await loadUsers()
  await loadCampaigns()
  await loadAllClauses()
  await loadMy()
})

// 自然排序（条款号 4.1 < 4.2 < 5.1 ...）
function natKey(s) { return (s || '').split('.').map(p => parseInt(p, 10) || 0) }
function natCmp(a, b) {
  const x = natKey(a), y = natKey(b)
  const n = Math.max(x.length, y.length)
  for (let i = 0; i < n; i++) {
    const d = (x[i] || 0) - (y[i] || 0)
    if (d) return d
  }
  return 0
}
</script>

<style scoped>
.bar { margin-bottom: 8px; display: flex; flex-wrap: wrap; gap: 8px; align-items: flex-end; }
.el-divider { margin: 12px 0; }
.clause-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px 16px; margin-bottom: 14px; }
.clause-head { font-size: 15px; font-weight: 600; margin-bottom: 6px; }
.clause-chapter { color: #909399; font-size: 13px; font-weight: 400; }
.clause-content {
  margin-bottom: 10px; line-height: 1.7; font-size: 14px; color: #303133;
  white-space: pre-wrap; word-break: break-word;
  background: #fafafa; border-left: 3px solid #409eff; padding: 8px 12px; border-radius: 4px;
}
.clause-checkpoint {
  margin-bottom: 10px; line-height: 1.7; font-size: 13px; color: #8b4513;
  white-space: pre-wrap; word-break: break-word;
  background: #fff8e1; border-left: 3px solid #ff9800; padding: 8px 12px; border-radius: 4px;
}
.clause-na { background: #f5f7fa; }
.clause-na .clause-content { background: #ebeef5; border-left-color: #c0c4cc; color: #909399; }
.na-notice { color: #909399; font-size: 13px; padding: 8px 0; }
.assign-detail { margin-top: 12px; border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; }
.assign-detail-bar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 8px; }
.report-bar { display: flex; align-items: center; gap: 10px; margin-bottom: 10px; }
.report-hint { color: #909399; font-size: 12px; }
.report-html {
  max-height: 72vh; overflow: auto; background: #fff; padding: 8px;
  border: 1px solid #ebeef5; border-radius: 4px;
}
.report-html :deep(table) { border-collapse: collapse; width: 100%; font-size: 12px; }
.report-html :deep(th), .report-html :deep(td) { border: 1px solid #333; padding: 5px 7px; vertical-align: top; text-align: left; }
.report-html :deep(th) { background: #f2f2f2; text-align: center; }
.report-html :deep(h2) { text-align: center; font-size: 18px; }
</style>
