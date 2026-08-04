<template>
  <div class="group-training">
    <el-tabs v-model="tag">
      <el-tab-pane label="组内培训" name="组内培训" />
      <el-tab-pane label="艾梅乙培训" name="艾梅乙" />
    </el-tabs>

    <el-collapse v-model="active">
      <el-collapse-item title="年度培训计划" name="plan">
        <CrudTable
          :columns="planColumns" :fetch="fetchPlan"
          search-placeholder="搜索计划标题"
          :extra-params="{ year: '' }"
          :can-write="canWrite"
          @add="openPlan()" @edit="openPlan" @delete="onDeletePlan" ref="planRef"
        />
        <el-dialog v-model="planVisible" :title="planForm.id ? '编辑培训计划' : '新增培训计划'" width="760px">
          <el-form :model="planForm" label-width="100px">
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="年份"><el-input v-model="planForm.year" /></el-form-item></el-col>
              <el-col :span="16"><el-form-item label="计划标题"><el-input v-model="planForm.title" /></el-form-item></el-col>
            </el-row>
            <el-divider content-position="left">计划内容</el-divider>
            <div class="plan-toolbar"><el-button :icon="Plus" @click="addPlanItem">加一行</el-button></div>
            <el-table :data="planForm.items_json" border size="small">
              <el-table-column label="项目" min-width="160"><template #default="{ row }"><el-input v-model="row.item" size="small" /></template></el-table-column>
              <el-table-column label="目标" min-width="160"><template #default="{ row }"><el-input v-model="row.goal" size="small" /></template></el-table-column>
              <el-table-column label="培训人" width="110"><template #default="{ row }"><el-input v-model="row.trainer" size="small" /></template></el-table-column>
              <el-table-column label="预计日期" width="120"><template #default="{ row }"><el-input v-model="row.expected_date" size="small" /></template></el-table-column>
              <el-table-column label="" width="50" align="center"><template #default="{ row }"><el-button link type="danger" :icon="Delete" @click="removePlanItem(row)" /></template></el-table-column>
            </el-table>
          </el-form>
          <template #footer>
            <el-button @click="planVisible = false">取消</el-button>
            <el-button type="primary" @click="savePlan">保存</el-button>
          </template>
        </el-dialog>
      </el-collapse-item>

      <el-collapse-item :title="tag + '记录'" name="session">
        <CrudTable
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
            <el-select v-model="sessionForm.tag" style="width:100%"><el-option label="组内培训" value="组内培训" /><el-option label="艾梅乙" value="艾梅乙" /></el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="培训对象"><el-input v-model="sessionForm.target" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="时间"><el-input v-model="sessionForm.train_time" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="地点"><el-input v-model="sessionForm.location" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="培训内容"><el-input v-model="sessionForm.content" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="培训效果及评价"><el-input v-model="sessionForm.effect_eval" type="textarea" :rows="3" /></el-form-item>
      </el-form>

      <el-alert v-if="!sessionForm.id" type="warning" :closable="false" title="请先保存培训记录，再使用签到表与上传附件" style="margin-bottom:12px" />

      <template v-if="sessionForm.id">
        <el-divider content-position="left">签到表（BG-KS-PX-805）</el-divider>
        <SignInSheet :owner-id="sessionForm.id" :header="sessionHeader" :can-write="canWrite" :saved-names="(sessionForm.sign_in_header && sessionForm.sign_in_header.names) || null" @save-header="onSaveHeader" />

        <el-divider content-position="left">课件 / 通知 / 考题 / 效果评价 存档</el-divider>
        <el-tabs v-model="attTab">
          <el-tab-pane label="课件(PPT)" name="courseware">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="courseware" label="课件" accept=".ppt,.pptx,.pdf" :can-write="canWrite" />
          </el-tab-pane>
          <el-tab-pane label="培训通知" name="notice">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="notice" label="通知" accept=".pdf,.jpg,.jpeg,.png,.doc,.docx" :can-write="canWrite" />
          </el-tab-pane>
          <el-tab-pane label="培训考题" name="exam">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="exam" label="考题" accept=".doc,.docx,.pdf" :can-write="canWrite" />
          </el-tab-pane>
          <el-tab-pane label="效果评价" name="effect_eval">
            <EducationAttachmentList owner-type="training_session" :owner-id="sessionForm.id" kind="effect_eval" label="效果评价" accept=".doc,.docx,.pdf" :can-write="canWrite" />
          </el-tab-pane>
        </el-tabs>
      </template>

      <template #footer>
        <el-button @click="sessionVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveSession">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import SignInSheet from '../SignInSheet.vue'
import EducationAttachmentList from '../EducationAttachmentList.vue'
import {
  listTrainingPlan, createTrainingPlan, updateTrainingPlan, deleteTrainingPlan,
  listTrainingSession, createTrainingSession, updateTrainingSession, deleteTrainingSession,
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
  { prop: 'year', label: '年份', width: 90 },
  { prop: 'title', label: '计划标题', minWidth: 200 },
  { prop: 'remark', label: '备注', minWidth: 160 },
]
const sessionColumns = [
  { prop: 'name', label: '培训名称', minWidth: 200 },
  { prop: 'teacher', label: '培训老师', width: 110 },
  { prop: 'train_time', label: '时间', width: 140 },
  { prop: 'location', label: '地点', width: 140 },
  { prop: 'tag', label: '类别', width: 100 },
]

// 计划
const planVisible = ref(false)
const planForm = ref(blankPlan())
function blankPlan() { return { id: null, year: new Date().getFullYear(), title: '', items_json: [], remark: '' } }
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
function blankSession() { return { id: null, name: '', teacher: '', target: '', train_time: '', location: '', content: '', effect_eval: '', tag: '组内培训', sign_in_header: {} } }
function openSession(row) { sessionForm.value = row ? { ...row, sign_in_header: row.sign_in_header || {} } : blankSession(); sessionVisible.value = true }
const sessionHeader = computed(() => ({
  name: sessionForm.value.name, teacher: sessionForm.value.teacher,
  train_time: sessionForm.value.train_time, location: sessionForm.value.location, target: sessionForm.value.target,
}))
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
function fetchSession(params) { return listTrainingSession(params) }
</script>

<style scoped>
.plan-toolbar { margin-bottom: 8px; }
</style>
