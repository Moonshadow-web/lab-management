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
        placeholder="生成时使用人员名单（留空则用系统全部活跃用户；每行一个姓名，或用逗号分隔）"
      />
      <el-alert type="info" :closable="false" class="tip" title="说明">
        框架版自动生成：仅工作日排班（周末/节假日另算）；白班岗按人员轮转、同人同日不重复占岗；
        每天白班人员中挑早班/连班各一名、尽量不同人、每人连续最多 2 天。生成后可在下方表格直接手改（双击单元格暂未开放，请用「每日分配」接口或后续表单）。
      </el-alert>
      <el-table v-if="grid.dates.length" :data="grid.posts" border class="grid" :max-height="520">
        <el-table-column prop="name" label="岗位" fixed width="130">
          <template #default="{ row }">
            <div class="post-cell">
              <span>{{ row.name }}</span>
              <el-tag size="small" :type="groupType(row.group)">{{ groupLabel(row.group) }}</el-tag>
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
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import { useAuthStore } from '../../store/auth'
import {
  listSchedulingPosts, createSchedulingPost, updateSchedulingPost, deleteSchedulingPost,
  listSchedulingPlans, createSchedulingPlan, updateSchedulingPlan, deleteSchedulingPlan,
  getSchedulingGrid, getMyToday, generateScheduling,
} from '../../api/scheduling'

const auth = useAuthStore()
const todayStr = new Date().toISOString().slice(0, 10)

// ---------------- 我的今日 ----------------
const myToday = ref([])
async function loadMyToday() {
  try {
    myToday.value = await getMyToday()
  } catch (e) {
    myToday.value = []
  }
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
  { prop: 'name', label: '岗位名称', width: 150 },
  { prop: 'group', label: '分组', width: 90, formatter: (r) => `<el-tag size="small" type="${groupType(r.group)}">${groupLabel(r.group)}</el-tag>` },
  { prop: 'required', label: '每日必填', width: 100, formatter: (r) => (r.required ? '是' : '否(可空缺)') },
  { prop: 'only_weekday', label: '仅星期', width: 90, formatter: (r) => (r.only_weekday == null ? '—' : WEEKDAY_TEXT[r.only_weekday]) },
  { prop: 'required_weekday', label: '必填星期', width: 100, formatter: (r) => (r.required_weekday == null ? '—' : WEEKDAY_TEXT[r.required_weekday]) },
  { prop: 'order', label: '顺序', width: 70 },
  { prop: 'notes', label: '备注', minWidth: 120 },
]
const postFields = [
  { prop: 'name', label: '岗位名称' },
  { prop: 'group', label: '分组', type: 'select', options: GROUP_OPTIONS },
  { prop: 'required', label: '每日必填', type: 'switch' },
  { prop: 'only_weekday', label: '仅该星期出现', type: 'select', options: [...WEEKDAY_NULL, ...WEEKDAY_OPTS] },
  { prop: 'required_weekday', label: '该星期必填', type: 'select', options: [...WEEKDAY_NULL, ...WEEKDAY_OPTS] },
  { prop: 'order', label: '显示顺序', type: 'number' },
  { prop: 'notes', label: '备注', type: 'textarea' },
]
const postRules = { name: [{ required: true, message: '请填写岗位名称', trigger: 'blur' }] }
const emptyPost = () => ({ name: '', group: 'day', required: true, only_weekday: null, required_weekday: null, order: 0, notes: '' })
const postForm = reactive(emptyPost())

function fetchPosts(params) { return listSchedulingPosts(params) }
function onAddPost() { Object.assign(postForm, emptyPost()); postEditingId.value = null; postDialog.value = true }
function onEditPost(row) { Object.assign(postForm, emptyPost(), row); postEditingId.value = row.id; postDialog.value = true }
async function onSubmitPost() {
  submitting.value = true
  try {
    if (postEditingId.value) await updateSchedulingPost(postEditingId.value, { ...postForm })
    else await createSchedulingPost({ ...postForm })
    ElMessage.success('已保存')
    postDialog.value = false
    postCrud.value?.refresh()
  } catch (e) { ElMessage.error('保存失败') }
  finally { submitting.value = false }
}
async function onDeletePost(row) {
  await ElMessageBox.confirm(`确认删除岗位「${row.name}」？`, '提示', { type: 'warning' })
  await deleteSchedulingPost(row.id)
  ElMessage.success('已删除')
  postCrud.value?.refresh()
}

// ---------------- 排班计划 ----------------
const planCrud = ref(null)
const planDialog = ref(false)
const planEditingId = ref(null)
const planColumns = [
  { prop: 'name', label: '计划名称', minWidth: 160 },
  { prop: 'start_date', label: '开始', width: 120 },
  { prop: 'end_date', label: '结束', width: 120 },
  { prop: 'notes', label: '备注', minWidth: 160 },
]
const planFields = [
  { prop: 'name', label: '计划名称' },
  { prop: 'start_date', label: '开始日期', type: 'date' },
  { prop: 'end_date', label: '结束日期', type: 'date' },
  { prop: 'notes', label: '备注', type: 'textarea' },
]
const planRules = { name: [{ required: true, message: '请填写计划名称', trigger: 'blur' }] }
const emptyPlan = () => ({ name: '', start_date: '', end_date: '', notes: '' })
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
const selPlan = ref(null)
const gridStart = ref('')
const gridEnd = ref('')
const peopleText = ref('')
const generating = ref(false)
const gridLoading = ref(false)
const grid = reactive({ dates: [], posts: [], cells: {} })

function cellOf(row, d) {
  return (grid.cells[row.id] && grid.cells[row.id][d]) || {}
}
function cellClass(row, d) {
  const c = cellOf(row, d)
  if (c.status === '病假') return 'c-sick'
  if (c.status === '质控') return 'c-qc'
  if (c.status === '开会') return 'c-meeting'
  return ''
}
function fmtDate(d) {
  const dt = new Date(d + 'T00:00:00')
  return `${d.slice(5)} ${WEEKDAY_TEXT[dt.getDay() === 0 ? 6 : dt.getDay() - 1]}`
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
  if (peopleText.value.trim()) {
    people = peopleText.value.split(/[\n,，]+/).map((s) => s.trim()).filter(Boolean)
  }
  generating.value = true
  try {
    const res = await generateScheduling({ plan_id: selPlan.value, people, start: gridStart.value, end: gridEnd.value })
    ElMessage.success(`已生成 ${res.generated} 条分配`)
    loadGrid()
  } catch (e) { ElMessage.error('生成失败') }
  finally { generating.value = false }
}

onMounted(() => {
  loadMyToday()
  loadPlanOptions()
})
</script>

<style scoped>
.page { display: flex; flex-direction: column; gap: 16px; }
.block { margin: 0; }
.card-head { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 8px; }
.grid-ctrl { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.people-input { margin-bottom: 10px; }
.tip { margin-bottom: 10px; }
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
</style>
