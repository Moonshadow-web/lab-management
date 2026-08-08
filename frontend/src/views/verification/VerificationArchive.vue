<template>
  <div class="var-page">
    <div class="var-toolbar">
      <el-button type="primary" @click="openNew">＋ 新建性能验证</el-button>
      <el-button :loading="loading" @click="loadList">刷新</el-button>
      <span class="var-count">共 {{ rows.length }} 份</span>
    </div>

    <el-table :data="rows" border stripe v-loading="loading">
      <el-table-column label="类型" width="76" align="center">
        <template #default="{ row }">
          <el-tag :type="row.report_type === 'qualitative' ? 'warning' : 'primary'" size="small">{{ row.report_type === 'qualitative' ? '定性' : '定量' }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="project_name" label="项目名称" min-width="150" show-overflow-tooltip />
      <el-table-column prop="instrument_model" label="仪器型号" width="110" />
      <el-table-column label="验证内容" min-width="150" show-overflow-tooltip>
        <template #default="{ row }">{{ itemNames(row.verify_items) }}</template>
      </el-table-column>
      <el-table-column prop="verify_date" label="验证日期" width="150" />
      <el-table-column label="报告" width="130">
        <template #default="{ row }">
          <el-tag v-if="row.report_file_path" type="success" size="small">已归档</el-tag>
          <el-tag v-else type="info" size="small">未生成</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="230" align="center" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="generate(row)">生成报告</el-button>
          <el-button size="small" type="success" plain :disabled="!row.report_file_path" @click="download(row)">下载</el-button>
          <el-button size="small" @click="openEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" plain @click="del(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新建/编辑向导 -->
    <el-drawer v-model="drawer" :title="editingId ? '编辑性能验证' : '新建性能验证'" size="92%" destroy-on-close>
      <div class="wiz-body" v-if="drawer">
        <el-card shadow="never" class="wiz-card">
          <template #header><b>① 项目基本信息</b></template>
          <el-form label-width="110px" label-position="right">
            <el-row :gutter="12">
              <el-col :span="8"><el-form-item label="验证类型" required>
                <el-radio-group v-model="form.report_type" @change="onTypeChange">
                  <el-radio-button value="qualitative">定性项目</el-radio-button>
                  <el-radio-button value="quantitative">定量项目</el-radio-button>
                </el-radio-group>
              </el-form-item></el-col>
              <el-col :span="8"><el-form-item label="项目名称" required><el-input v-model="form.project_name" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="项目方法"><el-input v-model="form.project_method" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="报告单位"><el-input v-model="form.unit" placeholder="COI / U/L" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器名称"><el-input v-model="form.instrument" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器厂家"><el-input v-model="form.instrument_manufacturer" /></el-form-item></el-col>
              <el-col :span="6"><el-form-item label="仪器型号"><el-input v-model="form.instrument_model" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="仪器编号"><el-input v-model="form.instrument_no" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="试剂"><el-input v-model="form.reagent" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="试剂批号"><el-input v-model="form.reagent_lot" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="校准品"><el-input v-model="form.calibrator" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="校准品批号"><el-input v-model="form.calibrator_lot" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="质控品"><el-input v-model="form.qc" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="质控品批号"><el-input v-model="form.qc_lot" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="允许总误差 TEA"><el-input v-model="form.tea" placeholder="如 0.18" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="声称线性范围"><el-input v-model="form.linear_low" placeholder="下限" style="width:45%" /> ~ <el-input v-model="form.linear_high" placeholder="上限" style="width:45%" /></el-form-item></el-col>
              <el-col :span="8" v-if="form.report_type === 'quantitative'"><el-form-item label="稀释倍数"><el-input v-model="form.dilution" placeholder="/" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="验证日期"><el-input v-model="form.verify_date" placeholder="如 2025年05月12日-2025年05月16日" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="操作人员"><el-input v-model="form.operator" /></el-form-item></el-col>
              <el-col :span="8"><el-form-item label="审核人员"><el-input v-model="form.reviewer" /></el-form-item></el-col>
            </el-row>
          </el-form>
        </el-card>

        <el-card shadow="never" class="wiz-card">
          <template #header><b>② 选择验证内容（可多选，逐项验证）</b></template>
          <el-checkbox-group v-model="form.verify_items">
            <el-checkbox v-for="(label, key) in itemOptions" :key="key" :value="key" border style="margin:4px">{{ label }}</el-checkbox>
          </el-checkbox-group>
        </el-card>

        <!-- 精密度 -->
        <el-card v-if="form.verify_items.includes('precision')" shadow="never" class="wiz-card">
          <template #header><b>③ 精密度验证数据（2 个水平 × 5 天 × 3 次）</b></template>
          <el-form label-width="90px">
            <div v-for="(lv, li) in form.data.precision.levels" :key="li" class="lvl-block">
              <div class="lvl-title">水平{{ li + 1 }}</div>
              <el-row :gutter="8">
                <el-col :span="8"><el-input v-model="lv.name" size="small" placeholder="水平名称（如 低值质控品）" /></el-col>
                <el-col :span="6"><el-input v-model="lv.target" size="small" placeholder="靶值" /></el-col>
              </el-row>
              <el-table :data="lv.rows" border size="small" style="margin-top:6px">
                <el-table-column label="天数" width="70" align="center">
                  <template #default="{ $index }">第{{ $index + 1 }}天</template>
                </el-table-column>
                <el-table-column v-for="k in 3" :key="k" :label="'第' + k + '次'">
                  <template #default="{ row }"><el-input v-model="row[k - 1]" size="small" /></template>
                </el-table-column>
              </el-table>
              <div class="auto-text">均值 {{ lv.meanText || '—' }}　CV {{ lv.cvText || '—' }}</div>
            </div>
            <el-form-item label="结论">
              <el-select v-model="resultMap.precision.conclusion" style="width:160px">
                <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 定性：方法符合率 -->
        <el-card v-if="form.report_type === 'qualitative' && form.verify_items.includes('conformity')" shadow="never" class="wiz-card">
          <template #header><b>③ 方法符合率验证数据（≥10 阴性 + ≥10 阳性样本）</b></template>
          <el-table :data="form.data.conformity.samples" border size="small">
            <el-table-column label="#" width="44" align="center"><template #default="{ $index }">{{ $index + 1 }}</template></el-table-column>
            <el-table-column label="样品编号"><template #default="{ row }"><el-input v-model="row.name" size="small" /></template></el-table-column>
            <el-table-column label="参考结果(N/P)" width="100"><template #default="{ row }"><el-select v-model="row.ref" size="small"><el-option label="N" value="N" /><el-option label="P" value="P" /></el-select></template></el-table-column>
            <el-table-column label="待评价方法结果"><template #default="{ row }"><el-input v-model="row.method" size="small" /></template></el-table-column>
            <el-table-column label="方法判定(N/P)" width="100"><template #default="{ row }"><el-select v-model="row.mresult" size="small"><el-option label="N" value="N" /><el-option label="P" value="P" /></el-select></template></el-table-column>
          </el-table>
          <div class="auto-text">阳性符合率 {{ conformityRate.pos }}　阴性符合率 {{ conformityRate.neg }}</div>
          <el-form-item label="结论" style="margin-top:8px">
            <el-select v-model="resultMap.conformity.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>

        <!-- 定性：方法检出限 -->
        <el-card v-if="form.report_type === 'qualitative' && form.verify_items.includes('lod')" shadow="never" class="wiz-card">
          <template #header><b>③ 方法检出限验证数据（≥20 个检出限浓度样本）</b></template>
          <el-table :data="form.data.lod.samples" border size="small">
            <el-table-column label="#" width="44" align="center"><template #default="{ $index }">{{ $index + 1 }}</template></el-table-column>
            <el-table-column label="参考品原浓度"><template #default="{ row }"><el-input v-model="row.orig" size="small" /></template></el-table-column>
            <el-table-column label="稀释后浓度"><template #default="{ row }"><el-input v-model="row.diluted" size="small" /></template></el-table-column>
            <el-table-column label="待评价方法结果"><template #default="{ row }"><el-input v-model="row.value" size="small" /></template></el-table-column>
            <el-table-column label="判定(N/P)" width="90"><template #default="{ row }"><el-select v-model="row.mresult" size="small"><el-option label="P" value="P" /><el-option label="N" value="N" /></el-select></template></el-table-column>
          </el-table>
          <div class="auto-text">检出阳性率 {{ lodRate }}</div>
          <el-form-item label="结论" style="margin-top:8px">
            <el-select v-model="resultMap.lod.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>

        <!-- 定量：正确度 -->
        <el-card v-if="form.report_type === 'quantitative' && form.verify_items.includes('trueness')" shadow="never" class="wiz-card">
          <template #header><b>③ 正确度验证数据（2 水平 × 5 天 × 2 次，靶值 = 标准物质赋值）</b></template>
          <div v-for="(lv, li) in form.data.trueness.levels" :key="li" class="lvl-block">
            <div class="lvl-title">水平{{ li + 1 }}</div>
            <el-row :gutter="8">
              <el-col :span="8"><el-input v-model="lv.name" size="small" placeholder="水平名称" /></el-col>
              <el-col :span="6"><el-input v-model="lv.target" size="small" placeholder="标准物质赋值/靶值" /></el-col>
            </el-row>
            <el-table :data="lv.rows" border size="small" style="margin-top:6px">
              <el-table-column label="天数" width="70" align="center"><template #default="{ $index }">第{{ $index + 1 }}天</template></el-table-column>
              <el-table-column label="第1次"><template #default="{ row }"><el-input v-model="row[0]" size="small" /></template></el-table-column>
              <el-table-column label="第2次"><template #default="{ row }"><el-input v-model="row[1]" size="small" /></template></el-table-column>
            </el-table>
            <div class="auto-text">均值 {{ lv.meanText || '—' }}　相对偏倚 {{ lv.biasText || '—' }}</div>
          </div>
          <el-form-item label="结论">
            <el-select v-model="resultMap.trueness.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>

        <!-- 定量：线性范围 -->
        <el-card v-if="form.report_type === 'quantitative' && form.verify_items.includes('linearity')" shadow="never" class="wiz-card">
          <template #header><b>③ 线性范围验证数据（6 个浓度点 × 3 次）</b></template>
          <el-table :data="form.data.linearity.points" border size="small">
            <el-table-column label="点" width="44" align="center"><template #default="{ $index }">{{ $index + 1 }}</template></el-table-column>
            <el-table-column label="低浓度比例"><template #default="{ row }"><el-input v-model="row.low" size="small" /></template></el-table-column>
            <el-table-column label="高浓度比例"><template #default="{ row }"><el-input v-model="row.high" size="small" /></template></el-table-column>
            <el-table-column v-for="k in 3" :key="k" :label="'测量' + k"><template #default="{ row }"><el-input v-model="row['v' + k]" size="small" /></template></el-table-column>
          </el-table>
          <el-form-item label="结论">
            <el-select v-model="resultMap.linearity.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>

        <!-- 可报告范围 / 参考范围 / 分析特异性 -->
        <el-card v-if="form.verify_items.includes('reportable')" shadow="never" class="wiz-card">
          <template #header><b>③ 可报告范围验证</b></template>
          <el-input v-model="form.data.reportable.note" type="textarea" :rows="2" placeholder="如：低限 5、高限 1500，稀释后报告范围……" />
          <el-form-item label="结论" style="margin-top:8px">
            <el-select v-model="resultMap.reportable.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>
        <el-card v-if="form.verify_items.includes('reference')" shadow="never" class="wiz-card">
          <template #header><b>③ 参考范围验证</b></template>
          <el-input v-model="form.data.reference.note" type="textarea" :rows="2" placeholder="如：参考区间 男：45-125 U/L、女：35-100 U/L，各组 20 个标本中超出参考区间不多于 2 个" />
          <el-form-item label="结论" style="margin-top:8px">
            <el-select v-model="resultMap.reference.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>
        <el-card v-if="form.verify_items.includes('specificity')" shadow="never" class="wiz-card">
          <template #header><b>③ 分析特异性验证</b></template>
          <el-input v-model="form.data.specificity.note" type="textarea" :rows="2" placeholder="如：胆红素、甘油三酯、血红蛋白抗干扰能力符合厂家声明" />
          <el-form-item label="结论" style="margin-top:8px">
            <el-select v-model="resultMap.specificity.conclusion" style="width:160px">
              <el-option label="符合要求" value="符合要求" /><el-option label="不符合要求" value="不符合要求" />
            </el-select>
          </el-form-item>
        </el-card>

        <el-card shadow="never" class="wiz-card">
          <template #header><b>④ 总结论</b></template>
          <el-input v-model="form.conclusion" type="textarea" :rows="2" placeholder="如：本实验室在××仪器上对××项目的分析性能验证均符合要求。" />
        </el-card>

        <div class="wiz-foot">
          <el-button @click="drawer = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listVerificationReports, createVerificationReport, updateVerificationReport,
  deleteVerificationReport, generateVerificationReport, downloadVerificationReport,
} from '../../api/verificationReports'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const rows = ref([])
const loading = ref(false)
const drawer = ref(false)
const editingId = ref(null)
const saving = ref(false)
const me = () => auth.user?.full_name || auth.user?.username || '金子铮'

const itemOptions = computed(() => ({
  precision: '精密度',
  ...(form.report_type === 'qualitative'
    ? { conformity: '方法符合率', lod: '方法检出限' }
    : { trueness: '正确度', linearity: '线性范围', reportable: '可报告范围' }),
  reference: form.report_type === 'qualitative' ? '参考范围' : '参考区间',
  specificity: '分析特异性',
}))
function itemNames(items) {
  const m = itemOptions.value
  return (items || []).map((i) => m[i] || i).join('、')
}

const resultMap = reactive({})
function emptyResultMap() {
  const keys = ['precision', 'conformity', 'lod', 'trueness', 'linearity', 'reportable', 'reference', 'specificity']
  const m = {}
  for (const k of keys) m[k] = { result: '', conclusion: '符合要求' }
  return m
}
Object.assign(resultMap, emptyResultMap())

const form = reactive({
  report_type: 'qualitative', project_name: '', project_method: '', unit: '',
  reagent: '', reagent_lot: '', calibrator: '', calibrator_lot: '', qc: '', qc_lot: '',
  instrument: '', instrument_manufacturer: '', instrument_model: '', instrument_no: '',
  tea: '', linear_low: '', linear_high: '', dilution: '',
  verify_date: '', operator: me(), reviewer: '杨静',
  verify_items: ['precision'],
  data: {
    precision: { levels: [] },
    conformity: { samples: [] },
    lod: { samples: [] },
    trueness: { levels: [] },
    linearity: { points: [] },
    reportable: { note: '' }, reference: { note: '' }, specificity: { note: '' },
  },
  conclusion: '',
})

function mkPrecisionLevels() {
  return [0, 1].map(() => ({
    name: '', target: '',
    rows: Array.from({ length: 5 }, () => ['', '', '']),
    meanText: '', cvText: '',
  }))
}
function mkTruenessLevels() {
  return [0, 1].map(() => ({ name: '', target: '', rows: Array.from({ length: 5 }, () => ['', '']), meanText: '', biasText: '' }))
}
function mkSamples(n, tpl) {
  return Array.from({ length: n }, () => ({ ...tpl }))
}
function mkLinearPoints() {
  return Array.from({ length: 6 }, (_, i) => ({ low: '', high: '', v1: '', v2: '', v3: '' }))
}
function initForm() {
  editingId.value = null
  Object.assign(form, {
    report_type: 'qualitative', project_name: '', project_method: '', unit: '',
    reagent: '', reagent_lot: '', calibrator: '', calibrator_lot: '', qc: '', qc_lot: '',
    instrument: '', instrument_manufacturer: '', instrument_model: '', instrument_no: '',
    tea: '', linear_low: '', linear_high: '', dilution: '',
    verify_date: '', operator: me(), reviewer: '杨静',
    verify_items: ['precision'],
    data: {
      precision: { levels: mkPrecisionLevels() },
      conformity: { samples: mkSamples(20, { name: '', ref: 'N', method: '', mresult: 'N' }) },
      lod: { samples: mkSamples(20, { orig: '', diluted: '', value: '', mresult: 'P' }) },
      trueness: { levels: mkTruenessLevels() },
      linearity: { points: mkLinearPoints() },
      reportable: { note: '' }, reference: { note: '' }, specificity: { note: '' },
    },
    conclusion: '',
  })
  Object.assign(resultMap, emptyResultMap())
}
function onTypeChange() {
  if (!form.verify_items.length) form.verify_items = ['precision']
  // 清理不适配项
  const ok = Object.keys(itemOptions.value)
  form.verify_items = form.verify_items.filter((i) => ok.includes(i))
}

// ---------- 自动计算 ----------
function nums(arr) { return (arr || []).map((v) => parseFloat(v)).filter((n) => !isNaN(n)) }
function stats(ns) {
  if (!ns.length) return null
  const mean = ns.reduce((a, b) => a + b, 0) / ns.length
  const sd = Math.sqrt(ns.reduce((s, v) => s + (v - mean) ** 2, 0) / (ns.length - 1))
  return { mean, cv: (sd / mean) * 100 }
}
function computeAll() {
  const rs = resultMap
  // 精密度
  if (form.verify_items.includes('precision')) {
    const texts = []
    form.data.precision.levels.forEach((lv, i) => {
      const vals = []
      lv.rows.forEach((r) => vals.push(...nums(r)))
      const st = stats(vals)
      lv.meanText = st ? st.mean.toFixed(2) : ''
      lv.cvText = st ? st.cv.toFixed(2) + '%' : ''
      if (st) texts.push(`水平${i + 1} CV ${st.cv.toFixed(2)}%`)
    })
    rs.precision.result = texts.join('，') || ''
  }
  // 符合率
  if (form.verify_items.includes('conformity')) {
    const smp = form.data.conformity.samples.filter((s) => s.ref && s.mresult)
    const pos = smp.filter((s) => s.ref === 'P')
    const neg = smp.filter((s) => s.ref === 'N')
    const posRate = pos.length ? (pos.filter((s) => s.mresult === 'P').length / pos.length * 100).toFixed(0) : '—'
    const negRate = neg.length ? (neg.filter((s) => s.mresult === 'N').length / neg.length * 100).toFixed(0) : '—'
    conformityRate.pos = posRate === '—' ? '—' : posRate + '%'
    conformityRate.neg = negRate === '—' ? '—' : negRate + '%'
    rs.conformity.result = `阳性符合率 ${posRate}%，阴性符合率 ${negRate}%`
  }
  // 检出限
  if (form.verify_items.includes('lod')) {
    const smp = form.data.lod.samples.filter((s) => s.mresult)
    const p = smp.filter((s) => s.mresult === 'P').length
    lodRate.value = smp.length ? `${p}/${smp.length}（${(p / smp.length * 100).toFixed(0)}%）` : '—'
    rs.lod.result = smp.length ? `${smp[0].diluted || ''} 阳性率 ${(p / smp.length * 100).toFixed(0)}%` : ''
  }
  // 正确度
  if (form.verify_items.includes('trueness')) {
    const texts = []
    form.data.trueness.levels.forEach((lv, i) => {
      const vals = []
      lv.rows.forEach((r) => vals.push(...nums(r)))
      const st = stats(vals)
      const t = parseFloat(lv.target)
      lv.meanText = st ? st.mean.toFixed(2) : ''
      lv.biasText = st && !isNaN(t) && t !== 0 ? (((st.mean - t) / t) * 100).toFixed(2) + '%' : ''
      if (st && !isNaN(t)) texts.push(`水平${i + 1} 偏倚 ${lv.biasText}`)
    })
    rs.trueness.result = texts.join('，') || ''
  }
  // 线性
  if (form.verify_items.includes('linearity')) {
    const pts = form.data.linearity.points.filter((p) => p.v1 || p.v2 || p.v3)
    rs.linearity.result = pts.length ? `共 ${pts.length} 个浓度点` : ''
  }
  // 文本项
  if (form.verify_items.includes('reportable')) rs.reportable.result = form.data.reportable.note || ''
  if (form.verify_items.includes('reference')) rs.reference.result = form.data.reference.note || ''
  if (form.verify_items.includes('specificity')) rs.specificity.result = form.data.specificity.note || ''
}
const conformityRate = reactive({ pos: '—', neg: '—' })
const lodRate = ref('—')

// ---------- 保存 / 生成 ----------
function buildPayload() {
  computeAll()
  return {
    report_type: form.report_type, project_name: form.project_name, project_method: form.project_method, unit: form.unit,
    reagent: form.reagent, reagent_lot: form.reagent_lot, calibrator: form.calibrator, calibrator_lot: form.calibrator_lot,
    qc: form.qc, qc_lot: form.qc_lot, instrument: form.instrument, instrument_manufacturer: form.instrument_manufacturer,
    instrument_model: form.instrument_model, instrument_no: form.instrument_no,
    tea: form.tea, linear_low: form.linear_low, linear_high: form.linear_high, dilution: form.dilution,
    verify_date: form.verify_date, operator: form.operator, reviewer: form.reviewer,
    verify_items: form.verify_items, data: JSON.parse(JSON.stringify(form.data)),
    result_summary: JSON.parse(JSON.stringify(resultMap)),
    conclusion: form.conclusion,
  }
}
async function save() {
  if (!form.project_name.trim()) { ElMessage.warning('请填写项目名称'); return }
  if (!form.verify_items.length) { ElMessage.warning('请至少选择一项验证内容'); return }
  saving.value = true
  try {
    const payload = buildPayload()
    if (editingId.value) {
      await updateVerificationReport(editingId.value, payload)
      ElMessage.success('已保存')
    } else {
      await createVerificationReport(payload)
      ElMessage.success('已保存，可点击「生成报告」')
    }
    drawer.value = false
    await loadList()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e?.message))
  } finally {
    saving.value = false
  }
}
async function generate(row) {
  try {
    await generateVerificationReport(row.id)
    ElMessage.success('报告已生成并归档')
    await loadList()
  } catch (e) {
    ElMessage.error('生成失败：' + (e?.response?.data?.detail || e?.message))
  }
}
async function download(row) {
  try {
    const blob = await downloadVerificationReport(row.id)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${row.project_name || '项目'}_性能验证.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    ElMessage.error('下载失败')
  }
}
async function del(row) {
  await ElMessageBox.confirm(`确认删除「${row.project_name}」？`, '提示', { type: 'warning' })
  await deleteVerificationReport(row.id)
  ElMessage.success('已删除')
  await loadList()
}
function openNew() {
  initForm()
  drawer.value = true
}
function openEdit(row) {
  editingId.value = row.id
  Object.assign(form, {
    report_type: row.report_type || 'qualitative', project_name: row.project_name || '', project_method: row.project_method || '', unit: row.unit || '',
    reagent: row.reagent || '', reagent_lot: row.reagent_lot || '', calibrator: row.calibrator || '', calibrator_lot: row.calibrator_lot || '',
    qc: row.qc || '', qc_lot: row.qc_lot || '', instrument: row.instrument || '', instrument_manufacturer: row.instrument_manufacturer || '',
    instrument_model: row.instrument_model || '', instrument_no: row.instrument_no || '',
    tea: row.tea || '', linear_low: row.linear_low || '', linear_high: row.linear_high || '', dilution: row.dilution || '',
    verify_date: row.verify_date || '', operator: row.operator || me(), reviewer: row.reviewer || '杨静',
    verify_items: row.verify_items?.length ? row.verify_items : ['precision'],
    data: row.data || form.data, conclusion: row.conclusion || '',
  })
  if (row.result_summary) Object.assign(resultMap, row.result_summary)
  drawer.value = true
}

async function loadList() {
  loading.value = true
  try {
    const res = await listVerificationReports()
    rows.value = Array.isArray(res) ? res : (res.items || [])
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message))
  } finally {
    loading.value = false
  }
}
onMounted(loadList)
</script>

<style scoped>
.var-toolbar { display: flex; gap: 10px; align-items: center; margin-bottom: 12px; }
.var-count { color: #909399; font-size: 13px; }
.wiz-body { display: flex; flex-direction: column; gap: 14px; }
.wiz-card { border-radius: 10px; }
.lvl-block { background: #f7fafc; border: 1px solid #e4e7ed; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.lvl-title { font-weight: 600; color: #4a5568; margin-bottom: 6px; }
.auto-text { margin-top: 6px; font-size: 13px; color: #409eff; font-weight: 600; }
.wiz-foot { display: flex; justify-content: flex-end; gap: 8px; }
</style>
