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
                  <el-button text :type="isDefault(it) ? 'info' : 'primary'" size="small" style="margin-left:8px" @click="toggleEvidence(it)">
                    {{ evidenceOpen[it] ? '收起依据' : (isDefault(it) ? '评估依据（默认）' : '评估依据') }}
                    <el-icon v-if="!isDefault(it)"><Check /></el-icon>
                  </el-button>
                </el-form-item>
                <!-- 评估依据展开区：已预填推荐方法与描述模板，按实际修改即可 -->
                <div v-if="evidenceOpen[it]" class="evidence-panel">
                  <el-form-item label="评估方法" label-width="80px">
                    <el-select v-model="evidences[it].method" placeholder="选择方法" clearable size="small" style="width:180px">
                      <el-option v-for="m in methodOptions" :key="m.value" :label="m.label" :value="m.value" />
                    </el-select>
                    <el-button v-if="!isDefault(it)" text size="small" style="margin-left:10px" @click="resetEvidence(it)">恢复默认</el-button>
                  </el-form-item>
                  <el-form-item label="依据描述" label-width="80px">
                    <el-input v-model="evidences[it].evidence" type="textarea" :rows="2" placeholder="已预填默认描述，按实际情况修改" size="small" />
                  </el-form-item>
                  <el-form-item v-if="needsRefId(evidences[it].method)" label="关联编号" label-width="80px">
                    <el-input v-model="evidences[it].ref_id" placeholder="样品编号/EQA计划号/比对记录ID（默认方法需补此项）" size="small" />
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

// 各评分项的推荐评估方法 + 依据描述模板：默认直接沿用，个别按实际修改即可
const defaultEvidenceMap = {
  // 职业道德（25 分 / 5 项）
  '遵守法律法规情况和医院、科室规章制度情况': ['observation', '日常考勤、交接班及科室例会记录完整，本年度无违规违纪记录。'],
  '执行体系文件情况': ['observation', '现场抽查 SOP 与记录表格执行情况，操作与现行体系文件一致，无偏离。'],
  '检验活动公正性执行情况': ['observation', '未发现影响检验公正性的利益冲突或干预，公正性声明执行到位。'],
  '工作态度': ['observation', '日常工作主动负责，服从安排，按时完成分配任务，无推诿拖延。'],
  '保密工作执行情况': ['observation', '患者信息及检验数据按授权范围使用，无泄露或违规外传事件。'],
  // 专业技术水平（50 分 / 10 项）
  '参加培训和继续教育情况': ['data_analysis', '本年度参加专业组培训 __ 次、科室培训 __ 次，继教学分达标。'],
  '观察常规工作现场实际操作情况': ['observation', '20__-__-__ 旁站观察常规操作，流程规范、符合 SOP，无需纠正。'],
  '检验特定样品的能力（已检验样品、EQA样品、比对样品）': ['pt_eqa', '本年度 EQA/PT 回报 __ 项、合格 __ 项，无不合格项。'],
  '核查记录填写情况': ['data_analysis', '抽查记录表格 __ 份，填写完整可追溯，修改规范、签字齐全。'],
  '观察设备维护和功能检查情况': ['observation', '现场观察日常维护与功能检查，按计划执行，记录完整及时。'],
  '监控检验结果的记录和报告过程': ['data_analysis', '抽查检验结果记录与报告 __ 份，录入准确、审核及时，无差错。'],
  '对检验结果的分析和判断能力': ['internal_comparison', '人员比对/留样再测 __ 次，结果一致，偏差在允许范围内。'],
  '信息系统使用、新增功能使用、信息安全防护的能力': ['observation', '熟练使用 LIS 及本年度新增功能，账号与数据安全管理符合要求。'],
  '执行应急预案的能力': ['observation', '参加应急演练 __ 次（断电/仪器故障/生物安全等），处置流程正确。'],
  '解决问题的能力': ['observation', '能独立判断并处理常见异常（复检、干扰、危急值、仪器报警等）。'],
  // 员工的表现（15 分 / 3 项）
  '服务对象满意度情况': ['data_analysis', '临床/患者满意度调查 __ 分，本年度无有效投诉。'],
  '团队合作情况': ['observation', '配合组内排班与带教工作，沟通顺畅，无协作问题。'],
  '个人发展情况': ['data_analysis', '本年度参加继续教育/学术活动 __ 次，取得学分 __ 分。'],
  // 主要工作业绩（10 分 / 2 项）
  '履行职责工作任务完成情况': ['data_analysis', '年度岗位职责与工作任务完成率 100%，无延误或漏项。'],
  '对科室的贡献情况': ['data_analysis', '参与科室质量改进/体系工作 __ 项（内审、SOP 修订、新项目开展等）。'],
}

function defaultEvidence(it) {
  const d = defaultEvidenceMap[it]
  return { method: d ? d[0] : 'observation', evidence: d ? d[1] : '', ref_id: '', assessor: '', date: '' }
}
// 仍为推荐默认且未补关联编号 → 视为未专门填写，不打勾、按钮显示"(默认)"
function isDefault(it) {
  const d = defaultEvidenceMap[it]
  const ev = evidences[it]
  if (!d || !ev) return true
  return ev.method === d[0] && ev.evidence === d[1] && !ev.ref_id
}
function resetEvidence(it) { evidences[it] = defaultEvidence(it) }

const form = ref(blank())
function blank() {
  const s = {}
  const e = {}
  for (const it of allItems) {
    s[it] = 0
    e[it] = defaultEvidence(it)
  }
  return {
    id: null, name: '', department: '生化免疫组', post: '',
    year: new Date().getFullYear(), scores_json: { ...s }, evidence_json: {},
    total: 0, conclusion: '', assessor: '', authorizer: '',
    assess_date: '', remark: ''
  }
}
const total = computed(() => allItems.reduce((a, it) => a + (Number(scores[it]) || 0), 0))

function toggleEvidence(it) {
  evidenceOpen[it] = !evidenceOpen[it]
  if (evidenceOpen[it] && !evidences[it]) evidences[it] = defaultEvidence(it)
}

function openForm(row) {
  const s = {}
  const e = {}
  for (const it of allItems) {
    s[it] = (row?.scores_json && row.scores_json[it] != null) ? Number(row.scores_json[it]) : 0
    const rev = row?.evidence_json?.[it]
    e[it] = rev ? { ...defaultEvidence(it), ...rev } : defaultEvidence(it)
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
