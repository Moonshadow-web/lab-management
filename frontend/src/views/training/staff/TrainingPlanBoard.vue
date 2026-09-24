<template>
  <div class="plan-board">
    <div v-if="current" class="pb-sign">
      <span>制定人：<b>{{ current.maker || '—' }}</b></span>
      <span>制定日期：<b>{{ current.made_date || '—' }}</b></span>
      <span>批准人：<b>{{ current.approver || '—' }}</b></span>
      <span>批准日期：<b>{{ current.approved_date || '—' }}</b></span>
    </div>
    <div class="pb-toolbar">
      <el-select v-model="year" size="small" style="width: 112px" @change="onYearChange">
        <el-option v-for="y in yearOptions" :key="y" :label="y + ' 年'" :value="y" />
      </el-select>
      <el-alert
        v-if="current"
        :title="progressText"
        :type="total && doneCount === total ? 'success' : 'info'"
        :closable="false" show-icon style="flex: 1"
      />
      <template v-if="canWrite">
        <el-button size="small" :icon="Plus" @click="addItem">加一条</el-button>
        <el-button size="small" type="primary" :icon="Check" :disabled="!dirty" @click="save">保存</el-button>
      </template>
    </div>

    <div v-if="!current" class="pb-empty">
      <el-empty description="该年度尚无培训计划">
        <el-button v-if="canWrite" type="primary" @click="createPlan">新建 {{ year }} 年度计划</el-button>
      </el-empty>
    </div>

    <el-table v-else :data="rows" border size="small" v-loading="loading" :row-class-name="rowClass">
      <el-table-column type="index" label="序号" width="56" align="center" />
      <el-table-column label="继续教育内容" min-width="230">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.item" size="small" placeholder="培训内容" />
          <span v-else>{{ row.item }}</span>
        </template>
      </el-table-column>
      <el-table-column label="主讲人" width="110">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.trainer" size="small" />
          <span v-else>{{ row.trainer }}</span>
        </template>
      </el-table-column>
      <el-table-column label="继续教育形式" width="120">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.form" size="small" />
          <span v-else>{{ row.form }}</span>
        </template>
      </el-table-column>
      <el-table-column label="参加人员" width="150">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.target" size="small" />
          <span v-else>{{ row.target }}</span>
        </template>
      </el-table-column>
      <el-table-column label="计划实施日期" width="150">
        <template #default="{ row }">
          <el-date-picker
            v-if="canWrite" v-model="row.expected_date" type="month" value-format="YYYY年M月"
            format="YYYY年M月" size="small" placeholder="选择月份" style="width: 100%"
          />
          <span v-else>{{ row.expected_date }}</span>
        </template>
      </el-table-column>
      <el-table-column label="完成情况" width="168" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.done" type="success" size="small" effect="dark">已完成 {{ row.done_date }}</el-tag>
          <el-tag v-else type="info" size="small" effect="plain">待实施</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="canWrite" label="操作" width="176" align="center" fixed="right">
        <template #default="{ row, $index }">
          <el-button v-if="!row.done" link type="primary" size="small" @click="openComplete(row)">记录完成</el-button>
          <el-button v-else link type="warning" size="small" @click="undoComplete(row)">撤销完成</el-button>
          <el-button link type="danger" size="small" @click="removeItem($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="dlgVisible" title="记录培训完成" width="560px">
      <el-form label-width="104px">
        <el-form-item label="培训内容"><div class="pb-name">{{ dlgRow?.item }}</div></el-form-item>
        <el-form-item label="实际完成日期">
          <el-date-picker v-model="dlgDate" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="关联培训记录">
          <el-select v-model="dlgSessionId" clearable placeholder="可关联「组内培训」里的记录（自动带出讲师/内容）" style="width: 100%">
            <el-option v-for="s in sessions" :key="s.id" :label="`${s.train_time} ${s.name}`" :value="s.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="dlgRemark" type="textarea" :rows="2" placeholder="如试卷、签到表情况，可留空" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmComplete">确认并保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Check } from '@element-plus/icons-vue'
import {
  listTrainingPlan, createTrainingPlan, updateTrainingPlan,
  listTrainingSession,
} from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))

const curYear = new Date().getFullYear()
const yearOptions = ref([curYear, curYear - 1, curYear + 1])
const year = ref(curYear)
const loading = ref(false)
const current = ref(null)   // 当前年度的计划记录
const rows = ref([])        // items_json（直接编辑这个数组）
const sessions = ref([])
const dirty = ref(false)

const total = computed(() => rows.value.length)
const doneCount = computed(() => rows.value.filter((r) => r.done).length)
const progressText = computed(() => {
  const d = doneCount.value
  const t = total.value
  const rate = t ? Math.round((d / t) * 100) : 0
  return `${current.value?.title || year.value + '年度培训计划'}　已完成 ${d} / ${t} 项（${rate}%）`
})

function rowClass({ row }) {
  return row.done ? 'pb-done-row' : ''
}

async function load() {
  loading.value = true
  try {
    const res = await listTrainingPlan({ page: 1, page_size: 100 })
    const items = res?.items || res || []
    const hit = items.find((p) => Number(p.year) === Number(year.value))
    current.value = hit || null
    rows.value = hit ? (hit.items_json ? JSON.parse(JSON.stringify(hit.items_json)) : []) : []
    dirty.value = false
  } catch (e) {
    ElMessage.error('加载培训计划失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

function onYearChange() { load() }

function createPlan() {
  rows.value = [blankItem()]
  current.value = { id: null, year: year.value, title: `${year.value}年度生免组继续教育培训计划`, items_json: [], remark: '' }
  dirty.value = true
}

function blankItem() {
  return { item: '', goal: '', trainer: '', form: '内部知识讲座', target: '生免组全体人员', expected_date: '', remark: '', done: false, done_date: '' }
}

function addItem() {
  if (!current.value) return createPlan()
  rows.value.push(blankItem())
  dirty.value = true
}

function removeItem(i) {
  rows.value.splice(i, 1)
  dirty.value = true
}

async function save(silent = false) {
  if (!current.value) return
  const payload = {
    ...current.value,
    year: Number(year.value),
    title: current.value.title || `${year.value}年度生免组继续教育培训计划`,
    items_json: rows.value,
  }
  try {
    if (payload.id) await updateTrainingPlan(payload.id, payload)
    else {
      const res = await createTrainingPlan(payload)
      current.value.id = res?.id ?? res
    }
    dirty.value = false
    if (!silent) ElMessage.success('已保存')
    await load()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  }
}

// ---- 记录完成 ----
const dlgVisible = ref(false)
const dlgRow = ref(null)
const dlgDate = ref('')
const dlgSessionId = ref(null)
const dlgRemark = ref('')

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function openComplete(row) {
  dlgRow.value = row
  dlgDate.value = today()
  dlgSessionId.value = null
  dlgRemark.value = row.remark || ''
  dlgVisible.value = true
}

async function confirmComplete() {
  if (!dlgDate.value) return ElMessage.warning('请选择实际完成日期')
  const row = dlgRow.value
  row.done = true
  row.done_date = dlgDate.value
  row.remark = dlgRemark.value
  if (dlgSessionId.value) {
    const s = sessions.value.find((x) => x.id === dlgSessionId.value)
    row.session_id = dlgSessionId.value
    if (s && !row.trainer) row.trainer = s.teacher || ''
  }
  dlgVisible.value = false
  dirty.value = true
  await save(true)
  ElMessage.success(`已记录完成时间：${row.done_date}`)
}

async function undoComplete(row) {
  row.done = false
  row.done_date = ''
  dirty.value = true
  await save(true)
  ElMessage.success('已撤销完成标记')
}

onMounted(async () => {
  await load()
  try {
    const res = await listTrainingSession({ page: 1, page_size: 200 })
    sessions.value = res?.items || res || []
  } catch (e) { /* 忽略 */ }
})
</script>

<style scoped>
.plan-board { margin-top: 8px; }
.pb-sign { display: flex; flex-wrap: wrap; gap: 26px; font-size: 13px; color: #606266; padding: 6px 2px 10px; }
.pb-sign b { color: #303133; font-weight: 600; }
.pb-toolbar { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
.pb-empty { padding: 8px 0; }
.pb-name { font-weight: 600; }
:deep(.pb-done-row) { background: #f0f9eb; }
:deep(.pb-done-row td) { background: transparent !important; }
</style>
