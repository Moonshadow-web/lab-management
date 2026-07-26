<template>
  <div class="page">
    <!-- 今日我的岗位 -->
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

    <el-tabs v-model="activeTab" class="sched-tabs">
      <!-- 月视图排班表 -->
      <el-tab-pane label="月视图排班表" name="month">
        <div class="grid-ctrl">
          <el-select v-model="selPlan" placeholder="选择计划" style="width: 200px" @change="onPlanChange">
            <el-option v-for="p in planOptions" :key="p.id" :label="p.name" :value="p.id" />
          </el-select>
          <el-date-picker v-model="monthValue" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width: 160px" @change="onMonthChange" />
          <el-select v-model="genDays" style="width: 120px" title="生成天数">
            <el-option v-for="d in [7,14,30]" :key="d" :label="`生成${d}天`" :value="d" />
          </el-select>
          <el-button type="primary" :loading="generating" @click="onGenerate">生成白班</el-button>
          <el-button :loading="gridLoading" @click="loadGrid">查询</el-button>
        </div>
        <el-alert type="info" :closable="false" class="tip" title="使用说明">
          ① 先在「批量录入」录入夜班/发热/休息等非白班约束；② 点「生成白班」自动排工作日岗（固定岗按优先级，夜班人员当天自动跳过）；
          ③ 点任意单元格可编辑/补录；④ 桌面端为矩阵、手机端自动切换为按日卡片。
        </el-alert>

        <div v-if="grid.dates.length" class="legend">
          <span class="lg" v-for="l in LEGEND" :key="l.k"><i :class="'dot ' + l.c"></i>{{ l.t }}</span>
        </div>

        <!-- 桌面矩阵 -->
        <div v-if="!isMobile" class="grid-wrap">
          <el-table :data="grid.rows" border class="grid" :max-height="580">
            <el-table-column label="岗位 / 状态" fixed width="128">
              <template #default="{ row }">
                <div class="row-head">
                  <span>{{ row.name }}</span>
                  <el-tag v-if="row.kind === 'post' && row.group === 'night'" size="small" type="danger">夜</el-tag>
                  <el-tag v-else-if="row.kind === 'post' && row.is_fever_day" size="small" type="success">发热</el-tag>
                </div>
              </template>
            </el-table-column>
            <el-table-column v-for="d in grid.dates" :key="d" :label="fmtDate(d)" :width="120" align="center">
              <template #default="{ row }">
                <div class="cell" :class="cellClass(row, d)" @click="openCellEditor(row, d)">
                  <template v-if="row.kind === 'post'">
                    <span class="person">{{ postCell(row, d).person || '—' }}</span>
                    <span v-if="postCell(row, d).is_early" class="mini-tag early">早</span>
                    <span v-if="postCell(row, d).is_continuous" class="mini-tag cont">连</span>
                    <span v-if="postCell(row, d).status && postCell(row, d).status !== '在岗'" class="mini-tag st">{{ postCell(row, d).status }}</span>
                  </template>
                  <template v-else>
                    <span v-for="p in statusCell(row, d).persons" :key="p.id" class="person-chip">{{ p.person }}</span>
                    <span v-if="!statusCell(row, d).persons.length" class="muted">—</span>
                  </template>
                </div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <!-- 移动端日卡 -->
        <div v-else class="mobile-cards">
          <div v-for="d in grid.dates" :key="d" class="day-card">
            <div class="day-head" :class="{ weekend: isWeekend(d) }">{{ fmtDate(d) }}</div>
            <div v-for="row in grid.rows" :key="rowKey(row)" class="day-row" :class="cellClass(row, d)" @click="openCellEditor(row, d)">
              <span class="dr-name">{{ row.name }}</span>
              <span class="dr-val">
                <template v-if="row.kind === 'post'">
                  {{ postCell(row, d).person || '—' }}
                  <template v-if="postCell(row, d).is_early"> 早</template>
                  <template v-if="postCell(row, d).is_continuous"> 连</template>
                  <template v-if="postCell(row, d).status && postCell(row, d).status !== '在岗'"> ·{{ postCell(row, d).status }}</template>
                </template>
                <template v-else>{{ statusCell(row, d).persons.map(p => p.person).join('、') || '—' }}</template>
              </span>
            </div>
          </div>
        </div>
        <el-empty v-if="!grid.dates.length" description="请选择计划与月份后查询" />
      </el-tab-pane>

      <!-- 批量录入 -->
      <el-tab-pane label="批量录入" name="batch">
        <!-- 状态矩阵录入：日期×状态，单元格多选人员 -->
        <div class="bm-block">
          <div class="bm-toolbar">
            <span class="bm-title">排班矩阵录入</span>
            <el-date-picker v-model="matrixMonth" type="month" value-format="YYYY-MM" placeholder="选择月份" style="width: 160px" @change="loadMatrix" />
            <el-button :loading="matrixLoading" @click="loadMatrix">加载矩阵</el-button>
            <el-button type="primary" :loading="matrixSaving" @click="saveMatrix">保存矩阵</el-button>
            <span class="tip-text">每行=一种排班项（休息/病假/开会/行政/质控/教学/夜班/发热白班），每列=一天；单元格下拉多选人员（一人占一行显示，可多人）；保存时按矩阵整体覆盖该月，取消勾选即移除</span>
          </div>
          <div v-if="matrixDates.length" class="bm-wrap">
            <table class="bm-table">
              <thead>
                <tr>
                  <th class="bm-corner">排班 \ 日期</th>
                  <th v-for="d in matrixDates" :key="d" :class="{ weekend: isWeekend(d) }">
                    <div class="bm-date">{{ d.slice(8) }}</div>
                    <div class="bm-wd">{{ WEEKDAY_TEXT[(new Date(d + 'T00:00:00').getDay() + 6) % 7] }}</div>
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in MATRIX_ROWS" :key="r.key" :class="{ 'bm-row-tall': r.tall }">
                  <th :class="['bm-rowhead', STATUS_CLASS[r.key] || '']">{{ r.label }}</th>
                  <td v-for="d in matrixDates" :key="d" :class="{ weekend: isWeekend(d) }">
                    <el-select
                      v-model="matrix[r.key][d]"
                      multiple
                      size="small" placeholder="" class="bm-select"
                      :disabled="!matrixLoaded"
                    >
                      <el-option v-for="p in peopleOptions" :key="p" :label="p" :value="p" />
                    </el-select>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <el-empty v-else description="选择月份后点「加载矩阵」" />
        </div>

        <el-divider content-position="left">夜班 / 发热白班录入（绑定岗位，周期方式）</el-divider>
        <el-form :model="batchForm" label-width="110px" class="batch-form">
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="类型">
                <el-select v-model="batchForm.type" style="width: 100%">
                  <el-option v-for="t in BATCH_TYPES" :key="t.value" :label="t.label" :value="t.value" />
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="batchTypeSpacing">
              <el-form-item label="每 N 天">
                <el-input-number v-model="batchForm.everyN" :min="1" :max="31" />
                <span class="hint">（发热门诊填 4）</span>
              </el-form-item>
            </el-col>
            <el-col :span="8" v-if="batchTypeSpacing">
              <el-form-item label="限星期">
                <el-select v-model="batchForm.weekdays" multiple collapse-tags placeholder="不限" style="width: 100%">
                  <el-option v-for="w in WEEKDAY_OPTS" :key="w.value" :label="w.label" :value="w.value" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-row :gutter="12">
            <el-col :span="8">
              <el-form-item label="起始日期">
                <el-date-picker v-model="batchForm.start" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="结束日期">
                <el-date-picker v-model="batchForm.end" type="date" value-format="YYYY-MM-DD" style="width: 100%" />
              </el-form-item>
            </el-col>
            <el-col :span="8">
              <el-form-item label="当前计划">
                <el-select v-model="selPlan" placeholder="选择计划" style="width: 100%" @change="onPlanChange">
                  <el-option v-for="p in planOptions" :key="p.id" :label="p.name" :value="p.id" />
                </el-select>
              </el-form-item>
            </el-col>
          </el-row>
          <el-form-item label="人员">
            <el-input v-model="batchForm.people" type="textarea" :rows="4" placeholder="每行一个姓名，如 张三 / 李四" />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="batchForm.note" placeholder="可选" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="batchSaving" @click="submitBatch">生成并录入</el-button>
            <span class="tip-text">按筛选条件为每位人员逐日生成记录（夜班类绑定对应夜班岗，其余为无岗位状态）</span>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <!-- 岗位定义 -->
      <el-tab-pane label="岗位定义" name="posts">
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
      </el-tab-pane>

      <!-- 排班计划 -->
      <el-tab-pane label="排班计划" name="plans">
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
      </el-tab-pane>

      <!-- 设置 -->
      <el-tab-pane label="设置" name="config">
        <div class="cfg-summary">
          <span>不参与排班：<b>{{ configExcludedText || '（无）' }}</b></span>
          <el-divider direction="vertical" />
          <span>常规生成：<b>{{ genDays }}</b> 天</span>
          <el-divider direction="vertical" />
          <span>早/连班可提前：<b>{{ earlyContDays }}</b> 天</span>
          <el-button size="small" type="primary" @click="openConfig">配置</el-button>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 单元格编辑弹窗 -->
    <el-dialog v-model="cellEdit.open" :title="cellTitle" width="440px">
      <template v-if="cellEdit.kind === 'post'">
        <el-form label-width="80px">
          <el-form-item label="人员"><UserSelect v-model="cellPostForm.person" /></el-form-item>
          <el-form-item label="早班/连班">
            <el-switch v-model="cellPostForm.is_early" active-text="早" />
            <el-switch v-model="cellPostForm.is_continuous" active-text="连" style="margin-left: 12px" />
          </el-form-item>
          <el-form-item label="备注"><el-input v-model="cellPostForm.note" placeholder="可选" /></el-form-item>
        </el-form>
        <div class="dlg-actions">
          <el-button type="primary" :loading="cellSaving" @click="savePostCell">保存</el-button>
          <el-button v-if="cellPostForm.id" type="danger" plain :loading="cellSaving" @click="deletePostCell">删除</el-button>
        </div>
      </template>
      <template v-else>
        <div class="persons-list">
          <el-tag
            v-for="p in cellExistingPersons"
            :key="p.id"
            closable
            class="person-tag"
            @close="removeStatusPerson(p.id)"
          >{{ p.person }}<span v-if="p.note" class="pn-note">（{{ p.note }}）</span></el-tag>
          <span v-if="!cellExistingPersons.length" class="muted">该状态暂无人员</span>
        </div>
        <el-divider />
        <el-form label-width="60px">
          <el-form-item label="人员"><UserSelect v-model="cellPersonForm.person" /></el-form-item>
          <el-form-item label="备注"><el-input v-model="cellPersonForm.note" placeholder="可选" /></el-form-item>
        </el-form>
        <div class="dlg-actions">
          <el-button type="primary" :loading="cellSaving" @click="addStatusPerson">添加</el-button>
        </div>
      </template>
    </el-dialog>

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
import { ref, reactive, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../components/CrudTable.vue'
import EditDialog from '../../components/EditDialog.vue'
import UserSelect from '../../components/UserSelect.vue'
import { useAuthStore } from '../../store/auth'
import {
  listSchedulingPosts, createSchedulingPost, updateSchedulingPost, deleteSchedulingPost,
  listSchedulingPlans, createSchedulingPlan, updateSchedulingPlan, deleteSchedulingPlan,
  deleteSchedulingAssignment,
  getSchedulingGrid, getMyToday, generateScheduling,
  getSchedulingConfig, updateSchedulingConfig, setSchedulingCell, batchSchedulingCells,
} from '../../api/scheduling'
import { listActiveUsers } from '../../api/users'

const auth = useAuthStore()
function pad(n) { return String(n).padStart(2, '0') }
function localDate(d) { return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}` }
const todayStr = localDate(new Date())

const STATUS_CLASS = {
  '病假': 'c-sick', '质控': 'c-qc', '开会': 'c-meeting', '休息': 'c-rest',
  '行政': 'c-admin', '教学': 'c-teach', '早班': 'c-early', '连班': 'c-cont',
}
const LEGEND = [
  { k: 'rest', t: '休息', c: 'c-rest' }, { k: 'sick', t: '病假', c: 'c-sick' },
  { k: 'meeting', t: '开会', c: 'c-meeting' }, { k: 'admin', t: '行政', c: 'c-admin' },
  { k: 'qc', t: '质控', c: 'c-qc' }, { k: 'teach', t: '教学', c: 'c-teach' },
  { k: 'early', t: '早班', c: 'c-early' }, { k: 'cont', t: '连班', c: 'c-cont' },
]
const BATCH_TYPES = [
  { label: '夜班（生化）', value: 'night_bio', post_name: '生化夜班' },
  { label: '夜班（发热）', value: 'night_fever', post_name: '发热夜班' },
  { label: '发热门诊白班', value: 'fever_day', post_name: '发热白班', spacing: true },
  { label: '休息', value: '休息' },
  { label: '病假', value: '病假' },
  { label: '开会', value: '开会' },
  { label: '行政', value: '行政' },
  { label: '质控', value: '质控' },
  { label: '教学', value: '教学' },
  { label: '早班', value: '早班' },
  { label: '连班', value: '连班' },
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
  { prop: 'preferred_people', label: '固定/优先人员', type: 'textarea', placeholder: '逗号或换行分隔，按顺序优先级递减，如 孔亚龙,吕文娟,郑飞' },
  { prop: 'order', label: '显示顺序', type: 'number' },
  { prop: 'notes', label: '备注', type: 'textarea' },
]
const postRules = { name: [{ required: true, message: '请填写岗位名称', trigger: 'blur' }] }
const emptyPost = () => ({ name: '', group: 'day', required: true, only_weekday: null, required_weekday: null, is_fever_day: false, preferred_people: '', order: 0, notes: '' })
const postForm = reactive(emptyPost())
function groupLabel(g) { return { day: '白班', night: '夜班', special: '特殊' }[g] || g }
function groupType(g) { return { day: 'primary', night: 'danger', special: 'warning' }[g] || 'info' }
function fetchPosts(params) { return listSchedulingPosts(params) }
function onAddPost() { Object.assign(postForm, emptyPost()); postEditingId.value = null; postDialog.value = true }
function onEditPost(row) {
  Object.assign(postForm, emptyPost(), { ...row, is_fever_day: !!row.is_fever_day, preferred_people: (row.preferred_people || []).join('\n') })
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

// ---------------- 月视图 ----------------
const activeTab = ref('month')
const isMobile = ref(false)
function checkMobile() { isMobile.value = window.innerWidth < 768 }
const planOptions = ref([])
const postsAll = ref([])
const selPlan = ref(null)
const monthValue = ref('')
const gridStart = ref('')
const gridEnd = ref('')
const generating = ref(false)
const gridLoading = ref(false)
const grid = reactive({ dates: [], rows: [], cells: {}, posts: [], status_rows: [] })

function rowKey(row) { return row.kind === 'post' ? `post:${row.id}` : `status:${row.key}` }
function postCell(row, d) { return (grid.cells[rowKey(row)] && grid.cells[rowKey(row)][d]) || {} }
function statusCell(row, d) { return (grid.cells[rowKey(row)] && grid.cells[rowKey(row)][d]) || { persons: [] } }
function cellClass(row, d) {
  const status = row.kind === 'post' ? postCell(row, d).status : row.key
  return STATUS_CLASS[status] || ''
}
function fmtDate(d) {
  const dt = new Date(d + 'T00:00:00')
  return `${d.slice(5)} ${WEEKDAY_TEXT[dt.getDay() === 0 ? 6 : dt.getDay() - 1]}`
}
function isWeekend(d) { const w = new Date(d + 'T00:00:00').getDay(); return w === 0 || w === 6 }
function lastDayOfMonth(y, m) { const d = new Date(y, m, 0); return `${y}-${pad(m)}-${pad(d.getDate())}` }

async function loadPostsAll() {
  try { const res = await listSchedulingPosts({ page: 1, page_size: 100 }); postsAll.value = res.items || [] }
  catch (e) { postsAll.value = [] }
}
async function loadPlanOptions() {
  try {
    const res = await listSchedulingPlans({ page: 1, page_size: 100 })
    planOptions.value = res.items || []
    if (!selPlan.value && planOptions.value.length) selPlan.value = planOptions.value[0].id
  } catch (e) { planOptions.value = [] }
}
function onPlanChange(id) {
  const p = planOptions.value.find((x) => x.id === id)
  if (p && !monthValue.value) { gridStart.value = p.start_date; gridEnd.value = p.end_date }
}
function onMonthChange() {
  if (!monthValue.value) return
  const [y, m] = monthValue.value.split('-').map(Number)
  gridStart.value = `${monthValue.value}-01`
  gridEnd.value = lastDayOfMonth(y, m)
  loadGrid()
}
async function loadGrid() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  if (!gridStart.value || !gridEnd.value) return
  gridLoading.value = true
  try {
    const res = await getSchedulingGrid({ plan_id: selPlan.value, start: gridStart.value, end: gridEnd.value })
    grid.dates = res.dates || []
    grid.rows = res.rows || []
    grid.cells = res.cells || {}
    grid.posts = res.posts || []
    grid.status_rows = res.status_rows || []
  } catch (e) { ElMessage.error('查询失败') }
  finally { gridLoading.value = false }
}
async function onGenerate() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  if (!gridStart.value || !gridEnd.value) { ElMessage.warning('请先选择月份'); return }
  generating.value = true
  try {
    const res = await generateScheduling({ plan_id: selPlan.value, start: gridStart.value, end: gridEnd.value })
    ElMessage.success(`已生成 ${res.generated} 条分配`)
    loadGrid()
  } catch (e) { ElMessage.error('生成失败') }
  finally { generating.value = false }
}

// ---------------- 单元格编辑 ----------------
const cellEdit = reactive({ open: false, kind: '', rowId: null, statusKey: '', rowName: '', date: '' })
const cellTitle = computed(() => `编辑 ${cellEdit.rowName} · ${cellEdit.date}`)
const cellSaving = ref(false)
const cellExistingPersons = ref([])
const cellPostForm = reactive({ id: null, person: '', is_early: false, is_continuous: false, note: '' })
const cellPersonForm = reactive({ person: '', note: '' })

function openCellEditor(row, d) {
  cellEdit.kind = row.kind
  cellEdit.rowName = row.name
  cellEdit.date = d
  if (row.kind === 'post') {
    cellEdit.rowId = row.id
    const c = postCell(row, d)
    cellPostForm.id = c.id || null
    cellPostForm.person = c.person || ''
    cellPostForm.is_early = !!c.is_early
    cellPostForm.is_continuous = !!c.is_continuous
    cellPostForm.note = c.note || ''
  } else {
    cellEdit.statusKey = row.key
    const c = statusCell(row, d)
    cellExistingPersons.value = c.persons ? [...c.persons] : []
    cellPersonForm.person = ''
    cellPersonForm.note = ''
  }
  cellEdit.open = true
}
async function savePostCell() {
  if (!cellPostForm.person) { ElMessage.warning('请选择人员'); return }
  cellSaving.value = true
  try {
    await setSchedulingCell({
      plan_id: selPlan.value, date: cellEdit.date, post_id: cellEdit.rowId,
      person: cellPostForm.person, status: '在岗',
      is_early: cellPostForm.is_early, is_continuous: cellPostForm.is_continuous, note: cellPostForm.note,
    })
    ElMessage.success('已保存')
    cellEdit.open = false
    loadGrid()
  } catch (e) { ElMessage.error('保存失败') }
  finally { cellSaving.value = false }
}
async function deletePostCell() {
  if (!cellPostForm.id) return
  await ElMessageBox.confirm('确认删除该分配记录？', '提示', { type: 'warning' })
  await deleteSchedulingAssignment(cellPostForm.id)
  ElMessage.success('已删除')
  cellEdit.open = false
  loadGrid()
}
async function addStatusPerson() {
  if (!cellPersonForm.person) { ElMessage.warning('请选择人员'); return }
  cellSaving.value = true
  try {
    await setSchedulingCell({
      plan_id: selPlan.value, date: cellEdit.date, post_id: null,
      person: cellPersonForm.person, status: cellEdit.statusKey, note: cellPersonForm.note,
    })
    ElMessage.success('已添加')
    cellPersonForm.person = ''
    cellPersonForm.note = ''
    loadGrid()
    // 重新载入编辑框内现有人员
    const c = statusCell({ kind: 'status', key: cellEdit.statusKey }, cellEdit.date)
    cellExistingPersons.value = c.persons ? [...c.persons] : []
  } catch (e) { ElMessage.error('添加失败') }
  finally { cellSaving.value = false }
}
async function removeStatusPerson(id) {
  await deleteSchedulingAssignment(id)
  ElMessage.success('已移除')
  cellExistingPersons.value = cellExistingPersons.value.filter((p) => p.id !== id)
  loadGrid()
}

// ---------------- 批量录入 ----------------
const batchSaving = ref(false)
const batchForm = reactive({ type: '休息', everyN: 1, weekdays: [], start: '', end: '', people: '', note: '' })
// 「每 N 天 / 限星期」字段仅对发热门诊白班（spacing）类型有意义，避免用户困惑
const batchTypeSpacing = computed(() => {
  const t = BATCH_TYPES.find((x) => x.value === batchForm.type)
  return !!(t && t.spacing)
})

// 排班矩阵批量录入：日期×排班项，单元格多选人员
// kind=status：无岗位状态行（休息/病假/开会/行政/质控/教学）
// kind=post：绑定岗位行（夜班/发热白班），key=岗位名，与种子岗位一致
const MATRIX_ROWS = [
  { key: '休息', label: '休息', kind: 'status', tall: true },
  { key: '病假', label: '病假', kind: 'status' },
  { key: '开会', label: '开会', kind: 'status' },
  { key: '行政', label: '行政', kind: 'status' },
  { key: '质控', label: '质控', kind: 'status' },
  { key: '教学', label: '教学', kind: 'status' },
  { key: '生化夜班', label: '夜班(生化)', kind: 'post' },
  { key: '发热夜班', label: '夜班(发热)', kind: 'post' },
  { key: '发热白班', label: '发热白班', kind: 'post', fever: true },
]
const matrixMonth = ref('')
const matrixDates = ref([])
const matrix = reactive({})
const matrixLoaded = ref(false)
const matrixLoading = ref(false)
const matrixSaving = ref(false)
const peopleOptions = computed(() => (userOptions.value || []).map((u) => u.full_name || u.username))
function _monthDates(y, m) {
  const n = new Date(y, m, 0).getDate()
  const out = []
  for (let day = 1; day <= n; day++) out.push(`${y}-${pad(m)}-${pad(day)}`)
  return out
}
function _postNameToId() {
  const map = {}
  for (const p of (postsAll.value || [])) map[p.name] = p.id
  return map
}
async function loadMatrix() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  if (!matrixMonth.value) { ElMessage.warning('请选择月份'); return }
  matrixLoading.value = true
  try {
    const [y, m] = matrixMonth.value.split('-').map(Number)
    const start = `${matrixMonth.value}-01`
    const end = lastDayOfMonth(y, m)
    const dates = _monthDates(y, m)
    matrixDates.value = dates
    for (const r of MATRIX_ROWS) {
      matrix[r.key] = matrix[r.key] || {}
      for (const d of dates) matrix[r.key][d] = matrix[r.key][d] || []
    }
    const res = await getSchedulingGrid({ plan_id: selPlan.value, start, end })
    const postMap = _postNameToId()
    for (const r of MATRIX_ROWS) {
      if (r.kind === 'status') {
        const cell = (res.cells || {})[`status:${r.key}`] || {}
        for (const d of dates) {
          const persons = (cell[d] && cell[d].persons) || []
          matrix[r.key][d] = persons.map((p) => p.person)
        }
      } else {
        const pid = postMap[r.key]
        if (!pid) continue
        const cell = (res.cells || {})[`post:${pid}`] || {}
        for (const d of dates) {
          const c = cell[d]
          matrix[r.key][d] = c && c.person ? [c.person] : []
        }
      }
    }
    matrixLoaded.value = true
  } catch (e) { ElMessage.error('加载矩阵失败') }
  finally { matrixLoading.value = false }
}
async function saveMatrix() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  if (!matrixLoaded.value) { ElMessage.warning('请先加载矩阵'); return }
  matrixSaving.value = true
  try {
    const items = []
    const prune_keys = []        // 状态行 [date, status]
    const prune_post_keys = []   // 岗位行 [date, post_id]
    const postMap = _postNameToId()
    for (const r of MATRIX_ROWS) {
      for (const d of matrixDates.value) {
        const people = (matrix[r.key][d] || []).filter(Boolean)
        if (r.kind === 'status') {
          prune_keys.push([d, r.key])
          for (const person of people) items.push({ person, date: d, post_id: null, status: r.key, note: '' })
        } else {
          const pid = postMap[r.key]
          if (!pid) continue
          prune_post_keys.push([d, String(pid)])
          for (const person of people) items.push({ person, date: d, post_id: pid, status: '在岗', note: '' })
        }
      }
    }
    const res = await batchSchedulingCells({ plan_id: selPlan.value, items, prune: true, prune_keys, prune_post_keys })
    ElMessage.success(`已保存（写入 ${res.upserted} 条）`)
    loadGrid()
  } catch (e) { ElMessage.error('保存失败') }
  finally { matrixSaving.value = false }
}

async function submitBatch() {
  if (!selPlan.value) { ElMessage.warning('请先选择排班计划'); return }
  const people = parsePeople(batchForm.people)
  if (!people.length) { ElMessage.warning('请至少填写一名人员'); return }
  if (!batchForm.start || !batchForm.end) { ElMessage.warning('请选择起止日期'); return }
  const type = BATCH_TYPES.find((t) => t.value === batchForm.type)
  let post_id = null
  if (type.post_name) {
    const p = postsAll.value.find((x) => x.name === type.post_name)
    if (!p) { ElMessage.error(`未找到岗位「${type.post_name}」，请先在岗位定义中创建`); return }
    post_id = p.id
  }
  const status = type.post_name ? '在岗' : type.value
  const items = []
  const [sy, sm, sd] = batchForm.start.split('-').map(Number)
  const [ey, em, ed] = batchForm.end.split('-').map(Number)
  let idx = 0
  const cur = new Date(sy, sm - 1, sd)
  const endD = new Date(ey, em - 1, ed)
  while (cur <= endD) {
    const wd = (cur.getDay() + 6) % 7
    if ((!batchForm.weekdays.length || batchForm.weekdays.includes(wd)) && idx % batchForm.everyN === 0) {
      const ds = localDate(cur)
      for (const person of people) items.push({ person, date: ds, post_id, status, note: batchForm.note })
    }
    cur.setDate(cur.getDate() + 1)
    idx++
  }
  if (!items.length) { ElMessage.warning('筛选条件下无匹配日期'); return }
  batchSaving.value = true
  try {
    const res = await batchSchedulingCells({ plan_id: selPlan.value, items })
    ElMessage.success(`已录入 ${res.upserted} 条`)
  } catch (e) { ElMessage.error('批量录入失败') }
  finally { batchSaving.value = false }
}

// ---------------- 初始化 ----------------
onMounted(() => {
  checkMobile()
  window.addEventListener('resize', checkMobile)
  loadMyToday()
  loadPlanOptions()
  loadPostsAll()
  loadConfigSummary()
  listActiveUsers().then((us) => { userOptions.value = us || [] }).catch(() => {})
  const now = new Date()
  monthValue.value = `${now.getFullYear()}-${pad(now.getMonth() + 1)}`
  onMonthChange()
})
onBeforeUnmount(() => { window.removeEventListener('resize', checkMobile) })

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
.tip { margin: 10px 0; }
.cfg-summary { font-size: 14px; color: #555; display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.my-today { display: flex; flex-wrap: wrap; gap: 8px; }
.mt-chip { font-size: 14px; padding: 6px 10px; }
.tag-sub { margin-left: 4px; opacity: 0.8; font-size: 12px; }
.sched-tabs { background: #fff; padding: 8px 12px; border-radius: 8px; }
.grid-ctrl { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.legend { display: flex; flex-wrap: wrap; gap: 12px; margin: 4px 0 8px; font-size: 12px; color: #666; }
.legend .dot { display: inline-block; width: 12px; height: 12px; border-radius: 3px; margin-right: 4px; vertical-align: middle; }
.grid-wrap { overflow-x: auto; }
.row-head { display: flex; flex-direction: column; gap: 4px; align-items: flex-start; }
.cell { display: flex; flex-direction: column; align-items: center; gap: 2px; min-height: 38px; justify-content: center; cursor: pointer; }
.cell:hover { background: #f5f7fa; }
.person { font-size: 13px; white-space: nowrap; }
.person-chip { display: inline-block; font-size: 12px; margin: 1px 2px; padding: 1px 5px; background: #eef3fb; border-radius: 3px; white-space: nowrap; }
.mini-tag { font-size: 11px; line-height: 1; padding: 1px 4px; border-radius: 3px; }
.mini-tag.early { background: #fdf6ec; color: #e6a23c; }
.mini-tag.cont { background: #f0f9eb; color: #67c23a; }
.mini-tag.st { background: #fef0f0; color: #f56c6c; }
.muted { color: #bbb; }
.c-sick { background: #fef0f0; }
.c-qc { background: #fdf6ec; }
.c-meeting { background: #f4f4f5; }
.c-rest { background: #eef3fb; }
.c-admin { background: #f3ecfb; }
.c-teach { background: #eafaf0; }
.batch-form { margin-top: 8px; max-width: 920px; }
.hint { font-size: 12px; color: #999; margin-left: 6px; }
.tip-text { font-size: 12px; color: #999; margin-left: 10px; }
.dlg-actions { display: flex; gap: 10px; justify-content: flex-end; margin-top: 8px; }
.persons-list { display: flex; flex-wrap: wrap; gap: 6px; min-height: 28px; }
.person-tag { font-size: 13px; }
.pn-note { opacity: 0.7; font-size: 11px; }
.mobile-cards { display: flex; flex-direction: column; gap: 12px; }
.day-card { border: 1px solid #ebeef5; border-radius: 8px; overflow: hidden; }
.day-head { background: #f5f7fa; padding: 6px 12px; font-weight: 600; font-size: 14px; }
.day-head.weekend { background: #fdf0f0; }
.day-row { display: flex; justify-content: space-between; padding: 6px 12px; border-top: 1px solid #f2f2f2; font-size: 13px; cursor: pointer; }
.day-row:hover { background: #f5f7fa; }
.dr-name { color: #666; }
.dr-val { color: #303133; text-align: right; }
.bm-block { background: #fff; border: 1px solid #ebeef5; border-radius: 8px; padding: 12px; }
.bm-toolbar { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }
.bm-title { font-weight: 600; font-size: 15px; }
.bm-wrap { overflow-x: auto; }
.bm-table { border-collapse: collapse; width: 100%; font-size: 12px; }
.bm-table th, .bm-table td { border: 1px solid #ebeef5; padding: 4px 6px; text-align: center; }
/* 日期列最小宽度：必须能容纳一个中文人名标签，否则标签被压到只剩 × */
.bm-table thead th:not(.bm-corner),
.bm-table tbody td { min-width: 92px; }
.bm-corner { background: #f5f7fa; min-width: 92px; position: sticky; left: 0; z-index: 2; }
.bm-table thead th { background: #f5f7fa; font-weight: 600; }
.bm-table thead th.weekend { background: #fdf0f0; }
.bm-rowhead { background: #fafafa; font-weight: 600; position: sticky; left: 0; z-index: 1; min-width: 92px; }
.bm-table tbody td.weekend { background: #fdfafa; }
.bm-date { font-weight: 600; font-size: 13px; }
.bm-wd { font-size: 11px; color: #999; }
.bm-select { width: 100%; }
/* 单元格顶部对齐，便于高行内多标签换行堆叠 */
.bm-table td { vertical-align: top; padding-top: 6px; padding-bottom: 6px; }
/* 休息等高行：约可容纳5名人名，一人占一行 */
.bm-row-tall td { height: 124px; }
.bm-row-tall .bm-select { min-height: 112px; }
/* 多选标签完整显示姓名、自动换行，不截断 */
.bm-select :deep(.el-select__tags) { flex-wrap: wrap; max-width: 100%; gap: 2px; align-items: flex-start; line-height: 1.4; }
.bm-select :deep(.el-select__tags-text) { max-width: none; }
.bm-select :deep(.el-tag) { max-width: 100%; height: auto; line-height: 1.4; padding: 2px 5px; margin: 1px 0; font-size: 12px; }
.bm-select :deep(.el-tag__content) { white-space: normal; word-break: keep-all; }
.bm-select :deep(.el-tag__close) { margin-left: 2px; }
</style>
