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
<tr><td><b>编制人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
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
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
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
<tr><td><b>编制人</b></td><td>${esc(p.prepared_by || '金子铮')}</td><td><b>审核人</b></td><td>${esc(p.reviewed_by || '杨静')}</td></tr>
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
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
</body></html>`
}

export function buildSummaryReport(list) {
  const rows = list.map((p, i) => {
    return `<tr>
    <td>${i + 1}</td>
    <td>${esc(p.project_name)}${p.mode === 'multi' ? ' <span style="color:#e6a23c;font-size:11px">[多系统]</span>' : ''}</td>
    <td>${esc(p.project_method || p.instrument || '-')}</td>
    <td>${(p.u_extended || 0).toFixed(2)}</td>
    <td>${(p.target_bias || 0).toFixed(2)}</td>
    <td>${esc(p.target_bias_source || '-')}</td>
    <td>${p.passed ? '符合' : '未达标'}</td>
    <td>${esc(p.eval_date || '-')}</td>
    <td>${esc(p.prepared_by || '')}</td>
  </tr>`}).join('')
  return `<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title><style>${reportStyle()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定汇总表</h1>
<p>表格编号：BG-SM-GL-020 | 编制日期：${todayStr()}</p>
<table><tr><th>序号</th><th>项目</th><th>测量方法</th><th>U(%)</th><th>允许总误差 TEa(%)</th><th>目标来源</th><th>判定</th><th>评定日期</th><th>编制人</th></tr>${rows}</table>
<p style="margin-top:14px">质量目标：卫健委 EQA 允许总误差（NCCL），U &lt; TEa 判为符合要求。</p>
<div class="sign"><div>编制人签字：____________</div><div>审核人签字：____________</div></div>
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
