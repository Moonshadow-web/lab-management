"""测量不确定度评估报告生成（Python 版，供后端批量 API 调用）。

按 BG-SM-CZ-072 模板，支持 single/multi 两种模式，公式与图1/图2示例一致。
"""
import io
import json
import math
from datetime import datetime

REPORT_CODE = "BG-SM-CZ-072"
REPORT_VERSION = "01"
REPORT_DATE = "2025.01.01"


def _esc(s):
    return "" if s is None else str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _fmt(v, n=2):
    try:
        return f"{float(v):.{n}f}"
    except Exception:
        return "-"


def _parse_multi_systems(v):
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        try:
            return json.loads(v or "[]")
        except Exception:
            return []
    return []


def _style():
    return """body{font-family:SimSun,serif;margin:20px;font-size:12pt;color:#000}
h1{text-align:center;font-size:18pt;margin:4px 0}
h1.s{font-size:16pt;margin:18px 0 8px}
h2{font-size:14pt;margin-top:14px;border-bottom:1px solid #333;padding-bottom:4px}
table{width:100%;border-collapse:collapse;margin:8px 0}
td,th{border:1px solid #333;padding:6px;font-size:11pt}
th{background:#f0f0f0;text-align:center}
.info td{width:25%}
.res{text-align:center;font-size:14pt;font-weight:700;color:#c00}
.passed{color:green}
.failed{color:#c00}
.note{font-size:11pt;margin:10px 0;line-height:1.7}
@page{size:A4;margin:18mm 16mm}
p{line-height:1.7}
@media print{body{margin:0}}"""


def _report_single_html(v):
    """单个测量系统报告（图1范式）。"""
    l1_mean = float(v.get("l1_mean") or 0)
    l1_sd = float(v.get("l1_sd") or 0)
    l1_n = int(v.get("l1_n") or 0)
    l2_mean = float(v.get("l2_mean") or 0)
    l2_sd = float(v.get("l2_sd") or 0)
    l2_n = int(v.get("l2_n") or 0)
    ucal = float(v.get("ucal") or 0)
    ucal_source = v.get("ucal_source") or "厂家"
    rsd1 = l1_sd / l1_mean * 100 if l1_mean > 0 else 0
    rsd2 = l2_sd / l2_mean * 100 if l2_mean > 0 else 0
    # u_Rw 公式
    if l1_n >= 2 and l2_n >= 2 and l1_mean > 0 and l2_mean > 0:
        u_rw_sq = (rsd1 ** 2 * (l1_n - 1) + rsd2 ** 2 * (l2_n - 1)) / (l1_n + l2_n - 2)
        u_rw = math.sqrt(u_rw_sq)
    else:
        u_rw_sq = 0
        u_rw = 0
    u_c = math.sqrt(u_rw ** 2 + ucal ** 2)
    u_ext = 2 * u_c
    target_bias = float(v.get("target_bias") or 0)
    target_text = v.get("target_bias_text") or ""
    target_src = v.get("target_bias_source") or ""
    passed = u_ext < target_bias if target_bias > 0 else u_ext < 15
    pv = float(v.get("patient_value") or 0)
    pv_unit = v.get("patient_unit") or ""
    pv_ext = pv * u_ext / 100 if pv > 0 else 0
    today = datetime.now().strftime("%Y年%m月%d日")
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>测量不确定度评定报告 - {_esc(v.get('project_name'))}</title>
<style>{_style()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h1 class="s">第一节 单个测量系统测量不确定度评定范例</h1>
<table class="info">
<tr><td><b>表格编号</b></td><td>{REPORT_CODE}</td><td><b>版本号</b></td><td>{REPORT_VERSION}</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">{_esc(v.get('project_name'))}</td></tr>
<tr><td><b>检测系统</b></td><td>{_esc(v.get('instrument'))}</td><td><b>试剂/校准品</b></td><td>{_esc(v.get('reagent'))}</td></tr>
<tr><td><b>评定日期</b></td><td>{_esc(v.get('eval_date'))}</td><td><b>评定周期</b></td><td>{int(v.get('cycle_months') or 12)} 个月</td></tr>
<tr><td><b>编制人</b></td><td>{_esc(v.get('prepared_by') or '金子铮')}</td><td><b>审核人</b></td><td>{_esc(v.get('reviewed_by') or '杨静')}</td></tr>
</table>
<h2>1. 定义被测量</h2>
<table class="info">
<tr><td><b>系统</b></td><td>血清</td><td><b>被测量</b></td><td>{_esc(v.get('project_name'))}</td></tr>
<tr><td><b>单位</b></td><td colspan="3">{_esc(pv_unit) or '—'}</td></tr>
<tr><td><b>测量方法</b></td><td colspan="3">{_esc(v.get('reagent')) or '—'}</td></tr>
</table>
<p><b>被测量定义为：</b>使用{_esc(v.get('instrument'))}测定{_esc(v.get('project_name'))}（{_esc(pv_unit) or '—'}）。</p>
<h2>2. 不精密度引入测量不确定度分量</h2>
<div class="note">一般采用 <b>≥12 个月</b>的室内质控数据（保证长期精密度评估的代表性）。</div>
<p><b>(1) 该测量系统测量室内质控数据</b></p>
<table>
<tr><th>水平</th><th>均值</th><th>标准差</th><th>u<sub>Rw</sub></th><th>相对标准差 RSD</th><th>测试数 n</th></tr>
<tr><td>质控水平 1 (L1)</td><td>{_fmt(l1_mean)} {_esc(pv_unit)}</td><td>{_fmt(l1_sd)} {_esc(pv_unit)}</td><td>{_fmt(l1_sd)} {_esc(pv_unit)}</td><td>{_fmt(rsd1)}%</td><td>{l1_n}</td></tr>
<tr><td>质控水平 2 (L2)</td><td>{_fmt(l2_mean)} {_esc(pv_unit)}</td><td>{_fmt(l2_sd)} {_esc(pv_unit)}</td><td>{_fmt(l2_sd)} {_esc(pv_unit)}</td><td>{_fmt(rsd2)}%</td><td>{l2_n}</td></tr>
</table>
<p><b>(2) 由不精密度引入的总不确定度（合并 L1、L2 RSD）</b></p>
<p>u<sub>Rw</sub> = √[(RSD<sub>L1</sub>² × (n<sub>L1</sub>-1) + RSD<sub>L2</sub>² × (n<sub>L2</sub>-1)) / (n<sub>L1</sub> + n<sub>L2</sub> - 2)]</p>
<p>= √[({_fmt(rsd1)}² × ({l1_n}-1) + {_fmt(rsd2)}² × ({l2_n}-1)) / ({l1_n}+{l2_n}-2)]</p>
<p>= <b>{_fmt(u_rw)}%</b></p>
<h2>3. 偏倚引入测量不确定度分量</h2>
<p><b>(1) 校准品定值引入的不确定度（u<sub>cal</sub>）：</b>来源：{_esc(ucal_source)}。校准品相对标准不确定度为 <b>{_fmt(ucal)}%</b>。</p>
<p><b>(2) 室间质评：</b>实验室参加 EQA 成绩合格（偏倚在允许范围内），偏倚分量不重复计算（已含于精密度）。</p>
<h2>4. 计算合成不确定度</h2>
<p>u<sub>c</sub> = √(u<sub>Rw</sub>² + u<sub>cal</sub>²) = √({_fmt(u_rw)}² + {_fmt(ucal)}²) = <b>{_fmt(u_c)}%</b></p>
<h2>5. 计算扩展不确定度</h2>
<p>U = k × u<sub>c</sub> = 2 × {_fmt(u_c)}% = <span class="res">{_fmt(u_ext)}%</span> （k=2，包含概率 P≈95.45%）</p>
<h2>6. 测量不确定度的报告</h2>
{'<p>患者在该系统的单个测量结果 = ' + _fmt(pv) + ' ' + _esc(pv_unit) + '，则扩展不确定度 = ' + _fmt(pv) + ' × ' + _fmt(u_ext) + '% = ' + _fmt(pv_ext, 4) + ' ' + _esc(pv_unit) + '（k=2），即测量结果 = (' + _fmt(pv) + ' ± ' + _fmt(pv_ext, 4) + ') ' + _esc(pv_unit) + '（k=2）。</p>' if pv > 0 else '<p>（未填患者结果，跳过报告区间）</p>'}
<h2>7. 结论</h2>
<div class="note">
<b>质量目标：</b>扩展不确定度 U 与允许总误差 TEa 参考比较。
{'<p>目标允许总误差 TEa（来源：' + _esc(target_src) + '） = <b>' + _fmt(target_bias) + '%</b>，原始标准：' + _esc(target_text) + '</p>' if target_bias > 0 else '<p>项目质量要求库未找到允许总误差，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>{_fmt(u_ext)}%</b> {('&lt;' if passed else '≥')} {(_fmt(target_bias) if target_bias > 0 else '15')}% → <span class="{('passed' if passed else 'failed')}">{('符合要求' if passed else '未达标')}</span></p>
<p><b>结论：</b>{('实验室' + _esc(v.get('instrument')) + '测量' + _esc(v.get('project_name')) + '浓度的性能符合要求。' if passed else '扩展不确定度超出质量目标，需改进精密度或校准溯源。')}</p>
</div>
<div style="margin-top:30px">编制人：____________　审核人：____________　日期：{today}</div>
</body></html>"""


def _report_multi_html(v):
    """多个测量系统报告（图2范式）。"""
    systems = _parse_multi_systems(v.get("multi_systems"))
    if not systems:
        return _report_single_html(v)  # 兜底按单系统
    # 计算每个系统 RSD1/RSD2
    rows_sys = []
    per_sys_rsd_sq = []
    l1_means, l2_means = [], []
    for s in systems:
        m1, sd1, n1 = float(s.get("l1_mean") or 0), float(s.get("l1_sd") or 0), int(s.get("l1_n") or 0)
        m2, sd2, n2 = float(s.get("l2_mean") or 0), float(s.get("l2_sd") or 0), int(s.get("l2_n") or 0)
        rsd1 = sd1 / m1 * 100 if m1 > 0 else 0
        rsd2 = sd2 / m2 * 100 if m2 > 0 else 0
        u_rw_sys = math.sqrt((rsd1 ** 2 + rsd2 ** 2) / 2)
        per_sys_rsd_sq.append(u_rw_sys ** 2)
        l1_means.append(m1)
        l2_means.append(m2)
        rows_sys.append((s.get("name") or "—", n1, m1, sd1, rsd1, m2, sd2, rsd2, u_rw_sys))
    # 系统内不精密度方差 = 各系统 RSD² 均值
    u2_within = sum(per_sys_rsd_sq) / len(per_sys_rsd_sq) if per_sys_rsd_sq else 0
    # 均值方差（按相对 RSD）
    def _mean_rsd_pct(arr):
        if len(arr) < 2:
            return 0.0
        avg = sum(arr) / len(arr)
        if avg <= 0:
            return 0.0
        # 总体标准差
        var = sum((x - avg) ** 2 for x in arr) / (len(arr) - 1)
        return math.sqrt(var) / avg * 100
    l1_rsd = _mean_rsd_pct(l1_means)
    l2_rsd = _mean_rsd_pct(l2_means)
    u2_between = (l1_rsd ** 2 + l2_rsd ** 2) / 2
    u_pooled = math.sqrt(u2_within + u2_between)
    # 总均值
    total_mean_l1 = sum(l1_means) / len(l1_means) if l1_means else 0
    total_mean_l2 = sum(l2_means) / len(l2_means) if l2_means else 0
    overall_mean = (total_mean_l1 + total_mean_l2) / 2
    u_rel = u_pooled / overall_mean * 100 if overall_mean > 0 else 0
    ucal = float(v.get("ucal") or 0)
    ucal_source = v.get("ucal_source") or "厂家"
    u_c = math.sqrt(u_rel ** 2 + ucal ** 2)
    u_ext = 2 * u_c
    target_bias = float(v.get("target_bias") or 0)
    target_text = v.get("target_bias_text") or ""
    target_src = v.get("target_bias_source") or ""
    passed = u_ext < target_bias if target_bias > 0 else u_ext < 15
    pv = float(v.get("patient_value") or 0)
    pv_unit = v.get("patient_unit") or ""
    pv_ext = pv * u_ext / 100 if pv > 0 else 0
    today = datetime.now().strftime("%Y年%m月%d日")
    # 系统表
    sys_rows_html = "".join([
        f"<tr><td>{_esc(name)}</td><td>{n1}</td><td>{_fmt(m1)}</td><td>{_fmt(sd1)}</td><td>{_fmt(rsd1)}%</td>"
        f"<td>{n2}</td><td>{_fmt(m2)}</td><td>{_fmt(sd2)}</td><td>{_fmt(rsd2)}%</td><td>{_fmt(u_sys):.4f}</td></tr>"
        for (name, n1, m1, sd1, rsd1, m2, sd2, rsd2, u_sys) in rows_sys
    ])
    return f"""<!DOCTYPE html><html><head><meta charset="UTF-8"><title>测量不确定度评定报告(多系统) - {_esc(v.get('project_name'))}</title>
<style>{_style()}</style></head><body>
<h1>民航总医院检验科生化免疫组</h1>
<h1>测量不确定度评定报告</h1>
<h1 class="s">第二节 多个测量系统测量不确定度评定范例</h1>
<table class="info">
<tr><td><b>表格编号</b></td><td>{REPORT_CODE}</td><td><b>版本号</b></td><td>{REPORT_VERSION}</td></tr>
<tr><td><b>项目名称</b></td><td colspan="3">{_esc(v.get('project_name'))}</td></tr>
<tr><td><b>检测系统数</b></td><td>{len(systems)}</td><td><b>系统列表</b></td><td>{_esc('、'.join(s.get('name') or '—' for s in systems))}</td></tr>
<tr><td><b>评定日期</b></td><td>{_esc(v.get('eval_date'))}</td><td><b>评定周期</b></td><td>{int(v.get('cycle_months') or 12)} 个月</td></tr>
<tr><td><b>编制人</b></td><td>{_esc(v.get('prepared_by') or '金子铮')}</td><td><b>审核人</b></td><td>{_esc(v.get('reviewed_by') or '杨静')}</td></tr>
</table>
<p>工作量大的临床实验室可使用几个相同的测量系统检测相同的被测量，所以同一个人体样本可能在其中任何一个系统上进行测量。此种情况下，评定单一 u(y) 是有用的，该 u(y) 可以合理地应用于由其中任一系统产生的结果。</p>
<p>多个测量系统通常用同一批次的 IQC 同时监控。分别计算每个测量系统的 u<sub>Rw</sub> 值。对于相同的 IQC 批次，每个系统可能得到不同的 IQC 均值。因此，必须计算多个测量系统该 IQC 批次的相对标准不确定度平均值，并用于计算合成平均不确定度。</p>
<h2>1. 定义被测量</h2>
<table class="info">
<tr><td><b>系统</b></td><td>血清</td><td><b>被测量</b></td><td>{_esc(v.get('project_name'))}</td></tr>
<tr><td><b>单位</b></td><td colspan="3">{_esc(pv_unit) or '—'}</td></tr>
<tr><td><b>测量方法</b></td><td colspan="3">{_esc(v.get('reagent')) or '—'}</td></tr>
</table>
<p><b>被测量定义为：</b>多系统测定{_esc(v.get('project_name'))}（{_esc(pv_unit) or '—'}）。</p>
<h2>2. 不精密度引入测量不确定度分量</h2>
<p><b>(1) {len(systems)} 个测量系统测量室内质控数据</b></p>
<table>
<tr><th rowspan="2">测量系统</th><th colspan="4">L1 水平</th><th colspan="4">L2 水平</th><th rowspan="2">u<sub>Rw</sub>(系统, %)</th></tr>
<tr><th>n<sub>L1</sub></th><th>均值</th><th>SD</th><th>RSD%</th><th>n<sub>L2</sub></th><th>均值</th><th>SD</th><th>RSD%</th></tr>
{sys_rows_html}
</table>
<p><b>(2) 计算各系统平均值的方差（系统间差异，水平内合并）</b></p>
<p>L1 系统均值 = ({' + '.join(_fmt(m) for m in l1_means)}) / {len(l1_means)} = {_fmt(total_mean_l1)} {(' ' + _esc(pv_unit)) if pv_unit else ''}</p>
<p>L2 系统均值 = ({' + '.join(_fmt(m) for m in l2_means)}) / {len(l2_means)} = {_fmt(total_mean_l2)} {(' ' + _esc(pv_unit)) if pv_unit else ''}</p>
<p>各系统 L1 均值相对标准差 RSD = {_fmt(l1_rsd)}%，L2 均值相对标准差 RSD = {_fmt(l2_rsd)}%</p>
<p>u²<sub>均值方差(A,B,C)</sub> = (RSD<sub>L1均值</sub>² + RSD<sub>L2均值</sub>²) / 2 = ({_fmt(l1_rsd)}² + {_fmt(l2_rsd)}²) / 2 = <b>{_fmt(u2_between, 4)}</b></p>
<p><b>(3) 计算测量系统内平均不精密度的方差</b></p>
<p>u²<sub>Rw(A,B,C)</sub> = (各系统 RSD² 均值) = {_fmt(u2_within, 4)}</p>
<p><b>(4) 将系统均值方差与系统内不精密度方差合并</b></p>
<p>u<sub>(pooled)</sub> = √(u²<sub>均值方差</sub> + u²<sub>Rw</sub>) = √({_fmt(u2_between, 4)} + {_fmt(u2_within, 4)}) = <b>{_fmt(u_pooled, 4)}</b></p>
<p>u<sub>rel(pooled)</sub> = u<sub>(pooled)</sub> / 总均值 × 100 = {_fmt(u_pooled, 4)} / {_fmt(overall_mean)} × 100 = <b>{_fmt(u_rel)}%</b></p>
<h2>3. 总不确定度评定</h2>
<p>厂家提供的校准品相对标准不确定度为 {_fmt(ucal)}%（来源：{_esc(ucal_source)}）。实验室参加 EQA 成绩合格，扩展不确定度计算如下：</p>
<p>U<sub>rel</sub> = √({_fmt(u_rel)}² + {_fmt(ucal)}²) × 2 = <span class="res">{_fmt(u_ext)}%</span>（k=2）</p>
<p>如果厂家未提供校准品的不确定度，则总不确定度可以计算为：U<sub>rel</sub> = u<sub>rel(pooled)</sub> × 2 = {_fmt(u_rel)} × 2 = <b>{_fmt(2*u_rel, 4)}%</b>（k=2）</p>
<h2>4. 测量不确定度的报告</h2>
{'<p>患者在该系统的单个测量结果 = ' + _fmt(pv) + ' ' + _esc(pv_unit) + '，则扩展不确定度 = ' + _fmt(pv) + ' × ' + _fmt(u_ext) + '% = ' + _fmt(pv_ext, 4) + ' ' + _esc(pv_unit) + '（k=2），即测量结果 = (' + _fmt(pv) + ' ± ' + _fmt(pv_ext, 4) + ') ' + _esc(pv_unit) + '（k=2）。</p>' if pv > 0 else '<p>（未填患者结果，跳过报告区间）</p>'}
<h2>5. 结论</h2>
<div class="note">
<b>质量目标：</b>扩展不确定度 U 与允许总误差 TEa 参考比较。
{'<p>目标允许总误差 TEa（来源：' + _esc(target_src) + '） = <b>' + _fmt(target_bias) + '%</b>，原始标准：' + _esc(target_text) + '</p>' if target_bias > 0 else '<p>项目质量要求库未找到允许总误差，临时按 U&lt;15% 兜底判断。</p>'}
<p><b>比较结果：</b>U = <b>{_fmt(u_ext)}%</b> {('&lt;' if passed else '≥')} {(_fmt(target_bias) if target_bias > 0 else '15')}% → <span class="{('passed' if passed else 'failed')}">{('符合要求' if passed else '未达标')}</span></p>
<p><b>结论：</b>{('实验室多个测量系统测定' + _esc(v.get('project_name')) + '的性能符合要求。' if passed else '扩展不确定度超出质量目标，需改进精密度或校准溯源。')}</p>
</div>
<div style="margin-top:30px">编制人：____________　审核人：____________　日期：{today}</div>
</body></html>"""


def build_uncertainty_html(record: dict) -> bytes:
    """按 record['mode'] 选择 single/multi 模板。"""
    v = record
    if v.get("mode") == "multi":
        return _report_multi_html(v).encode("utf-8")
    return _report_single_html(v).encode("utf-8")


def _summary_html(rows):
    items = []
    for i, p in enumerate(rows, 1):
        v = p if isinstance(p, dict) else {c.name: getattr(p, c.name) for c in p.__table__.columns}
        items.append(
            f'<tr><td>{i}</td><td>{_esc(v.get("project_name"))}</td><td>{_esc(v.get("instrument"))}</td>'
            f'<td>{_fmt(v.get("u_extended"))}</td><td>{_fmt(v.get("target_bias"))}</td>'
            f'<td>{_esc(v.get("target_bias_source"))}</td>'
            f'<td>{"符合" if v.get("passed") else "未达标"}</td><td>{_esc(v.get("eval_date"))}</td></tr>'
        )
    return (
        f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title>'
        f'<style>{_style()}</style></head><body>'
        f'<h1>民航总医院检验科生化免疫组</h1><h1>测量不确定度评定汇总表</h1>'
        f'<p>表格编号：BG-SM-GL-020 | 编制日期：{datetime.now().strftime("%Y年%m月%d日")}</p>'
        f'<table><tr><th>序号</th><th>项目名称</th><th>仪器/系统</th><th>U(%)</th><th>目标偏倚(%)</th><th>目标来源</th><th>判定</th><th>评定日期</th></tr>'
        f'{"".join(items)}</table>'
        f'<p style="margin-top:14px">目标偏倚优先级：WS/T 403-2024（行标） &gt; 2025 北京市互认 &gt; 1/2 × NCCL EQA 允许总误差。</p>'
        f'</body></html>'
    )


def build_summary_html(records: list) -> bytes:
    return _summary_html(records).encode("utf-8")
