<template>
  <div class="interlab-page">
    <div class="toolbar">
      <el-select v-model="filterYear" placeholder="年份" clearable style="width:110px" @change="reload">
        <el-option v-for="y in yearOptions" :key="y" :label="y" :value="y" />
      </el-select>
      <el-select v-model="filterHalf" placeholder="半年" clearable style="width:110px" @change="reload">
        <el-option label="上半年" :value="1" />
        <el-option label="下半年" :value="2" />
      </el-select>
      <el-select v-model="filterInstrument" placeholder="仪器" clearable filterable style="width:180px" @change="reload">
        <el-option v-for="i in instruments" :key="i.id" :label="i.name" :value="i.id" />
      </el-select>
      <div style="flex:1" />
      <el-button type="primary" :icon="Plus" @click="openPlanCreate" v-if="canCreate">新建计划</el-button>
    </div>

      <el-alert v-if="!plans.length" type="info" :closable="false" show-icon
      title="尚无室间比对计划。室间比对用于「无室间质评且有外部参比实验室」的项目，每半年一次。点击右上角「新建计划」开始。" />

    <el-card class="guide-card" shadow="never" style="margin-bottom:10px">
      <template #header>
        <span class="guide-title">必做室间比对项目（无室间质评，每半年一次）</span>
        <span class="guide-sub">—— 以下项目系统已按仪器档案自动归集，新建计划时会自动带出</span>
      </template>
      <el-table :data="mandatory" border size="small" max-height="260">
        <el-table-column prop="name" label="检验项目" min-width="200">
          <template #default="{ row }">
            <el-tag type="danger" size="small" effect="dark" style="margin-right:6px">必做</el-tag>{{ row.name }}
          </template>
        </el-table-column>
        <el-table-column prop="unit" label="单位" width="80" />
        <el-table-column label="所属仪器" min-width="200">
          <template #default="{ row }">
            <el-tag v-for="ins in (row.instruments||[])" :key="ins.id" size="small" style="margin-right:4px">{{ ins.name }}</el-tag>
            <span v-if="!row.instruments || !row.instruments.length" class="no">未关联仪器</span>
          </template>
        </el-table-column>
        <el-table-column label="上次比对" width="120">
          <template #default="{ row }">
            <span v-if="!row.last_plan" class="no">无</span>
            <span v-else>{{ row.last_plan }}</span>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag v-if="row.last_status === 'done'" type="success" size="small">已完成</el-tag>
            <el-tag v-else-if="row.last_status === 'in_progress'" type="warning" size="small">进行中</el-tag>
            <el-tag v-else type="info" size="small">未做</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="下次应做" width="130">
          <template #default="{ row }">
            <span v-if="row.last_status === 'done'" style="color:#16a34a">✓ {{ row.next_due }}</span>
            <span v-else-if="row.last_status === 'in_progress'" style="color:#d97706">{{ row.next_due }}</span>
            <span v-else style="color:#dc2626;font-weight:600">{{ row.next_due }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-table :data="plans" border size="small" style="margin-top:12px">
      <el-table-column prop="year" label="年份" width="90" />
      <el-table-column label="半年" width="80">
        <template #default="{ row }">{{ row.half === 1 ? '上半年' : '下半年' }}</template>
      </el-table-column>
      <el-table-column label="仪器" width="150">
        <template #default="{ row }">{{ instrumentName(row.instrument_id) }}</template>
      </el-table-column>
      <el-table-column prop="reference_lab" label="参比实验室" min-width="140" />
      <el-table-column prop="compared_at" label="比对日期" width="120" />
      <el-table-column prop="operator" label="操作者" width="90" />
      <el-table-column prop="reviewer" label="审核者" width="90" />
      <el-table-column label="结论" width="100">
        <template #default="{ row }">
          <el-tag v-if="row.conclusion === '可接受'" type="success" size="small">可接受</el-tag>
          <el-tag v-else-if="row.conclusion === '不可接受'" type="danger" size="small">不可接受</el-tag>
          <span v-else>-</span>
        </template>
      </el-table-column>
      <el-table-column label="报告" width="110">
        <template #default="{ row }">
          <el-tag v-if="row.report_filename" type="primary" size="small" effect="plain">已生成</el-tag>
          <span v-else class="no">未生成</span>
        </template>
      </el-table-column>
      <el-table-column label="原始结果" width="110" align="center">
        <template #default="{ row }">
          <el-badge v-if="row.attachment_count" :value="row.attachment_count" :max="99" type="primary">
            <el-button size="small" @click="openAttachments(row)">附件</el-button>
          </el-badge>
          <el-button v-else size="small" plain @click="openAttachments(row)" v-if="canCreate">+上传</el-button>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="280" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openEntry(row)" v-if="canCreate">录入</el-button>
          <el-button size="small" type="warning" @click="openReport(row)">报告管理</el-button>
          <el-button size="small" @click="openPlanEdit(row)" v-if="canEdit">编辑</el-button>
          <el-button size="small" type="danger" @click="onDeletePlan(row)" v-if="canEdit">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 计划对话框 -->
    <el-dialog v-model="planVisible" :title="editingPlan ? '编辑室间比对计划' : '新建室间比对计划'" width="560px">
      <el-form :model="planForm" label-width="96px">
        <el-form-item label="年份">
          <el-input-number v-model="planForm.year" :min="2000" :max="2100" />
        </el-form-item>
        <el-form-item label="半年">
          <el-radio-group v-model="planForm.half">
            <el-radio :value="1">上半年</el-radio>
            <el-radio :value="2">下半年</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="我室仪器">
          <el-select v-model="planForm.instrument_id" filterable placeholder="选择仪器" style="width:100%">
            <el-option v-for="i in instruments" :key="i.id" :label="i.name" :value="i.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="参比实验室">
          <el-input v-model="planForm.reference_lab" placeholder="如：某某医院检验科（可比较系统）" />
        </el-form-item>
        <el-form-item label="比较系统2仪器">
          <el-input v-model="planForm.compared_instrument2" placeholder="本实验室第二平台仪器名（若有2个平台），如：DxI800-线上3号机" />
        </el-form-item>
        <el-form-item label="比对日期">
          <el-date-picker v-model="planForm.compared_at" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item label="操作者">
          <UserSelect v-model="planForm.operator" />
        </el-form-item>
        <el-form-item label="审核者">
          <UserSelect v-model="planForm.reviewer" />
        </el-form-item>
        <el-form-item label="结论">
          <el-select v-model="planForm.conclusion" clearable placeholder="选择" style="width:100%">
            <el-option label="可接受" value="可接受" />
            <el-option label="不可接受" value="不可接受" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-radio-group v-model="planForm.status">
            <el-radio value="draft">进行中（未完）</el-radio>
            <el-radio value="done">已完成</el-radio>
          </el-radio-group>
          <div style="font-size:12px;color:#888;line-height:1.4;margin-top:2px">
            生成报告会自动置「已完成」；手动切回「进行中」后可重新录入/编辑。
          </div>
        </el-form-item>
        <el-form-item label="结果分析">
          <el-input v-model="planForm.summary" type="textarea" :rows="2"
            @input="summaryTouched = true" />
        </el-form-item>
        <el-form-item label="处理方案">
          <el-input v-model="planForm.handle_plan" type="textarea" :rows="2" placeholder="如不合格时的处理措施" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="planVisible = false">取消</el-button>
        <el-button type="primary" @click="savePlan" :loading="saving">保存</el-button>
      </template>
    </el-dialog>

    <!-- 结果录入对话框（5 水平） -->
    <el-dialog v-model="entryVisible" title="室间比对结果录入" width="90%" top="3vh">
      <div v-if="entryPlan">
        <el-alert type="info" :closable="false" show-icon style="margin-bottom:10px"
          :title="`${entryPlan.year}年${entryPlan.half === 1 ? '上半年' : '下半年'} ｜ 仪器：${instrumentName(entryPlan.instrument_id)} ｜ 参比实验室：${entryPlan.reference_lab || '—'}`" />
        <div style="margin-bottom:10px">
          <el-button size="small" type="primary" :icon="Plus" @click="addItemRow" v-if="canCreate">添加项目</el-button>
          <span class="tip">每个项目测 5 个水平。可比较系统=参比实验室，比较系统1=本实验室平台1，比较系统2=本实验室平台2（若有2个平台）。偏倚/符合自动计算。</span>
        </div>
        <!-- 逐项目分组展示 -->
        <div v-for="(item, idx) in entryRows" :key="idx" class="item-group">
          <div class="item-header">
            <div class="item-header-left">
              <el-select v-model="item.item" filterable allow-create default-first-option placeholder="检验项目"
                style="width:200px" @visible-change="(v)=>{ if(v) loadCandidates(entryPlan.instrument_id) }"
                @change="(val) => onItemSelect(idx, val)">
                <el-option v-for="p in candidates" :key="p.id" :label="p.name" :value="p.name">
                  <span v-if="p.mandatory" style="color:#c0392b">[必做]</span>{{ p.name }}
                </el-option>
              </el-select>
              <span style="margin-left:8px;">单位：<el-input v-model="item.unit" style="width:60px;display:inline-block" /></span>
              <span style="margin-left:8px;">TE：<el-input v-model="item.te" style="width:60px;display:inline-block" />%</span>
              <el-select v-model="item.mode" style="width:80px;margin-left:8px">
                <el-option label="相对%" value="relative" />
                <el-option label="绝对" value="absolute" />
              </el-select>
              <el-select v-model="item.kind" style="width:80px;margin-left:4px">
                <el-option label="定量" value="定量" />
                <el-option label="定性" value="定性" />
              </el-select>
            </div>
            <el-button size="small" type="danger" :icon="Delete" circle @click="entryRows.splice(idx, 1)" v-if="canCreate" />
          </div>
          <el-table :data="item.levels" border size="small">
            <el-table-column label="水平" width="50" fixed>
              <template #default="{ row: lv }">{{ lv.level_num }}</template>
            </el-table-column>

            <!-- 定量：比较系统1 / 比较系统2 分别计算偏倚与合格判定 -->
            <template v-if="item.kind === '定量'">
              <el-table-column label="参比值Y(可比较系统)" width="120">
                <template #default="{ row: lv }"><el-input v-model="lv.ref1_y1" /></template>
              </el-table-column>
              <el-table-column label="比较系统1值(本实验室)" width="120">
                <template #default="{ row: lv }"><el-input v-model="lv.our_value" /></template>
              </el-table-column>
              <el-table-column label="比较系统1偏倚" width="110">
                <template #default="{ row: lv }"><span :class="biasClass(lv, item)">{{ computeBias(lv, item) }}</span></template>
              </el-table-column>
              <el-table-column label="比较系统1状态" width="80">
                <template #default="{ row: lv }">
                  <el-tag v-if="biasPass(lv, item) === true" type="success" size="small">合格</el-tag>
                  <el-tag v-else-if="biasPass(lv, item) === false" type="danger" size="small">不合格</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="比较系统2值(本实验室)" width="120">
                <template #default="{ row: lv }"><el-input v-model="lv.ref2_y1" /></template>
              </el-table-column>
              <el-table-column label="比较系统2偏倚" width="110">
                <template #default="{ row: lv }"><span :class="biasClass2(lv, item)">{{ computeBias2(lv, item) }}</span></template>
              </el-table-column>
              <el-table-column label="比较系统2状态" width="80">
                <template #default="{ row: lv }">
                  <el-tag v-if="biasPass2(lv, item) === true" type="success" size="small">合格</el-tag>
                  <el-tag v-else-if="biasPass2(lv, item) === false" type="danger" size="small">不合格</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </template>

            <!-- 定性：比较系统1 / 比较系统2 分别与参比比较阴阳一致性 -->
            <template v-else>
              <el-table-column label="参比结果(可比较系统)" width="170">
                <template #default="{ row: lv }">
                  <div style="display:flex;gap:4px;align-items:center;">
                    <el-input :model-value="splitPn(lv.ref1_y1).val" placeholder="数值" style="width:80px;"
                      @update:model-value="v => setPn(lv, 'ref1_y1', 'val', v)" />
                    <el-select :model-value="splitPn(lv.ref1_y1).pn" placeholder="P/N" style="width:60px;"
                      @update:model-value="v => setPn(lv, 'ref1_y1', 'pn', v)">
                      <el-option label="P" value="P" />
                      <el-option label="N" value="N" />
                    </el-select>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="比较系统1(本实验室)" width="170">
                <template #default="{ row: lv }">
                  <div style="display:flex;gap:4px;align-items:center;">
                    <el-input :model-value="splitPn(lv.our_value).val" placeholder="数值" style="width:80px;"
                      @update:model-value="v => setPn(lv, 'our_value', 'val', v)" />
                    <el-select :model-value="splitPn(lv.our_value).pn" placeholder="P/N" style="width:60px;"
                      @update:model-value="v => setPn(lv, 'our_value', 'pn', v)">
                      <el-option label="P" value="P" />
                      <el-option label="N" value="N" />
                    </el-select>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="比较系统1符合" width="90">
                <template #default="{ row: lv }">
                  <el-tag v-if="pnMatch1(lv) === true" type="success" size="small">符合</el-tag>
                  <el-tag v-else-if="pnMatch1(lv) === false" type="danger" size="small">不符</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
              <el-table-column label="比较系统2(本实验室)" width="170">
                <template #default="{ row: lv }">
                  <div style="display:flex;gap:4px;align-items:center;">
                    <el-input :model-value="splitPn(lv.ref2_y1).val" placeholder="数值" style="width:80px;"
                      @update:model-value="v => setPn(lv, 'ref2_y1', 'val', v)" />
                    <el-select :model-value="splitPn(lv.ref2_y1).pn" placeholder="P/N" style="width:60px;"
                      @update:model-value="v => setPn(lv, 'ref2_y1', 'pn', v)">
                      <el-option label="P" value="P" />
                      <el-option label="N" value="N" />
                    </el-select>
                  </div>
                </template>
              </el-table-column>
              <el-table-column label="比较系统2符合" width="90">
                <template #default="{ row: lv }">
                  <el-tag v-if="pnMatch2(lv) === true" type="success" size="small">符合</el-tag>
                  <el-tag v-else-if="pnMatch2(lv) === false" type="danger" size="small">不符</el-tag>
                  <span v-else>-</span>
                </template>
              </el-table-column>
            </template>

            <el-table-column label="备注" min-width="120">
              <template #default="{ row: lv }"><el-input v-model="item.note" /></template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <template #footer>
        <el-button @click="entryVisible = false">关闭</el-button>
        <el-button type="primary" @click="saveEntry" :loading="saving" v-if="canCreate">保存结果</el-button>
      </template>
    </el-dialog>

    <!-- 报告管理对话框 -->
    <el-dialog v-model="reportVisible" :title="`报告管理 · ${reportPlan ? reportPlan.year + '年' + (reportPlan.half === 1 ? '上半年' : '下半年') + ' 室间比对' : ''}`" width="1000px" top="4vh">
      <div v-if="reportPlan">
        <el-descriptions :column="3" border size="small" style="margin-bottom:12px">
          <el-descriptions-item label="仪器（比较系统1）">{{ instrumentName(reportPlan.instrument_id) }}</el-descriptions-item>
          <el-descriptions-item label="参比实验室（可比较系统）">{{ reportPlan.reference_lab || '-' }}</el-descriptions-item>
          <el-descriptions-item label="比较系统2">{{ reportPlan.compared_instrument2 || '未填写' }}</el-descriptions-item>
          <el-descriptions-item label="比对日期">{{ reportPlan.compared_at || '-' }}</el-descriptions-item>
          <el-descriptions-item label="操作者">{{ reportPlan.operator || '-' }}</el-descriptions-item>
          <el-descriptions-item label="审核者">{{ reportPlan.reviewer || '-' }}</el-descriptions-item>
          <el-descriptions-item label="报告文件" :span="3">
            <span v-if="reportPlan.report_filename" class="yes">{{ reportPlan.report_filename }}</span>
            <span v-else class="no">未生成</span>
          </el-descriptions-item>
        </el-descriptions>

        <div class="rep-toolbar">
          <el-button :icon="View" @click="doPreview" :loading="previewing">预览</el-button>
          <el-button type="success" :icon="Document" @click="doGenerate" :loading="generating" v-if="canEdit">生成报告</el-button>
          <el-button :icon="Download" @click="doDownload" :disabled="!reportPlan || !reportPlan.report_filename">下载</el-button>
          <el-button :icon="Printer" @click="doPrint" :disabled="!previewHtml">打印</el-button>
          <el-upload :show-file-list="false" :auto-upload="true" :http-request="doUpload" v-if="canCreate">
            <el-button :icon="Upload">上传存档</el-button>
          </el-upload>
          <el-button type="danger" :icon="Delete" @click="doDeleteReport" :disabled="!reportPlan || !reportPlan.report_filename" v-if="canEdit">删除报告</el-button>
        </div>
        <div class="rep-preview" v-html="previewHtml" v-loading="previewing" />

        <el-divider content-position="left">原始报告存档</el-divider>
        <AttachmentList :plan-id="reportPlan.id" module="interlab" :can-write="canCreate" />
      </div>
    </el-dialog>

    <!-- 原始结果附件管理 -->
    <el-dialog v-model="attachVisible" :title="`原始结果 · ${activePlan?.year || ''} 半年${activePlan?.half === 2 ? '下' : '上'}半年`" width="900px" top="3vh">
      <AttachmentList v-if="activePlan" :plan-id="activePlan.id" module="interlab" :can-write="canCreate" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete, View, Document, Download, Printer, Upload } from '@element-plus/icons-vue'
import {
  interlabInstruments, interlabProjects, interlabMandatory, listInterlabPlans, createInterlabPlan,
  updateInterlabPlan, deleteInterlabPlan, getInterlabResults, saveInterlabResults,
  previewInterlabReport, generateInterlabReport, downloadInterlabReport,
  uploadInterlabReport, deleteInterlabReport,
} from '../../api/interlab'
import { useAuthStore } from '../../store/auth'
import { usePermissionStore } from '../../store/permission'
import UserSelect from '../../components/UserSelect.vue'
import AttachmentList from '../../components/AttachmentList.vue'

const auth = useAuthStore()
const perm = usePermissionStore()
// 新建/录入/上传 → interlab-create（admin/qc_manager/technical_support）
// 编辑/删除/生成报告 → interlab-edit（admin/qc_manager）
// 职工(member/staff) 仅可查看已生成报告，不能录入或改动。
const canCreate = computed(() => perm.canWrite(auth.myRoles, 'interlab-create'))
const canEdit = computed(() => perm.canWrite(auth.myRoles, 'interlab-edit'))

const instruments = ref([])
const plans = ref([])
const mandatory = ref([])
const filterYear = ref(null)
const filterHalf = ref(null)
const filterInstrument = ref(null)
const yearOptions = ref([])

const planVisible = ref(false)
const editingPlan = ref(null)
const saving = ref(false)
// 结果分析：用户手动改过后置 true，参比实验室联动不再覆盖
const summaryTouched = ref(false)
const planForm = reactive({
  year: new Date().getFullYear(), half: 1, instrument_id: null, reference_lab: '',
  compared_instrument2: '', compared_at: '', operator: '', reviewer: '', conclusion: '', summary: '', handle_plan: '',
  status: 'draft',
})

// 结果分析默认句（用户未改过时，随参比实验室联动）
function defaultSummary(refLab) {
  const lab = (refLab || '').trim() || '参比实验室'
  return `使用5例样本与${lab}进行室间比对，一致性可接受。`
}
// 监听参比实验室：用户未手动编辑时，自动更新结果分析默认句
watch(() => planForm.reference_lab, (v) => {
  if (!summaryTouched.value) planForm.summary = defaultSummary(v)
})

const entryVisible = ref(false)
const entryPlan = ref(null)
const entryRows = ref([])
const candidates = ref([])

const reportVisible = ref(false)
const reportPlan = ref(null)
const previewHtml = ref('')
const previewing = ref(false)
const generating = ref(false)

const attachVisible = ref(false)
const activePlan = ref(null)

const instrumentName = (id) => {
  const i = instruments.value.find((x) => x.id === id)
  return i ? i.name : (id ? `仪器${id}` : '—')
}

// ---- 5 水平辅助计算 ----
function parseNum(v) {
  const n = parseFloat(v)
  return isNaN(n) ? null : n
}
function computeBias(lv, item) {
  const our = parseNum(lv.our_value)
  const ref = parseNum(lv.ref1_y1)
  if (our === null || ref === null || ref === 0) return ''
  if (item.mode === 'absolute') return (our - ref).toFixed(3)
  return (((our - ref) / ref) * 100).toFixed(2) + '%'
}
function biasPass(lv, item) {
  const our = parseNum(lv.our_value)
  const ref = parseNum(lv.ref1_y1)
  const te = parseNum(item.te)
  if (our === null || ref === null || ref === 0 || te === null) return null
  if (item.mode === 'absolute') return Math.abs(our - ref) <= te + 1e-9
  return Math.abs((our - ref) / ref * 100) <= te + 1e-9
}
function biasClass(lv, item) {
  const p = biasPass(lv, item)
  if (p === true) return 'pass'
  if (p === false) return 'fail'
  return ''
}
// 比较系统2 偏倚/合格（相对/绝对，以可比较系统=参比 为基准）
function computeBias2(lv, item) {
  const sys2 = parseNum(lv.ref2_y1)
  const ref = parseNum(lv.ref1_y1)
  if (sys2 === null || ref === null || ref === 0) return ''
  if (item.mode === 'absolute') return (sys2 - ref).toFixed(3)
  return (((sys2 - ref) / ref) * 100).toFixed(2) + '%'
}
function biasPass2(lv, item) {
  const sys2 = parseNum(lv.ref2_y1)
  const ref = parseNum(lv.ref1_y1)
  const te = parseNum(item.te)
  if (sys2 === null || ref === null || ref === 0 || te === null) return null
  if (item.mode === 'absolute') return Math.abs(sys2 - ref) <= te + 1e-9
  return Math.abs((sys2 - ref) / ref * 100) <= te + 1e-9
}
function biasClass2(lv, item) {
  const p = biasPass2(lv, item)
  if (p === true) return 'pass'
  if (p === false) return 'fail'
  return ''
}
// 定性：把 "P(1.05)" / "N(1.05)" / "阳性(6.78)" / "阴性(1.05)" 拆成 {pn, val}
// 任意一边为空也安全（返回 {pn:'', val:原字符串} 或相反）。
function splitPn(s) {
  const t = String(s || '').trim()
  if (!t) return { pn: '', val: '' }
  const m = t.match(/^([PpNn]|[阳阴]性?)\s*\(\s*([^)]*?)\s*\)\s*$/)
  if (m) {
    const head = m[1].toUpperCase()
    let pn = ''
    if (head === 'P' || head === '阳' || head === '阳性' || head === '+') pn = 'P'
    else if (head === 'N' || head === '阴' || head === '阴性' || head === '-') pn = 'N'
    return { pn, val: m[2] || '' }
  }
  // 没匹配上：尝试从字符串前缀剥出 P/N/阳/阴
  const head2 = t.toUpperCase()
  if (/^P\+?$|^阳|^阳性|\+/.test(head2)) return { pn: 'P', val: t.replace(/^[Pp]|^阳(性)?|\+/, '').trim() }
  if (/^N-?$|^阴|^阴性|-/.test(head2)) return { pn: 'N', val: t.replace(/^[Nn]|^阴(性)?|-/, '').trim() }
  return { pn: '', val: t }
}

function joinPn(pn, val) {
  if (pn && val) return `${pn}(${val})`
  if (pn) return pn
  if (val) return val
  return ''
}

// 给定 lv 字段，把 pn / val 之一写回，组合成 "P(数值)" 存到原字段。
function setPn(lv, field, kind, v) {
  const cur = splitPn(lv[field])
  const next = kind === 'pn' ? { pn: v || '', val: cur.val } : { pn: cur.pn, val: v || '' }
  lv[field] = joinPn(next.pn, next.val)
}

// 定性：阴阳判定与符合
// 支持完整词和带括号/数值后缀的复合形式（"阴性(1.05)" / "阳性(6.78)" / "阴(+)" 等）。
function normPn(v) {
  const s = String(v || '').toUpperCase().trim()
  if (!s) return null
  const pos = ['阳', '阳性', 'POS', 'POSITIVE', 'P', '+', '1']
  const neg = ['阴', '阴性', 'NEG', 'NEGATIVE', 'N', '-', '0']
  if (pos.includes(s)) return 'positive'
  if (neg.includes(s)) return 'negative'
  // 前缀匹配：长前缀优先
  const prefixes = [
    ['阳性', 'positive'], ['POSITIVE', 'positive'], ['POS', 'positive'],
    ['阳', 'positive'], ['+', 'positive'], ['P', 'positive'],
    ['阴性', 'negative'], ['NEGATIVE', 'negative'], ['NEG', 'negative'],
    ['阴', 'negative'], ['-', 'negative'], ['N', 'negative'],
  ]
  for (const [tok, kind] of prefixes) {
    if (s.startsWith(tok)) return kind
  }
  return null
}
function pnMatch1(lv) {
  const a = normPn(lv.our_value)
  const b = normPn(lv.ref1_y1)
  if (a === null || b === null) return null
  return a === b
}
function pnMatch2(lv) {
  const a = normPn(lv.ref2_y1)
  const b = normPn(lv.ref1_y1)
  if (a === null || b === null) return null
  return a === b
}

function onItemSelect(idx, val) {
  const found = candidates.value.find(p => p.name === val)
  if (found && found.unit) {
    entryRows.value[idx].unit = found.unit
  }
}

function emptyLevels() {
  return [1, 2, 3, 4, 5].map(n => ({
    level_num: n, our_value: '',
    ref1_y1: '', ref1_y2: '', ref1_mean: '',
    ref2_y1: '', ref2_y2: '', ref2_mean: '',
  }))
}

async function loadInstruments() {
  try { instruments.value = await interlabInstruments() } catch (e) { instruments.value = [] }
}
async function loadMandatory() {
  try { mandatory.value = await interlabMandatory() } catch (e) { mandatory.value = [] }
}
async function reload() {
  const params = {}
  if (filterYear.value) params.year = filterYear.value
  if (filterHalf.value) params.half = filterHalf.value
  if (filterInstrument.value) params.instrument_id = filterInstrument.value
  const r = await listInterlabPlans(params)
  plans.value = r.items || []
  const yrs = new Set(plans.value.map((p) => p.year))
  yearOptions.value = Array.from(yrs).sort((a, b) => b - a)
}

function openPlanCreate() {
  editingPlan.value = null
  Object.assign(planForm, {
    year: new Date().getFullYear(), half: 1, instrument_id: null, reference_lab: '',
    compared_instrument2: '', compared_at: '', operator: '', reviewer: '', conclusion: '', summary: '', handle_plan: '',
    status: 'draft',
  })
  // 新建：结果分析填入默认句，标记未手动编辑（让 watch 随参比实验室联动）
  summaryTouched.value = false
  planForm.summary = defaultSummary(planForm.reference_lab)
  planVisible.value = true
}
function openPlanEdit(row) {
  editingPlan.value = row
  Object.assign(planForm, {
    year: row.year, half: row.half, instrument_id: row.instrument_id, reference_lab: row.reference_lab,
    compared_instrument2: row.compared_instrument2 || '',
    compared_at: row.compared_at, operator: row.operator, reviewer: row.reviewer,
    conclusion: row.conclusion, summary: row.summary, handle_plan: row.handle_plan,
    status: row.status || 'draft',
  })
  // 编辑：已存在 summary，标记为已手动编辑，避免 watch 覆盖
  summaryTouched.value = true
  planVisible.value = true
}
async function savePlan() {
  saving.value = true
  try {
    const payload = { ...planForm }
    if (editingPlan.value) {
      await updateInterlabPlan(editingPlan.value.id, payload)
      ElMessage.success('计划已更新')
    } else {
      await createInterlabPlan(payload)
      ElMessage.success('计划已创建')
    }
    planVisible.value = false
    await reload()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}
async function onDeletePlan(row) {
  try {
    await ElMessageBox.confirm(`确认删除 ${row.year}年${row.half === 1 ? '上半年' : '下半年'} 的室间比对计划？`, '警告', { type: 'warning' })
    await deleteInterlabPlan(row.id)
    ElMessage.success('已删除')
    await reload()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

async function openEntry(row) {
  entryPlan.value = row
  entryRows.value = []
  try {
    const r = await getInterlabResults(row.id)
    entryRows.value = (r.items || []).map((it) => ({
      item: it.item, unit: it.unit || '',
      te: it.te || '0', mode: it.mode || 'relative', kind: it.kind || '定量', note: it.note || '',
      levels: (it.levels && it.levels.length === 5)
        ? it.levels.map(l => ({ ...l }))
        : emptyLevels(),
    }))
  } catch (e) { /* ignore */ }
  entryVisible.value = true
}
function addItemRow() {
  entryRows.value.push({
    item: '', unit: '', te: '0', mode: 'relative', kind: '定量', note: '',
    levels: emptyLevels(),
  })
}
async function loadCandidates(instrumentId) {
  if (!instrumentId) return
  try { candidates.value = await interlabProjects(instrumentId) } catch (e) { candidates.value = [] }
}
async function saveEntry() {
  saving.value = true
  try {
    // 刷新每个水平的均值（前端可不传均值，服务端不依赖）
    const items = entryRows.value
      .filter(r => r.item)
      .map(r => ({
        item: r.item, unit: r.unit, te: r.te, mode: r.mode, kind: r.kind, note: r.note,
        levels: r.levels,
      }))
    await saveInterlabResults(entryPlan.value.id, { items })
    ElMessage.success('结果已保存')
    entryVisible.value = false
    await reload()
  } catch (e) {
    ElMessage.error('保存失败：' + (e.response?.data?.detail || e.message))
  } finally {
    saving.value = false
  }
}

function openReport(row) {
  reportPlan.value = row
  previewHtml.value = ''
  reportVisible.value = true
  if (row.report_filename) doPreview()
}
function openAttachments(row) {
  activePlan.value = row
  attachVisible.value = true
}
async function doPreview() {
  previewing.value = true
  try {
    const r = await previewInterlabReport(reportPlan.value.id)
    previewHtml.value = r.html
  } catch (e) {
    ElMessage.error('预览失败：' + (e.response?.data?.detail || e.message))
  } finally {
    previewing.value = false
  }
}
async function doGenerate() {
  generating.value = true
  try {
    const p = await generateInterlabReport(reportPlan.value.id)
    reportPlan.value = p
    ElMessage.success('报告已生成')
    await doPreview()
    await reload()
  } catch (e) {
    ElMessage.error('生成失败：' + (e.response?.data?.detail || e.message))
  } finally {
    generating.value = false
  }
}
function doPrint() {
  if (!previewHtml.value) { ElMessage.warning('请先预览'); return }
  const w = window.open('', '_blank')
  w.document.write('<!DOCTYPE html><html><head><meta charset="utf-8"></head><body>' + previewHtml.value + '</body></html>')
  w.document.close()
  setTimeout(() => { w.focus(); w.print() }, 300)
}
async function doDownload() {
  try {
    // request 拦截器已返回 response.data（即 Blob 本身），无需再取 .data
    const blob = await downloadInterlabReport(reportPlan.value.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = reportPlan.value.report_filename || '室间比对报告.docx'
    document.body.appendChild(a); a.click(); document.body.removeChild(a)
    URL.revokeObjectURL(url)
  } catch (e) { ElMessage.error('下载失败') }
}
async function doUpload(option) {
  try {
    const p = await uploadInterlabReport(reportPlan.value.id, option.file)
    reportPlan.value = p
    ElMessage.success('已上传存档')
    await reload()
  } catch (e) { ElMessage.error('上传失败：' + (e.response?.data?.detail || e.message)) }
}
async function doDeleteReport() {
  try {
    await ElMessageBox.confirm('确认删除已生成报告？', '警告', { type: 'warning' })
    const p = await deleteInterlabReport(reportPlan.value.id)
    reportPlan.value = p
    ElMessage.success('报告已删除')
    await reload()
  } catch (e) { if (e !== 'cancel') ElMessage.error('删除失败') }
}

onMounted(async () => {
  await loadInstruments()
  await loadMandatory()
  await reload()
})
</script>

<style scoped>
.interlab-page { padding: 4px; }
.toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 8px; }
.tip { font-size: 12px; color: #888; margin-left: 8px; }
.no { color: #c0392b; }
.guide-card { border: 1px solid #f0d9d9; }
.guide-title { font-weight: 700; color: #c0392b; }
.guide-sub { font-size: 12px; color: #888; margin-left: 8px; }
.rep-toolbar { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }
.rep-preview { border: 1px solid #ddd; border-radius: 4px; padding: 12px; min-height: 400px; max-height: 70vh; overflow: auto; background: #fff; }
.item-group { border: 1px solid #e4e7ed; border-radius: 4px; margin-bottom: 10px; }
.item-header { display: flex; justify-content: space-between; align-items: center; background: #f5f7fa; padding: 6px 10px; border-bottom: 1px solid #e4e7ed; }
.item-header-left { display: flex; align-items: center; flex-wrap: wrap; gap: 4px; }
.pass { color: #27ae60; font-weight: 700; }
.fail { color: #c0392b; font-weight: 700; }
</style>
