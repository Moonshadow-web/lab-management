<template>
  <div>
    <!-- 管理员：条款字典 + 活动 + 分配 -->
    <template v-if="auth.canWrite('iso15189')">
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
          <el-select v-model="assignForm.campaign_id" placeholder="选择活动" style="width:220px">
            <el-option v-for="c in campaigns" :key="c.id" :label="`${c.title}（${c.year}）`" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="员工">
          <el-select v-model="assignForm.assignee_id" filterable placeholder="选择员工" style="width:160px">
            <el-option v-for="u in users" :key="u.id" :label="u.full_name || u.username" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="条款范围">
          <el-input v-model="assignForm.clause_range" placeholder="如 第六章 资源要求" style="width:200px" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :disabled="!assignForm.campaign_id || !assignForm.assignee_id" @click="onPickClauses">选条款并分配</el-button>
        </el-form-item>
      </el-form>
    </template>

    <!-- 成员：我的条款分配 -->
    <el-divider content-position="left">我的自查分配</el-divider>
    <el-table :data="myAssigns" border size="small" v-loading="loadingMy">
      <el-table-column prop="assignee" label="员工" width="100" />
      <el-table-column prop="clause_range" label="条款范围" min-width="180" />
      <el-table-column prop="status" label="状态" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === '已提交' ? 'success' : 'warning'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" @click="openFill(row)">逐条填写</el-button>
          <el-button size="small" :disabled="row.status === '已提交'" @click="submitAssign(row)">提交</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 逐条填写弹窗 -->
    <el-dialog v-model="fillVisible" :title="`逐条填写（${fillRange}）`" width="860px">
      <div v-for="item in fillClauses" :key="item.clause.id" class="clause-card">
        <div class="clause-head">
          <b>{{ item.clause.clause_no }}</b>　{{ item.clause.title }}
          <span class="muted">（{{ item.clause.chapter }}）</span>
        </div>
        <div class="clause-content muted">{{ item.clause.content }}</div>
        <el-form label-width="90px" size="small">
          <el-form-item label="核查内容"><el-input v-model="item.form.check_content" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="核查结果">
            <el-select v-model="item.form.result" style="width:200px">
              <el-option v-for="r in resultOptions" :key="r" :label="r" :value="r" />
            </el-select>
          </el-form-item>
          <el-form-item label="问题描述"><el-input v-model="item.form.finding" type="textarea" :rows="2" /></el-form-item>
          <el-form-item label="采取措施"><el-input v-model="item.form.action" type="textarea" :rows="2" /></el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="fillVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveFill">保存全部条款</el-button>
      </template>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import request from '../../utils/request'
import {
  listClauses, createClause, updateClause, deleteClause, batchImportClauses,
  listCampaigns, createCampaign, updateCampaign, deleteCampaign,
  assignClausesBatch, myAssignments, assignmentClauses, upsertRecord, submitAssignment,
} from '../../api/selfInspection'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const users = ref([])
const campaigns = ref([])
const myAssigns = ref([])
const loadingMy = ref(false)
const resultOptions = ['符合', '不符合', '观察项', '不适用']

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
  await ElMessageBox.confirm('确认删除该活动？', '提示', { type: 'warning' })
  await deleteCampaign(row.id); ElMessage.success('已删除'); campCrud.value?.refresh()
}

// 分配条款
const assignForm = reactive({ campaign_id: null, assignee_id: null, clause_range: '' })
async function onPickClauses() {
  const r = await listClauses({ page_size: 1000 })
  const clauses = r.items || []
  if (!clauses.length) { ElMessage.warning('请先导入条款字典'); return }
  let picked = []
  try {
    picked = await ElMessageBox.prompt('输入要分配的条款号（逗号分隔，留空表示全选）：', '选择条款', { inputValue: '' })
      .then(({ value }) => value)
  } catch (e) { return }
  let sel
  if (!picked || !picked.trim()) sel = clauses.map((c) => c.id)
  else {
    const nos = picked.split(/[,，]/).map((s) => s.trim()).filter(Boolean)
    sel = clauses.filter((c) => nos.includes(c.clause_no)).map((c) => c.id)
  }
  if (!sel.length) { ElMessage.warning('未匹配到条款'); return }
  const u = users.value.find((x) => x.id === assignForm.assignee_id)
  await assignClausesBatch(assignForm.campaign_id, [{
    assignee: u?.full_name || u?.username || '', assignee_id: assignForm.assignee_id,
    clause_ids: sel, clause_range: assignForm.clause_range || `共${sel.length}条`,
  }])
  ElMessage.success('已分配')
  await loadMy()
}

// 批量导入条款
const importVisible = ref(false)
const importText = ref('')
function onImportClauses() { importText.value = ''; importVisible.value = true }
async function doImport() {
  const lines = importText.value.split('\n').map((l) => l.trim()).filter(Boolean)
  const items = []
  for (const line of lines) {
    const [clause_no, chapter, title, content] = line.split('|').map((s) => (s || '').trim())
    if (!clause_no && !title) continue
    items.push({ clause_no: clause_no || '', chapter: chapter || '', title: title || '', content: content || '' })
  }
  if (!items.length) { ElMessage.warning('没有可导入的条款'); return }
  await batchImportClauses(items)
  ElMessage.success(`已导入 ${items.length} 条`)
  importVisible.value = false
  clauseCrud.value?.refresh()
}

// 成员：我的分配 + 逐条填写
const fillVisible = ref(false)
const fillRange = ref('')
const fillClauses = ref([])
const fillAssign = ref(null)
async function openFill(row) {
  fillAssign.value = row
  fillRange.value = row.clause_range || ''
  const data = await assignmentClauses(row.id)
  fillClauses.value = (data || []).map((x) => ({
    clause: x.clause,
    form: reactive({
      check_content: x.record?.check_content || '',
      result: x.record?.result || '',
      finding: x.record?.finding || '',
      action: x.record?.action || '',
    }),
  }))
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
  await loadMy()
})
</script>

<style scoped>
.bar { margin-bottom: 8px; }
.el-divider { margin: 12px 0; }
.clause-card { border: 1px solid #ebeef5; border-radius: 6px; padding: 10px 14px; margin-bottom: 12px; }
.clause-head { font-size: 14px; margin-bottom: 4px; }
.clause-content { margin-bottom: 8px; line-height: 1.5; }
.muted { color: #909399; font-size: 12px; }
</style>
