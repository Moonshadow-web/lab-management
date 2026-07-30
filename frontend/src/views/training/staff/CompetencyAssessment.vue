<template>
  <div class="competency">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/岗位"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    />
    <el-dialog v-model="visible" :title="form.id ? '编辑人员能力评估' : '新增人员能力评估'" width="860px" top="3vh">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="所在部门"><el-input v-model="form.department" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="岗位"><el-input v-model="form.post" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="年份"><el-input v-model="form.year" placeholder="如 2026" /></el-form-item></el-col>
        </el-row>

        <el-divider content-position="left">评分（每项 0-5 分，合计 100 分；≥80 合格）</el-divider>
        <div v-for="grp in groups" :key="grp.title" class="score-group">
          <div class="grp-title">{{ grp.title }}（{{ grp.weight }}分）</div>
          <el-row :gutter="12">
            <el-col :span="12" v-for="it in grp.items" :key="it">
              <el-form-item :label="it" label-width="280px">
                <el-input-number v-model="scores[it]" :min="0" :max="5" @change="recalc" style="width:120px" />
              </el-form-item>
            </el-col>
          </el-row>
        </div>

        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="总分"><el-input :model-value="total" disabled /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="评估结论">
            <el-input :model-value="form.conclusion" disabled :placeholder="total >= 80 ? '合格' : '不合格'" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="评估人"><el-input v-model="form.assessor" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="授权人"><el-input v-model="form.authorizer" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="评估日期"><el-input v-model="form.assess_date" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import CrudTable from '../../../components/CrudTable.vue'
import { listCompetency, createCompetency, updateCompetency, deleteCompetency } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

const groups = [
  { title: '职业道德', weight: 25, items: ['遵守法律法规情况和医院、科室规章制度情况', '执行体系文件情况', '检验活动公正性执行情况', '工作态度', '保密工作执行情况'] },
  { title: '专业技术水平', weight: 50, items: ['参加培训和继续教育情况', '观察常规工作现场实际操作情况', '检验特定样品的能力（已检验样品、EQA样品、比对样品）', '核查记录填写情况', '观察设备维护和功能检查情况', '监控检验结果的记录和报告过程', '对检验结果的分析和判断能力', '信息系统使用、新增功能使用、信息安全防护的能力', '执行应急预案的能力', '解决问题的能力'] },
  { title: '员工的表现', weight: 15, items: ['服务对象满意度情况', '团队合作情况', '个人发展情况'] },
  { title: '主要工作业绩', weight: 10, items: ['履行职责工作任务完成情况', '对科室的贡献情况'] },
]
const allItems = groups.flatMap((g) => g.items)

const scores = reactive({})
const form = ref(blank())
function blank() {
  const s = {}
  for (const it of allItems) s[it] = 0
  return { id: null, name: '', department: '生化免疫组', post: '', year: new Date().getFullYear(), scores_json: { ...s }, total: 0, conclusion: '', assessor: '', authorizer: '', assess_date: '' }
}
const total = computed(() => allItems.reduce((a, it) => a + (Number(scores[it]) || 0), 0))

function openForm(row) {
  const s = {}
  for (const it of allItems) s[it] = (row?.scores_json && row.scores_json[it] != null) ? Number(row.scores_json[it]) : 0
  Object.assign(scores, s)
  form.value = row ? { ...row } : blank()
  visible.value = true
}
function recalc() { form.value.total = total.value; form.value.conclusion = total.value >= 80 ? '合格' : '不合格' }
async function save() {
  try {
    form.value.scores_json = { ...scores }
    form.value.total = total.value
    form.value.conclusion = total.value >= 80 ? '合格' : '不合格'
    if (form.value.id) await updateCompetency(form.value.id, form.value)
    else await createCompetency(form.value)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
async function onDelete(row) {
  try { await ElMessageBox.confirm('确认删除？', '提示', { type: 'warning' }); await deleteCompetency(row.id); ElMessage.success('已删除'); tableRef.value?.refresh() } catch (e) {}
}
function fetch(params) { return listCompetency(params) }
const visible = ref(false)
</script>

<style scoped>
.score-group { margin-bottom: 8px; }
.grp-title { font-weight: 600; color: #409eff; margin: 6px 0; }
</style>
