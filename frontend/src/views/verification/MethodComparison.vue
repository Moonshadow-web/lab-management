<template>
  <div class="mc">
    <div class="toolbar">
      <el-input v-model="q" placeholder="项目 / 仪器 / 批次" clearable style="width:220px" @keyup.enter="refresh" @clear="refresh" />
      <el-select v-model="batchFilter" placeholder="全部批次" clearable style="width:180px" @change="refresh">
        <el-option v-for="b in batchOptions" :key="b" :label="b" :value="b" />
      </el-select>
      <el-button type="primary" @click="refresh">查询</el-button>
      <div class="spacer" />
      <el-button :disabled="!canWrite" @click="openCreate">新增比对</el-button>
      <el-button @click="openSummary">汇总</el-button>
    </div>

    <el-table :data="rows" border stripe v-loading="loading" size="small">
      <el-table-column prop="project_name" label="项目" min-width="110" show-overflow-tooltip />
      <el-table-column label="类型" width="80" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.compare_type === 'qualitative' ? 'warning' : 'info'">
            {{ row.compare_type === 'qualitative' ? '定性' : '定量' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="batch_name" label="批次" min-width="120" show-overflow-tooltip />
      <el-table-column label="方法A（现行）" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.ref_instrument || '—' }}</template>
      </el-table-column>
      <el-table-column label="方法B（新）" min-width="140" show-overflow-tooltip>
        <template #default="{ row }">{{ row.test_instrument || '—' }}</template>
      </el-table-column>
      <el-table-column prop="sample_count" label="计划例数" width="90" align="center" />
      <el-table-column prop="compare_date" label="比对日期" width="130" show-overflow-tooltip />
      <el-table-column label="有效例数" width="90" align="center">
        <template #default="{ row }">{{ row.result_summary?.n_used ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="比例偏移 / 符合率" width="130" align="center">
        <template #default="{ row }">
          <span v-if="row.compare_type === 'qualitative' && row.result_summary?.total_rate != null" style="color:#1a365d">
            总符合 {{ row.result_summary.total_rate.toFixed(1) }}%
          </span>
          <span v-else-if="row.result_summary?.proportional_bias_pct != null"
                :style="{ color: Math.abs(row.result_summary.proportional_bias_pct) > 5 ? '#c00000' : '#303133' }">
            {{ row.result_summary.proportional_bias_pct > 0 ? '+' : '' }}{{ row.result_summary.proportional_bias_pct.toFixed(2) }}%
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="是否一致" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.result_summary?.valid" :type="(row.compare_type === 'qualitative' ? row.result_summary?.acceptable : row.result_summary?.ba_consistent) ? 'success' : 'danger'" size="small">
            {{ (row.compare_type === 'qualitative' ? row.result_summary?.acceptable : row.result_summary?.ba_consistent) ? '一致' : '不一致' }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="能否直接替换" width="110" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.result_summary?.valid" :type="row.result_summary?.can_replace ? 'success' : 'warning'" size="small">
            {{ row.result_summary?.can_replace ? '能' : '否' }}
          </el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="报告" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.report_file_path" type="success" size="small">已生成</el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right" align="center">
        <template #default="{ row }">
          <el-button link type="primary" size="small" @click="showDetail(row)">详情</el-button>
          <el-button link type="primary" size="small" :disabled="!canWrite" @click="openEdit(row)">编辑</el-button>
          <el-button link type="primary" size="small" @click="doCompute(row)">计算</el-button>
          <el-button link type="primary" size="small" @click="doGenerate(row)">生成报告</el-button>
          <el-button v-if="row.report_file_path" link type="primary" size="small" @click="doDownload(row)">下载</el-button>
          <el-button link type="danger" size="small" :disabled="!canWrite" @click="doDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="editOpen" :title="form.id ? '编辑方法学比对' : '新增方法学比对'" width="1080px" top="5vh">
      <el-tabs v-model="editTab">
        <el-tab-pane label="基本信息" name="info">
          <el-form :model="form" label-width="110px" size="small">
            <el-divider content-position="left">项目与方案</el-divider>
            <el-row :gutter="12">
              <el-col :span="24">
                <el-form-item label="比对类型">
                  <el-radio-group v-model="form.compare_type">
                    <el-radio value="quantitative">定量项目（EP9-A3：Deming / Passing-Bablok / Bland-Altman）</el-radio>
                    <el-radio value="qualitative">定性项目（符合率法：阳性/阴性符合率 + Kappa）</el-radio>
                  </el-radio-group>
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="项目名称"><el-input v-model="form.project_name" placeholder="如 C肽" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="报告单位"><el-input v-model="form.unit" placeholder="如 ug/L" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="批次（汇总）"><el-input v-model="form.batch_name" placeholder="如 2025.10 贝克曼比对" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="计划样本数">
                  <el-select v-model="form.sample_count" style="width:100%" @change="resizeSamples">
                    <el-option :value="20" label="20 例" />
                    <el-option :value="40" label="40 例（推荐）" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="允许总误差 TEa"><el-input v-model="form.tea" placeholder="如 10（%）" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="比对日期"><el-input v-model="form.compare_date" placeholder="如 2025.10.28-10.29" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="样本来源"><el-input v-model="form.sample_source" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="报告人"><el-input v-model="form.operator" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="审核人"><el-input v-model="form.reviewer" /></el-form-item></el-col>
            </el-row>

            <el-divider content-position="left">方法A（现行 / 参照）</el-divider>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="仪器"><el-input v-model="form.ref_instrument" placeholder="贝克曼DXI800" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="厂家"><el-input v-model="form.ref_manufacturer" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="试剂"><el-input v-model="form.ref_reagent" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="试剂批号"><el-input v-model="form.ref_reagent_lot" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="校准品"><el-input v-model="form.ref_calibrator" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="校准批号"><el-input v-model="form.ref_calibrator_lot" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="参考区间下限"><el-input v-model="form.ref_range_low" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="参考区间上限"><el-input v-model="form.ref_range_high" /></el-form-item></el-col>
            </el-row>

            <el-divider content-position="left">方法B（新方法 / 待评）</el-divider>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="仪器"><el-input v-model="form.test_instrument" placeholder="迈瑞CL-6000i" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="厂家"><el-input v-model="form.test_manufacturer" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="试剂"><el-input v-model="form.test_reagent" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="试剂批号"><el-input v-model="form.test_reagent_lot" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="校准品"><el-input v-model="form.test_calibrator" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="校准批号"><el-input v-model="form.test_calibrator_lot" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="参考区间下限"><el-input v-model="form.test_range_low" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="参考区间上限"><el-input v-model="form.test_range_high" /></el-form-item></el-col>
            </el-row>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="`样本数据（${filledCount}/${form.sample_count}）`" name="data">
          <div class="paste-bar">
            <span class="tip">可从 Excel 直接复制两列（A值、B值）粘贴到下方框，自动按行填入：</span>
            <el-input v-model="pasteText" type="textarea" :rows="3" placeholder="1.42	1.72&#10;2.32	2.99" style="margin:8px 0" />
            <el-button size="small" type="primary" @click="applyPaste">解析并填入</el-button>
            <el-button size="small" @click="pasteText=''">清空</el-button>
            <el-button size="small" @click="clearSamples">清空样本数据</el-button>
          </div>
          <el-table :data="samples" border size="small" height="360">
            <el-table-column prop="no" label="样本号" width="80" align="center" />
            <el-table-column label="方法A 结果" width="180">
              <template #default="{ row }">
                <el-select v-if="form.compare_type === 'qualitative'" v-model="row.a" size="small" clearable placeholder="阳性/阴性" style="width:100%">
                  <el-option label="阳性" value="阳性" /><el-option label="阴性" value="阴性" />
                </el-select>
                <el-input v-else v-model="row.a" size="small" placeholder="A" />
              </template>
            </el-table-column>
            <el-table-column label="方法B 结果" width="180">
              <template #default="{ row }">
                <el-select v-if="form.compare_type === 'qualitative'" v-model="row.b" size="small" clearable placeholder="阳性/阴性" style="width:100%">
                  <el-option label="阳性" value="阳性" /><el-option label="阴性" value="阴性" />
                </el-select>
                <el-input v-else v-model="row.b" size="small" placeholder="B" />
              </template>
            </el-table-column>
            <el-table-column v-if="form.compare_type === 'quantitative'" label="绝对偏差（实时）" width="140" align="center">
              <template #default="{ row }">{{ liveDiff(row).d }}</template>
            </el-table-column>
            <el-table-column v-if="form.compare_type === 'quantitative'" label="相对偏差（实时）" align="center">
              <template #default="{ row }">{{ liveDiff(row).p }}</template>
            </el-table-column>
            <el-table-column v-else label="是否一致（实时）" align="center">
              <template #default="{ row }">
                <el-tag v-if="row.a && row.b" :type="row.a === row.b ? 'success' : 'danger'" size="small">
                  {{ row.a === row.b ? '一致' : '不一致' }}
                </el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="editOpen=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-dialog v-model="detailOpen" title="方法学比对结果" width="980px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="项目">{{ detail.project_name }}</el-descriptions-item>
          <el-descriptions-item label="方法A">{{ detail.ref_instrument || '—' }}</el-descriptions-item>
          <el-descriptions-item label="方法B">{{ detail.test_instrument || '—' }}</el-descriptions-item>
          <el-descriptions-item label="计划例数">{{ detail.sample_count }}</el-descriptions-item>
          <el-descriptions-item label="有效例数">{{ detail.result_summary?.n_used ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="离群值">{{ (detail.result_summary?.outliers || []).join('、') || '无' }}</el-descriptions-item>
          <el-descriptions-item label="TEa %">{{ detail.tea || '—' }}</el-descriptions-item>
          <el-descriptions-item label="比例偏移">
            {{ detail.result_summary?.proportional_bias_pct != null
              ? (detail.result_summary.proportional_bias_pct > 0 ? '+' : '') + detail.result_summary.proportional_bias_pct.toFixed(2) + '%'
              : '—' }}
          </el-descriptions-item>
          <el-descriptions-item label="系统偏移">{{ detail.result_summary?.systematic_bias || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="detailSummaryRows" border size="small" style="margin-top:12px">
          <el-table-column prop="k" label="指标" width="200" />
          <el-table-column prop="v" label="结果" />
        </el-table>

        <div class="concl">
          <div class="concl-title">比对结论</div>
          <div v-for="(line, i) in (detail.result_summary?.conclusion_lines || [])" :key="i" class="concl-line">{{ i + 1 }}. {{ line }}</div>
          <div v-if="!detail.result_summary?.conclusion_lines?.length" class="concl-line">尚未计算，请先点「计算」</div>
        </div>
      </template>
    </el-dialog>

    <!-- 汇总 -->
    <el-dialog v-model="summaryOpen" title="方法学比对汇总" width="1180px" top="5vh">
      <div class="toolbar">
        <el-select v-model="summaryBatch" placeholder="按批次汇总（留空=全部）" clearable style="width:260px" @change="loadSummary">
          <el-option v-for="b in batchOptions" :key="b" :label="b" :value="b" />
        </el-select>
        <el-button @click="loadSummary">刷新</el-button>
        <div class="spacer" />
        <el-button type="primary" :loading="summaryLoading" @click="doSummaryDownload">下载汇总报告</el-button>
      </div>
      <el-table :data="summaryRows" border size="small" max-height="460">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="project_name" label="项目" min-width="100" />
        <el-table-column prop="systematic_bias" label="系统偏移" width="110" />
        <el-table-column label="比例偏移" width="90" align="center">
          <template #default="{ row }">{{ row.proportional_bias_pct != null ? (row.proportional_bias_pct > 0 ? '+' : '') + row.proportional_bias_pct.toFixed(2) + '%' : '—' }}</template>
        </el-table-column>
        <el-table-column label="能否接受" width="90" align="center">
          <template #default="{ row }">{{ row.acceptable === true ? '是' : row.acceptable === false ? '否' : '—' }}</template>
        </el-table-column>
        <el-table-column prop="ba_p" label="P值" width="90" align="center" />
        <el-table-column label="是否一致" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.valid" :type="row.ba_consistent ? 'success' : 'danger'" size="small">{{ row.ba_consistent ? '是' : '否' }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
        <el-table-column label="95%界限内最大差值" width="150" align="center">
          <template #default="{ row }">{{ row.ba_max_abs_within ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="能否直接替换" width="120" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.valid" :type="row.can_replace ? 'success' : 'warning'" size="small">{{ row.can_replace ? '能' : '否' }}</el-tag>
            <span v-else>—</span>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listMethodComparisons, createMethodComparison, updateMethodComparison, deleteMethodComparison,
  computeMethodComparison, generateMethodComparison, downloadMethodComparison,
  summaryMethodComparisons, downloadMethodComparisonSummary,
} from '../../api/methodComparison'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite ? auth.canWrite('verification') : true)

const rows = ref([])
const loading = ref(false)
const q = ref('')
const batchFilter = ref('')

const editOpen = ref(false)
const editTab = ref('info')
const saving = ref(false)
const samples = ref([])
const pasteText = ref('')

const detailOpen = ref(false)
const detail = ref(null)

const summaryOpen = ref(false)
const summaryBatch = ref('')
const summaryRows = ref([])
const summaryLoading = ref(false)

const blankForm = () => ({
  id: null, batch_name: '', compare_type: 'quantitative', project_name: '', project_method: '', unit: '',
  ref_instrument: '', ref_manufacturer: '', ref_reagent: '', ref_reagent_lot: '',
  ref_calibrator: '', ref_calibrator_lot: '', ref_range_low: '', ref_range_high: '',
  test_instrument: '', test_manufacturer: '', test_reagent: '', test_reagent_lot: '',
  test_calibrator: '', test_calibrator_lot: '', test_range_low: '', test_range_high: '',
  sample_count: 40, sample_source: '临床检测剩余血清样本', tea: '', scheme: 'EP9-A3',
  compare_date: '', operator: '', reviewer: '',
})
const form = ref(blankForm())

const batchOptions = computed(() => [...new Set(rows.value.map(r => r.batch_name).filter(Boolean))])
const filledCount = computed(() => samples.value.filter(s => String(s.a ?? '').trim() !== '' && String(s.b ?? '').trim() !== '').length)

const detailSummaryRows = computed(() => {
  const rs = detail.value?.result_summary || {}
  if (!rs.valid) return [{ k: '状态', v: rs.message || '未计算' }]
  const f = (v, n = 4) => (v == null ? '—' : Number(v).toFixed(n))
  if (rs.compare_type === 'qualitative') {
    return [
      { k: '纳入统计样本数', v: rs.n_used },
      { k: '2×2 列联表（TP/FN/FP/TN）', v: `${rs.tp} / ${rs.fn} / ${rs.fp} / ${rs.tn}` },
      { k: '阳性符合率', v: rs.ppa != null ? `${rs.ppa}%` : '—' },
      { k: '阴性符合率', v: rs.npa != null ? `${rs.npa}%` : '—' },
      { k: '总符合率', v: rs.total_rate != null ? `${rs.total_rate}%` : '—' },
      { k: 'Kappa 值', v: f(rs.kappa, 3) },
      { k: '一致性强度', v: rs.kappa_text || '—' },
      { k: '不一致样本数', v: rs.inconsistent_count ?? '—' },
      { k: '是否可接受', v: rs.acceptable ? '是' : '否' },
      { k: '能否直接替换', v: rs.can_replace ? '能' : '否' },
    ]
  }
  return [
    { k: '纳入统计样本数', v: rs.n_used },
    { k: '离群值说明', v: rs.outlier_text || '—' },
    { k: 'Deming 回归', v: '见报告（斜率/截距及 95%CI）' },
    { k: 'Passing-Bablok 斜率', v: f(rs.slope, 6) },
    { k: 'Passing-Bablok 截距', v: f(rs.intercept, 6) },
    { k: '比例偏移', v: rs.proportional_bias_pct != null ? `${rs.proportional_bias_pct.toFixed(2)}%` : '—' },
    { k: '系统偏移', v: rs.systematic_bias || '—' },
    { k: 'Pearson r', v: f(rs.pearson_r, 4) },
    { k: 'Bland-Altman P 值', v: rs.ba_p || '—' },
    { k: 'Bland-Altman 一致', v: rs.ba_consistent ? '是' : '否' },
    { k: '95% 界限内最大差值', v: rs.ba_max_abs_within ?? '—' },
    { k: '平均偏倚（%）', v: rs.bias_pct != null ? `${rs.bias_pct}%` : '—' },
    { k: '能否直接替换', v: rs.can_replace ? '能' : '否' },
  ]
})

function liveDiff(row) {
  const a = parseFloat(row.a), b = parseFloat(row.b)
  if (!isFinite(a) || !isFinite(b)) return { d: '—', p: '—' }
  const d = b - a
  return { d: d.toFixed(3), p: a ? `${(d / a * 100).toFixed(2)}%` : '—' }
}

function resizeSamples() {
  const n = Number(form.value.sample_count) || 0
  const cur = samples.value
  const next = []
  for (let i = 0; i < n; i++) next.push(cur[i] || { no: i + 1, a: '', b: '' })
  samples.value = next
}

async function refresh() {
  loading.value = true
  try {
    const params = { page: 1, page_size: 300 }
    if (q.value) params.q = q.value
    if (batchFilter.value) params.batch_name = batchFilter.value
    const res = await listMethodComparisons(params)
    rows.value = res.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

function openCreate() {
  form.value = blankForm()
  samples.value = []
  resizeSamples()
  pasteText.value = ''
  editTab.value = 'info'
  editOpen.value = true
}

function openEdit(row) {
  form.value = { ...blankForm(), ...row }
  const src = Array.isArray(row.pairs) ? row.pairs : []
  samples.value = src.length
    ? src.map((p, i) => ({ no: p.no ?? i + 1, a: p.a ?? '', b: p.b ?? '' }))
    : []
  resizeSamples()
  pasteText.value = ''
  editTab.value = 'info'
  editOpen.value = true
}

function applyPaste() {
  const lines = String(pasteText.value || '').split(/\r?\n/).filter(l => l.trim())
  let i = 0, ok = 0
  for (const line of lines) {
    const cols = line.split(/\t|,|\s{2,}|;/).map(s => s.trim()).filter(s => s !== '')
    if (!cols.length) continue
    let a, b
    if (cols.length >= 3) { a = cols[1]; b = cols[2] } else if (cols.length === 2) { a = cols[0]; b = cols[1] } else continue
    if (i >= samples.value.length) samples.value.push({ no: i + 1, a: '', b: '' })
    samples.value[i].a = a
    samples.value[i].b = b
    i++; ok++
  }
  ElMessage.success(`已填入 ${ok} 行`)
}

function clearSamples() {
  samples.value.forEach(s => { s.a = ''; s.b = '' })
}

async function save() {
  if (!form.value.project_name) return ElMessage.warning('请填写项目名称')
  const pairs = samples.value
    .map((s, i) => ({ no: s.no ?? i + 1, a: String(s.a ?? '').trim(), b: String(s.b ?? '').trim() }))
    .filter(p => p.a !== '' || p.b !== '')
  if (pairs.length < 3) return ElMessage.warning('至少录入 3 例有效样本（A、B 两侧都要有值）')
  saving.value = true
  try {
    const payload = { ...form.value, pairs }
    delete payload.created_at; delete payload.updated_at; delete payload.result_summary; delete payload.report_file_path
    let saved
    if (form.value.id) saved = await updateMethodComparison(form.value.id, payload)
    else saved = await createMethodComparison(payload)
    editOpen.value = false
    ElMessage.success('已保存，正在计算…')
    if (saved?.id) {
      try { await computeMethodComparison(saved.id) } catch (e) { ElMessage.warning('计算未通过：' + (e?.response?.data?.detail || e.message)) }
    }
    await refresh()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function showDetail(row) {
  detail.value = row
  detailOpen.value = true
}

async function doCompute(row) {
  try {
    const res = await computeMethodComparison(row.id)
    ElMessage.success(`计算完成：有效 ${res.result_summary?.n_used} 例`)
    await refresh()
    if (detail.value?.id === row.id) detail.value = res
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '计算失败')
  }
}

async function doGenerate(row) {
  try {
    await generateMethodComparison(row.id)
    ElMessage.success('报告已生成')
    await refresh()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '生成失败')
  }
}

async function doDownload(row) {
  try {
    const data = await downloadMethodComparison(row.id)
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.project_name || '项目'}_方法学比对报告.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function doDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.project_name}」的比对记录？`, '提示', { type: 'warning' })
    await deleteMethodComparison(row.id)
    ElMessage.success('已删除')
    await refresh()
  } catch (e) { /* 取消 */ }
}

async function openSummary() {
  summaryOpen.value = true
  if (batchFilter.value) summaryBatch.value = batchFilter.value
  await loadSummary()
}

async function loadSummary() {
  summaryLoading.value = true
  try {
    const params = summaryBatch.value ? { batch: summaryBatch.value } : {}
    const res = await summaryMethodComparisons(params)
    summaryRows.value = res.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '汇总加载失败')
  } finally {
    summaryLoading.value = false
  }
}

async function doSummaryDownload() {
  summaryLoading.value = true
  try {
    const params = summaryBatch.value ? { batch: summaryBatch.value } : {}
    const data = await downloadMethodComparisonSummary(params)
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `方法学比对汇总_${summaryBatch.value || '全部'}.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('汇总下载失败')
  } finally {
    summaryLoading.value = false
  }
}

onMounted(refresh)
</script>

<style scoped>
.mc { padding: 4px 0; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.spacer { flex: 1; }
.paste-bar { margin-bottom: 8px; }
.paste-bar .tip { font-size: 12px; color: #909399; }
.concl { margin-top: 14px; padding: 12px 14px; background: #f7f9fc; border: 1px solid #e4e7ed; border-radius: 6px; }
.concl-title { font-weight: 600; margin-bottom: 6px; color: #1a365d; }
.concl-line { font-size: 13px; line-height: 1.8; color: #303133; }
</style>
