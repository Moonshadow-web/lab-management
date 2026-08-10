"""测量不确定度评估报告生成（Python 版，供后端批量 API 调用）。

生成与前端 JS 版 buildSingleReport/buildSummaryReport 一致的 HTML 报告（精简版
用于批量 API 归档；前端 UI 仍可用 JS 版生成带交互样式的完整报告）。
"""
import io
from datetime import datetime

REPORT_CODE = "BG-SM-CZ-072"
REPORT_VERSION = "01"
REPORT_DATE = "2025.01.01"


def _esc(s):
    return "" if s is None else str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _stats(values):
    vals = [float(v) for v in (values or []) if v not in (None, "")]
    if not vals:
        return None
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return {"mean": mean, "sd": 0.0, "cv": 0.0, "n": n}
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    sd = var ** 0.5
    return {"mean": mean, "sd": sd, "cv": (sd / mean) * 100, "n": n}


def _calc(values, ucal, pt_result):
    s = _stats(values)
    if not s:
        return {"uc": 0, "U": 0, "passed": True}
    uBias = 0 if pt_result == "合格" else 0
    uc = (s["cv"] ** 2 + uBias ** 2 + (ucal or 0) ** 2) ** 0.5
    U = 2 * uc
    return {"uc": uc, "U": U, "passed": U < 15}


def _style():
    return """body{font-family:SimSun,serif;margin:20px;font-size:12pt;color:#000}
h1{text-align:center;font-size:18pt;margin:4px 0}
h1.s{font-size:16pt;margin:18px 0 8px}
table{width:100%;border-collapse:collapse;margin:10px 0}
td,th{border:1px solid #333;padding:7px;font-size:11pt}
th{background:#f0f0f0;text-align:center}
.info td{width:25%}
.res{text-align:center;font-size:14pt;font-weight:700;color:#c00}
.passed{color:green}
p{line-height:1.7}
@media print{body{margin:0}}"""


def _report_html(p):
    if isinstance(p, dict):
        v = p
    else:
        v = {c.name: getattr(p, c.name) for c in p.__table__.columns}
    l1_vals = v.get("l1_values") or []
    l2_vals = v.get("l2_values") or []
    s1 = _stats(l1_vals)
    s2 = _stats(l2_vals)
    pt = v.get("pt_result") or "合格"
    ucal = float(v.get("ucal") or 0)
    l1 = _calc(l1_vals, ucal, pt)
    l2 = _calc(l2_vals, ucal, pt)
    pass1 = "满足" if l1["passed"] else "待改进"
    pass2 = "满足" if l2["passed"] else "待改进"
    today = datetime.now().strftime("%Y年%m月%d日")
    def fmt(st, kind):
        if not st:
            return "-"
        if kind == "n":
            return str(st["n"])
        return f"{st[kind]:.2f}"
    n1, mn1, sd1, cv1 = fmt(s1, "n"), fmt(s1, "mean"), fmt(s1, "sd"), fmt(s1, "cv")
    n2, mn2, sd2, cv2 = fmt(s2, "n"), fmt(s2, "mean"), fmt(s2, "sd"), fmt(s2, "cv")
    return (
        f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>测量不确定度评定报告</title>'
        f'<style>{_style()}</style></head><body>'
        f'<h1>民航总医院检验科生化免疫组</h1><h1>测量不确定度评定报告</h1>'
        f'<table class="info"><tr><td><b>表格编号</b></td><td>{REPORT_CODE}</td><td><b>版本号</b></td><td>{REPORT_VERSION}</td></tr>'
        f'<tr><td><b>项目名称</b></td><td>{_esc(v.get("project_name"))}</td><td><b>仪器型号</b></td><td>{_esc(v.get("instrument"))}</td></tr>'
        f'<tr><td><b>试剂/校准品</b></td><td>{_esc(v.get("reagent"))}</td><td><b>评定日期</b></td><td>{_esc(v.get("eval_date"))}</td></tr>'
        f'<tr><td><b>编制人</b></td><td>{_esc(v.get("prepared_by") or "金子铮")}</td><td><b>审核人</b></td><td>{_esc(v.get("reviewed_by") or "杨静")}</td></tr></table>'
        f'<h1 class="s">一、不精密度评估</h1>'
        f'<table><tr><th>水平</th><th>n</th><th>均值</th><th>SD</th><th>CV%</th><th>uRw(%)</th></tr>'
        f'<tr><td>L1 水平</td><td>{n1}</td><td>{mn1}</td><td>{sd1}</td><td>{cv1}</td><td>{cv1}</td></tr>'
        f'<tr><td>L2 水平</td><td>{n2}</td><td>{mn2}</td><td>{sd2}</td><td>{cv2}</td><td>{cv2}</td></tr></table>'
        f'<h1 class="s">二、测量不确定度计算</h1>'
        f'<table><tr><th>水平</th><th>uRw(%)</th><th>uBias(%)</th><th>uCal(%)</th><th>Uc(%)</th><th>U(%) k=2</th><th>判定</th></tr>'
        f'<tr><td>L1 水平</td><td>{cv1}</td><td>0</td><td>{ucal:.2f}</td>'
        f'<td>{l1["uc"]:.2f}</td><td class="res">{l1["U"]:.2f}</td><td class="passed">{pass1}</td></tr>'
        f'<tr><td>L2 水平</td><td>{cv2}</td><td>0</td><td>{ucal:.2f}</td>'
        f'<td>{l2["uc"]:.2f}</td><td class="res">{l2["U"]:.2f}</td><td class="passed">{pass2}</td></tr></table>'
        f'<h1 class="s">三、评定结论</h1>'
        f'<p>合成公式：Uc = √(uRw² + uBias² + uCal²)，U = k × Uc（k=2，包含概率 P≈95.45%）。</p>'
        f'<p><b>结论：L1 水平扩展不确定度 U = {l1["U"]:.2f}%，L2 水平 U = {l2["U"]:.2f}%。'
        f'{"满足目标不确定度（U<15%）要求。" if l1["passed"] and l2["passed"] else "部分指标待改进。"}</b></p>'
        f'<div style="margin-top:30px">编制人：____________　审核人：____________　日期：{today}</div>'
        f'</body></html>'
    )


def _summary_html(rows):
    items = []
    for i, p in enumerate(rows, 1):
        v = p if isinstance(p, dict) else {c.name: getattr(p, c.name) for c in p.__table__.columns}
        items.append(
            f'<tr><td>{i}</td><td>{_esc(v.get("project_name"))}</td><td>{_esc(v.get("instrument"))}</td>'
            f'<td>{(v.get("l1_u") or 0):.2f}</td><td>{(v.get("l2_u") or 0):.2f}</td>'
            f'<td>{_esc(v.get("eval_date"))}</td><td>{_esc(v.get("prepared_by"))}</td>'
            f'<td>{"已完成" if (v.get("l1_passed") and v.get("l2_passed")) else "待改进"}</td></tr>'
        )
    return (
        f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>测量不确定度评定汇总表</title>'
        f'<style>{_style()}</style></head><body>'
        f'<h1>民航总医院检验科生化免疫组</h1><h1>测量不确定度评定汇总表</h1>'
        f'<p>表格编号：BG-SM-GL-020 | 编制日期：{datetime.now().strftime("%Y年%m月%d日")}</p>'
        f'<table><tr><th>序号</th><th>项目名称</th><th>仪器</th><th>L1 U(%)</th><th>L2 U(%)</th>'
        f'<th>评定日期</th><th>编制人</th><th>状态</th></tr>{"".join(items)}</table>'
        f'</body></html>'
    )


def build_uncertainty_html(record: dict) -> bytes:
    return _report_html(record).encode("utf-8")


def build_summary_html(records: list) -> bytes:
    return _summary_html(records).encode("utf-8")
