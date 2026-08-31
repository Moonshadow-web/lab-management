<template>
  <div class="competency">
    <CrudTable
      :columns="columns" :fetch="fetch"
      search-placeholder="搜索姓名/岗位"
      :can-write="canWrite"
      @add="openForm()" @edit="openForm" @delete="onDelete" ref="tableRef"
    >
      <template #row-extra="{ row }">
        <el-button link type="primary" :icon="Printer" @click="onPrint(row)">预览打印</el-button>
      </template>
    </CrudTable>
    <el-dialog v-model="visible" :title="form.id ? '编辑人员能力评估' : '新增人员能力评估'" width="920px" top="2vh">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="12">
          <el-col :span="6"><el-form-item label="姓名"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="所在部门"><el-input v-model="form.department" /></el-form-item></el-col>
          <el-col :span="6"><el-form-item label="岗位">
            <el-select v-model="postList" multiple collapse-tags collapse-tags-tooltip :max-collapse-tags="2"
                       placeholder="可多选" style="width:100%">
              <el-option v-for="p in postOptions" :key="p" :label="p" :value="p" />
            </el-select>
          </el-form-item></el-col>
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

    <Teleport to="body">
      <CompetencyAssessmentPrint v-if="printData" :data="printData" />
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Check, Printer } from '@element-plus/icons-vue'
import CrudTable from '../../../components/CrudTable.vue'
import { listCompetency, getCompetency, createCompetency, updateCompetency, deleteCompetency } from '../../../api/education'
import { useAuthStore } from '../../../store/auth'
import CompetencyAssessmentPrint from './CompetencyAssessmentPrint.vue'
import {
  groups, allItems, methodOptions, needsRefId, postOptions,
  defaultEvidenceMap, defaultEvidence, splitPost, joinPost,
} from './competencyMeta'

const auth = useAuthStore()
const canWrite = ref(auth.canWrite('training'))
const tableRef = ref(null)
const printData = ref(null)

// ---- 列表列（修复原缺失 columns 的 bug）----
const columns = [
  { prop: 'name', label: '姓名', width: 100 },
  { prop: 'department', label: '部门', width: 110 },
  { prop: 'post', label: '岗位', width: 160 },
  { prop: 'year', label: '年份', width: 80 },
  { prop: 'total', label: '总分', width: 80 },
  { prop: 'conclusion', label: '结论', width: 90 },
  { prop: 'assessor', label: '评估人', width: 100 },
  { prop: 'assess_date', label: '评估日期', width: 120 },
]

// ---- 评分状态 ----
const scores = reactive({})
const evidenceOpen = reactive({})
const evidences = reactive({})
const postList = ref([]) // 岗位多选（存库时以顿号连接写入 form.post）

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
  postList.value = splitPost(form.value.post)
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
    form.value.post = joinPost(postList.value)
    form.value.total = total.value
    form.value.conclusion = total.value >= 80 ? '合格' : '不合格'
    if (form.value.id) await updateCompetency(form.value.id, form.value)
    else await createCompetency(form.value)
    ElMessage.success('已保存'); visible.value = false; tableRef.value?.refresh()
  } catch (e) { ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message)) }
}
// 预览打印：拉最新完整记录（含 evidence_json）→ 渲染打印版式 → 调浏览器打印（可另存为 PDF）
async function onPrint(row) {
  try {
    printData.value = await getCompetency(row.id)
    await nextTick()
    window.print()
  } catch (e) { ElMessage.error('打印失败：' + (e.response?.data?.detail || e.message)) }
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
