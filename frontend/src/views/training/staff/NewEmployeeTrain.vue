<template>
  <div class="new-employee-train">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/类别"
      :can-write="canWrite"
      :action-width="210"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button link type="primary" :icon="Printer" @click="onPrint(row)">打印</el-button>
      </template>
    </CrudTable>

    <el-dialog v-model="visible" :title="form.id ? '编辑新员工培训及考核' : '新增新员工培训及考核'" width="1180px" top="3vh">
      <el-form :model="form" label-width="120px">
        <el-row :gutter="12">
          <el-col :span="8"><el-form-item label="员工姓名"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="8">
            <el-form-item label="员工类别">
              <el-select v-model="form.employee_category" style="width:100%">
                <el-option label="轮转" value="轮转" />
                <el-option label="新职工" value="新职工" />
                <el-option label="离岗6个月再上岗" value="离岗6个月再上岗" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="培训专业"><el-input v-model="form.train_major" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="入组时间"><el-input v-model="form.group_join_date" placeholder="如 2026-01" /></el-form-item></el-col>
          <el-col :span="16"><el-form-item label="培训时长"><el-input v-model="form.train_duration" placeholder="如 急诊3月、病房2月..." /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">能力评估（生化、免疫各一次）</el-divider>
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="生化评估结果">
              <el-select v-model="form.ability_bio_result" style="width:100%">
                <el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="生化评估负责人"><el-input v-model="form.ability_bio_responsible" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="免疫评估结果">
              <el-select v-model="form.ability_immuno_result" style="width:100%">
                <el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="免疫评估负责人"><el-input v-model="form.ability_immuno_responsible" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="理论/操作/口试">
              <el-select v-model="form.theory_operation_oral_result" style="width:100%">
                <el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">考核结果</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="考核结果">
              <el-select v-model="form.exam_result" style="width:100%">
                <el-option label="合格" value="合格" />
                <el-option label="不合格" value="不合格" />
                <el-option label="通过" value="通过" />
                <el-option label="不通过" value="不通过" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="8"><el-form-item label="考核负责人"><el-input v-model="form.exam_responsible" /></el-form-item></el-col>
          <el-col :span="8"><el-form-item label="考核时间"><el-input v-model="form.exam_time" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="状态"><el-select v-model="form.status" style="width:100%"><el-option label="进行中" value="进行中" /><el-option label="已完成" value="已完成" /></el-select></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">培训计划及考核内容（BG-SM-PX-005）</el-divider>
        <div class="plan-toolbar">
          <el-button :icon="Plus" @click="addPlanItem">加一行</el-button>
        </div>
        <el-table :data="form.plan_items" border size="small" height="320">
          <el-table-column label="培训类别" width="120">
            <template #default="{ row }"><el-input v-model="row.category" size="small" /></template>
          </el-table-column>
          <el-table-column label="培训内容" min-width="240">
            <template #default="{ row }"><el-input v-model="row.content" size="small" /></template>
          </el-table-column>
          <el-table-column label="培训方式" width="220">
            <template #default="{ row }">
              <el-select v-model="row.method" multiple collapse-tags collapse-tags-tooltip size="small" placeholder="讲解/PPT/文件" style="width:100%">
                <el-option label="讲解" value="讲解" />
                <el-option label="PPT" value="PPT" />
                <el-option label="文件" value="文件" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="考核方式" width="190">
            <template #default="{ row }">
              <el-select v-model="row.exam_method" multiple collapse-tags collapse-tags-tooltip size="small" placeholder="试卷/问答/实操" style="width:100%">
                <el-option label="试卷" value="试卷" />
                <el-option label="问答" value="问答" />
                <el-option label="实操" value="实操" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="" width="50" align="center">
            <template #default="{ row }"><el-button link type="danger" :icon="Delete" @click="removePlanItem(row)" /></template>
          </el-table-column>
        </el-table>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <Teleport to="body">
      <NewEmployeeTrainPrint v-if="printData" :data="printData" />
    </Teleport>
  </div>
</template>

<script setup>
import { ref, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, Printer } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import NewEmployeeTrainPrint from './NewEmployeeTrainPrint.vue'
import { listNewEmployee, getNewEmployee, createNewEmployee, updateNewEmployee, deleteNewEmployee } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const columns = [
  { prop: 'name', label: '员工姓名', width: 110 },
  { prop: 'employee_category', label: '员工类别', width: 140 },
  { prop: 'train_major', label: '培训专业', width: 100 },
  { prop: 'exam_result', label: '考核结果', width: 100 },
  { prop: 'exam_responsible', label: '考核负责人', width: 120 },
  { prop: 'status', label: '状态', width: 90 },
]

const visible = ref(false)
const printData = ref(null)

// 新增空行时的默认培训/考核方式（可改）
const DEFAULT_METHODS = ['讲解']
const DEFAULT_EXAM_METHODS = ['问答']

function blank() {
  return {
    id: null, name: '', employee_category: '新职工', train_major: '生免室', group_join_date: '',
    train_duration: '急诊3个月、病房2个月、门诊2个月、血凝电泳1个月、免疫手工1个月、免疫仪器2个月、免疫杂项1个月',
    ability_bio_result: '合格', ability_bio_responsible: '杨静',
    ability_immuno_result: '合格', ability_immuno_responsible: '金子铮',
    theory_operation_oral_result: '合格',
    exam_result: '合格', exam_responsible: '', exam_time: '',
    plan_items: defaultOutline(), status: '进行中', remark: '',
  }
}

// BG-SM-PX-005 原表默认划√项，逐行与纸质表格一致
function defaultOutline() {
  return [
    { category: '生物安全', content: '生免室生物安全风险点告知', method: ['讲解'], exam_method: ['问答'] },
    { category: '生物安全', content: '溢撒标本的处理', method: ['讲解'], exam_method: ['实操'] },
    { category: '情况简介', content: '生免室的布局、人员结构、工作岗位、设置情况、所开展的检验项目等', method: ['讲解'], exam_method: ['问答'] },
    { category: '情况简介', content: '急诊岗位职责', method: ['讲解'], exam_method: ['问答'] },
    { category: '急诊岗', content: '急诊标本的接收和处理', method: ['讲解'], exam_method: ['实操'] },
    { category: '急诊岗', content: '血气分析仪及血氨分析仪的操作使用流程', method: ['讲解'], exam_method: ['实操'] },
    { category: '急诊岗', content: '急诊 AU5800、DXI800、TOP C 及 E411 的操作使用流程', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '急诊岗', content: '生化检验项目组合及临床意义', method: ['讲解', 'PPT'], exam_method: ['问答', '实操'] },
    { category: '急诊岗', content: '临床危急值报告及样本拒收制度', method: ['讲解', 'PPT'], exam_method: ['实操'] },
    { category: '病房岗', content: '标本处理前，中，后的流程', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '病房岗', content: '日立 7600 仪器日常使用及维护', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '病房岗', content: '生化室室内质控规则及失控处理流程', method: ['讲解', 'PPT'], exam_method: ['问答', '实操'] },
    { category: '门诊岗', content: '了解试剂性能及携带污染等理论', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '门诊岗', content: '深入学习 5800 仪器生化项目的检测原理及反应曲线', method: ['讲解', 'PPT'], exam_method: ['实操'] },
    { category: '门诊岗', content: 'AU5822 仪器及流水线使用', method: ['讲解'], exam_method: ['实操'] },
    { category: '门诊岗', content: '生化检测项目的复检规则', method: ['讲解', 'PPT'], exam_method: ['试卷', '问答'] },
    { category: '门诊岗', content: '生化项目报告单发放', method: ['讲解'], exam_method: ['试卷', '问答'] },
    { category: '门诊岗', content: '参与室间质评及仪器比对', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '凝血岗', content: 'TOP 系列凝血流水线的使用', method: ['讲解'], exam_method: ['实操'] },
    { category: '凝血岗', content: '凝血相关试剂的配制及更换', method: ['讲解'], exam_method: ['实操'] },
    { category: '凝血岗', content: '凝血常规项目的质量控制、检测原理', method: ['讲解', 'PPT'], exam_method: ['试卷', '问答'] },
    { category: '凝血岗', content: '凝血报告的注意事项及临床意义', method: ['讲解'], exam_method: ['问答'] },
    { category: '凝血岗', content: 'APTT 纠正试验的操作流程及结果判读', method: ['讲解'], exam_method: ['问答'] },
    { category: '凝血岗', content: 'TOP 血凝仪凝血曲线的解读及凝血项目复检规则', method: ['讲解', 'PPT'], exam_method: ['试卷', '问答'] },
    { category: '电泳岗', content: '出凝血疾病的实验室诊断步骤', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '电泳岗', content: '糖化血红蛋白仪器操作及理论', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '电泳岗', content: '免疫固定电泳技术', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '免疫手工岗', content: 'ELISA 检测的原理，TECAN 仪器的操作流程，注意事项及结果分析', method: ['讲解'], exam_method: ['试卷', '问答', '实操'] },
    { category: '免疫手工岗', content: 'AIDS 初筛实验及报告方法，可疑样本的外送流程', method: ['讲解', '文件'], exam_method: ['问答', '实操'] },
    { category: '免疫手工岗', content: 'TRUST 的检测原理及操作', method: ['讲解'], exam_method: ['问答', '实操'] },
    { category: '免疫仪器岗', content: '免疫室化学发光法的检测项目及检测原理', method: ['讲解'], exam_method: ['试卷', '问答'] },
    { category: '免疫仪器岗', content: '罗氏 E601、迈瑞 CL6000i、贝克曼 I800 的使用、质控及定标流程，及各仪器的维护保养', method: ['讲解', 'PPT'], exam_method: ['实操'] },
    { category: '免疫仪器岗', content: '感染类项目（乙肝五项、甲肝抗体、丙肝抗体、戊肝抗体、艾滋抗体、梅毒抗体）、内分泌激素（胰岛素、C 肽、HCG、孕酮、雌二醇、雌三醇）及肿瘤标志物（甲胎蛋白、前列腺特异性抗原）的临床意义及复检规则', method: ['讲解', 'PPT'], exam_method: ['试卷', '问答'] },
    { category: '免疫杂项岗', content: '肾早期损伤项目、高血压组项、结核γ干扰素释放实验的检测原理及临床意义', method: ['讲解'], exam_method: ['试卷', '问答'] },
    { category: '免疫杂项岗', content: '安图 A2000 的检测原理、使用及仪器维护', method: ['讲解'], exam_method: ['实操'] },
    { category: '免疫杂项岗', content: '了解唐氏筛查的检测意义', method: ['讲解'], exam_method: ['问答', '实操'] },
  ]
}

// 把后端可能返回的字符串/列表统一成数组，防止 [..."字符串"] 把长字符串拆成单字符
function toMethodArray(v) {
  if (Array.isArray(v)) return v.slice()
  if (typeof v === 'string' && v.trim()) return v.split(/[,，\/、\s]+/).filter(Boolean)
  return []
}

// 编辑/打印时拉取完整记录，避免列表行 plan_items 为字符串导致的卡顿与空白
function normalizeRecord(full) {
  const items = Array.isArray(full.plan_items) ? full.plan_items : []
  return {
    ...full,
    plan_items: items.map((r) => ({
      category: r.category || '',
      content: r.content || '',
      method: toMethodArray(r.method),
      exam_method: toMethodArray(r.exam_method),
    })),
  }
}

async function openForm(row) {
  if (row && row.id) {
    const full = await getNewEmployee(row.id)
    form.value = normalizeRecord(full)
  } else {
    form.value = blank()
  }
  visible.value = true
}
function addPlanItem() {
  form.value.plan_items.push({ category: '', content: '', method: [...DEFAULT_METHODS], exam_method: [...DEFAULT_EXAM_METHODS] })
}
function removePlanItem(r) { form.value.plan_items = form.value.plan_items.filter((x) => x !== r) }

const form = ref(blank())

async function save() {
  try {
    if (form.value.id) await updateNewEmployee(form.value.id, form.value)
    else await createNewEmployee(form.value)
    ElMessage.success('已保存')
    visible.value = false
    tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try {
    await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' })
    await deleteNewEmployee(row.id)
    ElMessage.success('已删除')
    tableRef.value?.refresh()
  } catch (e) {}
}
async function onPrint(row) {
  try {
    const full = await getNewEmployee(row.id)
    printData.value = normalizeRecord(full)
    await nextTick()
    window.print()
  } catch (e) {
    ElMessage.error('打印准备失败：' + (e.response?.data?.detail || e.message))
  }
}
function fetch(params) { return listNewEmployee(params) }
</script>

<style scoped>
.plan-toolbar { margin-bottom: 8px; }
</style>
