<template>
  <div class="new-employee-train">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/类别"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    />
    <el-dialog v-model="visible" :title="form.id ? '编辑新员工培训及考核' : '新增新员工培训及考核'" width="960px" top="4vh">
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
              <el-select v-model="form.ability_bio_result" style="width:100%"><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="生化评估负责人"><el-input v-model="form.ability_bio_responsible" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="免疫评估结果">
              <el-select v-model="form.ability_immuno_result" style="width:100%"><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12"><el-form-item label="免疫评估负责人"><el-input v-model="form.ability_immuno_responsible" /></el-form-item></el-col>
          <el-col :span="12">
            <el-form-item label="理论/操作/口试">
              <el-select v-model="form.theory_operation_oral_result" style="width:100%"><el-option label="合格" value="合格" /><el-option label="不合格" value="不合格" /></el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">考核结果</el-divider>
        <el-row :gutter="12">
          <el-col :span="8">
            <el-form-item label="考核结果">
              <el-select v-model="form.exam_result" style="width:100%"><el-option label="通过" value="通过" /><el-option label="不通过" value="不通过" /></el-select>
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
        <el-table :data="form.plan_items" border size="small">
          <el-table-column label="培训类别" width="120">
            <template #default="{ row }"><el-input v-model="row.category" size="small" /></template>
          </el-table-column>
          <el-table-column label="培训内容" min-width="240">
            <template #default="{ row }"><el-input v-model="row.content" size="small" /></template>
          </el-table-column>
          <el-table-column label="培训老师" width="110">
            <template #default="{ row }"><el-input v-model="row.teacher" size="small" /></template>
          </el-table-column>
          <el-table-column label="培训方式" width="150">
            <template #default="{ row }"><el-input v-model="row.method" size="small" placeholder="讲解/PPT/文件" /></template>
          </el-table-column>
          <el-table-column label="考核方式" width="150">
            <template #default="{ row }"><el-input v-model="row.exam_method" size="small" placeholder="试卷/问答/实操" /></template>
          </el-table-column>
          <el-table-column label="考核成绩" width="110">
            <template #default="{ row }"><el-input v-model="row.score" size="small" placeholder=">80合格" /></template>
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
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import { listNewEmployee, createNewEmployee, updateNewEmployee, deleteNewEmployee } from '../../../api/education'
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
const form = ref(blank())
function blank() {
  return {
    id: null, name: '', employee_category: '新职工', train_major: '生免室', group_join_date: '',
    train_duration: '急诊3个月、病房2个月、门诊2个月、血凝电泳1个月、免疫手工1个月、免疫仪器2个月、免疫杂项1个月',
    ability_bio_result: '', ability_bio_responsible: '', ability_immuno_result: '', ability_immuno_responsible: '',
    theory_operation_oral_result: '', exam_result: '', exam_responsible: '', exam_time: '',
    plan_items: defaultOutline(), status: '进行中', remark: '',
  }
}
function defaultOutline() {
  const items = [
    ['生物安全', '生免室生物安全风险点告知', '金子铮'],
    ['生物安全', '溢撒标本的处理', '金子铮'],
    ['情况简介', '生免室的布局、人员结构、工作岗位、设置情况、所开展的检验项目等', '杨静'],
    ['情况简介', '急诊岗位职责', '杨静'],
    ['急诊岗', '急诊标本的接收和处理', '急诊岗人员'],
    ['急诊岗', '血气分析仪及血氨分析仪的操作使用流程', '急诊岗人员'],
    ['急诊岗', '急诊AU5800、DXI800、TOP C及E411的操作使用流程', '急诊岗人员'],
    ['急诊岗', '生化检验项目组合及临床意义', '急诊岗人员'],
    ['急诊岗', '临床危急值报告及样本拒收制度', '急诊岗人员'],
    ['病房岗', '标本处理前，中，后的流程', '病房岗人员'],
    ['病房岗', '日立7600仪器日常使用及维护', '病房岗人员'],
    ['病房岗', '生化室室内质控规则及失控处理流程', '病房岗人员'],
    ['病房岗', '了解试剂性能及携带污染等理论', '病房岗人员'],
    ['病房岗', '深入学习5800仪器生化项目的检测原理及反应曲线', '病房岗人员'],
    ['门诊岗', 'AU5822仪器及流水线使用', '门诊岗人员'],
    ['门诊岗', '生化检测项目的复检规则', '门诊岗人员'],
    ['门诊岗', '生化项目报告单发放', '门诊岗人员'],
    ['门诊岗', '参与室间质评及仪器比对', '朱春阳'],
    ['凝血岗', 'TOP系列凝血流水线的使用', '凝血岗人员'],
    ['凝血岗', '凝血相关试剂的配制及更换', '凝血岗人员'],
    ['凝血岗', '凝血常规项目的质量控制、检测原理', '凝血岗人员'],
    ['凝血岗', '凝血报告的注意事项及临床意义', '凝血岗人员'],
    ['凝血岗', 'APTT纠正试验的操作流程及结果判读', '凝血岗人员'],
    ['凝血岗', 'TOP血凝仪凝血曲线的解读及凝血项目复检规则', '凝血岗人员'],
    ['凝血岗', '出凝血疾病的实验室诊断步骤', '凝血岗人员'],
    ['电泳岗', '糖化血红蛋白仪器操作及理论', '电泳岗人员'],
    ['电泳岗', '免疫固定电泳技术', '电泳岗人员'],
    ['免疫手工岗', 'ELISA检测的原理，TECAN仪器的操作流程，注意事项及结果分析', '免疫手工岗人员'],
    ['免疫手工岗', 'AIDS初筛实验及报告方法，可疑样本的外送流程', '免疫手工岗人员'],
    ['免疫手工岗', 'TRUST的检测原理及操作', '免疫手工岗人员'],
    ['免疫手工岗', '免疫室化学发光法的检测项目及检测原理', '免疫手工岗人员'],
    ['免疫仪器岗', '罗氏E601、迈瑞CL6000i、贝克曼I800的使用、质控及定标流程，及各仪器的维护保养', '免疫仪器岗人员'],
    ['免疫仪器岗', '感染类项目（乙肝五项、甲肝抗体、丙肝抗体、戊肝抗体、艾滋抗体、梅毒抗体）、内分泌激素、肿瘤标志物的临床意义及复检规则', '免疫仪器岗人员'],
    ['免疫杂项岗', '肾早期损伤项目、高血压组项、结核γ干扰素释放实验的检测原理及临床意义', '免疫杂项岗人员'],
    ['免疫杂项岗', '安图A2000的检测原理、使用及仪器维护', '免疫杂项岗人员'],
    ['免疫杂项岗', '了解唐氏筛查的检测意义', '免疫杂项岗人员'],
  ]
  return items.map(([category, content, teacher]) => ({ category, content, teacher, method: '', exam_method: '', score: '' }))
}
function openForm(row) {
  if (row) {
    form.value = { ...row, plan_items: row.plan_items ? [...row.plan_items] : [] }
  } else {
    form.value = blank()
  }
  visible.value = true
}
function addPlanItem() { form.value.plan_items.push({ category: '', content: '', teacher: '', method: '', exam_method: '', score: '' }) }
function removePlanItem(r) { form.value.plan_items = form.value.plan_items.filter((x) => x !== r) }
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
function fetch(params) { return listNewEmployee(params) }
</script>

<style scoped>
.plan-toolbar { margin-bottom: 8px; }
</style>
