<template>
  <div class="internship">
    <el-tabs v-model="tab">
      <el-tab-pane label="培训大纲及带教评价（PX-003）" name="mentor">
        <CrudTable :columns="mentorCols" :fetch="fetchMentor" search-placeholder="搜索姓名"
          :can-write="canWriteMentor" @add="openMentor()" @edit="openMentor" @delete="onDeleteMentor" ref="mentorRef" />
      </el-tab-pane>
      <el-tab-pane label="实操考核成绩单（PX-004）" name="score">
        <CrudTable :columns="scoreCols" :fetch="fetchScore" search-placeholder="搜索姓名"
          :can-write="canWrite" @add="openScore()" @edit="openScore" @delete="onDeleteScore" ref="scoreRef">
          <template #toolbar-extra>
            <el-button :icon="Printer" @click="printScore(null, true)">打印空白表</el-button>
          </template>
          <template #row-extra="{ row }">
            <el-button link type="primary" :icon="Printer" @click="printScore(row)">打印</el-button>
          </template>
        </CrudTable>
      </el-tab-pane>
      <el-tab-pane label="讲课计划（实习生）" name="lecture">
        <InternLecture />
      </el-tab-pane>
    </el-tabs>

    <!-- PX-003 -->
    <el-dialog v-model="mentorVisible" :title="mentorForm.id ? '编辑带教评价' : '新增带教评价'" width="900px" top="3vh">
      <el-form :model="mentorForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="姓名"><el-input v-model="mentorForm.intern_name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类型">
            <el-select v-model="mentorForm.intern_type" style="width:100%"><el-option label="实习" value="实习" /><el-option label="进修" value="进修" /></el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="依据SOP"><el-input v-model="mentorForm.sop_ref" /></el-form-item></el-col>
        </el-row>
        <el-divider content-position="left">大纲要求及带教评价（BG-SM-PX-003）</el-divider>
        <el-table :data="mentorForm.items_json" border size="small">
          <el-table-column label="序号" width="60" type="index" align="center" />
          <el-table-column label="大纲要求" min-width="300"><template #default="{ row }"><el-input v-model="row.requirement" size="small" /></template></el-table-column>
          <el-table-column label="掌握程度" width="110"><template #default="{ row }"><el-input v-model="row.mastery" size="small" placeholder="掌握/熟悉/了解" /></template></el-table-column>
          <el-table-column label="带教老师" width="140"><template #default="{ row }"><el-input v-model="row.teacher" size="small" /></template></el-table-column>
          <el-table-column label="评价(1-5)" width="110"><template #default="{ row }"><el-input-number v-model="row.score" :min="0" :max="5" size="small" /></template></el-table-column>
          <el-table-column label="评价人" width="100"><template #default="{ row }"><el-input v-model="row.evaluator" size="small" /></template></el-table-column>
          <el-table-column label="日期" width="120"><template #default="{ row }"><el-date-picker v-model="row.date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" size="small" placeholder="YYYY-MM-DD" style="width:100%" /></template></el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <el-button @click="mentorVisible = false">取消</el-button>
        <el-button type="primary" @click="saveMentor">保存</el-button>
      </template>
    </el-dialog>

    <!-- PX-004 -->
    <el-dialog v-model="scoreVisible" :title="scoreForm.id ? '编辑实操考核' : '新增实操考核'" width="860px" top="3vh">
      <el-form :model="scoreForm" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="姓名"><el-input v-model="scoreForm.intern_name" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="类型">
            <el-select v-model="scoreForm.intern_type" style="width:100%"><el-option label="实习" value="实习" /><el-option label="进修" value="进修" /></el-select>
          </el-form-item></el-col>
          <el-col :span="8"><el-form-item label="考核日期"><el-date-picker v-model="scoreForm.date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="YYYY-MM-DD" style="width:100%"/></el-form-item></el-col>
        </el-row>
        <el-divider content-position="left">实操考核科目（BG-SM-PX-004）</el-divider>
        <el-table :data="scoreForm.subjects_json" border size="small">
          <el-table-column label="考核科目" min-width="260"><template #default="{ row }"><el-input v-model="row.subject" size="small" /></template></el-table-column>
          <el-table-column label="分值" width="90"><template #default="{ row }"><el-input v-model="row.score_value" size="small" /></template></el-table-column>
          <el-table-column label="考核教师" width="120"><template #default="{ row }"><el-input v-model="row.teacher" size="small" /></template></el-table-column>
          <el-table-column label="考核成绩" width="120"><template #default="{ row }"><el-input v-model="row.score" size="small" /></template></el-table-column>
        </el-table>
        <div style="margin:6px 0 2px;font-size:13px;color:#303133;">
          合计：<b>{{ scoreSummary(scoreForm).total }}</b> / {{ scoreSummary(scoreForm).full || 100 }} 分
          <el-tag size="small" :type="scoreSummary(scoreForm).done ? 'success' : 'info'" style="margin-left:10px;">
            {{ scoreSummary(scoreForm).status }}
          </el-tag>
        </div>
        <el-divider content-position="left">总体评价</el-divider>
        <el-form-item label="评语"><el-input v-model="scoreForm.overall_comment" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="组长签字"><el-input v-model="scoreForm.group_leader" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="日期"><el-date-picker v-model="scoreForm.sign_date" type="date" value-format="YYYY-MM-DD" format="YYYY-MM-DD" placeholder="YYYY-MM-DD" style="width:100%"/></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="scoreVisible = false">取消</el-button>
        <el-button :icon="Printer" @click="printScore(scoreForm)">打印成绩单</el-button>
        <el-button type="primary" @click="saveScore">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Printer } from '@element-plus/icons-vue'
import { printHtml } from '../../../utils/printHtml'
import CrudTable from '../../../components/CrudTable.vue'
import InternLecture from './InternLecture.vue'
import {
  listMentor, createMentor, updateMentor, deleteMentor,
  listScore, createScore, updateScore, deleteScore,
} from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
// 学生（实习生）可填写带教评价
const canWriteMentor = computed(() => canWrite.value || auth.isStudent)
const tab = ref('mentor')
const mentorRef = ref(null)
const scoreRef = ref(null)

const mentorCols = [
  { prop: 'intern_name', label: '姓名', width: 120 },
  { prop: 'intern_type', label: '类型', width: 80 },
  { prop: 'sop_ref', label: '依据SOP', width: 120 },
  { prop: 'remark', label: '备注', minWidth: 160 },
]
// 汇总实操成绩：总分 = 各科目成绩之和；完成状态 = 所有科目都已填成绩
function scoreSummary(row) {
  const subs = row.subjects_json || []
  let total = 0
  let full = 0
  let filled = 0
  subs.forEach((x) => {
    const v = parseFloat(String(x.score ?? '').replace(/[^\d.]/g, ''))
    const m = parseFloat(String(x.score_value ?? '').replace(/[^\d.]/g, ''))
    if (!isNaN(m)) full += m
    if (!isNaN(v) && String(x.score ?? '').trim() !== '') {
      total += v
      filled += 1
    }
  })
  const done = subs.length > 0 && filled === subs.length
  return {
    total,
    full,
    filled,
    done,
    text: `${total} / ${full || 100}`,
    status: done ? '已完成' : (filled === 0 ? '未开始' : `进行中 ${filled}/${subs.length}`),
  }
}

const scoreCols = [
  { prop: 'intern_name', label: '姓名', width: 110 },
  { prop: 'intern_type', label: '类型', width: 70 },
  { prop: 'date', label: '考核日期', width: 120 },
  { prop: 'total_score', label: '总成绩', width: 110, align: 'center', formatter: (r) => scoreSummary(r).text },
  { prop: 'done_status', label: '完成状态', width: 130, align: 'center', formatter: (r) => scoreSummary(r).status },
  { prop: 'group_leader', label: '组长签字', width: 110 },
]

const MENTOR_OUTLINE = [
  [1, '实验室环境的消毒、常规与应急处理及准备。', '掌握', '赵海元'],
  [2, '各种临床标本（血、尿及其他体液）的合格验收与分析前处理、储存的方法及注意事项。', '掌握', ''],
  [3, '生化免疫组常用试剂盒的合理保存及正确使用。', '掌握', ''],
  [4, '临床生化免疫检验室内质量控制的基本方法：质控品的应用、测定、质控结果分析、失控后的处理流程。', '掌握', '朱春阳'],
  [5, '急诊生化检测项目及其重要性，生化检验项目的危急值及处理流程。', '掌握', '吕文娟'],
  [6, '血气分析仪的工作原理、定标、操作规程、维护保养、注意事项及简单的故障处理。', '掌握', ''],
  [7, '全自动生化分析仪的工作原理、参数设置、定标、操作规程、维护保养、注意事项及简单的故障处理。', '掌握', '夏立娇'],
  [8, '肝肾功能、心功能、血脂、血糖、电解质、血清酶类等常见生化检测项目的分析方法、实验原理、检测操作流程、注意事项及临床意义。', '掌握', ''],
  [9, '（电）化学发光分析仪工作原理、定标、操作规程、维护保养、注意事项及简单的故障处理。', '掌握', '王淑华'],
  [10, '酶联免疫技术、免疫固定电泳的基本原理、仪器操作流程、维护保养、注意事项及简单的故障处理。', '掌握', ''],
  [11, '病毒血清标志物、内分泌激素、肿瘤标志物、血清各类球蛋白的检测流程、注意事项、应用及结果分析。', '掌握', ''],
  [12, '出血与血栓性疾病的实验室诊断步骤。', '掌握', '孔亚龙'],
  [13, '自动血凝分析仪的检测原理、操作方法、结果解释及质量控制。', '掌握', ''],
  [14, '常用凝血项目（PT、APTT、TT、FIB、DD等）实验原理、试剂配置、操作方法及临床意义。', '掌握', ''],
  [15, '临床生物化学检验方法（检测系统）的性能验证。', '熟悉', '金子铮'],
  [16, '临床生化检验室间质评的流程。', '熟悉', ''],
  [17, '实验室内仪器间比对、性能评价与验证等内容。', '熟悉', ''],
  [18, '常用抗凝剂的抗凝原理、使用中的注意事项。', '熟悉', '秦东芳'],
  [19, '生化检测试剂盒的选用标准、使用注意事项、保存。', '熟悉', ''],
  [20, 'AIDS初筛实验方法及报告方式。', '熟悉', ''],
  [21, 'LIS系统及条码的内容。', '了解', '张婵媛'],
  [22, '临床生化检验新项目、新方法、新技术的研究进展。', '了解', ''],
  [23, '临床免疫学检验的新技术、新方法及动向。', '了解', ''],
]
const SCORE_OUTLINE = [
  ['临床常见标本的签收和处理', '5'],
  ['血气分析仪的使用及危急值报告', '10'],
  ['全自动生化分析仪的日常使用、项目定标和维护', '10'],
  ['酶标仪的使用及日常维护', '5'],
  ['凝血试剂的配置', '10'],
  ['分析质控图及失控处理', '10'],
  ['免疫固定电泳仪的使用', '10'],
  ['常用生化检测项目复检规则的应用', '10'],
  ['病毒血清标志物阳性的处理流程', '10'],
  ['TURST的操作', '5'],
  ['生化反应曲线和凝血曲线的查看与分析', '15'],
]

// PX-003
const mentorVisible = ref(false)
const mentorForm = ref(blankMentor())
function blankMentor() {
  return { id: null, intern_name: '', intern_type: '实习', sop_ref: 'SM-SOP-025',
    items_json: MENTOR_OUTLINE.map(([seq, requirement, mastery, teacher]) => ({ seq, requirement, mastery, teacher, score: 0, evaluator: '', date: '' })),
    remark: '' }
}
function openMentor(row) {
  mentorForm.value = row ? { ...row, items_json: row.items_json ? [...row.items_json] : [] } : blankMentor()
  mentorVisible.value = true
}
async function saveMentor() {
  try {
    if (mentorForm.value.id) await updateMentor(mentorForm.value.id, mentorForm.value)
    else await createMentor(mentorForm.value)
    ElMessage.success('已保存'); mentorVisible.value = false; mentorRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDeleteMentor(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteMentor(row.id); ElMessage.success('已删除'); mentorRef.value?.refresh() } catch (e) {}
}
function fetchMentor(params) { return listMentor(params) }

// PX-004
const scoreVisible = ref(false)
const scoreForm = ref(blankScore())
function blankScore() {
  return { id: null, intern_name: '', intern_type: '实习', date: '',
    subjects_json: SCORE_OUTLINE.map(([subject, score_value]) => ({ subject, score_value, teacher: '', score: '' })),
    overall_comment: '', group_leader: '', sign_date: '', remark: '' }
}
function openScore(row) {
  scoreForm.value = row ? { ...row, subjects_json: row.subjects_json ? [...row.subjects_json] : [] } : blankScore()
  scoreVisible.value = true
}
async function saveScore() {
  try {
    if (scoreForm.value.id) await updateScore(scoreForm.value.id, scoreForm.value)
    else await createScore(scoreForm.value)
    ElMessage.success('已保存'); scoreVisible.value = false; scoreRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDeleteScore(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteScore(row.id); ElMessage.success('已删除'); scoreRef.value?.refresh() } catch (e) {}
}
function fetchScore(params) { return listScore(params) }

function esc(v) {
  return String(v == null ? '' : v)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// 打印实操考核成绩单（BG-SM-PX-004）；blank=true 打印空白表供现场填写
function printScore(row, blank = false) {
  const data = row || blankScore()
  const subs = (data.subjects_json && data.subjects_json.length) ? data.subjects_json : SCORE_OUTLINE.map(([subject, score_value]) => ({ subject, score_value, teacher: '', score: '' }))
  const summary = scoreSummary(data)

  const bodyRows = subs.map((x, i) => `
    <tr>
      <td class="num">${i + 1}</td>
      <td>${esc(x.subject)}</td>
      <td class="num">${esc(x.score_value)}</td>
      <td>${esc(blank ? '' : x.teacher)}</td>
      <td class="num">${esc(blank ? '' : x.score)}</td>
    </tr>`).join('')

  const html = `
    <h2 style="text-align:center;margin-bottom:2px;">实习生实操考核成绩单</h2>
    <div style="text-align:center;font-size:12px;color:#6b7280;margin-bottom:12px;">
      记录编号：BG-SM-PX-004　　民航总医院检验科
    </div>

    <table style="margin-bottom:8px;">
      <tr>
        <td style="width:10%;background:#f8fafc;">姓　名</td>
        <td style="width:23%">${esc(blank ? '' : data.intern_name)}</td>
        <td style="width:10%;background:#f8fafc;">类　型</td>
        <td style="width:23%">${esc(blank ? '' : data.intern_type)}</td>
        <td style="width:11%;background:#f8fafc;">考核日期</td>
        <td>${esc(blank ? '' : data.date)}</td>
      </tr>
    </table>

    <table>
      <thead>
        <tr>
          <th style="width:8%;text-align:center;">序号</th>
          <th>考核科目</th>
          <th style="width:10%;text-align:center;">分值</th>
          <th style="width:16%;">考核教师</th>
          <th style="width:12%;text-align:center;">考核成绩</th>
        </tr>
      </thead>
      <tbody>${bodyRows}</tbody>
      <tfoot>
        <tr>
          <td colspan="2" style="text-align:right;font-weight:600;">合　计</td>
          <td class="num" style="font-weight:600;">${summary.full || 100}</td>
          <td style="text-align:right;font-weight:600;">总成绩</td>
          <td class="num" style="font-weight:600;">${blank ? '' : summary.total}</td>
        </tr>
      </tfoot>
    </table>

    <table style="margin-top:10px;">
      <tr>
        <td style="width:12%;background:#f8fafc;">总体评价</td>
        <td style="height:56px;">${esc(blank ? '' : data.overall_comment)}</td>
      </tr>
    </table>

    <table style="margin-top:14px;border:0;">
      <tr>
        <td style="border:0;width:55%;padding-top:26px;">
          组长签字：<span style="display:inline-block;width:150px;border-bottom:1px solid #374151;">&nbsp;</span>
        </td>
        <td style="border:0;padding-top:26px;">
          日　期：<span style="display:inline-block;width:120px;border-bottom:1px solid #374151;">${blank ? '&nbsp;' : esc(data.sign_date || '')}</span>
        </td>
      </tr>
    </table>

    <div style="margin-top:18px;font-size:11px;color:#6b7280;">
      注：考核成绩按各科目分值打分，合计满 100 分；考核完成后由带教组长签字确认。
    </div>`

  printHtml('实习生实操考核成绩单', html)
}
</script>
