<template>
  <div class="page">
    <!-- 我的今日 -->
    <el-card class="block">
      <template #header>
        <div class="card-head">
          <span>今日我的岗位（{{ todayStr }}）</span>
          <el-button size="small" @click="loadMyToday">刷新</el-button>
        </div>
      </template>
      <el-empty v-if="!myToday.length" description="今日无排班记录" :image-size="60" />
      <div v-else class="my-today">
        <el-tag
          v-for="m in myToday"
          :key="m.id || m.post_id"
          :type="m.group === 'night' ? 'danger' : (m.group === 'special' ? 'warning' : 'primary')"
          effect="light"
          class="mt-chip"
        >
          {{ m.post_name }}
          <template v-if="m.is_early"><span class="tag-sub">早班</span></template>
          <template v-if="m.is_continuous"><span class="tag-sub">连班</span></template>
          <span v-if="m.status && m.status !== '在岗'" class="tag-sub">{{ m.status }}</span>
        </el-tag>
      </div>
    </el-card>

    <!-- 排班设置 -->
    <el-card class="block">
      <template #header>
        <div class="card-head">
          <span>排班设置</span>
          <el-button size="small" type="primary" @click="openConfig">配置</el-button>
        </div>
      </template>
      <div class="cfg-summary">
        <span>不参与排班：<b>{{ configExcludedText || '（无）' }}</b></span>
        <el-divider direction="vertical" />
        <span>常规生成：<b>{{ genDays }}</b> 天</span>
        <el-divider direction="vertical" />
        <span>早/连班可提前：<b>{{ earlyContDays }}</b> 天</span>
      </div>
      <el-alert type="info" :closable="false" class="tip" title="排班规则说明">
        ① 夜班（生化夜班/发热夜班）由科室提前录入，系统不自动生成；② 发热白班为每月固定一人、每4个工作日一班（在「排班计划」里指定固定人）；
        ③ 休息/病假/开会/行政/质控 日期人数不定，需提前在下方「手动录入」；④ 自动生成仅排工作日白班岗，按各岗固定人员轮转；
        ⑤ 排除名单中的人员永不被排入。
      </el-alert>
    </el-card>

    <!-- 岗位定义 -->
    <el-card class="block">
      <template #header><span>岗位定义</span></template>
      <CrudTable
        ref="postCrud"
        :columns="postColumns"
        :fetch="fetchPosts"
        search-placeholder="搜索岗位..."
        :show-add="auth.canWrite('scheduling')"
        :can-write="auth.canWrite('scheduling')"
        @add="onAddPost"
        @edit="onEditPost"
        @delete="onDeletePost"
      />
      <EditDialog
        v-model="postDialog"
        :title="postEditingId ? '编辑岗位' : '新增岗位'"
        :form="postForm"
        :fields="postFields"
        :rules="postRules"
        :submitting="submitting"
        @submit="onSubmitPost"
      />
    </el-card>

    <!-- 排班计划 -->
    <el-card class="block">
      <template #header><span>排班计划</span></template>
      <CrudTable
        ref="planCrud"
        :columns="planColumns"
        :fetch="fetchPlans"
        search-placeholder="搜索计划..."
        :show-add="auth.canWrite('scheduling')"
        :can-write="auth.canWrite('scheduling')"
        @add="onAddPlan"
        @edit="onEditPlan"
        @delete="onDeletePlan"
      />
      <EditDialog
        v-model="planDialog"
        :title="planEditingId ? '编辑计划' : '新增计划'"
        :form="planForm"
        :fields="planFields"
        :rules="planRules"
        :submitting="submitting"
        @submit="onSubmitPlan"
      />
    </el-card>

    <!-- 排班表 -->
    <el-card class="block">
      <template #header>
        <div class="card-head">
          <span>排班表</span>
          <div class="grid-ctrl">
            <el-select v-model="selPlan" placeholder="选择计划" style="width: 200px" @change="onPlanChange">
              <el-option v-for="p in planOptions" :key="p.id" :label="p.name" :value="p.id" />
            </el-select>
            <el-date-picker v-model="gridStart" type="date" value-format="YYYY-MM-DD" placeholder="开始" style="width: 150px" />
            <el-date-picker v-model="gridEnd" type="date" value-format="YYYY-MM-DD" placeholder="结束" style="width: 150px" />
            <el-select v-model="genDays" style="width: 120px" title="生成天数">
              <el-option v-for="d in [7,14,30]" :key="d" :label="`生成${d}天`" :value="d" />
            </el-select>
            <el-button type="primary" :loading="generating" @click="onGenerate">生成排班</el-button>
            <el-button :loading="gridLoading" @click="loadGrid">查询</el-button>
          </div>
        </div>
      </template>
      <el-input
        v-model="peopleText"
        type="textarea"
        :rows="2"
        class="people-input"
        placeholder="生成时白班岗的通用轮转人员（缺省用系统全部活跃用户）。各岗固定人员优先于此处；排除名单人员自动跳过。每行一个姓名，或逗号分隔。"
      />
      <el-table v-if="grid.dates.length" :data="grid.posts" border class="grid" :max-height="520">
        <el-table-column prop="name" label="岗位" fixed width="140">
          <template #default="{ row }">
            <div class="post-cell">
              <span>{{ row.name }}</span>
              <el-tag size="small" :type="groupType(row.group)">{{ groupLabel(row.group) }}</el-tag>
              <el-tag v-if="row.is_fever_day" size="small" type="success">发热固定</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column v-for="d in grid.dates" :key="d" :label="fmtDate(d)" :width="104" align="center">
          <template #default="{ row }">
            <div class="cell" :class="cellClass(row, d)">
              <span class="person">{{ cellOf(row, d).person || '—' }}</span>
              <span v-if="cellOf(row, d).is_early" class="mini-tag early">早</span>
              <span v-if="cellOf(row, d).is_continuous" class="mini-tag cont">连</span>
              <span v-if="cellOf(row, d).status && cellOf(row, d).status !== '在岗'" class="mini-tag st">{{ cellOf(row, d).status }}</span>
            </div>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-else description="请选择计划并设置日期范围后查询/生成" />
    </el-card>

    <!-- 手动录入 / 修改分配 -->
    <el-card class="block">
      <template #header>
        <div class="card-head">
          <span>手动录入 / 修改分配（夜班、休息、病假、开会、行政、质控等提前录入）</span>
        </div>
      </template>
      <el-form :model="cellForm" label-width="110px" class="cell-form">
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="计划">
              <el-select v-model="cellForm.plan_id" style="width: 100%">
                <el-option v-for="p in planOptions" :key="p.id" :label="p.name" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="日期">
              <el-date-picker v-model="cellForm.date" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="岗位">
              <el-select v-model="cellForm.post_id" style="width: 100%">
                <el-option v-for="p in postsAll" :key="p.id" :label="p.name + (p.is_fever_day ? '（发热）' : '')" :value="p.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="人员">
              <UserSelect v-model="cellForm.person" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="状态">
              <el-select v-model="cellForm.status" style="width: 100%">
                <el-option v-for="s in STATUS_OPTS" :key="s.value" :label="s.label" :value="s.value" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="早班 / 连班">
              <el-switch v-model="cellForm.is_early" active-text="早" style="margin-right: 10px" />
              <el-switch v-model="cellForm.is_continuous" active-text="连" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="16">
            <el-form-item label="备注">
              <el-input v-model="cellForm.note" placeholder="可选" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label=" ">
              <el-button type="primary" :loading="cellSaving" @click="saveCell">保存此格</el-button>
              <el-button :disabled="!cellId" @click="deleteCell">删除此格</el-button>
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <!-- 排班配置弹窗 -->
    <EditDialog
      v-model="configDialog"
      title="排班配置"
      :form="configForm"
      :fields="configFields"
      :rules="{}"
      :submitting="configSaving"
      @submit="saveConfig"
    />
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import UserSelect from '../../components/UserSelect.vue'
import { useAuthStore } from '../../store/auth'
import {
  listSchedulingPosts, createSchedulingPost, updateSchedulingPost, deleteSchedulingPost,
  listSchedulingPlans, createSchedulingPlan, updateSchedulingPlan, deleteSchedulingPlan,
  listSchedulingAssignments, deleteSchedulingAssignment,
  getSchedulingGrid, getMyToday, generateScheduling,
  getSchedulingConfig, updateSchedulingConfig, setSchedulingCell,
} from '../../api/scheduling'
import { listActiveUsers } from '../../api/users'

const auth = useAuthStore()
const todayStr = new Date().toISOString().slice(0, 10)

const STATUS_OPTS = [
  { label: '在岗', value: '在岗' },
  { label: '休息', value: '休息' },
  { label: '病假', value: '病假' },
  { label: '开会', value: '开会' },
  { label: '行政', value: '行政' },
  { label: '质控', value: '质控' },
]

function parsePeople(text) {
  return (text || '').split(/[\n,，]+/).map((s) => s.trim()).filter(Boolean)
}

// ---------------- 我的今日 ----------------
const myToday = ref([])
async function loadMyToday() {
  try { myToday.value = await getMyToday() } catch (e) { myToday.value = [] }
}

// ---------------- 配置 ----------------
const configDialog = ref(false)
const configSaving = ref(false)
const genDays = ref(14)
const earlyContDays = ref(30)
const configExcluded = ref([])
const configExcludedText = computed(() => (configExcluded.value || []).join('、') || '')
const configForm = reactive({ excluded_people: '', default_window_days: 14, early_continuous_window_days: 30 })
const configFields = [
  { prop: 'excluded_people', label: '不参与排班人员', type: 'textarea', placeholder: '逗号或换行分隔，如 王学晶,李东,管理员' },
  { prop: 'default_window_days', label: '常规生成天数', type: 'number' },
  { prop: 'early_continuous_window_days', label: '早班/连班可提前天数', type: 'number' },
]
async function openConfig() {
  try {
    const cfg = await getSchedulingConfig()
    configExcluded.value = cfg.excluded_people || []
    genDays.value = cfg.default_window_days || 14
    earlyContDays.value = cfg.early_continuous_window_days || 30
    Object.assign(configForm, {
      excluded_people: (cfg.excluded_people || []).join('\n'),
      default_window_days: cfg.default_window_days || 14,
      early_continuous_window_days: cfg.early_continuous_window_days || 30,
    })
    configDialog.value = true
  } catch (e) { ElMessage.error('读取配置失败') }
}
async function saveConfig() {
  configSaving.value = true
  try {
    const payload = {
      excluded_people: parsePeople(configForm.excluded_people),
      default_window_days: configForm.default_window_days || 14,
      early_continuous_window_days: configForm.early_continuous_window_days || 30,
    }
    const cfg = await updateSchedulingConfig(payload)
    configExcluded.value = cfg.excluded_people || []
    genDays.value = cfg.default_window_days || 14
    earlyContDays.value = cfg.early_continuous_window_days || 30
    ElMessage.success('已保存')
    configDialog.value = false
  } catch (e) { ElMessage.error('保存失败') }
  finally { configSaving.value = false }
}

// ---------------- 岗位定义 ----------------
const postCrud = ref(null)
const postDialog = ref(false)
const postEditingId = ref(null)
const submitting = ref(false)
const GROUP_OPTIONS = [
  { label: '白班', value: 'day' },
  { label: '夜班', value: 'night' },
  { label: '特殊(如周三质谱)', value: 'special' },
]
const WEEKDAY_NULL = [{ label: '不限', value: null }]
const WEEKDAY_OPTS = [
  { label: '周一', value: 0 }, { label: '周二', value: 1 }, { label: '周三', value: 2 },
  { label: '周四', value: 3 }, { label: '周五', value: 4 }, { label: '周六', value: 5 }, { label: '周日', value: 6 },
]
const WEEKDAY_TEXT = ['周一', '周二', '周三', '周四', '周五', '周六', '周日']

function groupLabel(g) { return { day: '白班', night: '夜班', special: '特殊' }[g] || g }
function groupType(g) { return { day: 'primary', night: 'danger', special: 'warning' }[g] || 'info' }

const postColumns = [
  { prop: 'name', label: '岗位名称', width: 130 },
  { prop: 'group', label: '分组', width: 90, formatter: (r) => `<el-tag size="small" type="${groupType(r.group)}">${groupLabel(r.group)}</el-tag>` },
  { prop: 'required', label: '每日必填', width: 100, formatter: (r) => (r.required ? '是' : '否(可空缺)') },
  { prop: 'only_weekday', label: '仅星期', width: 90, formatter: (r) => (r.only_weekday == null ? '—' : WEEKDAY_TEXT[r.only_weekday]) },
  { prop: 'required_weekday', label: '必填星期', width: 100, formatter: (r) => (r.required_weekday == null ? '—' : WEEKDAY_TEXT[r.required_weekday]) },
  { prop: 'is_fever_day', label: '发热固定', width: 90, formatter: (r) => (r.is_fever_day ? '是' : '否') },
  { prop: 'preferred_people', label: '固定/优先人员', minWidth: 160, formatter: (r) => (r.preferred_people && r.preferred_people.length ? r.preferred_people.join('、') : '—') },
  { prop: 'order', label: '顺序', width: 70 },
  { prop: 'notes', label: '备注', minWidth: 120 },
]
const postFields = [
  { prop: 'name', label: '岗位名称' },
  { prop: 'group', label: '分组', type: 'select', options: GROUP_OPTIONS },
  { prop: 'required', label: '每日必填', type: 'switch' },
  { prop: 'only_weekday', label: '仅该星期出现', type: 'select', options: [...WEEKDAY_NULL, ...WEEKDAY_OPTS] },
  { prop: 'required_weekday', label: '该星期必填', type: 'select', options: [...WEEKDAY_NULL, ...WEEKDAY_OPTS] },
  { prop: 'is_fever_day', label: '发热白班(固定人每4天一班)', type: 'switch' },
  { prop: 'preferred_people', label: '固定/优先人员', type: 'textarea', placeholder: '逗号或换行分隔，按顺序轮转，如 孔亚龙,吕文娟,郑飞' },
  { prop: 'order', label: '显示顺序', type: 'number' },
  { prop: 'notes', label: '备注', type: 'textarea' },
]
const postRules = { name: [{ required: true, message: '请填写岗位名称', trigger: 'blur' }] }
const emptyPost = () => ({ name: '', group: 'day', required: true, only_weekday: null, required_weekday: null, is_fever_day: false, preferred_people: '', order: 0, notes: '' })
const postForm = reactive(emptyPost())

function fetchPosts(params) { return listSchedulingPosts(params) }
function onAddPost() { Object.assign(postForm, emptyPost()); postEditingId.value = null; postDialog.value = true }
function onEditPost(row) {
  Object.assign(postForm, emptyPost(), {
    ...row,
    is_fever_day: !!row.is_fever_day,
    preferred_people: (row.preferred_people || []).join('\n'),
  })
  postEditingId.value = row.id; postDialog.value = true
}
async function onSubmitPost() {
  submitting.value = true
  try {
    const payload = { ...postForm, preferred_people: parsePeople(postForm.preferred_people) }
    if (postEditingId.value) await updateSchedulingPost(postEditingId.value, payload)
    else await createSchedulingPost(payload)
    ElMessage.success('已保存')
    postDialog.value = false
    postCrud.value?.refresh()
    loadPostsAll()
  } catch (e) { ElMessage.error('保存失败') }
  finally { submitting.value = false }
}
async function onDeletePost(row) {
  await ElMessageBox.confirm(`确认删除岗位「${row.name}」？`, '提示', { type: 'warning' })
  await deleteSchedulingPost(row.id)
  ElMessage.success('已删除')
  postCrud.value?.refresh()
  loadPostsAll()
}

// ---------------- 排班计划 ----------------
const planCrud = ref(null)
const planDialog = ref(false)
const planEditingId = ref(null)
const planColumns = [
  { prop: 'name', label: '计划名称', minWidth: 160 },
  { prop: 'start_date', label: '开始', width: 120 },
  { prop: 'end_date', label: '结束', width: 120 },
  { prop: 'fever_day_person', label: '发热白班固定人', width: 120 },
  { prop: 'notes', label: '备注', minWidth: 160 },
]
const userOptions = ref([])
const planFields = computed(() => [
  { prop: 'name', label: '计划名称' },
  { prop: 'start_date', label: '开始日期', type: 'date' },
  { prop: 'end_date', label: '结束日期', type: 'date' },
  { prop: 'fever_day_person', label: '发热白班固定人', type: 'select', options: [{ label: '（无）', value: '' }, ...userOptions.value.map((u) => ({ label: u.full_name || u.username, value: u.full_name || u.username }))] },
  { prop: 'notes', label: '备注', type: 'textarea' },
])
const planRules = { name: [{ required: true, message: '请填写计划名称', trigger: 'blur' }] }
const emptyPlan = () => ({ name: '', start_date: '', end_date: '', fever_day_person: '', notes: '' })
const planForm = reactive(emptyPlan())

function fetchPlans(params) { return listSchedulingPlans(params) }
function onAddPlan() { Object.assign(planForm, emptyPlan()); planEditingId.value = null; planDialog.value = true }
function onEditPlan(row) { Object.assign(planForm, emptyPlan(), row); planEditingId.value = row.id; planDialog.value = true }
async function onSubmitPlan() {
  submitting.value = true
  try {
    if (planEditingId.value) await updateSchedulingPlan(planEditingId.value, { ...planForm })
    else await createSchedulingPlan({ ...planForm })
    ElMessage.success('已保存')
    planDialog.value = false
    planCrud.value?.refresh()
    loadPlanOptions()
  } catch (e) { ElMessage.error('保存失败') }
  finally { submitting.value = false }
}
async function onDeletePlan(row) {
  await ElMessageBox.confirm(`确认删除计划「${row.name}」？`, '提示', { type: 'warning' })
  await deleteSchedulingPlan(row.id)
  ElMessage.success('已删除')
  planCrud.value?.refresh()
  loadPlanOptions()
}

// ---------------- 排班表 ----------------
const planOptions = ref([])
const postsAll = ref([])
const selPlan = ref(null)
const gridStart = ref('')
const gridEnd = ref('')
const peopleText = ref('')
const generating = ref(false)
const gridLoading = ref(false)
const grid = reactive({ dates: [], posts: [], cells: {} })

function cellOf(row, d) { return (grid.cells[row.id] && grid.cells[row.id][d]) || {} }
function cellClass(row, d) {
  const c = cellOf(row, d)
  if (c.status === '病假') return 'c-sick'
  if (c.status === '质控') return 'c-qc'
  if (c.status === '开会') return 'c-meeting'
  if (c.status === '休息') return 'c-rest'
  if (c.status === '行政') return 'c-admin'
  return ''
}
function fmtDate(d) {
  const dt = new Date(d + 'T00:00:00')
  return `${d.slice(5)} ${WEEKDAY_TEXT[dt.getDay() === 0 ? 6 : dt.getDay() - 1]}`
}
async function loadPostsAll() {
  try { const res = await listSchedulingPosts({ page: 1, page_size: 100 }); postsAll.value = res.items || [] }
  catch (e) { postsAll.value = [] }
}
async function loadPlanOptions() {
  try {
    const res = await listSchedulingPlans({ page: 1, page_size: 100 })
    planOptions.value = res.items || []
    if (!selPlan.value && planOptions.value.length) {
      selPlan.value = planOptions.value[0].id
      onPlanChange(selPlan.value)
    }
  } catch (e) { planOptions.value = [] }
}
function onPlanChange(id) {
  const p = planOptions.value.find((x) => x.id === id)
  if (p) { gridStart.value = p.start_date; gridEnd.value = p.end_date }
}
function addDays(dateStr, n) {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return d.toISOString().slice(0, 10)
}
async function loadGrid() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  gridLoading.value = true
  try {
    const res = await getSchedulingGrid({ plan_id: selPlan.value, start: gridStart.value, end: gridEnd.value })
    grid.dates = res.dates || []
    grid.posts = res.posts || []
    grid.cells = res.cells || {}
  } catch (e) { ElMessage.error('查询失败') }
  finally { gridLoading.value = false }
}
async function onGenerate() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  let people = null
  if (peopleText.value.trim()) people = parsePeople(peopleText.value)
  const start = gridStart.value || undefined
  generating.value = true
  try {
    const res = await generateScheduling({ plan_id: selPlan.value, people, start, days: genDays.value })
    ElMessage.success(`已生成 ${res.generated} 条分配`)
    if (start && genDays.value) gridEnd.value = addDays(start, genDays.value - 1)
    loadGrid()
  } catch (e) { ElMessage.error('生成失败') }
  finally { generating.value = false }
}

// ---------------- 手动录入单元格 ----------------
const cellSaving = ref(false)
const cellId = computed(() => {
  const c = grid.cells[cellForm.post_id] && grid.cells[cellForm.post_id][cellForm.date]
  return c ? c.id : null
})
const cellForm = reactive({ plan_id: null, date: todayStr, post_id: null, person: '', status: '在岗', is_early: false, is_continuous: false, note: '' })
async function saveCell() {
  if (!cellForm.plan_id) { ElMessage.warning('请选择计划'); return }
  if (!cellForm.date || !cellForm.post_id) { ElMessage.warning('请选择日期与岗位'); return }
  if (!cellForm.person) { ElMessage.warning('请选择人员'); return }
  cellSaving.value = true
  try {
    await setSchedulingCell({ ...cellForm })
    ElMessage.success('已保存')
    loadGrid()
  } catch (e) { ElMessage.error('保存失败') }
  finally { cellSaving.value = false }
}
async function deleteCell() {
  const id = cellId.value
  if (!id) { ElMessage.warning('该格当前无记录'); return }
  await ElMessageBox.confirm('确认删除该分配记录？', '提示', { type: 'warning' })
  await deleteSchedulingAssignment(id)
  ElMessage.success('已删除')
  loadGrid()
}

onMounted(() => {
  loadMyToday()
  loadPlanOptions()
  loadPostsAll()
  loadConfigSummary()
  listActiveUsers().then((us) => { userOptions.value = us || [] }).catch(() => {})
})
async function loadConfigSummary() {
  try {
    const cfg = await getSchedulingConfig()
    configExcluded.value = cfg.excluded_people || []
    genDays.value = cfg.default_window_days || 14
    earlyContDays.value = cfg.early_continuous_window_days || 30
  } catch (e) {}
}
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.block { margin: 0; }
.card-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.grid-ctrl { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.people-input { margin-bottom: 10px; }
.tip { margin-bottom: 10px; }
.cfg-summary { font-size: 14px; color: #555; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.my-today { display: flex; flex-wrap: wrap; gap: 8px; }
.mt-chip { font-size: 14px; padding: 6px 10px; }
.tag-sub { margin-left: 4px; opacity: 0.8; font-size: 12px; }
.post-cell { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.cell { display: flex; flex-direction: column; align-items: center; gap: 2px; min-height: 38px; justify-content: center; }
.person { font-size: 13px; }
.mini-tag { font-size: 11px; line-height: 1; padding: 1px 4px; border-radius: 3px; }
.mini-tag.early { background: #fdf6ec; color: #e6a23c; }
.mini-tag.cont { background: #f0f9eb; color: #67c23a; }
.mini-tag.st { background: #fef0f0; color: #f56c6c; }
.c-sick { background: #fef0f0; }
.c-qc { background: #fdf6ec; }
.c-meeting { background: #f4f4f5; }
.c-rest { background: #eef3fb; }
.c-admin { background: #f3ecfb; }
.cell-form { margin-top: 4px; }
</style>
