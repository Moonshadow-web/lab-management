<template>
  <div class="uncert-page">
    <div class="uncert-header">
      <h2>📊 测量不确定度评估</h2>
      <span>民航总医院检验科生化免疫组 | BG-SM-CZ-072 评定报告生成</span>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：数据输入 -->
      <el-col :span="13" :xs="24">
        <el-card shadow="never">
          <template #header><b>📝 项目信息与数据输入</b></template>

          <el-form label-width="100px" label-position="right">
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="项目名称" required><el-input v-model="form.project_name" placeholder="如：ALT（丙氨酸氨基转移酶）" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="项目编号"><el-input v-model="form.project_code" placeholder="如：SM-SOP-101" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="检测系统/仪器"><el-input v-model="form.instrument" placeholder="如：贝克曼 AU5800" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="试剂/校准品"><el-input v-model="form.reagent" placeholder="如：XXX试剂盒" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="评定日期"><el-date-picker v-model="form.eval_date" type="date" value-format="YYYY-MM-DD" style="width:100%" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="评定周期(月)"><el-input-number v-model="form.cycle_months" :min="1" :max="36" style="width:100%" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="编制人"><el-input v-model="form.prepared_by" /></el-form-item></el-col>
              <el-col :span="12"><el-form-item label="审核人"><el-input v-model="form.reviewed_by" /></el-form-item></el-col>
            </el-row>

            <!-- L1 数据 -->
            <div class="data-block">
              <div class="data-block-title">📈 L1 水平室内质控数据（至少 5 个，建议 ≥20）</div>
              <div class="data-grid">
                <el-input v-for="(v, i) in form.l1" :key="'l1_' + i" v-model="form.l1[i]" size="small" :placeholder="'值' + (i + 1)" class="data-cell" />
              </div>
              <div class="stats-bar" style="background:#67c23a">
                <div class="stat-item"><label>平均值</label><b>{{ l1Stats.mean != null ? l1Stats.mean.toFixed(2) : '-' }}</b></div>
                <div class="stat-item"><label>标准差</label><b>{{ l1Stats.sd != null ? l1Stats.sd.toFixed(2) : '-' }}</b></div>
                <div class="stat-item"><label>CV%</label><b>{{ l1Stats.cv != null ? l1Stats.cv.toFixed(2) + '%' : '-' }}</b></div>
                <div class="stat-item"><label>n</label><b>{{ l1Stats.n }}</b></div>
              </div>
            </div>

            <!-- L2 数据 -->
            <div class="data-block">
              <div class="data-block-title">📉 L2 水平室内质控数据（至少 5 个，建议 ≥20）</div>
              <div class="data-grid">
                <el-input v-for="(v, i) in form.l2" :key="'l2_' + i" v-model="form.l2[i]" size="small" :placeholder="'值' + (i + 1)" class="data-cell" />
              </div>
              <div class="stats-bar" style="background:#e6a23c">
                <div class="stat-item"><label>平均值</label><b>{{ l2Stats.mean != null ? l2Stats.mean.toFixed(2) : '-' }}</b></div>
                <div class="stat-item"><label>标准差</label><b>{{ l2Stats.sd != null ? l2Stats.sd.toFixed(2) : '-' }}</b></div>
                <div class="stat-item"><label>CV%</label><b>{{ l2Stats.cv != null ? l2Stats.cv.toFixed(2) + '%' : '-' }}</b></div>
                <div class="stat-item"><label>n</label><b>{{ l2Stats.n }}</b></div>
              </div>
            </div>

            <!-- 质评与校准品 -->
            <div class="data-block">
              <div class="data-block-title">🎯 室间质评与校准品信息</div>
              <el-form-item label="室间质评结果">
                <el-radio-group v-model="form.pt_result">
                  <el-radio value="合格">✅ 合格（偏倚已含于精密度，不需填偏倚）</el-radio>
                  <el-radio value="不合格">❌ 不合格（需填偏倚数据）</el-radio>
                </el-radio-group>
              </el-form-item>
              <div v-if="form.pt_result === '不合格'" class="bias-box">
                <div class="bias-tip">💡 请输入室间质评靶值和测量值（1~3 组），用于计算偏倚分量</div>
                <el-row :gutter="8" v-for="i in 3" :key="'b' + i" style="margin-bottom:6px">
                  <el-col :span="12"><el-input v-model="form['target' + i]" size="small" :placeholder="'靶值' + i" /></el-col>
                  <el-col :span="12"><el-input v-model="form['value' + i]" size="small" :placeholder="'测量值' + i" /></el-col>
                </el-row>
                <div class="stats-bar" style="background:#f56c6c; margin-top:8px">
                  <div class="stat-item"><label>RMS偏倚(%)</label><b>{{ biasRMS != null ? biasRMS.toFixed(2) + '%' : '-' }}</b></div>
                  <div class="stat-item"><label>偏倚分量</label><b>将计入 U</b></div>
                </div>
              </div>
              <div v-else class="stats-bar" style="background:#67c23a; margin-bottom:12px">
                <div class="stat-item" style="width:100%"><b>✅ 室间质评合格，偏倚分量不计入不确定度</b></div>
              </div>
              <el-form-item label="校准品不确定度 Ucal (%)">
                <el-input-number v-model="form.ucal" :min="0" :precision="2" :step="0.1" style="width:180px" />
              </el-form-item>
            </div>

            <div class="btn-row">
              <el-button type="primary" :loading="saving" @click="save">💾 保存并计算</el-button>
              <el-button @click="clearForm">🔄 清空</el-button>
              <el-button v-if="editingId" @click="cancelEdit">取消编辑</el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：结果与列表 -->
      <el-col :span="11" :xs="24">
        <el-card shadow="never">
          <template #header><b>📋 计算结果与报告</b></template>

          <div v-if="current" class="result-box">
            <div class="res-row"><span>项目名称</span><b>{{ current.project_name }}</b></div>
            <div class="res-row"><span>L1 水平 扩展不确定度 U</span><b class="hl">{{ current.l1_u.toFixed(2) }}%</b></div>
            <div class="res-row"><span>L2 水平 扩展不确定度 U</span><b class="hl">{{ current.l2_u.toFixed(2) }}%</b></div>
            <div class="res-row"><span>L1 判定</span><el-tag :type="current.l1_passed ? 'success' : 'danger'" size="small">{{ current.l1_passed ? '合格' : '待改进' }}</el-tag></div>
            <div class="res-row"><span>L2 判定</span><el-tag :type="current.l2_passed ? 'success' : 'danger'" size="small">{{ current.l2_passed ? '合格' : '待改进' }}</el-tag></div>
            <div class="res-row"><span>报告编号</span><b>BG-SM-CZ-072</b></div>
          </div>
          <el-empty v-else description="暂无评定记录，请在左侧输入数据并保存" :image-size="70" />

          <div class="btn-row" style="margin-top:14px">
            <el-button type="primary" :disabled="!projects.length" @click="previewSingle">📄 预览单项目报告</el-button>
            <el-button :disabled="!projects.length" @click="downloadSingle">⬇️ 下载单项目报告</el-button>
            <el-button :disabled="!projects.length" @click="previewSummary">📑 预览汇总表</el-button>
            <el-button :disabled="!projects.length" @click="downloadSummary">⬇️ 下载汇总表</el-button>
          </div>

          <el-divider>已保存项目（{{ projects.length }}）</el-divider>
          <div class="project-list">
            <div v-for="p in projects" :key="p.id" class="project-item">
              <div class="p-info">
                <div class="p-name">{{ p.project_name }}</div>
                <div class="p-meta">{{ p.eval_date || '未设日期' }} | L1_U={{ p.l1_u ? p.l1_u.toFixed(2) : '-' }}% | L2_U={{ p.l2_u ? p.l2_u.toFixed(2) : '-' }}%</div>
              </div>
              <div class="p-actions">
                <el-button size="small" @click="loadProject(p)">查看</el-button>
                <el-button size="small" type="success" @click="previewOne(p)">报告</el-button>
                <el-button size="small" type="danger" @click="delProject(p)">删除</el-button>
              </div>
            </div>
            <el-empty v-if="!projects.length" description="暂无已保存项目" :image-size="60" />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 报告预览 -->
    <el-dialog v-model="previewOpen" :title="previewTitle" width="86%" top="3vh">
      <iframe :srcdoc="previewHtml" style="width:100%; height:72vh; border:1px solid #dcdfe6; border-radius:4px"></iframe>
      <template #footer>
        <el-button @click="previewOpen = false">关闭</el-button>
        <el-button type="primary" @click="downloadCurrentHtml">下载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { listUncertainty, createUncertainty, updateUncertainty, deleteUncertainty } from '../../api/uncertainty'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const projects = ref([])
const current = ref(null) // 当前展示结果
const saving = ref(false)
const editingId = ref(null)
const previewOpen = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')

const REPORT_CODE = 'BG-SM-CZ-072'
const REPORT_VERSION = '01'
const REPORT_DATE = '2025.01.01'

const todayStr = () => {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const form = reactive({
  project_name: '', project_code: '', instrument: '', reagent: '',
  eval_date: todayStr(), cycle_months: 12,
  prepared_by: auth.user?.full_name || auth.user?.username || '金子铮',
  reviewed_by: '杨静',
  l1: Array(20).fill(''), l2: Array(20).fill(''),
  pt_result: '合格',
  target1: '', value1: '', target2: '', value2: '', target3: '', value3: '',
  ucal: 0,
})

// ---------- 统计计算 ----------
function getNums(arr) {
  return (arr || []).map((v) => parseFloat(v)).filter((n) => !isNaN(n))
}
function calcStats(nums) {
  if (!nums.length) return { mean: null, sd: null, cv: null, n: 0 }
  const n = nums.length
  const mean = nums.reduce((a, b) => a + b, 0) / n
  const variance = nums.reduce((s, v) => s + (v - mean) ** 2, 0) / (n - 1)
  const sd = Math.sqrt(variance)
  return { mean, sd, cv: (sd / mean) * 100, n }
}
const l1Stats = computed(() => calcStats(getNums(form.l1)))
const l2Stats = computed(() => calcStats(getNums(form.l2)))
const biasRMS = computed(() => {
  const pairs = []
  for (let i = 1; i <= 3; i++) {
    const t = parseFloat(form['target' + i])
    const v = parseFloat(form['value' + i])
    if (!isNaN(t) && !isNaN(v) && t !== 0) pairs.push([t, v])
  }
  if (!pairs.length) return null
  let sum = 0
  for (const [t, v] of pairs) {
    const b = ((v - t) / t) * 100
    sum += b * b
  }
  return Math.sqrt(sum / pairs.length)
})

// ---------- 合成不确定度 ----------
function calcUncertainty(cv, ptPassed, ucal) {
  const uBias = ptPassed ? 0 : biasRMS.value || 0
  const uc = Math.sqrt(cv * cv + uBias * uBias + ucal * ucal)
  const U = 2 * uc
  return { uc, U, passed: U < 15 }
}

// ---------- 保存 ----------
async function save() {
  if (!form.project_name.trim()) { ElMessage.warning('请输入项目名称'); return }
  const n1 = getNums(form.l1)
  const n2 = getNums(form.l2)
  if (n1.length < 5) { ElMessage.warning('L1 水平请至少输入 5 个数据'); return }
  if (n2.length < 5) { ElMessage.warning('L2 水平请至少输入 5 个数据'); return }
  const s1 = calcStats(n1)
  const s2 = calcStats(n2)
  const ptPassed = form.pt_result === '合格'
  const u1 = calcUncertainty(s1.cv, ptPassed, parseFloat(form.ucal) || 0)
  const u2 = calcUncertainty(s2.cv, ptPassed, parseFloat(form.ucal) || 0)
  const payload = {
    project_name: form.project_name.trim(), project_code: form.project_code, instrument: form.instrument,
    reagent: form.reagent, eval_date: form.eval_date, cycle_months: form.cycle_months,
    prepared_by: form.prepared_by || '金子铮', reviewed_by: form.reviewed_by || '杨静',
    l1_values: n1, l2_values: n2,
    l1_mean: s1.mean, l1_sd: s1.sd, l1_cv: s1.cv,
    l2_mean: s2.mean, l2_sd: s2.sd, l2_cv: s2.cv,
    bias_rms: biasRMS.value || 0, ucal: parseFloat(form.ucal) || 0, pt_result: form.pt_result,
    l1_u: u1.U, l2_u: u2.U, l1_passed: u1.passed, l2_passed: u2.passed,
  }
  saving.value = true
  try {
    if (editingId.value) {
      await updateUncertainty(editingId.value, payload)
      ElMessage.success('已保存修改')
    } else {
      await createUncertainty(payload)
      ElMessage.success('保存成功')
    }
    editingId.value = null
    current.value = { ...payload, id: editingId.value }
    clearForm()
    await loadProjects()
  } catch (e) {
    ElMessage.error('保存失败：' + (e?.response?.data?.detail || e?.message || '未知错误'))
  } finally {
    saving.value = false
  }
}

// ---------- 列表 ----------
async function loadProjects() {
  try {
    const res = await listUncertainty({ page_size: 300 })
    projects.value = res.items || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message))
  }
}
function loadProject(p) {
  editingId.value = p.id
  Object.assign(form, {
    project_name: p.project_name || '', project_code: p.project_code || '',
    instrument: p.instrument || '', reagent: p.reagent || '',
    eval_date: p.eval_date || todayStr(), cycle_months: p.cycle_months || 12,
    prepared_by: p.prepared_by || '金子铮', reviewed_by: p.reviewed_by || '杨静',
    l1: fill20(p.l1_values || []), l2: fill20(p.l2_values || []),
    pt_result: p.pt_result || '合格', ucal: p.ucal || 0,
  })
  for (let i = 1; i <= 3; i++) { form['target' + i] = ''; form['value' + i] = '' }
  current.value = p
  ElMessage.info('已载入，可修改后保存')
}
function fill20(arr) {
  const out = Array(20).fill('')
  arr.forEach((v, i) => { if (i < 20) out[i] = String(v) })
  return out
}
async function delProject(p) {
  await ElMessageBox.confirm(`确认删除「${p.project_name}」的评定记录？`, '提示', { type: 'warning' })
  await deleteUncertainty(p.id)
  if (current.value && current.value.id === p.id) current.value = null
  ElMessage.success('已删除')
  await loadProjects()
}
function cancelEdit() {
  editingId.value = null
  clearForm()
}
function clearForm() {
  editingId.value = null
  Object.assign(form, {
    project_name: '', project_code: '', instrument: '', reagent: '',
    eval_date: todayStr(), cycle_months: 12,
    prepared_by: auth.user?.full_name || auth.user?.username || '金子铮', reviewed_by: '杨静',
    l1: Array(20).fill(''), l2: Array(20).fill(''),
    pt_result: '合格', target1: '', value1: '', target2: '', value2: '', target3: '', value3: '', ucal: 0,
  })
  current.value = null
}

// ---------- 报告生成（HTML） ----------
function reportStyle() {
  return `body{font-family:"SimSun",serif;margin:20px;font-size:12pt;color:#000}
h1{text-align:center;font-size:18pt;margin:4px 0}
h2{font-size:14pt;margin-top:20px;border-bottom:1px solid #333;padding-bottom:5px}
table{width:100%;border-collapse:collapse;margin:10px 0}
td,th{border:1px solid #333;padding:7px;font-size:11pt}
th{background:#f0f0f0;text-align:center}
.info-table td{width:25%}
.data-table td,.data-table th{text-align:center}
.sign{display:flex;justify-content:space-between;margin-top:40px}
.footer{margin-top:30px}
p{text-indent:2em;line-height:1.7}
@media print{body{margin:0}}`
}
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function buildSingleReport(p) {
  const uBias = p.pt_result === '合格' ? 0 : p.bias_rms || 0
  const uc1 = Math.sqrt((p.l1_cv || 0) ** 2 + uBias ** 2 + (p.ucal || 0) ** 2)
  const uc2 = Math.sqrt((p.l2_cv || 0) ** 2 + uBias ** 2 + (p.ucal || 0) ** 2)
  const j1 = p.l1_passed ? '合格' : '待改进'
  const j2 = p.l2_passed ? '合格' : '待改进'
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告</title><style>${reportStyle()}</style></head><body>
<div style="page-break-after: always">
  <div class="header"><h1>民航总医院检验科生化免疫组</h1><h1>测量不确定度评定报告</h1></div>
  <table class="info-table">
    <tr><td><strong>表格编号</strong></td><td>${REPORT_CODE}</td><td><strong>版本号</strong></td><td>${REPORT_VERSION}</td></tr>
    <tr><td><strong>颁布部门</strong></td><td>生化免疫组</td><td><strong>生效日期</strong></td><td>${REPORT_DATE}</td></tr>
    <tr><td><strong>项目名称</strong></td><td>${esc(p.project_name)}</td><td><strong>项目编号</strong></td><td>${esc(p.project_code || '-')}</td></tr>
    <tr><td><strong>检测系统</strong></td><td>${esc(p.instrument || '-')}</td><td><strong>试剂/校准品</strong></td><td>${esc(p.reagent || '-')}</td></tr>
    <tr><td><strong>评定日期</strong></td><td>${esc(p.eval_date || '-')}</td><td><strong>评定周期</strong></td><td>${p.cycle_months || 12} 个月</td></tr>
    <tr><td><strong>编制人</strong></td><td>${esc(p.prepared_by || '金子铮')}</td><td><strong>审核人</strong></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
  </table>
  <h2>一、测量不确定度评定方法概述</h2>
  <p>本评定依据《医学实验室质量和能力认可准则》（ISO 15189）及《生化免疫组测量不确定度评定作业指导书》（SM-SOP-024）进行。</p>
  <p><strong>1. 评定模型：</strong>采用"自上而下"法，综合考虑不精密度、偏倚和校准品不确定度三个分量。</p>
  <p><strong>2. 合成公式：</strong>U<sub>c</sub> = √(u<sub>Rw</sub>² + u<sub>Bias</sub>² + u<sub>Cal</sub>²)；扩展不确定度 U = k × U<sub>c</sub>（k=2，包含概率 P≈95.45%）</p>
  <p><strong>3. 各分量来源：</strong>u<sub>Rw</sub>（重复性，由室内质控 CV% 计算）；u<sub>Bias</sub>（偏倚，由室间质评 RMS 偏倚计算，质评合格时为 0）；u<sub>Cal</sub>（校准，由校准品厂家提供）。</p>
  <h2>二、不精密度评估（L1 水平）</h2>
  <table class="data-table"><tr><th>测量次数(n)</th><th>平均值</th><th>标准差</th><th>变异系数(CV%)</th><th>uRw(%)</th></tr>
  <tr><td>${(p.l1_values || []).length}</td><td>${(p.l1_mean || 0).toFixed(2)}</td><td>${(p.l1_sd || 0).toFixed(2)}</td><td>${(p.l1_cv || 0).toFixed(2)}</td><td>${(p.l1_cv || 0).toFixed(2)}</td></tr></table>
  <h2>三、不精密度评估（L2 水平）</h2>
  <table class="data-table"><tr><th>测量次数(n)</th><th>平均值</th><th>标准差</th><th>变异系数(CV%)</th><th>uRw(%)</th></tr>
  <tr><td>${(p.l2_values || []).length}</td><td>${(p.l2_mean || 0).toFixed(2)}</td><td>${(p.l2_sd || 0).toFixed(2)}</td><td>${(p.l2_cv || 0).toFixed(2)}</td><td>${(p.l2_cv || 0).toFixed(2)}</td></tr></table>
  <h2>四、偏倚评估</h2>
  <table class="data-table"><tr><th>RMS偏倚(%)</th><th>室间质评结果</th><th>偏倚分量处理</th><th>校准品不确定度Ucal(%)</th></tr>
  <tr><td>${(p.bias_rms || 0).toFixed(2)}</td><td>${p.pt_result === '合格' ? '合格' : '不合格'}</td><td>${p.pt_result === '合格' ? '不采用（已含于精密度）' : '采用'}</td><td>${(p.ucal || 0).toFixed(2)}</td></tr></table>
  <h2>五、测量不确定度计算</h2>
  <table class="data-table"><tr><th>水平</th><th>uRw(%)</th><th>uBias(%)</th><th>uCal(%)</th><th>Uc(%)</th><th>U(%) k=2</th><th>判定</th></tr>
  <tr><td>L1 水平</td><td>${(p.l1_cv || 0).toFixed(2)}</td><td>${uBias.toFixed(2)}</td><td>${(p.ucal || 0).toFixed(2)}</td><td>${uc1.toFixed(2)}</td><td><strong>${(p.l1_u || 0).toFixed(2)}</strong></td><td>${j1}</td></tr>
  <tr><td>L2 水平</td><td>${(p.l2_cv || 0).toFixed(2)}</td><td>${uBias.toFixed(2)}</td><td>${(p.ucal || 0).toFixed(2)}</td><td>${uc2.toFixed(2)}</td><td><strong>${(p.l2_u || 0).toFixed(2)}</strong></td><td>${j2}</td></tr></table>
  <h2>六、评定结论</h2>
  <p>根据《生化免疫组测量不确定度评定作业指导书》(SM-SOP-024)，对本项目进行了测量不确定度评定。</p>
  <p>计算公式：Uc = sqrt(uRw² + uBias² + uCal²)，U = k × Uc（k=2，包含概率 P=95.45%）。</p>
  <p><strong>结论：</strong>L1 水平扩展不确定度 U = ${(p.l1_u || 0).toFixed(2)}%，L2 水平扩展不确定度 U = ${(p.l2_u || 0).toFixed(2)}%。${p.l1_passed && p.l2_passed ? '满足目标不确定度要求。' : '部分指标待改进。'}</p>
  <div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div><div>批准人签字：____________</div></div>
  <div style="text-align:right;margin-top:20px">日期：____________</div>
</div></body></html>`
}
function buildSummaryReport(list) {
  const rows = list.map((p, i) => `<tr>
    <td>${i + 1}</td><td>${esc(p.project_code || '-')}</td><td>${esc(p.project_name)}</td><td>${esc(p.instrument || '-')}</td>
    <td>${(p.l1_u || 0).toFixed(2)}</td><td>${(p.l2_u || 0).toFixed(2)}</td><td>${(p.bias_rms || 0).toFixed(2)}</td>
    <td>${(p.ucal || 0).toFixed(2)}</td><td>${esc(p.eval_date || '-')}</td><td>${p.cycle_months || 12}</td>
    <td>${p.l1_passed && p.l2_passed ? '已完成' : '待改进'}</td><td></td></tr>`).join('')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title><style>${reportStyle()}</style></head><body>
  <div class="header"><h1>民航总医院检验科生化免疫组</h1><h1>测量不确定度评定汇总表</h1>
  <p>表格编号：BG-SM-GL-020 | 版本号：01 | 生效日期：2025.01.01</p><p>编制日期：${todayStr()}</p></div>
  <table><tr><th>序号</th><th>项目编号</th><th>项目名称</th><th>检测系统</th><th>L1水平 U(%)</th><th>L2水平 U(%)</th><th>偏倚(%)</th><th>校准品不确定度(%)</th><th>评定日期</th><th>周期(月)</th><th>状态</th><th>备注</th></tr>${rows}</table>
  <div style="margin-top:40px"><p><strong>说明：</strong></p>
  <p>1. 本表汇总本科室所有定量检验项目的测量不确定度评定结果。</p>
  <p>2. 评定周期为 12 个月，期满需重新评定。</p>
  <p>3. 扩展不确定度 U 包含概率约为 95.45%（k=2）。</p>
  <p>4. 目标不确定度参考：U &lt; 15% 为基本要求。</p></div>
  <div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div><div>批准人签字：____________</div></div>
</body></html>`
}

// ---------- 预览 / 下载 ----------
function previewOne(p) {
  previewTitle.value = `测量不确定度评定报告 - ${p.project_name}`
  previewHtml.value = buildSingleReport(p)
  previewOpen.value = true
}
function previewSingle() {
  const p = current.value || projects.value[0]
  if (p) previewOne(p)
}
function previewSummary() {
  previewTitle.value = '测量不确定度评定汇总表'
  previewHtml.value = buildSummaryReport(projects.value)
  previewOpen.value = true
}
function downloadHtml(html, name) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = name
  a.click()
  URL.revokeObjectURL(url)
}
function downloadSingle() {
  const p = current.value || projects.value[0]
  if (!p) return
  downloadHtml(buildSingleReport(p), `测量不确定度评定报告_${p.project_name || '项目'}_${todayStr()}.html`)
}
function downloadSummary() {
  downloadHtml(buildSummaryReport(projects.value), `测量不确定度评定汇总表_${todayStr()}.html`)
}
function downloadCurrentHtml() {
  const html = previewHtml.value
  if (html) downloadHtml(html, `${previewTitle.value || '测量不确定度报告'}_${todayStr()}.html`)
}

onMounted(loadProjects)
</script>

<style scoped>
.uncert-page { padding: 4px 8px; }
.uncert-header { margin-bottom: 14px; }
.uncert-header h2 { margin: 0 0 4px; color: #303133; }
.uncert-header span { font-size: 13px; color: #909399; }
.data-block { background: #f7fafc; border-radius: 10px; padding: 14px; margin-bottom: 14px; border: 1px solid #e4e7ed; }
.data-block-title { font-size: 14px; font-weight: 600; color: #4a5568; margin-bottom: 10px; }
.data-grid { display: grid; grid-template-columns: repeat(5, 1fr); gap: 6px; margin-bottom: 10px; }
.data-cell { width: 100%; }
.stats-bar { border-radius: 8px; padding: 10px 14px; color: #fff; display: flex; gap: 18px; }
.stats-bar .stat-item { flex: 1; text-align: center; }
.stats-bar .stat-item label { display: block; font-size: 11px; opacity: .85; margin-bottom: 2px; }
.stats-bar .stat-item b { font-size: 16px; color: #ffd700; }
.bias-box { background: #fff5f5; border: 1px solid #fde2e2; border-radius: 8px; padding: 10px; margin-bottom: 12px; }
.bias-tip { font-size: 12px; color: #c53030; margin-bottom: 8px; }
.btn-row { margin-top: 6px; display: flex; gap: 8px; flex-wrap: wrap; }
.result-box { border: 2px solid #e2e8f0; border-radius: 10px; padding: 8px 16px; }
.res-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid #eef1f5; font-size: 14px; color: #4a5568; }
.res-row:last-child { border-bottom: none; }
.res-row .hl { color: #409eff; font-size: 17px; font-weight: 700; }
.project-list { max-height: 420px; overflow-y: auto; }
.project-item { display: flex; justify-content: space-between; align-items: center; background: #f7fafc; border: 1px solid #e4e7ed; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.p-name { font-weight: 600; color: #2d3748; }
.p-meta { font-size: 12px; color: #718096; }
.p-actions { display: flex; gap: 6px; }
</style>
