<template>
  <div class="uncert-page">
    <div class="uncert-header">
      <h2>测量不确定度评定</h2>
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
              <el-col :span="12"><el-form-item label="测量方法" required>
                <el-select
                  v-model="form.project_method"
                  filterable
                  remote
                  reserve-keyword
                  :remote-method="searchMethod"
                  :loading="methodLoading"
                  placeholder="输入项目名模糊搜索测量方法（可手动输入）"
                  style="width:100%"
                  allow-create
                  clearable
                >
                  <el-option v-for="m in methodOptions" :key="m" :label="methodLabel(m)" :value="m" />
                </el-select>
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="样本类型">
                <el-radio-group v-model="form.sample_type">
                  <el-radio value="血清">血清</el-radio>
                  <el-radio value="血浆">血浆</el-radio>
                  <el-radio value="尿液">尿液</el-radio>
                  <el-radio value="其他">其他</el-radio>
                </el-radio-group>
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="被测量">
                <el-radio-group v-model="analyteKind" @change="updateAnalyte">
                  <el-radio value="浓度">浓度</el-radio>
                  <el-radio value="活性">活性</el-radio>
                </el-radio-group>
                <el-input v-model="form.analyte" size="small" style="margin-top:6px;width:100%" placeholder="自动拼接，也可手动微调" />
              </el-form-item></el-col>
              <el-col :span="24">
                <el-form-item label="质量目标">
                  <el-select
                    v-model="selectedTargetId"
                    filterable
                    remote
                    reserve-keyword
                    :remote-method="searchTargets"
                    :loading="targetLoading"
                    placeholder="输入项目名搜索卫健委 EQA 质量目标（可手动选择）"
                    style="width:100%"
                    clearable
                    @change="onTargetSelect"
                  >
                    <el-option
                      v-for="t in targetOptions"
                      :key="t.id"
                      :label="`${t.item_name}（TEa ${t.tea_pct}%）`"
                      :value="t.id"
                    />
                  </el-select>
                  <div v-if="form.target_bias > 0" class="mode-tip" style="margin-top:4px">
                    已选质量目标：<b>{{ form.target_bias_source }} = {{ form.target_bias }}%</b>（{{ form.target_bias_text }}）
                  </div>
                </el-form-item>
              </el-col>
              <el-col :span="12"><el-form-item label="试剂品牌">
                <el-select
                  v-model="form.reagent"
                  filterable
                  remote
                  reserve-keyword
                  :remote-method="(q) => searchItemField(q, 'brand')"
                  :loading="reagentLoading"
                  placeholder="选择或输入试剂品牌"
                  style="width:100%"
                  allow-create
                  clearable
                  @focus="searchItemField('', 'brand')"
                >
                  <el-option v-for="(it, idx) in reagentOptions" :key="idx" :label="it.brand || '?'" :value="it.brand" />
                </el-select>
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="校准品">
                <el-select
                  v-model="form.calibrator"
                  filterable
                  remote
                  reserve-keyword
                  :remote-method="(q) => searchItemField(q, 'calibrator')"
                  :loading="calibratorLoading"
                  placeholder="输入项目名/校准品搜索（可手动输入）"
                  style="width:100%"
                  allow-create
                  clearable
                >
                  <el-option v-for="(it, idx) in calibratorOptions" :key="idx" :label="`${it.name} - ${it.calibrator || '?'}`" :value="it.calibrator" />
                  <template #label="{ value }">{{ value }}</template>
                </el-select>
              </el-form-item></el-col>
              <el-col :span="12"><el-form-item label="报告单位">
                <el-select
                  v-model="form.patient_unit"
                  filterable
                  remote
                  reserve-keyword
                  :remote-method="(q) => searchItemField(q, 'unit')"
                  :loading="unitLoading"
                  placeholder="输入项目名/单位搜索（可手动输入）"
                  style="width:100%"
                  allow-create
                  clearable
                >
                  <el-option v-for="(it, idx) in unitOptions" :key="idx" :label="`${it.name} - ${it.unit || '?'}`" :value="it.unit" />
                  <template #label="{ value }">{{ value }}</template>
                </el-select>
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
              <el-col :span="12"><el-form-item label="患者结果">
                <el-input-number v-model="form.patient_value" :min="0" :precision="4" :controls="false" style="width:100%" />
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
                    <el-input-number v-model="form.l1_mean" :min="0" :controls="false" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="标准差" label-width="60px">
                    <el-input-number v-model="form.l1_sd" :min="0" :controls="false" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="测试数 n" label-width="60px">
                    <el-input-number v-model="form.l1_n" :min="0" :controls="false" :precision="0" style="width:100%" />
                  </el-form-item>
                </el-col>
                <el-col :span="12">
                  <div class="level-tag" style="background:#e6a23c">L2 水平</div>
                  <el-form-item label="均值" label-width="60px">
                    <el-input-number v-model="form.l2_mean" :min="0" :controls="false" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="标准差" label-width="60px">
                    <el-input-number v-model="form.l2_sd" :min="0" :controls="false" :precision="4" style="width:100%" />
                  </el-form-item>
                  <el-form-item label="测试数 n" label-width="60px">
                    <el-input-number v-model="form.l2_n" :min="0" :controls="false" :precision="0" style="width:100%" />
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
                <el-row :gutter="16">
                  <el-col :span="4"><el-form-item label="名称" label-position="top" label-width="0"><el-input v-model="s.name" :placeholder="'系统' + String.fromCharCode(65+idx)" /></el-form-item></el-col>
                  <el-col :span="5"><el-form-item label="L1 均值" label-position="top" label-width="0"><el-input-number v-model="s.l1_mean" :min="0" :precision="4" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="5"><el-form-item label="L1 SD" label-position="top" label-width="0"><el-input-number v-model="s.l1_sd" :min="0" :precision="4" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="4"><el-form-item label="L1 n" label-position="top" label-width="0"><el-input-number v-model="s.l1_n" :min="0" :precision="0" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L1 RSD%" label-position="top" label-width="0"><el-input :value="s.l1_mean > 0 ? ((s.l1_sd / s.l1_mean) * 100).toFixed(2) + '%' : ''" readonly /></el-form-item></el-col>
                </el-row>
                <el-row :gutter="16">
                  <el-col :span="4"><el-form-item label="&nbsp;" label-position="top" label-width="0">&nbsp;</el-form-item></el-col>
                  <el-col :span="5"><el-form-item label="L2 均值" label-position="top" label-width="0"><el-input-number v-model="s.l2_mean" :min="0" :precision="4" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="5"><el-form-item label="L2 SD" label-position="top" label-width="0"><el-input-number v-model="s.l2_sd" :min="0" :precision="4" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="4"><el-form-item label="L2 n" label-position="top" label-width="0"><el-input-number v-model="s.l2_n" :min="0" :precision="0" :controls="false" style="width:100%" /></el-form-item></el-col>
                  <el-col :span="6"><el-form-item label="L2 RSD%" label-position="top" label-width="0"><el-input :value="s.l2_mean > 0 ? ((s.l2_sd / s.l2_mean) * 100).toFixed(2) + '%' : ''" readonly /></el-form-item></el-col>
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
                <el-input-number v-model="form.ucal" :min="0" :controls="false" :precision="2" :step="0.1" style="width:180px" />
                <span style="margin-left:8px;color:#909399;font-size:12px">多个校准品时，保守选择相对标准不确定度最大的</span>
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
              <span>质量目标（允许总误差）</span>
              <b class="hl2">{{ fmtPct(current.target_bias) }}</b>
            </div>
            <div class="res-row" v-if="current.target_bias_source" style="font-size:12px;color:#909399">
              <span>来源</span>
              <span>{{ current.target_bias_source }}（{{ current.target_bias_text }}）</span>
            </div>
            <div class="res-row" v-if="!current.target_bias">
              <span>质量目标</span>
              <el-tag type="info" size="small">未查到允许总误差（兜底按 U&lt;15% 判定）</el-tag>
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
              <el-button size="small" type="success" @click="downloadOne(current)">⬇️ 下载 PDF / 打印</el-button>
            </div>
          </div>
          <el-empty v-else description="暂无计算结果，请在左侧录入并保存" :image-size="70" />

          <!-- 汇总表的预览/打印/下载已迁移至「性能验证 → 不确定度汇总」独立页面 -->

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
// 报告 HTML 构建 / 打印 / 下载已抽到共享工具（不确定度汇总页复用同一份）
import { esc, todayStr, reportStyle, buildSingleReport, buildMultiReport, buildSummaryReport, printOrSavePdf, downloadHtml } from '../../utils/uncertaintyReport'

// 常用试剂品牌兜底（项目库 reagent 字段普遍为空，保证下拉有候选可选）
const COMMON_REAGENTS = ['贝克曼', '罗氏', '西门子', '雅培', '迈瑞', '积水', '柏定', '德赛', '九强', '安图', '奥森多', '强生', '迈克', '中生北控']

const auth = useAuthStore()
const projects = ref([])
const current = ref(null)
const saving = ref(false)
const editingId = ref(null)
const previewOpen = ref(false)
const previewTitle = ref('')
const previewHtml = ref('')
// 质量目标搜索选择
const targetOptions = ref([])
const targetLoading = ref(false)
const selectedTargetId = ref(null)
const targetMap = reactive({})
// 测量方法下拉选项（从 test_items 模糊搜索得到）
const methodOptions = ref([])
const methodLoading = ref(false)
// 试剂/校准品/单位下拉选项
const reagentOptions = ref([])
const reagentLoading = ref(false)
const calibratorOptions = ref([])
const calibratorLoading = ref(false)
const unitOptions = ref([])
const unitLoading = ref(false)
// 被测量类型：浓度 / 活性（像样本类型一样点选）
const analyteKind = ref('浓度')


const form = reactive({
  project_name: '', project_method: '', reagent: '',
  sample_type: '血清',  // 血清/血浆/尿液/其他
  analyte: '',  // 被测量 = 项目 + 浓度/活性（自动推断）
  eval_date: todayStr(), cycle_months: 12,
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
  // 质量目标（允许总误差 TEa，手动选择）
  target_bias: 0, target_bias_text: '', target_bias_source: '',
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

// 项目名变更时：模糊搜索 test_items（自动填方法/单位/被测量）+ 卫健委 EQA 质量目标
let lookupTimer = null
async function onProjectChange() {
  clearTimeout(lookupTimer)
  if (!form.project_name || form.project_name.length < 2) return
  lookupTimer = setTimeout(async () => {
    try {
      // 1) 搜索 test_items 自动填方法/单位/试剂/校准品
      await searchMethod(form.project_name)
      if (methodOptions.value.length) {
        // 自动选第一个方法
        form.project_method = methodOptions.value[0]
        // 同步填被测量（按方法推断）
        autoFillAnalyte(methodOptions.value[0])
        // 从第一个匹配项填报告单位/试剂/校准品
        const hit = methodMap[methodOptions.value[0]]
        if (hit) {
          if (hit.unit) form.patient_unit = hit.unit
          if (hit.brand && !form.reagent) form.reagent = hit.brand
          if (hit.calibrator && !form.calibrator) form.calibrator = hit.calibrator
        }
        // 标本类型默认血清
        if (!form.sample_type) form.sample_type = '血清'
        // 同时搜 reagent/calibrator/unit 候选下拉
        await searchItemField(form.project_name, 'brand')
        await searchItemField(form.project_name, 'calibrator')
        await searchItemField(form.project_name, 'unit')
      } else {
        ElMessage.warning('未在系统找到该项目，请手动填写测量方法')
      }
      // 2) 搜索卫健委 EQA 质量目标
      await searchTargets(form.project_name)
      if (targetOptions.value.length) {
        selectedTargetId.value = targetOptions.value[0].id
        onTargetSelect(selectedTargetId.value)
      } else {
        ElMessage.warning('未找到该项目的卫健委 EQA 质量目标，将兜底按 U<15% 判定')
      }
    } catch (e) { console.error('[onProjectChange]', e) }
  }, 400)
}

// 推断被测量：单位是 U/L → 活性，否则浓度（浓度/活性可点选，也可手动微调）
function autoFillAnalyte(method) {
  if (!form.project_name) return
  analyteKind.value = (form.patient_unit === 'U/L') ? '活性' : '浓度'
  updateAnalyte()
}

function updateAnalyte() {
  if (!form.project_name) return
  form.analyte = `${form.project_name}${analyteKind.value}`
}

const methodMap = reactive({})

async function searchMethod(query) {
  if (!query || query.length < 1) { methodOptions.value = []; return }
  methodLoading.value = true
  try {
    const res = await request.get('/api/v1/test-items', { params: { q: query, page_size: 8 } })
    const items = (res && (res.items || res)) || []
    // 收集 method 去重（保留首次出现顺序）
    const seen = new Set()
    const methods = []
    items.forEach(it => {
      const m = (it.method || '').trim()
      if (m && !seen.has(m)) { seen.add(m); methods.push(m); methodMap[m] = it }
    })
    methodOptions.value = methods
  } finally {
    methodLoading.value = false
  }
}

async function searchTargets(query) {
  if (!query || query.length < 1) { targetOptions.value = []; return }
  targetLoading.value = true
  try {
    const res = await request.get('/api/v1/uncertainty/_search_targets', { params: { q: query } })
    const items = (res && res.items) || []
    items.forEach(t => { targetMap[t.id] = t })
    targetOptions.value = items
  } finally {
    targetLoading.value = false
  }
}

function onTargetSelect(id) {
  const t = targetMap[id]
  if (t) {
    form.target_bias = t.tea_pct
    form.target_bias_text = t.tea
    form.target_bias_source = '卫健委 EQA（允许总误差）'
  } else {
    form.target_bias = 0
    form.target_bias_text = ''
    form.target_bias_source = ''
  }
}

// 试剂 / 校准品 / 报告单位候选搜索（按项目名搜 test_items，分别取对应字段）
async function searchItemField(query, field) {
  const loadingRef = field === 'brand' ? reagentLoading : field === 'calibrator' ? calibratorLoading : unitLoading
  const optionsRef = field === 'brand' ? reagentOptions : field === 'calibrator' ? calibratorOptions : unitOptions
  loadingRef.value = true
  try {
    const params = { page_size: 50 }
    if (query && query.length >= 1) params.q = query
    const res = await request.get('/api/v1/test-items', { params })
    const items = (res && (res.items || res)) || []
    // 试剂品牌从 test_items.brand 取（按品牌去重）；空查询时列出库内全部已知品牌
    if (field === 'brand') {
      const seen = new Set()
      const dbOpts = items.filter(it => {
        const v = (it.brand || '').trim()
        if (!v || seen.has(v)) return false
        seen.add(v)
        return true
      })
      if (dbOpts.length) {
        optionsRef.value = dbOpts
      } else {
        // 库内无品牌数据时，给出常用试剂品牌兜底，保证下拉有候选
        const q = (query || '').trim()
        let fb = COMMON_REAGENTS.filter(b => !q || b.includes(q)).map(b => ({ brand: b, name: b }))
        if (!fb.length) fb = COMMON_REAGENTS.map(b => ({ brand: b, name: b }))
        optionsRef.value = fb
      }
    } else {
      optionsRef.value = items
    }
  } finally {
    loadingRef.value = false
  }
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
    project_method: form.project_method,
    sample_type: form.sample_type,
    analyte: form.analyte,
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
    unit: form.patient_unit,
    project_code: '',
    pt_result: form.pt_result || '合格',
    bias_levels: form.pt_result === '不合格' ? form.bias_levels : [],
    calibrator: form.calibrator,
    target_bias: form.target_bias,
    target_bias_text: form.target_bias_text,
    target_bias_source: form.target_bias_source,
  }
  saving.value = true
  try {
    // 先调 _preview 拿完整计算结果 + 质量目标
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
  form.project_method = p.project_method || ''
  form.sample_type = p.sample_type || '血清'
  form.analyte = p.analyte || ''
  analyteKind.value = (form.analyte.includes('活性')) ? '活性' : '浓度'
  form.calibrator = p.calibrator || ''
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
  form.target_bias = p.target_bias || 0
  form.target_bias_text = p.target_bias_text || ''
  form.target_bias_source = p.target_bias_source || ''
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
    project_name: '', project_method: '', reagent: '',
    sample_type: '血清', analyte: '', calibrator: '',
    eval_date: todayStr(), cycle_months: 12,
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
    target_bias: 0, target_bias_text: '', target_bias_source: '',
  })
  selectedTargetId.value = null
  targetOptions.value = []
  analyteKind.value = '浓度'
  current.value = null
}

// ───────── 报告生成（前端用最新计算结果） ─────────

function previewOne(p) {
  previewTitle.value = `测量不确定度评定报告 - ${p.project_name}`
  previewHtml.value = p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p)
  previewOpen.value = true
}
function downloadOne(p) {
  const html = p.mode === 'multi' ? buildMultiReport(p) : buildSingleReport(p)
  printOrSavePdf(html, `测量不确定度评定报告_${p.project_name || '项目'}_${todayStr()}`)
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
