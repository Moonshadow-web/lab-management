<template>
  <div class="sc">
    <div class="toolbar">
      <el-input v-model="q" placeholder="项目 / 标本类型 / 批次" clearable style="width:230px" @keyup.enter="refresh" @clear="refresh" />
      <el-select v-model="batchFilter" placeholder="全部批次" clearable style="width:180px" @change="refresh">
        <el-option v-for="b in batchOptions" :key="b" :label="b" :value="b" />
      </el-select>
      <el-button type="primary" @click="refresh">查询</el-button>
      <div class="spacer" />
      <el-button :disabled="!canWrite" @click="openCreate">新增验证</el-button>
      <el-button @click="openSummary">汇总</el-button>
    </div>

    <div class="tips">
      判定依据 CNAS-CL02:2023 7.3.7.4：允许偏倚取 <b>1/2 TEa</b>，达到允许偏倚的样本比例 <b>≥80%</b> 判为可比；
      定量项目有效样本不少于 5 例（常规建议 20 例）。斜率与相关系数仅作展示。
    </div>

    <el-table :data="rows" border stripe v-loading="loading" size="small">
      <el-table-column prop="project_name" label="项目" min-width="110" show-overflow-tooltip />
      <el-table-column label="标本类型" min-width="200" show-overflow-tooltip>
        <template #default="{ row }">{{ row.specimen_a }} vs {{ row.specimen_b }}</template>
      </el-table-column>
      <el-table-column label="验证类型" width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ typeText(row.verify_type) }}</template>
      </el-table-column>
      <el-table-column prop="sample_count" label="计划例数" width="90" align="center" />
      <el-table-column label="有效例数" width="90" align="center">
        <template #default="{ row }">{{ row.result_summary?.n_used ?? '—' }}</template>
      </el-table-column>
      <el-table-column label="允许偏倚" width="95" align="center">
        <template #default="{ row }">
          {{ row.result_summary?.allow_bias != null ? '±' + row.result_summary.allow_bias + '%' : '—' }}
        </template>
      </el-table-column>
      <el-table-column label="达标率" width="95" align="center">
        <template #default="{ row }">
          <span v-if="row.result_summary?.pass_rate != null"
                :style="{ color: row.result_summary.pass_rate >= 80 ? '#1a7f37' : '#c00000' }">
            {{ row.result_summary.pass_rate.toFixed(1) }}%
          </span>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="平均偏倚" width="95" align="center">
        <template #default="{ row }">
          {{ row.result_summary?.mean_bias_pct != null ? (row.result_summary.mean_bias_pct > 0 ? '+' : '') + row.result_summary.mean_bias_pct.toFixed(2) + '%' : '—' }}
        </template>
      </el-table-column>
      <el-table-column label="判定" width="90" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.result_summary?.verdict === true" type="success" size="small">可比</el-tag>
          <el-tag v-else-if="row.result_summary?.verdict === false" type="danger" size="small">不可比</el-tag>
          <el-tag v-else-if="row.result_summary?.valid" type="info" size="small">待定</el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="报告" width="80" align="center">
        <template #default="{ row }">
          <el-tag v-if="row.report_file_path" type="success" size="small">已生成</el-tag>
          <span v-else>—</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="250" fixed="right" align="center">
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
    <el-dialog v-model="editOpen" :title="form.id ? '编辑样本类型可比性验证' : '新增样本类型可比性验证'" width="1060px" top="5vh">
      <el-tabs v-model="editTab">
        <el-tab-pane label="基本信息" name="info">
          <el-form :model="form" label-width="112px" size="small">
            <el-divider content-position="left">项目与方案</el-divider>
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="项目名称"><el-input v-model="form.project_name" placeholder="如 葡萄糖" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="报告单位"><el-input v-model="form.unit" placeholder="如 mmol/L" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="批次（汇总）"><el-input v-model="form.batch_name" placeholder="如 2026.10 标本类型验证" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-form-item label="验证类型">
                  <el-select v-model="form.verify_type" style="width:100%" @change="onTypeChange">
                    <el-option label="血清 vs 血浆" value="serum_vs_plasma" />
                    <el-option label="血浆-肝素 vs 血浆-EDTA" value="plasma_anticoagulant" />
                    <el-option label="不同采血管" value="different_tube" />
                    <el-option label="不同放置时间" value="standing_time" />
                    <el-option label="其他（自定义）" value="other" />
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="8">
                <el-form-item label="计划例数">
                  <el-input-number v-model="form.sample_count" :min="3" :max="200" style="width:100%" @change="resizeSamples" />
                </el-form-item>
              </el-col>
              <el-col :span="8"><el-form-item label="允许总误差 TEa"><el-input v-model="form.tea" placeholder="如 10（%，留空自动取质量库）" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="标本类型 A"><el-input v-model="form.specimen_a" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="标本类型 B"><el-input v-model="form.specimen_b" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="验证日期"><el-input v-model="form.verify_date" placeholder="如 2026-10-28" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="检测仪器"><el-input v-model="form.instrument" /></el-form-item></el-col>
            </el-row>

            <el-divider content-position="left">采集与处理条件（评审必查）</el-divider>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="采血管 A"><el-input v-model="form.tube_a" placeholder="品牌/型号" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="采血管 B"><el-input v-model="form.tube_b" placeholder="品牌/型号" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="离心条件"><el-input v-model="form.centrifuge" placeholder="如 3000rpm×10min" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="放置条件"><el-input v-model="form.storage" placeholder="如 室温 2h 内上机" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="样本来源"><el-input v-model="form.sample_source" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="报告人"><el-input v-model="form.operator" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="审核人"><el-input v-model="form.reviewer" /></el-form-item></el-col>
            </el-row>
            <el-row :gutter="12">
              <el-col :span="6"><el-form-item label="参考区间下限"><el-input v-model="form.ref_range_low" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="参考区间上限"><el-input v-model="form.ref_range_high" /></el-form-item></el-col>
            </el-row>
          </el-form>
        </el-tab-pane>

        <el-tab-pane :label="`样本数据（${filledCount}/${form.sample_count}）`" name="data">
          <div class="paste-bar">
            <span class="tip">可从 Excel 直接复制两列（A 值、B 值）粘贴，自动按行填入：</span>
            <el-input v-model="pasteText" type="textarea" :rows="3" placeholder="1.42	1.45&#10;2.32	2.30" style="margin:8px 0" />
            <el-button size="small" type="primary" @click="applyPaste">解析并填入</el-button>
            <el-button size="small" @click="pasteText=''">清空</el-button>
            <el-button size="small" @click="clearSamples">清空样本数据</el-button>
          </div>
          <el-table :data="samples" border size="small" height="360">
            <el-table-column prop="no" label="样本号" width="80" align="center" />
            <el-table-column :label="`A：${form.specimen_a || '标本A'}`" width="170">
              <template #default="{ row }"><el-input v-model="row.a" size="small" placeholder="A" /></template>
            </el-table-column>
            <el-table-column :label="`B：${form.specimen_b || '标本B'}`" width="170">
              <template #default="{ row }"><el-input v-model="row.b" size="small" placeholder="B" /></template>
            </el-table-column>
            <el-table-column label="绝对偏差" width="120" align="center">
              <template #default="{ row }">{{ liveDiff(row).d }}</template>
            </el-table-column>
            <el-table-column label="相对偏差" width="120" align="center">
              <template #default="{ row }">{{ liveDiff(row).p }}</template>
            </el-table-column>
            <el-table-column label="是否在允许偏倚内" align="center">
              <template #default="{ row }">
                <el-tag v-if="liveDiff(row).pass === true" type="success" size="small">是</el-tag>
                <el-tag v-else-if="liveDiff(row).pass === false" type="danger" size="small">否</el-tag>
                <span v-else>—</span>
              </template>
            </el-table-column>
          </el-table>
          <div class="tip" style="margin-top:6px">
            允许偏倚按 1/2 TEa 计算；TEa 留空时由系统从质量要求库自动带出（计算时生效）。
          </div>
        </el-tab-pane>
      </el-tabs>

      <template #footer>
        <el-button @click="editOpen=false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 详情 -->
    <el-dialog v-model="detailOpen" title="样本类型可比性验证结果" width="980px" top="5vh">
      <template v-if="detail">
        <el-descriptions :column="3" border size="small">
          <el-descriptions-item label="项目">{{ detail.project_name }}</el-descriptions-item>
          <el-descriptions-item label="标本类型">{{ detail.specimen_a }} vs {{ detail.specimen_b }}</el-descriptions-item>
          <el-descriptions-item label="验证类型">{{ typeText(detail.verify_type) }}</el-descriptions-item>
          <el-descriptions-item label="计划例数">{{ detail.sample_count }}</el-descriptions-item>
          <el-descriptions-item label="有效例数">{{ detail.result_summary?.n_used ?? '—' }}</el-descriptions-item>
          <el-descriptions-item label="允许偏倚">
            {{ detail.result_summary?.allow_bias != null ? '±' + detail.result_summary.allow_bias + '%（1/2 TEa）' : '未设置' }}
          </el-descriptions-item>
          <el-descriptions-item label="检测仪器">{{ detail.instrument || '—' }}</el-descriptions-item>
          <el-descriptions-item label="离心条件">{{ detail.centrifuge || '—' }}</el-descriptions-item>
          <el-descriptions-item label="放置条件">{{ detail.storage || '—' }}</el-descriptions-item>
        </el-descriptions>

        <el-table :data="detailRows" border size="small" style="margin-top:12px">
          <el-table-column prop="k" label="指标" width="230" />
          <el-table-column prop="v" label="结果" />
        </el-table>

        <div class="read-note">
          <b>判定说明：</b>按 CNAS-CL02:2023 7.3.7.4，允许偏倚取 1/2 TEa（TEa 依 WS/T 403-2024），
          达到允许偏倚的样本比例 ≥80%（“5 份中至少 4 份”）判为可比；定量项目有效样本不少于 5 例。
          Passing-Bablok 斜率与相关系数 r 仅作展示，不参与判定。
        </div>

        <div class="concl">
          <div class="concl-title">验证结论</div>
          <div v-for="(line, i) in detailConclusionLines" :key="i" class="concl-line">{{ i + 1 }}. {{ line }}</div>
          <div v-if="!detail.result_summary?.conclusion_lines?.length" class="concl-line">尚未计算，请先点「计算」</div>
        </div>

        <div class="charts" v-loading="chartsLoading">
          <div class="charts-title">图表</div>
          <div v-if="detailCharts.length" class="chart-grid">
            <div v-for="c in detailCharts" :key="c.key" class="chart-item">
              <img :src="'data:image/png;base64,' + c.png" class="chart-img" />
              <div class="chart-cap">{{ chartCaption(c.key) }}</div>
            </div>
          </div>
          <div v-else-if="!chartsLoading" class="chart-empty">暂无图表（请先点「计算」）</div>
        </div>
      </template>
    </el-dialog>

    <!-- 汇总 -->
    <el-dialog v-model="summaryOpen" title="样本类型可比性验证汇总" width="1180px" top="5vh">
      <div class="toolbar">
        <el-select v-model="summaryBatch" placeholder="按批次汇总（留空=全部）" clearable style="width:260px" @change="loadSummary">
          <el-option v-for="b in batchOptions" :key="b" :label="b" :value="b" />
        </el-select>
        <el-button @click="loadSummary">刷新</el-button>
      </div>
      <el-table :data="summaryRows" border size="small" max-height="480">
        <el-table-column type="index" label="序号" width="60" align="center" />
        <el-table-column prop="project_name" label="项目" min-width="100" />
        <el-table-column label="标本类型" min-width="170">
          <template #default="{ row }">{{ row.specimen_a }} vs {{ row.specimen_b }}</template>
        </el-table-column>
        <el-table-column label="有效例数" width="85" align="center">
          <template #default="{ row }">{{ row.n_used ?? '—' }}</template>
        </el-table-column>
        <el-table-column label="允许偏倚" width="90" align="center">
          <template #default="{ row }">{{ row.allow_bias != null ? '±' + row.allow_bias + '%' : '—' }}</template>
        </el-table-column>
        <el-table-column label="达标例数" width="100" align="center">
          <template #default="{ row }">{{ row.pass_n != null ? row.pass_n + '/' + row.n_used : '—' }}</template>
        </el-table-column>
        <el-table-column label="达标率" width="90" align="center">
          <template #default="{ row }">{{ row.pass_rate != null ? row.pass_rate.toFixed(1) + '%' : '—' }}</template>
        </el-table-column>
        <el-table-column label="平均偏倚" width="95" align="center">
          <template #default="{ row }">{{ row.mean_bias_pct != null ? (row.mean_bias_pct > 0 ? '+' : '') + row.mean_bias_pct.toFixed(2) + '%' : '—' }}</template>
        </el-table-column>
        <el-table-column label="判定" width="90" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.verdict === true" type="success" size="small">可比</el-tag>
            <el-tag v-else-if="row.verdict === false" type="danger" size="small">不可比</el-tag>
            <el-tag v-else type="info" size="small">待定</el-tag>
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
  listSpecimenComparisons, createSpecimenComparison, updateSpecimenComparison, deleteSpecimenComparison,
  computeSpecimenComparison, generateSpecimenComparison, downloadSpecimenComparison,
  specimenCharts, summarySpecimenComparisons,
} from '../../api/specimenComparability'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const canWrite = computed(() => auth.canWrite ? auth.canWrite('verification') : true)

const TYPE_TEXT = {
  serum_vs_plasma: '血清 vs 血浆',
  plasma_anticoagulant: '血浆-肝素 vs 血浆-EDTA',
  different_tube: '不同采血管',
  standing_time: '不同放置时间',
  other: '其他（自定义）',
}
const typeText = (t) => TYPE_TEXT[t] || t || '—'

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
const detailCharts = ref([])
const chartsLoading = ref(false)

const summaryOpen = ref(false)
const summaryBatch = ref('')
const summaryRows = ref([])

const blankForm = () => ({
  id: null, batch_name: '', verify_type: 'serum_vs_plasma',
  project_name: '', project_method: '', unit: '',
  specimen_a: '血清', specimen_b: '血浆-肝素锂',
  tube_a: '', tube_b: '', centrifuge: '', storage: '', instrument: '',
  sample_count: 20, sample_source: '同一患者同次采集的配对标本',
  tea: '', ref_range_low: '', ref_range_high: '', verify_date: '',
  operator: '', reviewer: '',
})
const form = ref(blankForm())

const batchOptions = computed(() => [...new Set(rows.value.map(r => r.batch_name).filter(Boolean))])
const filledCount = computed(() => samples.value.filter(s => String(s.a ?? '').trim() !== '' && String(s.b ?? '').trim() !== '').length)

const detailConclusionLines = computed(() =>
  (detail.value?.result_summary?.conclusion_lines || []).map(l => String(l).split('**').join(''))
)

const detailRows = computed(() => {
  const rs = detail.value?.result_summary || {}
  const f = (v, n = 2) => (v == null ? '—' : Number(v).toFixed(n))
  const ci = (arr) => (Array.isArray(arr) && arr[0] != null ? `（${Number(arr[0]).toFixed(2)}%，${Number(arr[1]).toFixed(2)}%）` : '')
  if (!rs.valid) return [{ k: '状态', v: rs.message || '未计算' }]
  return [
    { k: '允许偏倚（1/2 TEa）', v: rs.allow_bias != null ? `±${rs.allow_bias}%` : '未设置' },
    { k: '达标例数 / 要求', v: rs.pass_n != null ? `${rs.pass_n}/${rs.n_used}（需 ≥${rs.pass_needed} 例）` : '—' },
    { k: '达标率', v: rs.pass_rate != null ? `${rs.pass_rate}%` : '—' },
    { k: '平均偏倚（95%CI）', v: rs.mean_bias_pct != null ? `${rs.mean_bias_pct > 0 ? '+' : ''}${rs.mean_bias_pct}%${ci(rs.bias_pct_ci)}` : '—' },
    { k: '最大单例相对偏倚', v: rs.max_abs_rel_pct != null ? `${rs.max_abs_rel_pct}%` : '—' },
    { k: 'Passing-Bablok 斜率（95%CI）', v: rs.slope != null ? `${Number(rs.slope).toFixed(4)}${Array.isArray(rs.slope_ci) && rs.slope_ci[0] != null ? `（${Number(rs.slope_ci[0]).toFixed(4)}，${Number(rs.slope_ci[1]).toFixed(4)}）` : ''}` : '—' },
    { k: '截距', v: rs.intercept != null ? Number(rs.intercept).toFixed(6) : '—' },
    { k: '相关系数 r（仅参考）', v: rs.pearson_r != null ? Number(rs.pearson_r).toFixed(4) : '—' },
    { k: 'Bland-Altman P', v: rs.ba_p || '—' },
    { k: '判定依据', v: rs.reason || '—' },
  ]
})

function liveDiff(row) {
  const a = parseFloat(row.a), b = parseFloat(row.b)
  const allow = parseFloat(form.value.tea) / 2
  if (!isFinite(a) || !isFinite(b)) return { d: '—', p: '—', pass: null }
  const d = b - a
  const p = a ? (d / a * 100) : null
  return {
    d: d.toFixed(3),
    p: p != null ? p.toFixed(2) + '%' : '—',
    pass: (isFinite(allow) && p != null) ? Math.abs(p) <= allow : null,
  }
}

function onTypeChange(v) {
  if (v === 'serum_vs_plasma') { form.value.specimen_a = '血清'; form.value.specimen_b = '血浆-肝素锂' }
  else if (v === 'plasma_anticoagulant') { form.value.specimen_a = '血浆-肝素锂'; form.value.specimen_b = '血浆-EDTA' }
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
    const res = await listSpecimenComparisons(params)
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
  samples.value = src.length ? src.map((p, i) => ({ no: p.no ?? i + 1, a: p.a ?? '', b: p.b ?? '' })) : []
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
    if (cols.length < 2) continue
    const a = cols.length >= 3 ? cols[1] : cols[0]
    const b = cols.length >= 3 ? cols[2] : cols[1]
    if (i >= samples.value.length) samples.value.push({ no: i + 1, a: '', b: '' })
    samples.value[i].a = a
    samples.value[i].b = b
    i++; ok++
  }
  ElMessage.success(`已填入 ${ok} 行`)
}

function clearSamples() { samples.value.forEach(s => { s.a = ''; s.b = '' }) }

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
    const saved = form.value.id
      ? await updateSpecimenComparison(form.value.id, payload)
      : await createSpecimenComparison(payload)
    editOpen.value = false
    ElMessage.success('已保存，正在计算…')
    if (saved?.id) {
      try { await computeSpecimenComparison(saved.id) } catch (e) { ElMessage.warning('计算未通过：' + (e?.response?.data?.detail || e.message)) }
    }
    await refresh()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function chartCaption(k) {
  return ({ A: '图A　配对结果散点图（含 Passing-Bablok 回归线）', B: '图B　相对偏差排序图', C: '图C　Bland-Altman 一致性图' })[k] || k
}

async function showDetail(row) {
  detail.value = row
  detailOpen.value = true
  detailCharts.value = []
  chartsLoading.value = true
  try {
    const res = await specimenCharts(row.id)
    detailCharts.value = res.charts || []
  } catch (e) {
    detailCharts.value = []
  } finally {
    chartsLoading.value = false
  }
}

async function doCompute(row) {
  try {
    const res = await computeSpecimenComparison(row.id)
    const rs = res.result_summary || {}
    const tag = rs.verdict === true ? '可比' : rs.verdict === false ? '不可比' : '待定'
    ElMessage.success(`计算完成：${rs.n_used} 例，达标率 ${rs.pass_rate ?? '—'}%，${tag}`)
    await refresh()
    if (detail.value?.id === row.id) detail.value = res
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '计算失败')
  }
}

async function doGenerate(row) {
  try {
    await generateSpecimenComparison(row.id)
    ElMessage.success('报告已生成')
    await refresh()
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '生成失败')
  }
}

async function doDownload(row) {
  try {
    const data = await downloadSpecimenComparison(row.id)
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.project_name || '项目'}_样本类型可比性报告.docx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}

async function doDelete(row) {
  try {
    await ElMessageBox.confirm(`确认删除「${row.project_name}」的验证记录？`, '提示', { type: 'warning' })
    await deleteSpecimenComparison(row.id)
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
  try {
    const res = await summarySpecimenComparisons(summaryBatch.value ? { batch: summaryBatch.value } : {})
    summaryRows.value = res.items || []
  } catch (e) {
    ElMessage.error(e?.response?.data?.detail || '汇总加载失败')
  }
}

onMounted(refresh)
</script>

<style scoped>
.sc { padding: 4px 0; }
.toolbar { display: flex; align-items: center; gap: 8px; margin-bottom: 10px; }
.spacer { flex: 1; }
.tips { font-size: 12px; color: #8a6d3b; background: #fdf6ec; border: 1px solid #f5dab1; border-radius: 6px; padding: 8px 12px; margin-bottom: 10px; line-height: 1.7; }
.paste-bar .tip { font-size: 12px; color: #909399; }
.read-note { margin-top: 12px; padding: 10px 12px; background: #fdf6ec; border: 1px solid #f5dab1; border-radius: 6px; font-size: 12px; line-height: 1.7; color: #8a6d3b; }
.concl { margin-top: 14px; padding: 12px 14px; background: #f7f9fc; border: 1px solid #e4e7ed; border-radius: 6px; }
.concl-title { font-weight: 600; margin-bottom: 6px; color: #1a365d; }
.concl-line { font-size: 13px; line-height: 1.8; color: #303133; }
.charts { margin-top: 16px; }
.charts-title { font-weight: 600; margin-bottom: 8px; color: #1a365d; }
.chart-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.chart-item { border: 1px solid #e4e7ed; border-radius: 6px; padding: 8px; background: #fff; }
.chart-img { width: 100%; display: block; }
.chart-cap { font-size: 12px; color: #606266; text-align: center; margin-top: 6px; }
.chart-empty { font-size: 13px; color: #909399; padding: 12px 0; }
</style>
