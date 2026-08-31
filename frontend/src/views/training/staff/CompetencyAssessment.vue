<template>
  <div class="competency">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/岗位"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    />
    <el-dialog v-model="visible" :title="form.id ? '编辑人员能力评估' : '新增人员能力评估'" width="920px" top="2vh">
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
            <el-col :span="12" v-for="it in grp.items" :key="it" class="score-item-col">
              <div class="score-item">
                <el-form-item :label="it" label-width="260px">
                  <el-input-number v-model="scores[it]" :min="0" :max="5" @change="recalc" style="width:100px" size="small" />
                  <el-button text type="primary" size="small" style="margin-left:8px" @click="toggleEvidence(it)">
                    {{ evidenceOpen[it] ? '收起依据' : '评估依据' }}
                    <el-icon v-if="hasEvidence(it)"><Check /></el-icon>
                  </el-button>
                </el-form-item>
                <!-- 评估依据展开区 -->
                <div v-if="evidenceOpen[it]" class="evidence-panel">
                  <el-form-item label="评估方法" label-width="80px">
                    <el-select v-model="evidences[it].method" placeholder="选择方法" clearable size="small" style="width:180px">
                      <el-option v-for="m in methodOptions" :key="m.value" :label="m.label" :value="m.value" />
                    </el-select>
                  </el-form-item>
                  <el-form-item label="依据描述" label-width="80px">
                    <el-input v-model="evidences[it].evidence" type="textarea" :rows="2" placeholder="填写评估依据详情，如：盲样#B2026-08-001 偏倚+1.2% 通过 / 2026-08-15 旁站观察操作规范" size="small" />
                  </el-form-item>
                  <el-form-item v-if="needsRefId(evidences[it].method)" label="关联编号" label-width="80px">
                    <el-input v-model="evidences[it].ref_id" placeholder="样品编号/EQA计划号/比对记录ID等" size="small" />
                  </el-form-item>
                </div>
              </div>
            </el-col>
          </el-row>
        </div>

        <el-divider content-position="left">汇总</el-divider>
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="总分"><el-input :model-value="total" disabled /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="评估结论">
            <el-input :model-value="form.conclusion" disabled :placeholder="total >= 80 ? '合格' : '不合格'" />
          </el-form-item></el-col>
          <el-col :span="6"><el-form-item label="评估人"><el-input v-model="form.assessor" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="授权人"><el-input v-model="form.authorizer" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="12">
          <el-col :span="12"><el-form-item label="评估日期"><el-input v-model="form.assess_date" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="备注"><el-input v-model="form.remark" placeholder="可选" /></el-form-item></el-col>
        </el-row>
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
import { Check } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import { listCompetency, createCompetency, updateCompetency, deleteCompetency } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)

// ---- 列表列（修复原缺失 columns 的 bug）----
const columns = [
  { prop: 'name', label: '姓名', width: 100 },
  { prop: 'department', label: '部门', width: 110 },
  { prop: 'post', label: '岗位', width: 100 },
  { prop: 'year', label: '年份', width: 80 },
  { prop: 'total', label: '总分', width: 80 },
  { prop: 'conclusion', label: '结论', width: 90 },
  { prop: 'assessor', label: '评估人', width: 100 },
  { prop: 'assess_date', label: '评估日期', width: 120 },
]

// ---- 评分分组（4 类 20 项，与 BG-KS-PX-808 一致）----
const groups = [
  { title: '职业道德', weight: 25, items: ['遵守法律法规情况和医院、科室规章制度情况', '执行体系文件情况', '检验活动公正性执行情况', '工作态度', '保密工作执行情况'] },
  { title: '专业技术水平', weight: 50, items: ['参加培训和继续教育情况', '观察常规工作现场实际操作情况', '检验特定样品的能力（已检验样品、EQA样品、比对样品）', '核查记录填写情况', '观察设备维护和功能检查情况', '监控检验结果的记录和报告过程', '对检验结果的分析和判断能力', '信息系统使用、新增功能使用、信息安全防护的能力', '执行应急预案的能力', '解决问题的能力'] },
  { title: '员工的表现', weight: 15, items: ['服务对象满意度情况', '团队合作情况', '个人发展情况'] },
  { title: '主要工作业绩', weight: 10, items: ['履行职责工作任务完成情况', '对科室的贡献情况'] },
]
const allItems = groups.flatMap((g) => g.items)

// ---- 评估方法选项 ----
const methodOptions = [
  { value: 'observation', label: '直接观察' },
  { value: 'blind_sample', label: '盲样/未知样测试' },
  { value: 'internal_comparison', label: '内部比对/人员间比对' },
  { value: 'pt_eqa', label: 'PT/EQA 表现' },
  { value: 'data_analysis', label: '数据分析' },
]
// 需要关联编号的方法
const methodsNeedingRefId = new Set(['blind_sample', 'internal_comparison', 'pt_eqa'])
function needsRefId(method) { return methodsNeedingRefId.has(method) }

// ---- 评分状态 ----
const scores = reactive({})
const evidenceOpen = reactive({})
const evidences = reactive({})

function blankEvidence() {
  return { method: '', evidence: '', ref_id: '', assessor: '', date: '' }
}

const form = ref(blank())
function blank() {
  const s = {}
  const e = {}
  for (const it of allItems) {
    s[it] = 0
    e[it] = blankEvidence()
  }
  return {
    id: null, name: '', department: '生化免疫组', post: '',
    year: new Date().getFullYear(), scores_json: { ...s }, evidence_json: {},
    total: 0, conclusion: '', assessor: '', authorizer: '',
    assess_date: '', remark: ''
  }
}
const total = computed(() => allItems.reduce((a, it) => a + (Number(scores[it]) || 0), 0))

function hasEvidence(it) {
  const ev = evidences[it]
  return ev && (ev.method || ev.evidence)
}
function toggleEvidence(it) {
  evidenceOpen[it] = !evidenceOpen[it]
  if (evidenceOpen[it] && !evidences[it]) evidences[it] = blankEvidence()
}

function openForm(row) {
  const s = {}
  const e = {}
  for (const it of allItems) {
    s[it] = (row?.scores_json && row.scores_json[it] != null) ? Number(row.scores_json[it]) : 0
    const rev = row?.evidence_json?.[it]
    e[it] = rev ? { ...blankEvidence(), ...rev } : blankEvidence()
    evidenceOpen[it] = false
  }
  Object.assign(scores, s)
  Object.assign(evidences, e)
  form.value = row ? { ...row } : blank()
  visible.value = true
}
function recalc() {
  form.value.total = total.value
  form.value.conclusion = total.value >= 80 ? '合格' : '不合格'
}
async function save() {
  try {
    // 构建干净的 evidence_json（只保留有方法或证据的项）
    const cleanEv = {}
    for (const it of allItems) {
      const ev = evidences[it]
      if (ev && (ev.method || ev.evidence)) {
        cleanEv[it] = {
          method: ev.method || '',
          evidence: ev.evidence || '',
          ref_id: ev.ref_id || '',
          assessor: form.value.assessor || '',
          date: form.value.assess_date || '',
        }
      }
    }
    form.value.scores_json = { ...scores }
    form.value.evidence_json = cleanEv
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
.competency { }
.score-group { margin-bottom: 10px; background: #fafbfc; border-radius: 6px; padding: 8px 12px; }
.grp-title { font-weight: 600; color: #409eff; margin: 4px 0 8px; font-size: 14px; }
.score-item-col { margin-bottom: 4px; }
.score-item { position: relative; }
.score-item .el-form-item { margin-bottom: 4px; }
.evidence-panel {
  margin: 0 0 8px 36px;
  padding: 10px 12px;
  background: #f0f7ff;
  border: 1px solid #b3d8ff;
  border-radius: 6px;
  margin-top: -4px;
}
.evidence-panel .el-form-item { margin-bottom: 8px; }
</style>
