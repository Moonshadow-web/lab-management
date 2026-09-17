// 测量不确定度报告 HTML 构建与打印/下载（前端共享）。
// 抽离自 UncertaintyAssessment.vue，供「测量不确定度评定」与「不确定度汇总」两个页面复用。
// 2026-08-21：汇总表「判定」列去 ✅、去绿字（改为正常黑色文字），与后端 _summary_html 保持一致。
import { ElMessage } from 'element-plus'

export function esc(s) {
  return String(s == null ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

export function todayStr() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

export function reportStyle() {
  return `body{font-family:"SimSun",serif;margin:20px;font-size:12pt;color:#000}
h1{text-align:center;font-size:18pt;margin:4px 0}
h2{font-size:14pt;margin-top:18px;border-bottom:1px solid #333;padding-bottom:5px}
table{width:100%;border-collapse:collapse;margin:10px 0}
td,th{border:1px solid #333;padding:7px;font-size:11pt}
th{background:#f0f0f0;text-align:center}
.info-table td{width:25%}
.data-table td,.data-table th{text-align:center}
.sign{display:flex;justify-content:space-between;margin-top:40px}
.note{font-size:11pt;margin:10px 0;line-height:1.7}
p{text-indent:2em;line-height:1.7}
@page{size:A4;margin:18mm 16mm}
@media print{body{margin:0} h1{font-size:16pt} h2{page-break-after:avoid}}`
}

export function buildSingleReport(p) {
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
  const method = p.project_method || '该检测方法'
  const sample = p.sample_type || '血清'
  const analyte = p.analyte || (p.project_name || '')
  // 报告标题：「方法 测量人 样本 被测量 测量结果不确定度的评定」（不再加"第一节"）
  const section1Title = `${method}测量人${sample}${analyte}测量结果不确定度的评定`
  // 结论：「实验室 方法 测量人 样本 被测量 的性能符合要求」
  const conclusionText = passed
    ? `实验室${method}测量人${sample}${analyte}的性能符合要求。`
    : '扩展不确定度超出质量目标，需改进精密度或校准溯源。'
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告 - ${esc(p.project_name)}</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h2 style="text-align:center">${esc(section1Title)}</h2>
<table class="info-table">
<tr><td><b>表格编号</b></td><td>BG-SM-CZ-072</td><td><b>版本号</b></td><td>01</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">${esc(p.project_name)}</td></tr>
<tr><td><b>试剂</b></td><td>${esc(p.reagent || '-')}</td><td><b>校准品</b></td><td>${esc(p.calibrator || '-')}</td></tr>
<tr><td><b>评定日期</b></td><td>${esc(p.eval_date || '-')}</td><td><b>评定周期</b></td><td>${p.cycle_months || 12} 个月</td></tr>
<tr><td><b>评定人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
</table>
<h2>1. 定义被测量</h2>
<table class="info-table">
<tr><td><b>测量方法</b></td><td colspan="3">${esc(method)}</td></tr>
<tr><td><b>样本类型</b></td><td>${esc(sample)}</td><td><b>报告单位</b></td><td>${esc(pvUnit) || '—'}</td></tr>
<tr><td><b>被测量</b></td><td colspan="3">${esc(analyte)}</td></tr>
</table>
<p><b>被测量定义为：</b>采用${esc(method)}测定${esc(sample)}中${esc(analyte)}（${esc(pvUnit) || '—'}）。</p>
<h2>2. 不精密度引入测量不确定度分量</h2>
<div class="note">一般采用 <b>≥6 个月</b>的室内质控数据（保证长期精密度评估的代表性）。</div>
<p><b>(1) 该测量系统测量室内质控数据</b></p>
<table class="data-table"><tr><th>水平</th><th>均值</th><th>标准差</th><th>u<sub>Rw</sub></th><th>相对标准差 RSD</th><th>测试数 n</th></tr>
<tr><td>质控水平 1 (L1)</td><td>${(p.l1_mean || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l1_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l1_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${rsd1.toFixed(2)}%</td><td>${p.l1_n || 0}</td></tr>
<tr><td>质控水平 2 (L2)</td><td>${(p.l2_mean || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l2_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${(p.l2_sd || 0).toFixed(2)} ${esc(pvUnit)}</td><td>${rsd2.toFixed(2)}%</td><td>${p.l2_n || 0}</td></tr>
</table>
<p><b>(2) 由不精密度引入的总不确定度（合并 L1、L2 RSD）</b></p>
<p>u<sub>Rw</sub> = √[(RSD<sub>L1</sub>² × (n<sub>L1</sub>-1) + RSD<sub>L2</sub>² × (n<sub>L2</sub>-1)) / (n<sub>L1</sub> + n<sub>L2</sub> - 2)] = √[(${rsd1.toFixed(2)}²×(${(p.l1_n||0)-1}) + ${rsd2.toFixed(2)}²×(${(p.l2_n||0)-1})) / (${(p.l1_n||0)+(p.l2_n||0)}-2)] = <b>${uRw.toFixed(2)}%</b></p>
<h2>3. 校准品定值引入测量不确定度分量</h2>
<p><b>(1) u<sub>cal</sub>：</b>来源：${esc(p.ucal_source || '厂家')}，相对标准不确定度为 <b>${ucal.toFixed(2)}%</b>。</p>
${p.pt_result === '不合格' ? '<p><b>(2) 室间质评：</b>EQA 成绩不合格，需填入 5 水平偏倚数据（详见偏倚计算）。</p>' : '<p><b>(2) 室间质评：</b>实验室参加 EQA 成绩合格，偏倚分量不重复计算（已含于精密度）。</p>'}
<h2>4. 计算合成不确定度</h2>
<p>u<sub>c</sub> = √(u<sub>Rw</sub>² + u<sub>cal</sub>²${p.pt_result === '不合格' ? ' + bias²' : ''}) = <b>${uC.toFixed(2)}%</b></p>
<h2>5. 计算扩展不确定度</h2>
<p>U = k × u<sub>c</sub> = 2 × ${uC.toFixed(2)}% = <strong>${uExt.toFixed(2)}%</strong>（k=2，包含概率 P≈95.45%）</p>
<h2>6. 测量不确定度的报告</h2>
${pv > 0 ? `<p>患者在该系统的单个测量结果 = ${pv} ${esc(pvUnit)}，则扩展不确定度 = ${pv} × ${uExt.toFixed(2)}% = ${pvExt.toFixed(4)} ${esc(pvUnit)}（k=2），即测量结果 = (${pv} ± ${pvExt.toFixed(4)}) ${esc(pvUnit)}（k=2）。</p>` : '<p>（未填患者结果，跳过报告区间）</p>'}
<h2>7. 结论</h2>
<div class="note">
${targetBias > 0 ? `<p><b>质量目标：</b>目标允许总误差 TEa（来源：${esc(targetSrc)}） = <b>${targetBias.toFixed(2)}%</b>，原始标准：${esc(targetText)}</p>` : '<p>项目质量要求库未找到允许总误差，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>${uExt.toFixed(2)}%</b> ${passed ? '&lt;' : '≥'} ${targetBias > 0 ? targetBias.toFixed(2) : '15'}% → <strong style="color:${passed ? 'green' : 'red'}">${passed ? '符合要求' : '未达标'}</strong></p>
<p><b>结论：</b>${esc(conclusionText)}</p>
</div>
<div class="sign"><div>评定人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}

export function buildMultiReport(p) {
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
  const method = p.project_method || '该检测方法'
  const sample = p.sample_type || '血清'
  const analyte = p.analyte || (p.project_name || '')
  const sectionTitle = `多系统${method}测量人${sample}${analyte}测量结果不确定度的评定`
  const conclusionText = passed
    ? `实验室${method}测量人${sample}${analyte}（多测量系统合并评定）的性能符合要求。`
    : '扩展不确定度超出质量目标，需改进精密度或校准溯源。'
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告(多系统) - ${esc(p.project_name)}</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h2 style="text-align:center">${esc(sectionTitle)}</h2>
<table class="info-table">
<tr><td><b>表格编号</b></td><td>BG-SM-CZ-072</td><td><b>版本号</b></td><td>01</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">${esc(p.project_name)}</td></tr>
<tr><td><b>系统数</b></td><td>${sys.length}</td><td><b>系统列表</b></td><td>${esc(sys.map(s => s.name).join('、'))}</td></tr>
<tr><td><b>评定日期</b></td><td>${esc(p.eval_date || '-')}</td><td><b>评定周期</b></td><td>${p.cycle_months || 12} 个月</td></tr>
<tr><td><b>评定人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
</table>
<p>工作量大的临床实验室可使用几个相同的测量系统检测同一被测量。多个系统通常用同一批次 IQC 同时监控，需将系统内不精密度与系统间均值方差合并后算 u<sub>(pooled)</sub>。</p>
<h2>1. 定义被测量</h2>
<p><b>被测量定义为：</b>采用${esc(method)}，${esc(sys.map(s => s.name).join('、'))} 共 ${sys.length} 个测量系统联合测定${esc(sample)}中${esc(analyte)}（${esc(pvUnit) || '—'}）。</p>
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
${targetBias > 0 ? `<p><b>质量目标：</b>目标允许总误差 TEa（来源：${esc(targetSrc)}） = <b>${targetBias.toFixed(2)}%</b>，原始标准：${esc(targetText)}</p>` : '<p>项目质量要求库未找到允许总误差，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>${(p.u_extended||0).toFixed(2)}%</b> ${passed ? '&lt;' : '≥'} ${targetBias > 0 ? targetBias.toFixed(2) : '15'}% → <strong style="color:${passed ? 'green' : 'red'}">${passed ? '符合要求' : '未达标'}</strong></p>
<p><b>结论：</b>${esc(conclusionText)}</p>
</div>
<div class="sign"><div>评定人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}

export function buildQualitativeReport(p) {
  const cutoff = Number(p.cutoff || 0)
  const uRep = Number(p.u_rw || 0)
  const uCal = Number(p.ucal_abs || 0)
  const uC = Number(p.u_c || 0)
  const uExt = Number(p.u_ext_abs || p.u_extended || 0)
  const gl = Number(p.gray_low || 0), gh = Number(p.gray_high || 0)
  const r = Number(p.patient_value || 0)
  const lr = Number(p.lr_value || 0)
  const lrl = p.lr_level || ''
  const inGray = r > 0 && r >= gl && r <= gh
  const method = p.project_method || p.instrument || '该检测方法'
  const sample = p.sample_type || '血清'
  const projName = p.project_name || ''
  const pooled = (p.u_rep_mode || 'l1_only') === 'pooled'
  // 质控明细行
  const lvRows = []
  ;[['L1', 'l1_mean', 'l1_sd', 'l1_n'], ['L2', 'l2_mean', 'l2_sd', 'l2_n']].forEach(([nm, mk, sk, nk]) => {
    const n = Number(p[nk] || 0), sd = Number(p[sk] || 0)
    if (n >= 2 && sd > 0) {
      lvRows.push(`<tr><td>${nm}</td><td>${Number(p[mk] || 0).toFixed(2)}</td><td>${sd.toFixed(4)}</td><td>${n}</td></tr>`)
    }
  })
  const lvHtml = lvRows.length ? lvRows.join('') : '<tr><td>L1</td><td>—</td><td>—</td><td>—</td></tr>'
  const ucalNote = uCal === 0
    ? `<div class="note"><b>关于 u<sub>cal</sub> 的处理：</b>厂家未提供检测器/校准品的不确定度信息。依据 CNAS-CL01-G003 6.3（无法严格评定时可基于理论原理与实践经验合理评定），本评定以室内质控的<b>期间精密度 u<sub>rep</sub> 作为主要分量</b>——长期（≥6 个月）室内质控的标准差已包含日常校准、试剂批号更换等变动引入的影响；故未单独计入 u<sub>cal</sub>。提示：该处理使 U 相对保守偏小，临界区判读宜结合复检规则使用。</div>`
    : `<p>u<sub>cal</sub> 来源：${esc(p.ucal_source || '厂家证书（U÷k）')}</p>`
  const conclusionText = inGray
    ? `测值 ${r.toFixed(2)} S/CO 落在灰区（${gl.toFixed(4)} ~ ${gh.toFixed(4)}），结果不能判定，建议复检或采用确认试验。`
    : (r > 0
        ? `测值 ${r.toFixed(2)} S/CO 的似然比 LR = ${lr.toFixed(2)}，为<b>${esc(lrl)}</b>，该定性判读成立。`
        : '未录入待判读信号值。评定结果可用于建立本项目的灰区（LR&lt;10 区间）。')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>定性项目测量不确定度评定报告 - ${esc(projName)}</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>${esc(projName)} 定性项目测量不确定度评定报告</h1>
<table class="info-table">
<tr><td><b>表格编号</b></td><td>BG-SM-CZ-072</td><td><b>版本号</b></td><td>01</td></tr>
<tr><td><b>项目名称</b></td><td>${esc(projName)}</td><td><b>测量方法</b></td><td>${esc(method)}</td></tr>
<tr><td><b>标本类型</b></td><td>${esc(sample)}</td><td><b>测量单位</b></td><td>S/CO（信号值/阈值比）</td></tr>
<tr><td><b>试剂</b></td><td>${esc(p.reagent || '-')}</td><td><b>校准品</b></td><td>${esc(p.calibrator || '-')}</td></tr>
<tr><td><b>判定阈值 cutoff</b></td><td>${cutoff.toFixed(2)} S/CO</td><td><b>数据周期</b></td><td>${p.cycle_months || 6} 个月室内质控</td></tr>
<tr><td><b>评定人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
<tr><td><b>评定日期</b></td><td colspan="3">${esc(p.eval_date || '-')}</td></tr>
</table>
<h2>1. 定义被测量</h2>
<p>本项目的定性结果（阳性/阴性）由仪器输出信号 <b>S/CO</b>（信号值/阈值比，亦称 COI）与判定阈值 <b>cutoff = ${cutoff.toFixed(2)} S/CO</b> 比较得出。因此本评定以<b>仪器输出信号 S/CO 的量值</b>为被测量，其测量不确定度以<b>绝对单位（S/CO）</b>表示。</p>
<p>依据 ISO 15189:2022 条款 7.3.4 f)：当定性检验结果基于定量输出数据并按阈值判定为阳性或阴性时，应用有代表性的阳性和阴性样品估计输出量值的测量不确定度；CNAS-CL01-G003 6.2 规定，对阴性/阳性等非数值结果宜采用其他方法评估测量不确定度，例如<b>假阳性或假阴性的概率</b>。故本报告采用<b>绝对不确定度 + 似然比（LR）</b>判读，不使用允许总误差（TEa）。</p>
<h2>2. 不精密度引入测量不确定度分量 u<sub>rep</sub></h2>
<p>数据来源：室内质控（IQC）信号值，覆盖 ${p.cycle_months || 6} 个月，以期间精密度评定。</p>
<table class="data-table"><tr><th>水平</th><th>质控均值 x̄ (S/CO)</th><th>标准差 SD (S/CO)</th><th>测试数 n</th></tr>${lvHtml}</table>
<p>u<sub>rep</sub>（${pooled ? '合并标准差，L1+L2' : '取自 L1（接近 cutoff 的弱阳性质控）'}）= <b>${uRep.toFixed(4)} S/CO</b></p>
<div class="note">说明：为保证对临界区（cutoff 附近）的代表性，宜以<b>接近 cutoff 的弱阳性质控</b>为主要水平；合并高值水平会因其 SD 较大而<b>削弱临界区判读力</b>，故定性项目推荐只采用弱阳性水平。</div>
<h2>3. 校准/检测器引入测量不确定度分量 u<sub>cal</sub></h2>
<p>u<sub>cal</sub> = <b>${uCal.toFixed(4)} S/CO</b>（来源：${esc(p.ucal_source || '厂家')}）</p>
${ucalNote}
<h2>4. 计算合成标准不确定度</h2>
<p>u<sub>c</sub> = √(u<sub>rep</sub>² + u<sub>cal</sub>²) = √(${uRep.toFixed(4)}² + ${uCal.toFixed(4)}²) = <b>${uC.toFixed(4)} S/CO</b></p>
<h2>5. 计算扩展不确定度</h2>
<p>U = k × u<sub>c</sub> = 2 × ${uC.toFixed(4)} = <strong>${uExt.toFixed(4)} S/CO</strong>（k=2，包含概率 P≈95%）</p>
<h2>6. 判定阈值附近的判读（灰区与似然比）</h2>
<p>以似然比 LR=10（"中等支持"下限）为界，<b>灰区</b>（LR&lt;10，无法判定的信号区间）为 <b>${gl.toFixed(4)} ~ ${gh.toFixed(4)} S/CO</b>。当测得信号落于该区间时，阳性与阴性判读的似然比均不足以支持结论，应复检或采用替代/确认方法。</p>
<table class="data-table"><tr><th>待判读信号值 r (S/CO)</th><th>似然比 LR</th><th>支持程度</th><th>是否落在灰区</th></tr>
<tr><td>${r > 0 ? r.toFixed(2) : '—'}</td><td>${r > 0 ? lr.toFixed(2) : '—'}</td><td>${esc(lrl) || '—'}</td><td>${inGray ? '是' : '否'}</td></tr></table>
<div class="note">注：LR = 真阳性率 / 假阴性率，按正态分布由 z=(cutoff−r)/u<sub>c</sub> 计算：r≥cutoff 时 TPR=1−Φ(z)、FNR=Φ(z)，LR=TPR/FNR；r&lt;cutoff 时以 TNR/FPR 表示。LR 越大对相应定性结论的支持越强（1–10 微弱、10–100 中等、100–1000 中等偏强、1000–10⁴ 强烈、10⁴–10⁶ 非常强烈、&gt;10⁶ 极强）。</div>
<h2>7. 结论</h2>
<p>${conclusionText}</p>
<div class="sign"><div>评定人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}


export function buildSummaryReport(list) {
  const rows = list.map((p, i) => {
    const isQ = p.mode === 'qualitative'
    const tag = isQ
      ? ' <span style="color:#67c23a;font-size:11px">[定性]</span>'
      : (p.mode === 'multi' ? ' <span style="color:#e6a23c;font-size:11px">[多系统]</span>' : '')
    const uTxt = isQ
      ? `${Number(p.u_ext_abs ?? p.u_extended ?? 0).toFixed(4)} S/CO`
      : `${Number(p.u_extended || 0).toFixed(2)}%`
    // 定性项目的"目标"即灰区（LR<10 不能判定的信号区间）
    const gl = Number(p.gray_low || 0), gh = Number(p.gray_high || 0)
    const tgtTxt = isQ
      ? ((gl || gh) ? `${gl.toFixed(4)} ~ ${gh.toFixed(4)} S/CO` : '—（未算）')
      : `${Number(p.target_bias || 0).toFixed(2)}%`
    const judge = isQ
      ? (p.passed ? '支持判读' : '落灰区')
      : (p.passed ? '符合' : '未达标')
    return `<tr>
    <td>${i + 1}</td>
    <td>${esc(p.project_name)}${tag}</td>
    <td>${esc(p.project_method || p.instrument || '-')}</td>
    <td>${uTxt}</td>
    <td>${tgtTxt}</td>
    <td>${esc(p.target_bias_source || '-')}</td>
    <td>${judge}</td>
    <td>${esc(p.eval_date || '-')}</td>
    <td>${esc(p.prepared_by || '')}</td>
  </tr>`}).join('')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定汇总表</h1>
<p>表格编号：BG-SM-GL-020 | 编制日期：${todayStr()}</p>
<table><tr><th>序号</th><th>项目</th><th>测量方法</th><th>U</th><th>目标 / 灰区</th><th>目标来源</th><th>判定</th><th>评定日期</th><th>评定人</th></tr>${rows}</table>
<p style="margin-top:14px"><b>判定说明：</b>定量项目 U 以相对值(%)表示，判定标准 U &lt; TEa（允许总误差）；定性项目 U 以绝对值(S/CO)表示，<b>「目标 / 灰区」列给出灰区区间</b>（LR&lt;10 不能判定的信号范围），按似然比判读，不适用 TEa。</p>
<p>质量目标：卫健委 EQA 允许总误差（NCCL），U &lt; TEa 判为符合要求。</p>
<div class="sign"><div>评定人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}

export function buildAllReports(list) {
  // 把多条「完整评定报告」拼成一个连续 HTML，每条另起一页（A4），
  // 便于一次性打印/另存为单个 PDF 归档。
  const parts = (list || []).map((p) => {
    const html = p.mode === 'multi'
      ? buildMultiReport(p)
      : (p.mode === 'qualitative' ? buildQualitativeReport(p) : buildSingleReport(p))
    const m = /<body>([\s\S]*?)<\/body>/.exec(html)
    return m ? m[1] : ''
  }).filter(Boolean)

  const body = parts
    .map((b, i) => (i === 0 ? b : `<div style="page-break-before:always"></div>${b}`))
    .join('\n')

  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定报告汇编</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告汇编</h1>
<p>共 ${parts.length} 份报告 | 编制日期：${todayStr()}</p>
<div style="page-break-before:always"></div>
${body}
</body></html>`
}

export function downloadHtml(html, name) {
  const blob = new Blob([html], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = name; a.click()
  URL.revokeObjectURL(url)
}

export function printOrSavePdf(html, name) {
  // 浏览器原生：打开新窗口 → 写 HTML → 调 window.print()
  // 用户在弹窗选"另存为 PDF"或打印机 → A4 排版（依赖 CSS @page）
  const w = window.open('', '_blank')
  if (!w) { ElMessage.warning('请允许浏览器弹窗以打印/下载 PDF'); return }
  w.document.open()
  w.document.write(html)
  w.document.close()
  w.focus()
  setTimeout(() => { try { w.print() } catch (e) { console.error(e) } }, 400)
}
