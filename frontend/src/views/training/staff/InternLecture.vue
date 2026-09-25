<template>
  <div class="intern-lecture">
    <!-- ===== 讲课计划 ===== -->
    <div class="no-print toolbar">
      <el-alert
        type="info" :closable="false" show-icon
        :title="`实习生讲课计划　已完成 ${doneCount} / ${rows.length} 项（${rate}%）`"
      >
        面向实习/进修人员的科室讲课安排；讲课结束后点「记录完成」填写实际日期，并可打印下方签到表留存。
      </el-alert>
      <div class="actions">
        <el-button v-if="canWrite" type="primary" :icon="Check" :disabled="!dirty" @click="save">保存计划</el-button>
        <el-button v-if="canWrite" :icon="Plus" @click="addItem">加一条</el-button>
      </div>
    </div>

    <el-table :data="rows" border size="small" v-loading="loading" :row-class-name="rowClass">
      <el-table-column type="index" label="序号" width="60" align="center" />
      <el-table-column label="讲课教师" width="120">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.teacher" size="small" placeholder="教师姓名" />
          <span v-else>{{ row.teacher }}</span>
        </template>
      </el-table-column>
      <el-table-column label="计划讲课日期" width="140">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.date" size="small" placeholder="如 2026.7" />
          <span v-else>{{ row.date }}</span>
        </template>
      </el-table-column>
      <el-table-column label="讲课题目" min-width="280">
        <template #default="{ row }">
          <el-input v-if="canWrite" v-model="row.topic" size="small" placeholder="讲课题目" />
          <span v-else>{{ row.topic }}</span>
        </template>
      </el-table-column>
      <el-table-column label="完成情况" width="150" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.done" type="success" size="small" effect="dark">已完成 {{ row.done_date }}</el-tag>
          <el-tag v-else type="info" size="small" effect="plain">待实施</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="canWrite" label="操作" width="170" align="center" fixed="right">
        <template #default="{ row, $index }">
          <el-button v-if="!row.done" link type="primary" size="small" @click="openComplete(row)">记录完成</el-button>
          <el-button v-else link type="warning" size="small" @click="undoComplete(row)">撤销完成</el-button>
          <el-button link type="danger" size="small" @click="removeItem($index)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- ===== 签到表 ===== -->
    <div class="no-print">
      <el-divider content-position="left">实习生讲课签到表（打印后现场签名，扫描留存）</el-divider>
      <div class="actions">
        <el-button type="primary" :icon="Printer" @click="doPrint">打印空白签到表</el-button>
        <span class="hint">打印为 A4 单页；名单可在下方调整</span>
      </div>
    </div>

    <div class="sheet preview no-print">
      <h2 class="sheet-title">民航总医院检验科实习生讲课签到表</h2>
      <table class="sheet-head">
        <tr>
          <td class="lbl">讲课日期</td>
          <td>　</td>
          <td class="lbl">讲课教师</td>
          <td>　</td>
        </tr>
        <tr>
          <td class="lbl">讲课题目</td>
          <td colspan="3">　</td>
        </tr>
      </table>
      <table class="sign-grid">
        <thead>
          <tr><th>姓　名</th><th>学校 / 专业</th><th>签 到</th><th>姓　名</th><th>学校 / 专业</th><th>签 到</th></tr>
        </thead>
        <tbody>
          <tr v-for="(pair, i) in pairedRows" :key="i">
            <template v-if="pair.left"><td>{{ pair.left.name }}</td><td>{{ pair.left.org }}</td><td class="sign-cell"></td></template>
            <template v-else><td></td><td></td><td class="sign-cell"></td></template>
            <template v-if="pair.right"><td>{{ pair.right.name }}</td><td>{{ pair.right.org }}</td><td class="sign-cell"></td></template>
            <template v-else><td></td><td></td><td class="sign-cell"></td></template>
          </tr>
        </tbody>
        <tfoot>
          <tr><td colspan="6" class="sign-foot">带教老师签字：＿＿＿＿＿＿＿＿　　科室负责人签字：＿＿＿＿＿＿＿＿</td></tr>
        </tfoot>
      </table>
    </div>

    <!-- 打印专用副本 -->
    <Teleport to="body">
      <div class="print-root sheet pr-il">
        <h2 class="sheet-title">民航总医院检验科实习生讲课签到表</h2>
        <table class="sheet-head">
          <tr>
            <td class="lbl">讲课日期</td><td>　</td><td class="lbl">讲课教师</td><td>　</td>
          </tr>
          <tr>
            <td class="lbl">讲课题目</td><td colspan="3">　</td>
          </tr>
        </table>
        <table class="sign-grid">
          <thead>
            <tr><th>姓　名</th><th>学校 / 专业</th><th>签 到</th><th>姓　名</th><th>学校 / 专业</th><th>签 到</th></tr>
          </thead>
          <tbody>
            <tr v-for="(pair, i) in pairedRows" :key="i">
              <template v-if="pair.left"><td>{{ pair.left.name }}</td><td>{{ pair.left.org }}</td><td class="sign-cell"></td></template>
              <template v-else><td></td><td></td><td class="sign-cell"></td></template>
              <template v-if="pair.right"><td>{{ pair.right.name }}</td><td>{{ pair.right.org }}</td><td class="sign-cell"></td></template>
              <template v-else><td></td><td></td><td class="sign-cell"></td></template>
            </tr>
          </tbody>
          <tfoot>
            <tr><td colspan="6" class="sign-foot">带教老师签字：＿＿＿＿＿＿＿＿　　科室负责人签字：＿＿＿＿＿＿＿＿</td></tr>
            <tr><td colspan="6" class="foot-cell">表格编号：BG-SM-PX-009　　民航总医院检验科　　实习生讲课签到表</td></tr>
          </tfoot>
        </table>
      </div>
    </Teleport>

    <div class="no-print">
      <el-divider content-position="left">编辑签到名单（打印前可调）</el-divider>
      <div class="actions">
        <el-button :icon="Plus" @click="addMember">加一名学生</el-button>
        <span class="hint">新增或修改后，点上方「保存计划」即可长期保留</span>
      </div>
      <el-table :data="members" border size="small">
        <el-table-column label="姓名" width="170">
          <template #default="{ row }"><el-input v-model="row.name" size="small" placeholder="姓名" @input="dirty = true" /></template>
        </el-table-column>
        <el-table-column label="学校 / 专业" min-width="220">
          <template #default="{ row }"><el-input v-model="row.org" size="small" placeholder="如 某某医学院 / 医学检验" @input="dirty = true" /></template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ row }">
            <el-button link type="danger" size="small" :icon="Delete" @click="removeMember(row)" />
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 记录完成 -->
    <el-dialog v-model="dlgVisible" title="记录讲课完成" width="520px">
      <el-form label-width="104px">
        <el-form-item label="讲课题目"><div class="dlg-name">{{ dlgRow?.topic }}</div></el-form-item>
        <el-form-item label="计划日期"><div>{{ dlgRow?.date || '—' }}</div></el-form-item>
        <el-form-item label="实际完成日期">
          <el-date-picker v-model="dlgDate" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="选择日期" style="width: 100%" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dlgRemark" type="textarea" :rows="2" placeholder="如签到人数、留存情况，可留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dlgVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmComplete">确认并保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus, Delete, Printer, Check } from '@element-plus/icons-vue'
import { listTrainingPlan, createTrainingPlan, updateTrainingPlan, listMentor } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))

const TAG = '实习讲课'
const loading = ref(false)
const dirty = ref(false)
const planId = ref(null)
const rows = ref([])
const members = ref([])
const membersLoaded = ref(false)  // 名单是否已由计划里保存的数据载入（载入后不再用档案覆盖）

// 图片里的 12 条实习生讲课计划（原文 "2026.1"/"2026..12" 为笔误，按月份序修正）
const SEED = [
  ['龚珂', '2026.7', '血常规直方图分析及报告注意事项'],
  ['赵华', '2026.7', '尿沉渣检验原理、图形分析及报告解析'],
  ['刘书理', '2026.8', '血尿常规复检规则'],
  ['朱春阳', '2026.8', '室内质量控制基础'],
  ['夏立娇', '2026.9', '生化反应方法学及曲线解析'],
  ['吕文娟', '2026.9', '生化室项目介绍及报告注意事项'],
  ['孔亚龙', '2026.10', '凝血项目介绍及报告注意事项'],
  ['金子铮', '2026.11', '免疫室项目介绍及报告注意事项'],
  ['吴朋', '2026.11', '临床常见标本的微生物学检验'],
  ['时琰丽', '2026.12', '微生物项目介绍及报告注意事项'],
  ['李昊俊', '2026.12', '常用分子生物学技术的原理和应用'],
  ['贾国伟', '2027.1', '输血相关知识简介及操作流程'],
]

function seedRows() {
  return SEED.map(([teacher, date, topic]) => ({ teacher, date, topic, done: false, done_date: '', remark: '' }))
}

const doneCount = computed(() => rows.value.filter((r) => r.done).length)
const rate = computed(() => (rows.value.length ? Math.round((doneCount.value / rows.value.length) * 100) : 0))

function rowClass({ row }) { return row.done ? 'il-done-row' : '' }

const pairedRows = computed(() => {
  const out = []
  for (let i = 0; i < members.value.length; i += 2) {
    out.push({ left: members.value[i], right: members.value[i + 1] || null })
  }
  // 打印空表一页：补足到 20 行（含实习生后仍留手写位）
  while (out.length < 20) out.push({ left: null, right: null })
  return out
})

async function load() {
  loading.value = true
  try {
    const res = await listTrainingPlan({ page: 1, page_size: 100 })
    const list = res?.items || res || []
    const hit = list.find((p) => p.tag === TAG)
    if (hit) {
      planId.value = hit.id
      const its = Array.isArray(hit.items_json) ? hit.items_json : []
      rows.value = its.length
        ? its.map((x) => ({
            teacher: x.teacher || x.trainer || '',
            date: x.date || x.expected_date || '',
            topic: x.topic || x.item || '',
            done: !!x.done,
            done_date: x.done_date || '',
            remark: x.remark || '',
          }))
        : seedRows()
      // 名单：优先用计划里保存过的，没有才回落到实习生档案
      const saved = Array.isArray(hit.members_json) ? hit.members_json : []
      if (saved.length) {
        members.value = saved.map((m) => ({ name: m.name || '', org: m.org || '' }))
        membersLoaded.value = true
      }
    } else {
      planId.value = null
      rows.value = seedRows()
    }
    dirty.value = false
  } catch (e) {
    ElMessage.error('加载讲课计划失败：' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

async function loadMembers() {
  if (membersLoaded.value) return  // 计划里已有保存的名单，不再用实习生档案覆盖
  try {
    const res = await listMentor({ page: 1, page_size: 200 })
    const list = res?.items || res || []
    const seen = new Set()
    members.value = list
      .map((m) => ({ name: (m.intern_name || '').trim(), org: '' }))
      .filter((m) => m.name && !seen.has(m.name) && seen.add(m.name))
  } catch (e) { /* 忽略 */ }
  if (!members.value.length) members.value = [{ name: '', org: '' }]
}

function addMember() {
  members.value.push({ name: '', org: '' })
  dirty.value = true
}

function addItem() { rows.value.push({ teacher: '', date: '', topic: '', done: false, done_date: '', remark: '' }); dirty.value = true }
function removeItem(i) { rows.value.splice(i, 1); dirty.value = true }
function removeMember(r) {
  members.value = members.value.filter((x) => x !== r)
  dirty.value = true
}

async function save(silent = false) {
  const payload = {
    year: new Date().getFullYear(),
    title: '实习生讲课计划',
    tag: TAG,
    remark: '实习/进修人员科室讲课安排（签到表见本页下方）',
    items_json: rows.value.map((r) => ({
      item: r.topic, topic: r.topic, trainer: r.teacher, teacher: r.teacher,
      expected_date: r.date, date: r.date, form: '科室讲课', target: '实习/进修人员',
      done: !!r.done, done_date: r.done_date || '', remark: r.remark || '',
    })),
    // 签到名单一并保存，避免刷新后新增的学生丢失
    members_json: members.value.map((m) => ({ name: m.name || '', org: m.org || '' })),
  }
  try {
    if (planId.value) await updateTrainingPlan(planId.value, payload)
    else {
      const res = await createTrainingPlan(payload)
      planId.value = res?.id ?? res
    }
    dirty.value = false
    if (!silent) ElMessage.success('讲课计划已保存')
    await load()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  }
}

// ---- 记录完成 ----
const dlgVisible = ref(false)
const dlgRow = ref(null)
const dlgDate = ref('')
const dlgRemark = ref('')

function today() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

function openComplete(row) {
  dlgRow.value = row
  dlgDate.value = today()
  dlgRemark.value = row.remark || ''
  dlgVisible.value = true
}

async function confirmComplete() {
  if (!dlgDate.value) return ElMessage.warning('请选择实际完成日期')
  const row = dlgRow.value
  row.done = true
  row.done_date = dlgDate.value
  row.remark = dlgRemark.value
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

async function doPrint() {
  // 只打印本组件这一张：给 body 打标记，打印样式据此只显示对应的 print-root
  document.body.dataset.printTarget = 'il'
  await new Promise((r) => setTimeout(r, 100))
  window.print()
  // 打印后复位，避免影响其它打印组件（能力评估/新员工培训等）
  delete document.body.dataset.printTarget
}

onMounted(async () => {
  await load()
  await loadMembers()
})
</script>

<style scoped>
.intern-lecture { padding: 4px 0; }
.toolbar { margin-bottom: 12px; }
.actions { margin-top: 10px; display: flex; align-items: center; gap: 10px; }
.hint { font-size: 12px; color: #909399; }
.dlg-name { font-weight: 600; }
.sheet { margin-top: 12px; }
.sheet-title { text-align: center; font-size: 21px; letter-spacing: 3px; margin: 8px 0 14px; }
.sheet-head { width: 100%; border-collapse: collapse; margin-bottom: 10px; }
.sheet-head td { border: 1px solid #333; padding: 6px 10px; font-size: 14px; }
.sheet-head .lbl { width: 90px; background: #f5f5f5; font-weight: 600; text-align: center; }
.sign-grid { width: 100%; border-collapse: collapse; }
.sign-grid th, .sign-grid td { border: 1px solid #333; padding: 6px 10px; font-size: 14px; text-align: center; height: 30px; }
.sign-grid th { background: #f5f5f5; }
.sign-cell { height: 30px; }
.sign-foot { border: none !important; text-align: left; font-size: 13px; padding: 8px 2px !important; height: auto !important; }
.foot-cell { border: none !important; text-align: center; font-size: 12px; color: #333; padding-top: 8px !important; height: auto !important; }
:deep(.il-done-row) { background: #f0f9eb; }

.print-root { display: none; }
@media print {
  .no-print { display: none !important; }
  @page { size: A4; margin: 14mm 12mm 20mm 12mm; }
  body > *:not(.print-root) { display: none !important; }
  /* 只显示当前点「打印」的那一张打印副本；未设标记时不影响其它打印组件 */
  body[data-print-target] > .print-root { display: none !important; }
  body[data-print-target="il"] > .print-root.pr-il { display: block !important; }
  .print-root { position: static !important; width: 100% !important; visibility: visible !important; }
}
</style>
