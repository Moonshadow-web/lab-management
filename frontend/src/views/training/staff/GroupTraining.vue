<template>
  <div class="group-training">
    <el-tabs v-model="tag">
      <el-tab-pane label="组内培训" name="组内培训" />
      <el-tab-pane label="科内培训" name="科内培训" />
    </el-tabs>

    <el-collapse v-model="active">
      <el-collapse-item title="年度培训计划" name="plan">
        <CrudTable
          :columns="planColumns" :fetch="fetchPlan"
          search-placeholder="搜索计划标题"
          :extra-params="{ tag }"
          :can-write="canWrite"
          @add="openPlan()" @edit="openPlan" @delete="onDeletePlan" ref="planRef"
        />
        <el-dialog v-model="planVisible" :title="planForm.id ? '编辑培训计划' : '新增培训计划'" width="760px">
          <el-form :model="planForm" label-width="100px">
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="年份"><el-input v-model="planForm.year" /></el-form-item></el-col>
              <el-col :span="16"><el-form-item label="计划标题"><el-input v-model="planForm.title" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="制定人"><el-input v-model="planForm.maker" placeholder="如 金子铮" /></el-form-item></el-col>
              <el-col :span="6">
                <el-form-item label="制定日期">
                  <el-date-picker v-model="planForm.made_date" type="date" value-format="YYYY.M.D" format="YYYY.M.D" placeholder="YYYY.M.D" style="width:100%" />
                </el-form-item>
              </el-col>
              <el-col :span="6"><el-form-item label="批准人"><el-input v-model="planForm.approver" placeholder="如 王学晶" /></el-form-item></el-col>
              <el-col :span="6">
                <el-form-item label="批准日期">
                  <el-date-picker v-model="planForm.approved_date" type="date" value-format="YYYY.M.D" format="YYYY.M.D" placeholder="YYYY.M.D" style="width:100%" />
                </el-form-item>
              </el-col>
            </el-row>
            <el-divider content-position="left">计划内容</el-divider>
            <div class="plan-toolbar"><el-button :icon="Plus" @click="addPlanItem">加一行</el-button></div>
            <el-table :data="planForm.items_json" border size="small">
              <el-table-column label="项目" min-width="160"><template #default="{ row }"><el-input v-model="row.item" size="small" /></template></el-table-column>
              <el-table-column label="目标" min-width="160"><template #default="{ row }"><el-input v-model="row.goal" size="small" /></template></el-table-column>
              <el-table-column label="培训人" width="110"><template #default="{ row }"><el-input v-model="row.trainer" size="small" /></template></el-table-column>
              <el-table-column label="预计日期" width="120"><template #default="{ row }"><el-date-picker v-model="row.expected_date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" size="small" placeholder="YYYY-MM-DD" style="width:100%" /></template></el-table-column>
              <el-table-column label="" width="50" align="center"><template #default="{ row }"><el-button link type="danger" :icon="Delete" @click="removePlanItem(row)" /></template></el-table-column>
            </el-table>
          </el-form>
          <template #footer>
            <el-button @click="planVisible = false">取消</el-button>
            <el-button type="primary" @click="savePlan">保存</el-button>
          </template>
        </el-dialog>
        <TrainingPlanBoard :tag="tag" />
      </el-collapse-item>

      <el-collapse-item :title="tag + '记录'" name="session">        <CrudTable
          :columns="sessionColumns" :fetch="fetchSession"
          :search-placeholder="'搜索' + tag + '名称'"
          :extra-params="{ tag }"
          :can-write="canWrite"
          @add="openSession()" @edit="openSession" @delete="onDeleteSession" ref="sessionRef"
        />
      </el-collapse-item>
    </el-collapse>

    <!-- 培训记录编辑 -->
    <el-dialog v-model="sessionVisible" :title="sessionForm.id ? '编辑培训记录' : '新增培训记录'" width="960px" top="3vh">
      <el-form :model="sessionForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="培训名称"><el-input v-model="sessionForm.name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="培训老师"><el-input v-model="sessionForm.teacher" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类别">
            <el-select v-model="sessionForm.tag" style="width:100%"><el-option label="组内培训" value="组内培训" /><el-option label="科内培训" value="科内培训" /></el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="培训对象"><el-input v-model="sessionForm.target" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="时间"><el-date-picker v-model="sessionForm.train_time" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="地点"><el-input v-model="sessionForm.location" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="培训内容"><el-input v-model="sessionForm.content" type="textarea" :rows="3" /></el-form-item>
      </el-form>

      <el-alert v-if="!sessionForm.id" type="warning" :closable="false" title="请先保存培训记录，再使用签到表与上传附件" style="margin-bottom:12px" />

      <template v-if="sessionForm.id">
        <el-divider content-position="left">课件 / 通知 / 考题 / 效果评价 / 签到 存档</el-divider>
        <el-alert v-if="sessionStats.title" type="info" :closable="false" class="stats-strip">
          考题自动解析：考核人数 <b>{{ sessionStats.exam_person_count }}</b> 人　合格率 <b>{{ sessionStats.exam_pass_rate }}</b>%　|　效果评价满意率 <b>{{ sessionStats.eval_satisfy_rate }}</b>%
        </el-alert>
        <el-tabs v-model="attTab">
          <el-tab-pane label="课件(PPT)" name="courseware">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="courseware" label="课件" accept=".ppt,.pptx,.pdf" :can-write="canWrite" />
          </el-tab-pane>
          <el-tab-pane label="培训通知" name="notice">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="notice" label="通知" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" :can-write="canWrite" />
          </el-tab-pane>
          <el-tab-pane label="培训考题" name="exam">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="exam" label="考题" accept=".doc,.docx,.pdf" :can-write="canWrite" @uploaded="refreshSessionMeta" />
          </el-tab-pane>
          <el-tab-pane label="效果评价" name="effect_eval">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="effect_eval" label="效果评价" accept=".doc,.docx,.pdf" :can-write="canWrite" @uploaded="refreshSessionMeta" />
          </el-tab-pane>
          <el-tab-pane label="签到扫描件" name="sign_in">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="sign_in" label="签到扫描件" accept=".pdf,.jpg,.jpeg,.png" hint="上传打印并签名后的扫描件/照片" :can-write="canWrite" />
          </el-tab-pane>
        </el-tabs>

        <el-divider content-position="left">签到表（BG-SM-PX-006）</el-divider>
        <SignInSheet :key="sessionForm.id" :owner-id="sessionForm.id" :header="sessionHeader" :can-write="canWrite" :saved-names="(sessionForm.sign_in_header && sessionForm.sign_in_header.names) || null" @save-header="onSaveHeader" />
      </template>

      <template #footer>
        <el-button @click="sessionVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveSession">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import SignInSheet from '../SignInSheet.vue'
import EducationAttachmentList from '../EducationAttachmentList.vue'
import TrainingPlanBoard from './TrainingPlanBoard.vue'
import {
  listTrainingPlan, createTrainingPlan, updateTrainingPlan, deleteTrainingPlan,
  listTrainingSession, getTrainingSession, createTrainingSession, updateTrainingSession, deleteTrainingSession,
} from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tag = ref('组内培训')
const active = ref(['plan', 'session'])
const attTab = ref('courseware')

const planRef = ref(null)
const sessionRef = ref(null)

const planColumns = [
  { prop: 'year', label: '年份', width: 80 },
  { prop: 'title', label: '计划标题', minWidth: 180 },
  { prop: 'maker', label: '制定人', width: 88, formatter: (r) => r.maker || '—' },
  { prop: 'made_date', label: '制定日期', width: 106, formatter: (r) => r.made_date || '—' },
  { prop: 'approver', label: '批准人', width: 88, formatter: (r) => r.approver || '—' },
  { prop: 'approved_date', label: '批准日期', width: 106, formatter: (r) => r.approved_date || '—' },
  { prop: 'remark', label: '备注', minWidth: 140 },
]
const sessionColumns = [
  { prop: 'name', label: '培训名称', minWidth: 200 },
  { prop: 'teacher', label: '培训老师', width: 110 },
  { prop: 'train_time', label: '时间', width: 140 },
  { prop: 'location', label: '地点', width: 140 },
  { prop: 'tag', label: '类别', width: 90 },
  { prop: 'plan_item_name', label: '对应年度计划项', minWidth: 190, formatter: (r) => r.plan_item_name || '—' },
  { prop: 'exam_person_count', label: '考核人数', width: 90, formatter: (r) => r.exam_person_count ?? '—' },
  { prop: 'exam_pass_rate', label: '合格率', width: 90, formatter: (r) => r.exam_pass_rate != null ? r.exam_pass_rate + '%' : '—' },
  { prop: 'eval_satisfy_rate', label: '满意率', width: 90, formatter: (r) => r.eval_satisfy_rate != null ? r.eval_satisfy_rate + '%' : '—' },
]

// 计划
const planVisible = ref(false)
const planForm = ref(blankPlan())
function blankPlan() { return { id: null, year: new Date().getFullYear(), title: '', tag: tag.value, items_json: [], remark: '', maker: '', made_date: '', approver: '', approved_date: '' } }
function openPlan(row) { planForm.value = row ? { ...row, items_json: row.items_json ? [...row.items_json] : [] } : blankPlan(); planVisible.value = true }
function addPlanItem() { planForm.value.items_json.push({ item: '', goal: '', trainer: '', expected_date: '', remark: '' }) }
function removePlanItem(r) { planForm.value.items_json = planForm.value.items_json.filter((x) => x !== r) }
async function savePlan() {
  try {
    if (planForm.value.id) await updateTrainingPlan(planForm.value.id, planForm.value)
    else await createTrainingPlan(planForm.value)
    ElMessage.success('已保存'); planVisible.value = false; planRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDeletePlan(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteTrainingPlan(row.id); ElMessage.success('已删除'); planRef.value?.refresh() } catch (e) {}
}
function fetchPlan(params) { return listTrainingPlan(params) }

// 培训记录
const sessionVisible = ref(false)
const sessionForm = ref(blankSession())
function blankSession() { return { id: null, name: '', teacher: '', target: '', train_time: '', location: '', content: '', effect_eval: '', tag: tag.value, sign_in_header: {} } }
function openSession(row) { sessionForm.value = row ? { ...row, sign_in_header: row.sign_in_header || {} } : blankSession(); sessionVisible.value = true }
const sessionHeader = computed(() => ({
  name: sessionForm.value.name, teacher: sessionForm.value.teacher,
  train_time: sessionForm.value.train_time, location: sessionForm.value.location, target: sessionForm.value.target,
}))
const sessionStats = computed(() => ({
  title: !!(sessionForm.value.exam_person_count || sessionForm.value.exam_pass_rate || sessionForm.value.eval_satisfy_rate),
  exam_person_count: sessionForm.value.exam_person_count ?? '—',
  exam_pass_rate: sessionForm.value.exam_pass_rate ?? '—',
  eval_satisfy_rate: sessionForm.value.eval_satisfy_rate ?? '—',
}))
async function refreshSessionMeta() {
  if (!sessionForm.value.id) return
  try {
    const res = await getTrainingSession(sessionForm.value.id)
    sessionForm.value = { ...sessionForm.value, ...res }
  } catch (e) {}
}
async function onSaveHeader({ names }) {
  // 仅本地使用（名单已体现在打印表）；如需持久化可存 sign_in_header
  sessionForm.value.sign_in_header = { ...sessionForm.value.sign_in_header, names }
}
async function saveSession() {
  try {
    const payload = { ...sessionForm.value }
    if (payload.id) await updateTrainingSession(payload.id, payload)
    else {
      const res = await createTrainingSession(payload)
      sessionForm.value.id = res.id
    }
    ElMessage.success('已保存'); sessionVisible.value = false; sessionRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDeleteSession(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteTrainingSession(row.id); ElMessage.success('已删除'); sessionRef.value?.refresh() } catch (e) {}
}
// 培训记录 ↔ 年度计划项 的反向关联（按 items_json 里的 session_id 反查）
const sessionPlanMap = ref({})
async function buildSessionPlanMap() {
  try {
    const res = await listTrainingPlan({ page: 1, page_size: 100 })
    const list = res?.items || res || []
    const m = {}
    for (const p of list) {
      const its = Array.isArray(p.items_json) ? p.items_json : []
      for (const it of its) {
        if (it && it.session_id) {
          m[it.session_id] = { year: p.year, item: it.item, done_date: it.done_date || '' }
        }
      }
    }
    sessionPlanMap.value = m
  } catch (e) { /* 忽略 */ }
}
async function fetchSession(params) {
  await buildSessionPlanMap()
  const res = await listTrainingSession(params)
  const items = (res?.items || []).map((s) => {
    const hit = sessionPlanMap.value[s.id]
    return { ...s, plan_item_name: hit ? `${hit.year}年 · ${hit.item}` : '' }
  })
  return { ...(res || {}), items }
}

// 切换「组内培训 / 科内培训」时，两套界面各自刷新（计划与记录均按 tag 隔离）
watch(tag, () => {
  planRef.value?.refresh()
  sessionRef.value?.refresh()
})
</script>

<style scoped>
.plan-toolbar { margin-bottom: 8px; }
.stats-strip { margin-bottom: 10px; }
.stats-strip :deep(.el-alert__title) { line-height: 1.6; }
</style>
