<template>
  <div class="internship">
    <el-tabs v-model="tab">
      <el-tab-pane label="培训大纲及带教评价（PX-003）" name="mentor">
        <CrudTable :columns="mentorCols" :fetch="fetchMentor" search-placeholder="搜索姓名"
          :can-write="canWrite" @add="openMentor()" @edit="openMentor" @delete="onDeleteMentor" ref="mentorRef" />
      </el-tab-pane>
      <el-tab-pane label="实操考核成绩单（PX-004）" name="score">
        <CrudTable :columns="scoreCols" :fetch="fetchScore" search-placeholder="搜索姓名"
          :can-write="canWrite" @add="openScore()" @edit="openScore" @delete="onDeleteScore" ref="scoreRef" />
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
          <el-table-column label="日期" width="120"><template #default="{ row }"><el-input v-model="row.date" size="small" /></template></el-table-column>
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
          <el-col :span="8"><el-form-item label="考核日期"><el-input v-model="scoreForm.date" /></el-form-item></el-col>
        </el-row>
        <el-divider content-position="left">实操考核科目（BG-SM-PX-004）</el-divider>
        <el-table :data="scoreForm.subjects_json" border size="small">
          <el-table-column label="考核科目" min-width="260"><template #default="{ row }"><el-input v-model="row.subject" size="small" /></template></el-table-column>
          <el-table-column label="分值" width="90"><template #default="{ row }"><el-input v-model="row.score_value" size="small" /></template></el-table-column>
          <el-table-column label="考核教师" width="120"><template #default="{ row }"><el-input v-model="row.teacher" size="small" /></template></el-table-column>
          <el-table-column label="考核成绩" width="120"><template #default="{ row }"><el-input v-model="row.score" size="small" /></template></el-table-column>
        </el-table>
        <el-divider content-position="left">总体评价</el-divider>
        <el-form-item label="评语"><el-input v-model="scoreForm.overall_comment" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="组长签字"><el-input v-model="scoreForm.group_leader" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="日期"><el-input v-model="scoreForm.sign_date" /></el-form-item></el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="scoreVisible = false">取消</el-button>
        <el-button type="primary" @click="saveScore">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import {
  listMentor, createMentor, updateMentor, deleteMentor,
  listScore, createScore, updateScore, deleteScore,
} from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tab = ref('mentor')
const mentorRef = ref(null)
const scoreRef = ref(null)

const mentorCols = [
  { prop: 'intern_name', label: '姓名', width: 120 },
  { prop: 'intern_type', label: '类型', width: 80 },
  { prop: 'sop_ref', label: '依据SOP', width: 120 },
  { prop: 'remark', label: '备注', minWidth: 160 },
]
const scoreCols = [
  { prop: 'intern_name', label: '姓名', width: 120 },
  { prop: 'intern_type', label: '类型', width: 80 },
  { prop: 'date', label: '考核日期', width: 130 },
  { prop: 'group_leader', label: '组长签字', width: 120 },
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
</script>
