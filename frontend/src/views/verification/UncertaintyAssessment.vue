<template>
  <div class="uncert-page">
    <div class="uncert-header">
      <h2>测量不确定度评估</h2>
      <span>民航总医院检验科生化免疫组 | BG-SM-CZ-072 | 2026-08-18 重构版</span>
    </div>

    <el-row :gutter="16">
      <!-- 左侧：数据输入 -->
      <el-col :span="14" :xs="24">
        <el-card shadow="never">
          <template #header><b>📝 项目信息与数据输入</b></template>

          <el-form label-width="100px" label-position="right">
            <el-row :gutter="12">
              <el-col :span="12"><el-form-item label="项目名称" required>
                <el-input v-model="form.project_name" placeholder="如：ALT（丙氨酸氨基转移酶）" @blur="onProjectChange" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="项目编号">
                <el-input v-model="form.project_code" placeholder="如：SM-SOP-101" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="检测系统/仪器">
                <el-input v-model="form.instrument" :placeholder="form.mode === 'multi' ? '如：贝克曼 AU5800（多系统用 A/B/C 区分）' : '如：贝克曼 AU5800'" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="试剂/校准品">
                <el-input v-model="form.reagent" placeholder="如：贝克曼原装试剂" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="报告单位">
                <el-input v-model="form.patient_unit" placeholder="如：U/L、mmol/L、ng/mL" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="评定日期">
                <el-date-picker v-model="form.eval_date" type="date" value-format="YYYY-MM-DD" style="width:100%" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="评定周期(月)">
                <el-input-number v-model="form.cycle_months" :min="1" :max="36" style="width:100%" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="编制人">
                <el-input v-model="form.prepared_by" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="审核人">
                <el-input v-model="form.reviewed_by" />
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="患者结果(可选)">
                <el-input-number v-model="form.patient_value" :min="0" :precision="4" style="width:100%" />
              </el-form-item></el-col>
            </el-row>

            <!-- 测量系统模式选择 -->
            <div class="data-block">
              <div class="data-block-title">🔬 测量系统模式</div>
              <el-radio-group v-model="form.mode" @change="onModeChange" style="width:100%">
                <el-radio-button value="single">📊 单个测量系统</el-radio-button>
                <el-radio-button value="multi">🔗 多个测量系统（合并评定）</el-radio-button>
              </el-radio-group>
              <div class="mode-tip" v-if="form.mode === 'single'">
                💡 录入 L1/L2 两个水平室内质控的<b>均值、标准差、测试数</b>（一般采用 <b>≥6 个月</b> 的质控数据，保证长期精密度评估的代表性）
              </div>
              <div class="mode-tip" v-else>
                💡 工作量大的实验室可能使用几个相同的测量系统检测同一被测量。每个系统分别录入 L1/L2 的<b>均值、标准差、测试数</b>，系统内不精密度与系统间均值方差合并后算 u<sub>(pooled)</sub>
              </div>
            </div>

            <!-- 单个系统：L1/L2 数据 -->
            <div v-if="form.mode === 'single'" class="data-block">
              <div class="data-block-title">📈 单系统室内质控数据（≥6 个月）</div>
              <el-row :gutter="12">
                <el-col :span="12">
                  <div class="level-tag" style="background:#67c23a">L1 水平</div>
                  <el-form-item label="均值" label-width="60px">
                    <el-input-number v-model="form.l1_mean" :min="0" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="标准差" label-width="60px">
                    <el-input-number v-model="form.l1_sd" :min="0" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="测试数 n" label-width="60px">
                    <el-input-number v-model="form.l1_n" :min="0" :precision="0" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <div class="level-tag" style="background:#e6a23c">L2 水平</div>
                  <el-form-item label="均值" label-width="60px">
                    <el-input-number v-model="form.l2_mean" :min="0" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="标准差" label-width="60px">
                    <el-input-number v-model="form.l2_sd" :min="0" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="测试数 n" label-width="60px">
                    <el-input-number v-model="form.l2_n" :min="0" :precision="0" style="width:100%" />
                  </el-form-item>
                </el-col>
              </el-row>
              <div v-if="singlePreview" class="formula">
                u<sub>Rw</sub> = √[(RSD<sub>L1</sub>² × (n<sub>L1</sub>-1) + RSD<sub>L2</sub>² × (n<sub>L2</sub>-1)) / (n<sub>L1</sub>+n<sub>L2</sub>-2)]
                = √[{{ singlePreview.rsd1 }}²×{{ singlePreview.l1_n-1 }} + {{ singlePreview.rsd2 }}²×{{ singlePreview.l2_n-1 }}] / {{ singlePreview.l1_n + singlePreview.l2_n - 2 }}
                = <b>{{ singlePreview.u_rw }}%</b>
              </div>
            </div>

            <!-- 多个系统：每个系统录 L1/L2 -->
            <div v-else class="data-block">
              <div class="data-block-title">🔗 多系统室内质控数据（每个系统分别录入 L1/L2）</div>
              <div class="mode-tip">系统名称（如 A/B/C），每个系统分别录入其 L1、L2 的均值/标准差/测试数。</div>
              <div v-for="(s, idx) in form.multi_systems" :key="idx" class="sys-row">
                <div class="sys-header">
                  <span class="sys-title">系统 {{ String.fromCharCode(65 + idx) }}</span>
                  <el-button v-if="form.multi_systems.length > 2" size="small" type="danger" plain @click="form.multi_systems.splice(idx, 1)">删除</el-button>
                </div>
                <el-row :gutter="8">
                  <el-col :span="6"><el-form-item label="名称" label-width="48px"><el-input v-model="s.name" :placeholder="'系统' + String.fromCharCode(65+idx)" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L1 均值" label-width="60px"><el-input-number v-model="s.l1_mean" :min="0" :precision="4" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L1 SD" label-width="48px"><el-input-number v-model="s.l1_sd" :min="0" :precision="4" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L1 n" label-width="48px"><el-input-number v-model="s.l1_n" :min="0" :precision="0" style="width:100%" /></el-form-item></el-col>
                </el-row>
                <el-row :gutter="8">
                  <el-col :span="6"><el-form-item label="L2 均值" label-width="60px"><el-input-number v-model="s.l2_mean" :min="0" :precision="4" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L2 SD" label-width="48px"><el-input-number v-model="s.l2_sd" :min="0" :precision="4" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L2 n" label-width="48px"><el-input-number v-model="s.l2_n" :min="0" :precision="0" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6">
                    <div class="sys-cov" v-if="s.l1_mean > 0 && s.l2_mean > 0">
                      L1 RSD {{ ((s.l1_sd / s.l1_mean) * 100).toFixed(2) }}%<br/>
                      L2 RSD {{ ((s.l2_sd / s.l2_mean) * 100).toFixed(2) }}%
                    </div>
                  </el-col>
                </el-row>
              </div>
              <el-button size="small" plain @click="addSystem">+ 增加测量系统</el-button>
              <div v-if="multiPreview" class="formula">
                <p>① 测量系统内平均不精密度方差 u²<sub>Rw(A,B,C)</sub> = (RSD1²+RSD2²)/2 各系统平均
                  = <b>{{ multiPreview.u2_within }}</b></p>
                <p>② 系统平均值的方差（水平内合并） u²<sub>均值方差</sub> = (RSD<sub>L1均值</sub>² + RSD<sub>L2均值</sub>²) / 2
                  = <b>{{ multiPreview.u2_between }}</b></p>
                <p>③ 合并：u<sub>(pooled)</sub> = √(u²<sub>均值方差</sub> + u²<sub>Rw</sub>)
                  = √({{ multiPreview.u2_between }} + {{ multiPreview.u2_within }})
                  = <b>{{ multiPreview.u_pooled }}%</b></p>
                <p>④ u<sub>rel(pooled)</sub> = {{ multiPreview.u_pooled }} / {{ multiPreview.overall_mean }} × 100
                  = <b>{{ multiPreview.u_rel }}%</b></p>
              </div>
            </div>

            <!-- 校准品不确定度 -->
            <div class="data-block">
              <div class="data-block-title">🎯 校准品不确定度</div>
              <el-form-item label="u_cal (%)">
                <el-input-number v-model="form.ucal" :min="0" :precision="2" :step="0.1" style="width:180px" />
                <span style="margin-left:8px;color:#909399;font-size:12px">厂家提供相对标准不确定度（%），填 0 表示厂家未提供</span>
              </el-form-item>
              <el-form-item label="来源">
                <el-radio-group v-model="form.ucal_source">
                  <el-radio value="厂家">厂家提供</el-radio>
                  <el-radio value="有证标准物质">有证标准物质</el-radio>
                </el-radio-group>
              </el-form-item>
            </div>

            <!-- 室间质评偏倚 -->
            <div class="data-block">
              <div class="data-block-title">🧪 室间质评（EQA）偏倚</div>
              <el-form-item label="EQA 成绩">
                <el-radio-group v-model="form.pt_result">
                  <el-radio value="合格">合格</el-radio>
                  <el-radio value="不合格">不合格</el-radio>
                </el-radio-group>
              </el-form-item>

              <div v-if="form.pt_result === '合格'" class="mode-tip">
                ✅ EQA 成绩合格，偏倚已含于精密度，<b>不需填写偏倚数据</b>（bias = 0）。
              </div>

              <div v-else>
                <div class="mode-tip" style="margin-bottom:8px">
                  ⚠️ EQA 成绩不合格，请填写 <b>5 个水平</b>的靶值与测量值，系统按 RMS（均方根）计算偏倚：
                  bias<sub>RMS</sub> = √(Σ((测量值-靶值)/靶值×100%)² / n)，并纳入合成不确定度。
                </div>
                <el-table :data="form.bias_levels" border size="small" style="margin-bottom:8px">
                  <el-table-column label="水平" width="70" align="center">
                    <template #default="{ $index }">第{{ $index + 1 }}水平</template>
                  </el-table-column>
                  <el-table-column label="靶值（参考值）">
                    <template #default="{ row }">
                      <el-input-number v-model="row.target" :min="0" :precision="4" :controls="false" style="width:100%" placeholder="靶值" />
                    </template>
                  </el-table-column>
                  <el-table-column label="测量值">
                    <template #default="{ row }">
                      <el-input-number v-model="row.measured" :min="0" :precision="4" :controls="false" style="width:100%" placeholder="测量值" />
                    </template>
                  </el-table-column>
                  <el-table-column label="偏倚 %" width="100" align="center">
                    <template #default="{ row }">
                      <span v-if="Number(row.target) > 0 && Number(row.measured) > 0">
                        {{ (((Number(row.measured) - Number(row.target)) / Number(row.target)) * 100).toFixed(2) }}%
                      </span>
                      <span v-else style="color:#c0c4cc">—</span>
                    </template>
                  </el-table-column>
                </el-table>
                <div class="formula" v-if="rmsBias > 0">
                  bias<sub>RMS</sub> = √(Σ bias<sub>i</sub>² / {{ biasRows.length }})
                  = <b>{{ rmsBias.toFixed(2) }}%</b>
                </div>
              </div>
            </div>

            <div class="btn-row">
              <el-button type="primary" :loading="saving" @click="save">💾 保存并计算</el-button>
              <el-button @click="clearForm">🔄 清空</el-button>
              <el-button v-if="editingId" @click="cancelEdit">取消编辑</el-button>
            </div>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：实时结果与列表 -->
      <el-col :span="10" :xs="24">
        <el-card shadow="never">
          <template #header><b>📋 计算结果与质量目标</b></template>

          <div v-if="current" class="result-box">
            <div class="res-row"><span>项目</span><b>{{ current.project_name }}</b></div>
            <div class="res-row"><span>模式</span>
              <el-tag size="small">{{ current.mode === 'multi' ? '多测量系统' : '单测量系统' }}</el-tag>
            </div>
            <div class="res-row"><span>不精密度 u<sub>Rw</sub></span><b>{{ fmtPct(current.u_rw) }}</b></div>
            <div class="res-row"><span>校准品不确定度 u<sub>cal</sub></span><b>{{ fmtPct(current.ucal) }}</b></div>
            <div class="res-row"><span>合成不确定度 u<sub>c</sub></span><b>{{ fmtPct(current.u_c) }}</b></div>
            <div class="res-row"><span>扩展不确定度 U (k=2)</span><b class="hl">{{ fmtPct(current.u_extended) }}</b></div>
            <div class="divider"></div>
            <div class="res-row" v-if="current.target_bias">
              <span>质量目标（允许偏倚）</span>
              <b class="hl2">{{ fmtPct(current.target_bias) }}</b>
            </div>
            <div class="res-row" v-if="current.target_bias_source" style="font-size:12px;color:#909399">
              <span>来源</span>
              <span>{{ current.target_bias_source }}（{{ current.target_bias_text }}）</span>
            </div>
            <div class="res-row" v-if="!current.target_bias">
              <span>质量目标</span>
              <el-tag type="info" size="small">未查到允许偏倚（兜底按 U&lt;15% 判定）</el-tag>
            </div>
            <div class="res-row">
              <span>结论</span>
              <el-tag v-if="current.passed" type="success" size="small">✅ 符合要求</el-tag>
              <el-tag v-else type="danger" size="small">❌ 未达标</el-tag>
            </div>
            <div v-if="form.patient_value > 0" class="res-row" style="background:#f0f9ff;padding:6px 10px;margin:4px 0;border-radius:4px">
              <span>患者结果</span>
              <span><b>{{ form.patient_value }}</b> ± <b>{{ (form.patient_value * current.u_extended / 100).toFixed(4) }}</b> {{ form.patient_unit || '—' }}</span>
            </div>
            <div class="btn-row" style="margin-top:10px">
              <el-button size="small" type="primary" @click="previewOne(current)">📄 预览报告</el-button>
              <el-button size="small" type="success" @click="downloadOne(current)">⬇️ 下载报告</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无计算结果，请在左侧录入并保存" :image-size="70" />

          <div class="btn-row" style="margin-top:14px">
            <el-button :disabled="!projects.length" @click="previewSummary">📑 预览汇总表</el-button>
            <el-button :disabled="!projects.length" @click="downloadSummary">⬇️ 下载汇总表</el-button>
          </div>

          <el-divider>已保存项目（{{ projects.length }}）</el-divider>
          <div class="project-list">
            <div v-for="p in projects" :key="p.id" class="project-item">
              <div class="p-info">
                <div class="p-name">
                  {{ p.project_name }}
                  <el-tag v-if="p.mode === 'multi'" size="small" type="warning" style="margin-left:4px">多系统</el-tag>
                </div>
                <div class="p-meta">
                  {{ p.eval_date || '未设日期' }} | U={{ fmtPct(p.u_extended) }} | 目标={{ fmtPct(p.target_bias) }}
                  <el-tag v-if="p.passed" type="success" size="small" style="margin-left:4px">✅</el-tag>
                  <el-tag v-else type="danger" size="small" style="margin-left:4px">❌</el-tag>
                </div>
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
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../../utils/request'
import { downloadReportArchive } from '../../api/reportArchives'
import { useAuthStore } from '../../store/auth'

const auth = useAuthStore()
const projects = ref([])
const current = ref(null)
const saving = ref(false)
const editingId = ref(null)
const previewOpen = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')

const todayStr = () => {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

const form = reactive({
  project_name: '', project_code: '', instrument: '', reagent: '',
  eval_date: todayStr(), cycle_months: 6,
  prepared_by: auth.user?.full_name || auth.user?.username || '金子铮',
  reviewed_by: '杨静',
  mode: 'single',
  // 单系统
  l1_mean: 0, l1_sd: 0, l1_n: 0,
  l2_mean: 0, l2_sd: 0, l2_n: 0,
  // 多系统
  multi_systems: defaultMultiSystems(),
  // 校准品
  ucal: 0, ucal_source: '厂家',
  // 患者
  patient_value: 0, patient_unit: '',
  // 室间质评（EQA）偏倚
  pt_result: '合格',
  bias_levels: defaultBiasLevels(),
})

function defaultMultiSystems() {
  return [
    { name: 'A', l1_mean: 0, l1_sd: 0, l1_n: 0, l2_mean: 0, l2_sd: 0, l2_n: 0 },
    { name: 'B', l1_mean: 0, l1_sd: 0, l1_n: 0, l2_mean: 0, l2_sd: 0, l2_n: 0 },
    { name: 'C', l1_mean: 0, l1_sd: 0, l1_n: 0, l2_mean: 0, l2_sd: 0, l2_n: 0 },
  ]
}

function defaultBiasLevels() {
  return [
    { target: 0, measured: 0 },
    { target: 0, measured: 0 },
    { target: 0, measured: 0 },
    { target: 0, measured: 0 },
    { target: 0, measured: 0 },
  ]
}

function fmtPct(v) {
  if (v == null || v === '' || isNaN(Number(v))) return '—'
  return Number(v).toFixed(2) + '%'
}

// ───────── 室间质评偏倚（5 水平 → RMS 相对偏倚） ─────────
const biasLevelsValid = computed(() =>
  form.bias_levels.filter(lv => Number(lv.target) > 0 && Number(lv.measured) > 0)
)
const biasRows = computed(() =>
  biasLevelsValid.value.map(lv => {
    const t = Number(lv.target), m = Number(lv.measured)
    const b = (m - t) / t * 100
    return { target: t, measured: m, bias: b }
  })
)
const rmsBias = computed(() => {
  const rows = biasRows.value
  if (!rows.length) return 0
  const sq = rows.reduce((s, r) => s + r.bias ** 2, 0)
  return Math.sqrt(sq / rows.length)
})

// ───────── 实时预览（前端计算 + 后端 _preview） ─────────
const singlePreview = computed(() => {
  if (form.mode !== 'single') return null
  const { l1_mean, l1_sd, l1_n, l2_mean, l2_sd, l2_n } = form
  if (l1_n < 2 || l2_n < 2 || l1_mean <= 0 || l2_mean <= 0) return null
  const rsd1 = l1_sd / l1_mean * 100
  const rsd2 = l2_sd / l2_mean * 100
  const u_rw = Math.sqrt((rsd1 ** 2 * (l1_n - 1) + rsd2 ** 2 * (l2_n - 1)) / (l1_n + l2_n - 2))
  return { rsd1: rsd1.toFixed(2), rsd2: rsd2.toFixed(2), l1_n, l2_n, u_rw: u_rw.toFixed(2) }
})

const multiPreview = computed(() => {
  if (form.mode !== 'multi') return null
  const sys = form.multi_systems.filter(s => s.l1_mean > 0 && s.l2_mean > 0)
  if (sys.length < 2) return null
  const per_sys_rsd_sq = []
  const l1_means = [], l2_means = []
  for (const s of sys) {
    const rsd1 = s.l1_sd / s.l1_mean * 100
    const rsd2 = s.l2_sd / s.l2_mean * 100
    per_sys_rsd_sq.push((rsd1 ** 2 + rsd2 ** 2) / 2)
    l1_means.push(s.l1_mean); l2_means.push(s.l2_mean)
  }
  const u2_within = per_sys_rsd_sq.reduce((a, b) => a + b, 0) / per_sys_rsd_sq.length
  function meanRsdPct(arr) {
    if (arr.length < 2) return 0
    const avg = arr.reduce((a, b) => a + b, 0) / arr.length
    if (avg <= 0) return 0
    const var_ = arr.reduce((s, v) => s + (v - avg) ** 2, 0) / (arr.length - 1)
    return Math.sqrt(var_) / avg * 100
  }
  const l1_rsd = meanRsdPct(l1_means)
  const l2_rsd = meanRsdPct(l2_means)
  const u2_between = (l1_rsd ** 2 + l2_rsd ** 2) / 2
  const u_pooled = Math.sqrt(u2_within + u2_between)
  const total = (l1_means.reduce((a, b) => a + b, 0) / l1_means.length + l2_means.reduce((a, b) => a + b, 0) / l2_means.length) / 2
  const u_rel = u_pooled / total * 100
  return {
    u2_within: u2_within.toFixed(4),
    u2_between: u2_between.toFixed(4),
    u_pooled: u_pooled.toFixed(4),
    overall_mean: total.toFixed(4),
    u_rel: u_rel.toFixed(2),
  }
})

// 项目名变更时去查允许偏倚
let lookupTimer = null
async function onProjectChange() {
  clearTimeout(lookupTimer)
  if (!form.project_name || form.project_name.length < 2) return
  lookupTimer = setTimeout(async () => {
    try {
      const tg = await request.get('/api/v1/uncertainty/_lookup_target_bias', { params: { project_name: form.project_name } })
      if (tg && tg.bias) {
        ElMessage.info(`找到目标允许偏倚 ${tg.bias}%（来源：${tg.source}）`)
      } else {
        ElMessage.warning('未找到该项目的允许偏倚，将兜底按 U<15% 判定')
      }
    } catch (e) { /* ignore */ }
  }, 400)
}

function onModeChange() {
  if (form.mode === 'multi' && (!form.multi_systems || form.multi_systems.length < 2)) {
    form.multi_systems = defaultMultiSystems()
  }
}
function addSystem() {
  const ch = String.fromCharCode(65 + (form.multi_systems.length || 0))
  form.multi_systems.push({ name: ch, l1_mean: 0, l1_sd: 0, l1_n: 0, l2_mean: 0, l2_sd: 0, l2_n: 0 })
}

// ───────── 保存 ─────────
async function save() {
  if (!form.project_name.trim()) { ElMessage.warning('请输入项目名称'); return }
  // 模式数据校验
  if (form.mode === 'single') {
    if (form.l1_n < 2 || form.l2_n < 2) { ElMessage.warning('L1/L2 测试数 n 必须 ≥ 2（建议 ≥ 6 个月数据）'); return }
    if (form.l1_mean <= 0 || form.l2_mean <= 0) { ElMessage.warning('请填入 L1/L2 的均值（>0）'); return }
  } else {
    const valid = form.multi_systems.filter(s => s.l1_mean > 0 && s.l2_mean > 0)
    if (valid.length < 2) { ElMessage.warning('多系统模式至少需要 2 个有效测量系统'); return }
  }
  const payload = {
    project_name: form.project_name.trim(),
    project_code: form.project_code,
    instrument: form.instrument,
    reagent: form.reagent,
    eval_date: form.eval_date,
    cycle_months: form.cycle_months,
    prepared_by: form.prepared_by || '金子铮',
    reviewed_by: form.reviewed_by || '杨静',
    mode: form.mode,
    ucal: form.ucal,
    ucal_source: form.ucal_source,
    l1_mean: form.l1_mean, l1_sd: form.l1_sd, l1_n: form.l1_n,
    l2_mean: form.l2_mean, l2_sd: form.l2_sd, l2_n: form.l2_n,
    multi_systems: form.mode === 'multi' ? form.multi_systems : [],
    patient_value: form.patient_value,
    patient_unit: form.patient_unit,
    pt_result: form.pt_result || '合格',
    bias_levels: form.pt_result === '不合格' ? form.bias_levels : [],
  }
  saving.value = true
  try {
    // 先调 _preview 拿完整计算结果 + 目标偏倚
    const preview = await request.post('/api/v1/uncertainty/_preview', payload)
    const full = { ...payload, ...preview }
    let rec
    if (editingId.value) {
      try {
        rec = await request.put(`/api/v1/uncertainty/${editingId.value}`, full)
        ElMessage.success('已保存修改')
      } catch (putErr) {
        // 编辑的记录可能已被删除（404 未找到记录）→ 降级为新建，避免卡死
        if (putErr?.response?.status === 404) {
          rec = await request.post('/api/v1/uncertainty', full)
          ElMessage.warning('原记录已不存在，已转为新建保存')
        } else {
          throw putErr
        }
      }
    } else {
      rec = await request.post('/api/v1/uncertainty', full)
      ElMessage.success('保存成功')
    }
    current.value = rec
    editingId.value = null
    // 自动生成报告归档
    try { await request.post(`/api/v1/uncertainty/${rec.id}/generate`) } catch (e) {}
    await loadProjects()
  } catch (e) {
    // 正确序列化后端返回的 detail（可能是字符串/数组/对象），避免显示成 [object Object]
    let msg = '未知错误'
    const detail = e?.response?.data?.detail
    if (typeof detail === 'string') {
      msg = detail
    } else if (Array.isArray(detail)) {
      msg = detail.map(d => d?.msg || JSON.stringify(d)).join('；')
    } else if (detail) {
      msg = JSON.stringify(detail)
    } else if (e?.message) {
      msg = e.message
    }
    console.error('[uncertainty save] 完整错误：', e)
    ElMessage.error('保存失败：' + msg)
  } finally {
    saving.value = false
  }
}

async function loadProjects() {
  try {
    const res = await request.get('/api/v1/uncertainty', { params: { page_size: 300 } })
    projects.value = (res && (res.items || res)) || []
  } catch (e) {
    ElMessage.error('加载失败：' + (e?.response?.data?.detail || e?.message))
  }
}
function loadProject(p) {
  editingId.value = p.id
  form.mode = p.mode || 'single'
  form.project_name = p.project_name || ''
  form.project_code = p.project_code || ''
  form.instrument = p.instrument || ''
  form.reagent = p.reagent || ''
  form.eval_date = p.eval_date || todayStr()
  form.cycle_months = p.cycle_months || 6
  form.prepared_by = p.prepared_by || '金子铮'
  form.reviewed_by = p.reviewed_by || '杨静'
  form.ucal = p.ucal || 0
  form.ucal_source = p.ucal_source || '厂家'
  form.l1_mean = p.l1_mean || 0; form.l1_sd = p.l1_sd || 0; form.l1_n = p.l1_n || 0
  form.l2_mean = p.l2_mean || 0; form.l2_sd = p.l2_sd || 0; form.l2_n = p.l2_n || 0
  try {
    form.multi_systems = (typeof p.multi_systems === 'string') ? JSON.parse(p.multi_systems) : (p.multi_systems || defaultMultiSystems())
    if (!Array.isArray(form.multi_systems) || form.multi_systems.length < 2) form.multi_systems = defaultMultiSystems()
  } catch (e) { form.multi_systems = defaultMultiSystems() }
  form.patient_value = p.patient_value || 0
  form.patient_unit = p.patient_unit || ''
  form.pt_result = p.pt_result || '合格'
  try {
    form.bias_levels = (typeof p.bias_levels === 'string') ? JSON.parse(p.bias_levels) : (p.bias_levels || defaultBiasLevels())
    if (!Array.isArray(form.bias_levels)) form.bias_levels = defaultBiasLevels()
    while (form.bias_levels.length < 5) form.bias_levels.push({ target: 0, measured: 0 })
  } catch (e) { form.bias_levels = defaultBiasLevels() }
  current.value = p
  ElMessage.info('已载入，可修改后保存')
}
async function delProject(p) {
  await ElMessageBox.confirm(`确认删除「${p.project_name}」的评定记录？`, '提示', { type: 'warning' })
  await request.delete(`/api/v1/uncertainty/${p.id}`)
  if (current.value && current.value.id === p.id) current.value = null
  ElMessage.success('已删除')
  await loadProjects()
}
function cancelEdit() { editingId.value = null; clearForm() }
function clearForm() {
  editingId.value = null
  Object.assign(form, {
    project_name: '', project_code: '', instrument: '', reagent: '',
    eval_date: todayStr(), cycle_months: 6,
    prepared_by: auth.user?.full_name || auth.user?.username || '金子铮',
    reviewed_by: '杨静',
    mode: 'single',
    l1_mean: 0, l1_sd: 0, l1_n: 0,
    l2_mean: 0, l2_sd: 0, l2_n: 0,
    multi_systems: defaultMultiSystems(),
    ucal: 0, ucal_source: '厂家',
    patient_value: 0, patient_unit: '',
    pt_result: '合格',
    bias_levels: defaultBiasLevels(),
  })
  current.value = null
}

// ───────── 报告生成（前端用最新计算结果） ─────────
function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}
function reportStyle() {
  return `body{font-family:"SimSun",serif;margin:20px;font-size:12pt;color:#000}
h1{text-align:center;font-size:18pt;margin:4px 0}
h2{font-size:14pt;margin-top:18px;border-bottom:1px solid #333;padding-bottom:5px}
table{width:100%;border-collapse:collapse;margin:10px 0}
td,th{border:1px solid #333;padding:7px;font-size:11pt}
th{background:#f0f0f0;text-align:center}
.info-table td{width:25%}
.data-table td,.data-table th{text-align:center}
.sign{display:flex;justify-content:space-between;margin-top:40px}
.note{background:#f9f9d0;padding:8px;border-left:4px solid #d6b800;font-size:11pt;margin:10px 0}
p{text-indent:2em;line-height:1.7}
@media print{body{margin:0}}`
}
function buildSingleReport(p) {
  const rsd1 = p.l1_mean > 0 ? p.l1_sd / p.l1_mean * 100 : 0
  const rsd2 = p.l2_mean > 0 ? p.l2_sd / p.l2_mean * 100 : 0
  const uRw = p.u_rw || 0
  const ucal = p.ucal || 0
  const uC = p.u_c || 0
  const uExt = p.u_extended || 0
  const targetBias = p.target_bias || 0
  const targetText = p.target_bias_text || ''
  const targetSrc = p.target_bias_source || ''
  const passed = !!p.passed
  const pv = p.patient_value || 0
  const pvUnit = p.patient_unit || ''
  const pvExt = p.patient_extended_value || 0
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告 - ${esc(p.project_name)}</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h2 style="text-align:center">第一节 单个测量系统测量不确定度评定范例</h2>
<table class="info-table">
<tr><td><b>表格编号</b></td><td>BG-SM-CZ-072</td><td><b>版本号</b></td><td>01</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">${esc(p.project_name)}</td></tr>
<tr><td><b>检测系统</b></td><td>${esc(p.instrument || '-')}</td><td><b>试剂/校准品</b></td><td>${esc(p.reagent || '-')}</td></tr>
<tr><td><b>评定日期</b></td><td>${esc(p.eval_date || '-')}</td><td><b>评定周期</b></td><td>${p.cycle_months || 6} 个月</td></tr>
<tr><td><b>编制人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
</table>
<h2>1. 定义被测量</h2>
<table class="info-table">
<tr><td><b>系统</b></td><td>血清</td><td><b>被测量</b></td><td>${esc(p.project_name)}</td></tr>
<tr><td><b>单位</b></td><td colspan="3">${esc(pvUnit) || '—'}</td></tr>
<tr><td><b>测量方法</b></td><td colspan="3">${esc(p.reagent || '-')}</td></tr>
</table>
<p><b>被测量定义为：</b>使用${esc(p.instrument || '该检测系统')}测定${esc(p.project_name)}（${esc(pvUnit) || '—'}）。</p>
<h2>2. 不精密度引入测量不确定度分量</h2>
<div class="note">💡 一般采用 <b>≥6 个月</b>的室内质控数据（保证长期精密度评估的代表性）。</div>
<p><b>(1) 该测量系统测量室内质控数据</b></p>
<table class="data-table"><tr><th>水平</th><th>均值</th><th>标准差</th><th>u<sub>Rw</sub></th><th>相对标准差 RSD</th><th>测试数 n</th></tr>
<tr><td>质控水平 1 (L1)</td><td>${(p.l1_mean || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l1_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l1_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${rsd1.toFixed(2)}%</td><td>${p.l1_n || 0}</td></tr>
<tr><td>质控水平 2 (L2)</td><td>${(p.l2_mean || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l2_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l2_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${rsd2.toFixed(2)}%</td><td>${p.l2_n || 0}</td></tr>
</table>
<p><b>(2) 由不精密度引入的总不确定度（合并 L1、L2 RSD）</b></p>
<p>u<sub>Rw</sub> = √[(RSD<sub>L1</sub>² × (n<sub>L1</sub>-1) + RSD<sub>L2</sub>² × (n<sub>L2</sub>-1)) / (n<sub>L1</sub> + n<sub>L2</sub> - 2)] = √[(${rsd1.toFixed(2)}²×(${(p.l1_n||0)-1}) + ${rsd2.toFixed(2)}²×(${(p.l2_n||0)-1})) / (${(p.l1_n||0)+(p.l2_n||0)}-2)] = <b>${uRw.toFixed(2)}%</b></p>
<h2>3. 偏倚引入测量不确定度分量</h2>
<p><b>(1) 校准品定值引入的不确定度（u<sub>cal</sub>）：</b>来源：${esc(p.ucal_source || '厂家')}，相对标准不确定度为 <b>${ucal.toFixed(2)}%</b>。</p>
<p><b>(2) 室间质评：</b>实验室参加 EQA 成绩合格，偏倚分量不重复计算（已含于精密度）。</p>
<h2>4. 计算合成不确定度</h2>
<p>u<sub>c</sub> = √(u<sub>Rw</sub>² + u<sub>cal</sub>²) = √(${uRw.toFixed(2)}² + ${ucal.toFixed(2)}²) = <b>${uC.toFixed(2)}%</b></p>
<h2>5. 计算扩展不确定度</h2>
<p>U = k × u<sub>c</sub> = 2 × ${uC.toFixed(2)}% = <strong>${uExt.toFixed(2)}%</strong>（k=2，包含概率 P≈95.45%）</p>
<h2>6. 测量不确定度的报告</h2>
${pv > 0 ? `<p>患者在该系统的单个测量结果 = ${pv} ${esc(pvUnit)}，则扩展不确定度 = ${pv} × ${uExt.toFixed(2)}% = ${pvExt.toFixed(4)} ${esc(pvUnit)}（k=2），即测量结果 = (${pv} ± ${pvExt.toFixed(4)}) ${esc(pvUnit)}（k=2）。</p>` : '<p>（未填患者结果，跳过报告区间）</p>'}
<h2>7. 结论</h2>
<div class="note">
${targetBias > 0 ? `<p><b>质量目标：</b>目标允许偏倚（来源：${esc(targetSrc)}） = <b>${targetBias.toFixed(2)}%</b>，原始标准：${esc(targetText)}</p>` : '<p>⚠️ 项目质量要求库未找到允许偏倚，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>${uExt.toFixed(2)}%</b> ${passed ? '&lt;' : '≥'} ${targetBias > 0 ? targetBias.toFixed(2) : '15'}% → <strong style="color:${passed ? 'green' : 'red'}">${passed ? '符合要求' : '未达标'}</strong></p>
<p><b>结论：</b>${passed ? `实验室${esc(p.instrument || '')}测量${esc(p.project_name)}浓度的性能符合要求。` : '扩展不确定度超出质量目标，需改进精密度或校准溯源。'}</p>
</div>
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}
function buildMultiReport(p) {
  const sys = Array.isArray(p.multi_systems) ? p.multi_systems : []
  const rsdRows = sys.map((s, i) => {
    const rsd1 = s.l1_mean > 0 ? s.l1_sd / s.l1_mean * 100 : 0
    const rsd2 = s.l2_mean > 0 ? s.l2_sd / s.l2_mean * 100 : 0
    return `<tr><td>${esc(s.name || ('系统' + String.fromCharCode(65+i)))}</td><td>${s.l1_n || 0}</td><td>${(s.l1_mean||0).toFixed(2)}</td><td>${(s.l1_sd||0).toFixed(2)}</td><td>${rsd1.toFixed(2)}%</td><td>${s.l2_n || 0}</td><td>${(s.l2_mean||0).toFixed(2)}</td><td>${(s.l2_sd||0).toFixed(2)}</td><td>${rsd2.toFixed(2)}%</td></tr>`
  }).join('')
  const pv = p.patient_value || 0
  const pvUnit = p.patient_unit || ''
  const pvExt = p.patient_extended_value || 0
  const passed = !!p.passed
  const targetBias = p.target_bias || 0
  const targetText = p.target_bias_text || ''
  const targetSrc = p.target_bias_source || ''
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告(多系统) - ${esc(p.project_name)}</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h2 style="text-align:center">第二节 多个测量系统测量不确定度评定范例</h2>
<table class="info-table">
<tr><td><b>表格编号</b></td><td>BG-SM-CZ-072</td><td><b>版本号</b></td><td>01</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">${esc(p.project_name)}</td></tr>
<tr><td><b>系统数</b></td><td>${sys.length}</td><td><b>系统列表</b></td><td>${esc(sys.map(s => s.name).join('、'))}</td></tr>
<tr><td><b>评定日期</b></td><td>${esc(p.eval_date || '-')}</td><td><b>评定周期</b></td><td>${p.cycle_months || 6} 个月</td></tr>
<tr><td><b>编制人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
</table>
<p>工作量大的临床实验室可使用几个相同的测量系统检测同一被测量。多个系统通常用同一批次 IQC 同时监控，需将系统内不精密度与系统间均值方差合并后算 u<sub>(pooled)</sub>。</p>
<h2>1. 定义被测量</h2>
<p><b>被测量定义为：</b>多系统测定${esc(p.project_name)}（${esc(pvUnit) || '—'}）。</p>
<h2>2. 不精密度引入测量不确定度分量</h2>
<p><b>(1) ${sys.length} 个测量系统测量室内质控数据</b></p>
<table class="data-table"><tr><th rowspan="2">测量系统</th><th colspan="4">L1 水平</th><th colspan="4">L2 水平</th></tr>
<tr><th>n<sub>L1</sub></th><th>均值</th><th>SD</th><th>RSD%</th><th>n<sub>L2</sub></th><th>均值</th><th>SD</th><th>RSD%</th></tr>
${rsdRows}
</table>
<p><b>(2) 各系统平均值的方差（系统间差异，水平内合并）</b></p>
<p>各系统 L1/L2 均值相对标准差合并为系统均值方差；与各系统内 RSD² 均值合并：</p>
<p>u²<sub>均值方差</sub> + u²<sub>Rw(A,B,C)</sub> = u<sub>(pooled)</sub>²</p>
<p>u<sub>rel(pooled)</sub> = u<sub>(pooled)</sub> / 总均值 × 100 = <b>${(p.u_rw || 0).toFixed(2)}%</b></p>
<h2>3. 总不确定度评定</h2>
<p>校准品相对标准不确定度为 <b>${(p.ucal || 0).toFixed(2)}%</b>（来源：${esc(p.ucal_source || '厂家')}）。实验室参加 EQA 成绩合格，扩展不确定度计算：</p>
<p>U<sub>rel</sub> = √(u<sub>rel(pooled)</sub>² + u<sub>cal</sub>²) × 2 = √(${(p.u_rw||0).toFixed(2)}² + ${(p.ucal||0).toFixed(2)}²) × 2 = <strong>${(p.u_extended||0).toFixed(2)}%</strong>（k=2）</p>
<h2>4. 测量不确定度的报告</h2>
${pv > 0 ? `<p>患者在该系统的单个测量结果 = ${pv} ${esc(pvUnit)}，则扩展不确定度 = ${pv} × ${(p.u_extended||0).toFixed(2)}% = ${pvExt.toFixed(4)} ${esc(pvUnit)}（k=2），即测量结果 = (${pv} ± ${pvExt.toFixed(4)}) ${esc(pvUnit)}（k=2）。</p>` : '<p>（未填患者结果，跳过报告区间）</p>'}
<h2>5. 结论</h2>
<div class="note">
${targetBias > 0 ? `<p><b>质量目标：</b>目标允许偏倚（来源：${esc(targetSrc)}） = <b>${targetBias.toFixed(2)}%</b>，原始标准：${esc(targetText)}</p>` : '<p>⚠️ 项目质量要求库未找到允许偏倚，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>${(p.u_extended||0).toFixed(2)}%</b> ${passed ? '&lt;' : '≥'} ${targetBias > 0 ? targetBias.toFixed(2) : '15'}% → <strong style="color:${passed ? 'green' : 'red'}">${passed ? '符合要求' : '未达标'}</strong></p>
<p><b>结论：</b>${passed ? `实验室多个测量系统测定${esc(p.project_name)}的性能符合要求。` : '扩展不确定度超出质量目标，需改进精密度或校准溯源。'}</p>
</div>
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}
function buildSummaryReport(list) {
  const rows = list.map((p, i) => {
    return `<tr>
    <td>${i + 1}</td>
    <td>${esc(p.project_name)}${p.mode === 'multi' ? ' <span style="color:#e6a23c;font-size:11px">[多系统]</span>' : ''}</td>
    <td>${esc(p.instrument || '-')}</td>
    <td>${(p.u_extended || 0).toFixed(2)}</td>
    <td>${(p.target_bias || 0).toFixed(2)}</td>
    <td>${esc(p.target_bias_source || '-')}</td>
    <td>${p.passed ? '<span style="color:green">✅ 符合</span>' : '<span style="color:red">❌ 未达标</span>'}</td>
    <td>${esc(p.eval_date || '-')}</td>
    <td>${esc(p.prepared_by || '')}</td>
  </tr>`}).join('')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定汇总表</h1>
<p>表格编号：BG-SM-GL-020 | 编制日期：${todayStr()}</p>
<table><tr><th>序号</th><th>项目</th><th>检测系统</th><th>U(%)</th><th>目标偏倚(%)</th><th>目标来源</th><th>判定</th><th>评定日期</th><th>编制人</th></tr>${rows}</table>
<p style="margin-top:14px">目标偏倚优先级：WS/T 403-2024（行标） &gt; 2025 北京市互认 &gt; 1/2 × NCCL EQA 允许总误差。</p>
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}

function previewOne(p) {
  previewTitle.value = `测量不确定度评定报告 - ${p.project_name}`
  previewHtml.value = p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p)
  previewOpen.value = true
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
  a.href = url; a.download = name; a.click()
  URL.revokeObjectURL(url)
}
function downloadOne(p) {
  const html = p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p)
  downloadHtml(html, `测量不确定度评定报告_${p.project_name || '项目'}_${todayStr()}.html`)
}
function downloadSummary() {
  downloadHtml(buildSummaryReport(projects.value), `测量不确定度评定汇总表_${todayStr()}.html`)
}
function downloadCurrentHtml() {
  if (previewHtml.value) downloadHtml(previewHtml.value, `${previewTitle.value || '测量不确定度报告'}_${todayStr()}.html`)
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
.mode-tip { font-size: 12px; color: #606266; background: #fffbe6; border-left: 3px solid #d6b800; padding: 6px 10px; margin-top: 8px; border-radius: 4px; }
.level-tag { color: #fff; font-weight: 600; padding: 4px 12px; border-radius: 6px; display: inline-block; margin-bottom: 8px; }
.formula { background: #fafbfc; border: 1px solid #e4e7ed; border-radius: 6px; padding: 10px 14px; font-size: 13px; color: #303133; margin-top: 10px; }
.formula p { margin: 4px 0; line-height: 1.7; }
.sys-row { background: #fff; border: 1px solid #dde4ec; border-radius: 8px; padding: 10px 12px; margin-bottom: 10px; }
.sys-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
.sys-title { font-weight: 600; color: #409eff; }
.sys-cov { background: #f0f9ff; border-radius: 4px; padding: 4px 8px; font-size: 11px; color: #4a5568; line-height: 1.6; }
.btn-row { margin-top: 6px; display: flex; gap: 8px; flex-wrap: wrap; }
.result-box { border: 2px solid #e2e8f0; border-radius: 10px; padding: 8px 16px; }
.res-row { display: flex; justify-content: space-between; padding: 9px 0; border-bottom: 1px solid #eef1f5; font-size: 14px; color: #4a5568; gap: 8px; }
.res-row:last-child { border-bottom: none; }
.res-row .hl { color: #409eff; font-size: 18px; font-weight: 700; }
.res-row .hl2 { color: #67c23a; font-size: 16px; font-weight: 700; }
.divider { height: 1px; background: #e4e7ed; margin: 8px 0; }
.project-list { max-height: 420px; overflow-y: auto; }
.project-item { display: flex; justify-content: space-between; align-items: center; background: #f7fafc; border: 1px solid #e4e7ed; border-radius: 8px; padding: 10px 12px; margin-bottom: 8px; }
.p-name { font-weight: 600; color: #2d3748; }
.p-meta { font-size: 12px; color: #718096; }
.p-actions { display: flex; gap: 6px; }
</style>
