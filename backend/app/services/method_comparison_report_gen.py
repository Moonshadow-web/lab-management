"""方法学比对报告生成（docx）。

两种报告：
- build_single_report(rec_dict) -> bytes   单项目报告（离群值/回归/Bland-Altman/结论/原始数据）
- build_summary_report(rec_dicts) -> bytes 汇总报告（汇总表 + 各项目原始结果）

图表用 Pillow 自绘并嵌入（轴标签用 ASCII，避免容器缺中文字体导致乱码）。
"""
import io
import math

from docx import Document
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

try:
    from PIL import Image, ImageDraw
    _PIL_OK = True
except Exception:  # pragma: no cover
    _PIL_OK = False

CHART_W, CHART_H = 900, 380
COLOR_AXIS = (60, 66, 78)
COLOR_MAIN = (30, 79, 168)
COLOR_ALT = (217, 83, 79)
COLOR_GRID = (225, 228, 233)


# ─────────────────────────── docx 基础工具 ───────────────────────────
def _new_doc():
    doc = Document()
    sec = doc.sections[0]
    sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.0)
    sec.left_margin, sec.right_margin = Cm(2.4), Cm(2.2)
    st = doc.styles["Normal"]
    st.font.name = "宋体"
    st.font.size = Pt(10.5)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")
    return doc


def _title(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(16)
    r.font.name = "黑体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
    return p


def _subtitle(doc, text):
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(12)
    return p


def _h(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(11.5)
    r.font.name = "黑体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "黑体")
    p.paragraph_format.space_before = Pt(10)
    p.paragraph_format.space_after = Pt(4)
    return p


def _para(doc, text, indent=True, size=10.5):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    p.paragraph_format.line_spacing = 1.5
    if indent:
        p.paragraph_format.first_line_indent = Pt(21)
    return p


def _cell(cell, text, bold=False, size=9, center=True):
    cell.text = ""
    p = cell.paragraphs[0]
    if center:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = p.add_run(str(text) if text is not None else "")
    r.bold = bold
    r.font.size = Pt(size)
    r.font.name = "宋体"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "宋体")


def _table(doc, header, rows, widths=None, size=9, merge_header=None):
    """merge_header: [(row_idx, col_start, col_end)] 用于跨列表头。"""
    t = doc.add_table(rows=len(rows) + (1 if header else 0), cols=len(header) if header else len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    r0 = 0
    if header:
        for j, h in enumerate(header):
            _cell(t.rows[0].cells[j], h, bold=True, size=size)
        r0 = 1
    for i, row in enumerate(rows):
        for j, v in enumerate(row[: len(t.columns)]):
            _cell(t.rows[r0 + i].cells[j], v, size=size)
    if merge_header:
        for (ri, c1, c2) in merge_header:
            try:
                t.rows[ri].cells[c1].merge(t.rows[ri].cells[c2])
            except Exception:
                pass
    if widths:
        for row in t.rows:
            for j, w in enumerate(widths[: len(row.cells)]):
                row.cells[j].width = Cm(w)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t


def _figure(doc, img_bytes, caption, width_cm=15.5):
    if not img_bytes:
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(io.BytesIO(img_bytes), width=Cm(width_cm))
    c = doc.add_paragraph()
    c.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = c.add_run(caption)
    r.font.size = Pt(9)


def _num(v, nd=2):
    if v is None:
        return "—"
    try:
        f = float(v)
    except Exception:
        return str(v)
    if abs(f) >= 1000:
        return f"{f:,.{nd}f}"
    return f"{f:.{nd}f}".rstrip("0").rstrip(".") if nd else f"{f:.0f}"


def _info_block(doc, rec):
    rows = [
        ["项目名称", rec.get("project_name") or "—", "报告单位", rec.get("unit") or "—"],
        ["参照方法（A）", rec.get("ref_instrument") or "—", "待评方法（B）", rec.get("test_instrument") or "—"],
        ["A 试剂", rec.get("ref_reagent") or "—", "B 试剂", rec.get("test_reagent") or "—"],
        ["A 校准品", rec.get("ref_calibrator") or "—", "B 校准品", rec.get("test_calibrator") or "—"],
        ["比对方案", rec.get("scheme") or "EP9-A3", "计划样本数", str(rec.get("sample_count") or "—")],
        ["比对日期", rec.get("compare_date") or "—", "允许总误差 TEa", (rec.get("tea") or "—") + ("%" if rec.get("tea") else "")],
    ]
    t = doc.add_table(rows=len(rows), cols=4)
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            _cell(t.rows[i].cells[j], v, bold=(j % 2 == 0), size=9)
    for row in t.rows:
        row.cells[0].width = Cm(3.2)
        row.cells[1].width = Cm(6.4)
        row.cells[2].width = Cm(3.2)
        row.cells[3].width = Cm(4.2)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _sign_block(doc, rec):
    doc.add_paragraph()
    t = doc.add_table(rows=1, cols=4)
    t.style = "Table Grid"
    _cell(t.rows[0].cells[0], "报告人", bold=True)
    _cell(t.rows[0].cells[1], rec.get("operator") or "")
    _cell(t.rows[0].cells[2], "审核人", bold=True)
    _cell(t.rows[0].cells[3], rec.get("reviewer") or "")
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    r = p.add_run(f"民航总医院检验科　生化免疫组　{rec.get('compare_date') or ''}")
    r.font.size = Pt(9)


# ─────────────────────────── Pillow 图表 ───────────────────────────
def _canvas(title_ascii):
    img = Image.new("RGB", (CHART_W, CHART_H), (255, 255, 255))
    d = ImageDraw.Draw(img)
    d.text((14, 10), title_ascii, fill=COLOR_AXIS)
    return img, d


def _scatter_chart(xs, ys, xlabel, ylabel, hlines=None, fit=None, title="", invert=False):
    """通用散点图；hlines=[(y,color)]；fit=(slope,intercept) 在 x 轴同尺度下画线。"""
    if not _PIL_OK or not xs:
        return None
    img, d = _canvas(title)
    L, R, T, B = 70, 24, 40, 46
    pw, ph = CHART_W - L - R, CHART_H - T - B
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    if hlines:
        for y, _c in hlines:
            ymin, ymax = min(ymin, y), max(ymax, y)
    if fit:
        for x in (xmin, xmax):
            yv = fit[0] * x + fit[1]
            ymin, ymax = min(ymin, yv), max(ymax, yv)
    if xmax == xmin:
        xmax = xmin + 1
    if ymax == ymin:
        ymax = ymin + 1
    padx, pady = (xmax - xmin) * 0.06, (ymax - ymin) * 0.10
    xmin, xmax = xmin - padx, xmax + padx
    ymin, ymax = ymin - pady, ymax + pady

    def sx(v):
        return L + (v - xmin) / (xmax - xmin) * pw

    def sy(v):
        return T + ph - (v - ymin) / (ymax - ymin) * ph

    # 网格 + 轴
    for i in range(1, 5):
        yv = ymin + (ymax - ymin) * i / 5
        d.line([(L, sy(yv)), (L + pw, sy(yv))], fill=COLOR_GRID)
        d.text((8, sy(yv) - 5), _num(yv, 2), fill=COLOR_AXIS)
    d.line([(L, T), (L, T + ph)], fill=COLOR_AXIS)
    d.line([(L, T + ph), (L + pw, T + ph)], fill=COLOR_AXIS)
    d.text((L, T + ph + 8), xlabel, fill=COLOR_AXIS)
    d.text((L + pw - 120, T + ph + 26), ylabel, fill=COLOR_AXIS)
    for i in range(5):
        xv = xmin + (xmax - xmin) * i / 4
        d.text((sx(xv) - 12, T + ph + 24), _num(xv, 1), fill=COLOR_AXIS)
    # 参考线
    for y, c in (hlines or []):
        d.line([(L, sy(y)), (L + pw, sy(y))], fill=c, width=2)
        d.text((L + 4, sy(y) - 13), _num(y, 3), fill=c)
    # 拟合线
    if fit:
        d.line([(sx(xmin), sy(fit[0] * xmin + fit[1])),
                (sx(xmax), sy(fit[0] * xmax + fit[1]))], fill=COLOR_ALT, width=2)
    # 散点
    for x, y in zip(xs, ys):
        px, py = sx(x), sy(y)
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=COLOR_MAIN)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _rank_chart(values, title, ylabel):
    """排序差值图（按值排序后连线）。"""
    if not _PIL_OK or not values:
        return None
    img, d = _canvas(title)
    L, R, T, B = 70, 24, 40, 46
    pw, ph = CHART_W - L - R, CHART_H - T - B
    vs = sorted(values)
    ymin, ymax = min(vs + [0]), max(vs + [0])
    if ymax == ymin:
        ymax = ymin + 1
    pad = (ymax - ymin) * 0.1
    ymin, ymax = ymin - pad, ymax + pad

    def sy(v):
        return T + ph - (v - ymin) / (ymax - ymin) * ph

    def sx(i):
        return L + (i / max(1, len(vs) - 1)) * pw

    for i in range(1, 5):
        yv = ymin + (ymax - ymin) * i / 5
        d.line([(L, sy(yv)), (L + pw, sy(yv))], fill=COLOR_GRID)
        d.text((8, sy(yv) - 5), _num(yv, 2), fill=COLOR_AXIS)
    d.line([(L, T), (L, T + ph)], fill=COLOR_AXIS)
    d.line([(L, T + ph), (L + pw, T + ph)], fill=COLOR_AXIS)
    d.line([(L, sy(0)), (L + pw, sy(0))], fill=COLOR_AXIS)
    pts = [(sx(i), sy(v)) for i, v in enumerate(vs)]
    if len(pts) > 1:
        d.line(pts, fill=COLOR_MAIN, width=2)
    for px, py in pts:
        d.ellipse([px - 3, py - 3, px + 3, py + 3], fill=COLOR_MAIN)
    d.text((L, T + ph + 30), "Sample rank (sorted)", fill=COLOR_AXIS)
    d.text((L + pw - 140, T + ph + 30), ylabel, fill=COLOR_AXIS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _charts(pairs, models, ba):
    """生成 5 张图；任一失败返回空，不影响正文。"""
    out = {}
    try:
        xs = [p["a"] for p in pairs]
        ys = [p["b"] for p in pairs]
        diffs = [p["b"] - p["a"] for p in pairs]
        rels = [((p["b"] - p["a"]) / p["a"] * 100) if p["a"] else 0.0 for p in pairs]
        out["A"] = _rank_chart(diffs, "Figure A  Difference (B-A) sorted", "Difference")
        out["B"] = _rank_chart(rels, "Figure B  Percent difference sorted", "Percent (%)")
        pb = models.get("pb") or {}
        if pb.get("slope") is not None:
            out["C"] = _scatter_chart(xs, ys, "Method A (reference)", "Method B (test)",
                                      fit=(pb["slope"], pb["intercept"]),
                                      title="Figure C  Passing-Bablok regression")
        means = [(p["a"] + p["b"]) / 2 for p in pairs]
        hlines = [(ba["mean_diff"], COLOR_AXIS),
                  (ba["loa_high"], COLOR_ALT), (ba["loa_low"], COLOR_ALT)]
        out["E"] = _scatter_chart(means, diffs, "Mean of A and B", "Difference (B-A)",
                                  hlines=hlines, title="Figure E  Bland-Altman plot")
    except Exception:
        pass
    return out


# ─────────────────────────── 单项目报告 ───────────────────────────
def build_single_report(rec: dict) -> bytes:
    rs = rec.get("result_summary") or {}
    det = rec.get("details") or rs.get("details") or {}
    if not rs.get("valid"):
        raise ValueError(rs.get("message") or "比对结果无效，无法生成报告")
    if (rec.get("compare_type") or rs.get("compare_type")) == "qualitative":
        return build_qualitative_report(rec)

    pairs = det.get("per_sample") or rec.get("per_sample") or []
    deming = det.get("deming") or {}
    pb = det.get("pb") or {}
    ba = det.get("ba") or {}
    esd = det.get("esd") or {}
    pr = det.get("pearson") or {}

    doc = _new_doc()
    _title(doc, "方法学比对报告——EP9-A3方案")
    _subtitle(doc, f"（{rec.get('ref_instrument') or '方法A'} vs {rec.get('test_instrument') or '方法B'}"
                   f"——{rec.get('project_name') or ''}）")
    _info_block(doc, rec)

    # 一、离群值检查
    _h(doc, "一、离群值检查")
    rounds = esd.get("rounds") or []
    removed = esd.get("removed_nos") or []
    _para(doc,
          f"根据EP9-A3文件要求，通过广义极端学生化偏差（ESD）方法检验离群值点。"
          f"最初{rs.get('n_input')}份标本中包含{len(removed)}个离群值，"
          + (f"离群点剔除后补充{len(removed)}份样本数据再分析，未发现离群值点。"
             if removed else "未发现离群值点。"))
    if rounds:
        header = ["参数"] + [f"第{r['round']}轮（n={r['n']}）" for r in rounds] + ["剔除后（n=%d）" % rs.get("n_used", 0)]
        rows = [
            ["相对偏差平均值 d"] + [_num(r["mean_d"], 4) for r in rounds] + [_num((rounds[-1]["mean_d"] if rounds else None), 4)],
            ["相对偏差标准差 SD"] + [_num(r["sd_d"], 4) for r in rounds] + [_num((rounds[-1]["sd_d"] if rounds else None), 4)],
            ["ESDmax"] + [_num(r["esd_max"], 4) for r in rounds] + ["—"],
            ["λi（α=0.05）"] + [_num(r["lambda"], 4) for r in rounds] + ["—"],
            ["方法相对偏差（%）"] + [f"{_num(r['outlier_rel_pct'], 2)}（#{r['outlier_no']}）" for r in rounds] + ["—"],
            ["是否离群值"] + ["是" if r["is_outlier"] else "否" for r in rounds] + ["否"],
        ]
        _table(doc, header, rows, size=8.5)
    _para(doc, f"最终纳入统计的有效样本为 {rs.get('n_used')} 例"
               + (f"（剔除第 {'、'.join(str(v) for v in removed)} 号样本）" if removed else "") + "。")

    # 二、方法比对与偏移评估
    _h(doc, "二、方法比对与偏移评估")
    _para(doc, "（1）利用偏差图分析方法间差值的潜在特征：对纳入统计的样本结果绘制差值排序偏差图（图A）"
               "和百分比差值排序偏差图（图B），用于判断差值是否随浓度变化（恒定偏差或比例偏差）。")
    charts = _charts(pairs, {"pb": pb}, ba) if pairs else {}
    _figure(doc, charts.get("A"), "图A　差值排序偏差图")
    _figure(doc, charts.get("B"), "图B　百分比差值排序偏差图")

    prop_txt = (det.get("pb_prop") or {}).get("text") or rs.get("systematic_bias") or "—"
    _para(doc, f"（2）偏移的回归分析：根据EP9-A3文件，使用Deming模型和Passing-Bablok模型进行回归分析。"
               f"以{rec.get('ref_instrument') or '方法A'}结果为X，{rec.get('test_instrument') or '方法B'}结果为Y。"
               f"结果显示比例偏移：{prop_txt}。")
    if pb.get("slope") is not None:
        _figure(doc, charts.get("C"), "图C　Passing-Bablok 回归图")
        ci_s = pb.get("slope_ci") or [None, None]
        ci_i = pb.get("intercept_ci") or [None, None]
        d_ci_s = deming.get("slope_ci") or [None, None]
        d_ci_i = deming.get("intercept_ci") or [None, None]
        rows = [
            ["回归模型", deming.get("equation") or "—", pb.get("equation") or "—"],
            ["Pearson 相关系数",
             f"{_num(pr.get('r'), 4)}（{_num(pr.get('ci_low'), 4)}, {_num(pr.get('ci_high'), 4)}）" if pr else "—",
             f"{_num(pr.get('r'), 4)}（{_num(pr.get('ci_low'), 4)}, {_num(pr.get('ci_high'), 4)}）" if pr else "—"],
            ["斜率的 95%CI",
             f"（{_num(d_ci_s[0], 6)}，{_num(d_ci_s[1], 6)}）" if d_ci_s[0] is not None else "—",
             f"（{_num(ci_s[0], 6)}，{_num(ci_s[1], 6)}）" if ci_s[0] is not None else "—"],
            ["比例偏移",
             (det.get("deming_prop") or {}).get("text", "—"),
             (det.get("pb_prop") or {}).get("text", "—")],
            ["截距的 95%CI",
             f"（{_num(d_ci_i[0], 6)}，{_num(d_ci_i[1], 6)}）" if d_ci_i[0] is not None else "—",
             f"（{_num(ci_i[0], 6)}，{_num(ci_i[1], 6)}）" if ci_i[0] is not None else "—"],
            ["系统偏移",
             (det.get("deming_sys") or {}).get("text", "—"),
             (det.get("pb_sys") or {}).get("text", "—")],
        ]
        _table(doc, ["", "Deming", "Passing-Bablok"], rows, widths=[3.6, 6.2, 6.2])
        _para(doc, "判读说明：Deming 与 Passing-Bablok 应同时看——① 两者结论一致时，以该结论为准；"
                   "② Passing-Bablok 对离群值与分布偏态更稳健，Deming 在已知两法测量误差比例（λ）时更有效，"
                   "本文按 λ=1 处理；③ 若两者对斜率是否偏离 1 的判断不一致，提示数据存在离群点、"
                   "精度随浓度变化或样本覆盖不足，应补充样本后复评，不宜直接下结论；"
                   "④ 斜率 95%CI 不含 1 判为比例偏移，截距 95%CI 不含 0 判为系统偏移，"
                   "两者均不存在再看 Bland-Altman 一致性。")

    # 三、Bland-Altman
    _h(doc, "三、Bland-Altman 一致性评价")
    if ba:
        _para(doc, f"以两种方法的平均值为X轴作Bland-Altman图（图E），P{ba.get('p_text')}，"
                   f"表明两种方法{rec.get('project_name') or ''}检测在统计学上"
                   f"{'一致' if ba.get('consistent') else '不一致'}。")
        _figure(doc, charts.get("E"), "图E　Bland-Altman 图")
        _table(doc, ["平均偏差", "偏差 SD", "95% 一致性下限", "95% 一致性上限", "界限内最大差值", "P 值", "是否一致"],
               [[_num(ba.get("mean_diff"), 4), _num(ba.get("sd_diff"), 4),
                 _num(ba.get("loa_low"), 4), _num(ba.get("loa_high"), 4),
                 _num(ba.get("max_abs_within"), 4), ba.get("p_text"), "是" if ba.get("consistent") else "否"]],
               size=8.5)
    else:
        _para(doc, "未获得有效的 Bland-Altman 统计结果。")

    # 四、结论
    _h(doc, "四、方法学比对结论")
    for line in (rs.get("conclusion_lines") or [rs.get("conclusion", "")]):
        if line:
            _para(doc, line)

    # 五、原始结果
    if pairs:
        _h(doc, "五、原始结果")
        rows = []
        for p in pairs:
            rows.append([p.get("no"), _num(p.get("a"), 3), _num(p.get("b"), 3),
                         _num(p.get("diff"), 3),
                         f"{_num(p.get('rel_pct'), 2)}%" if p.get("rel_pct") is not None else "—"])
        _table(doc, ["样本号", f"方法A（{rec.get('ref_instrument') or ''}）",
                     f"方法B（{rec.get('test_instrument') or ''}）", "绝对偏差", "相对偏差"],
               rows, widths=[2.0, 4.6, 4.6, 3.0, 3.0], size=8.5)

    _sign_block(doc, rec)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ─────────────────────────── 汇总报告 ───────────────────────────
def _stats_desc(recs):
    has_q = any((r.get("compare_type") or (r.get("result_summary") or {}).get("compare_type")) != "qualitative"
                for r in recs)
    has_u = any((r.get("compare_type") or (r.get("result_summary") or {}).get("compare_type")) == "qualitative"
                for r in recs)
    parts = []
    if has_q:
        parts.append("ESD 离群值检验、Deming / Passing-Bablok 偏移评估、Bland-Altman 一致性评价")
    if has_u:
        parts.append("2×2 列联表、阳性/阴性符合率、总符合率与 Kappa 一致性")
    return "；".join(parts) or "—"


def build_summary_report(recs: list) -> bytes:
    if not recs:
        raise ValueError("无可用比对记录")
    doc = _new_doc()
    _title(doc, "方法学比对报告（汇总）")

    first = recs[0]
    projects = "、".join(r.get("project_name", "") for r in recs if r.get("project_name"))
    instruments = sorted({(r.get("ref_instrument") or "") for r in recs}
                         | {(r.get("test_instrument") or "") for r in recs} - {""})
    n_plan = sorted({str(r.get("sample_count")) for r in recs if r.get("sample_count")})
    intro = (
        f"民航总医院检验科　生化免疫组\n"
        f"比对日期：{first.get('compare_date') or '—'}　　比对方案（{first.get('scheme') or 'EP9-A3'}）：\n"
        f"样本：至少{'/'.join(n_plan) or '40'}例不同浓度水平（覆盖正常及高低病理水平）的"
        f"{first.get('sample_source') or '临床检测剩余血清样本'}。\n"
        f"仪器：{'，'.join(x for x in instruments if x)}。\n"
        f"项目：{projects}。\n"
        f"统计分析：{_stats_desc(recs)}。"
    )
    for line in intro.split("\n"):
        _para(doc, line, indent=False, size=10)

    _h(doc, "一、比对结论汇总")

    def _kind(r):
        return (r.get("compare_type") or (r.get("result_summary") or {}).get("compare_type")
                or "quantitative")

    quant = [r for r in recs if _kind(r) != "qualitative"]
    qual = [r for r in recs if _kind(r) == "qualitative"]

    if quant:
        if qual:
            _para(doc, "（1）定量项目（EP9-A3：偏移评估 + Bland-Altman）", indent=False, size=10)
        header = ["序号", "项目", "系统偏移", "比例偏移", "偏移比例", "能否接受",
                  "P值", "是否一致", "95%界限内最大差值", "能否直接替换"]
        rows = []
        for i, r in enumerate(quant, 1):
            rs = r.get("result_summary") or {}
            if not rs.get("valid"):
                rows.append([i, r.get("project_name") or "", "—", "—", "—", "—", "—", "—", "—", "—"])
                continue
            pct = rs.get("proportional_bias_pct")
            rows.append([
                i,
                r.get("project_name") or "",
                rs.get("systematic_bias") or "—",
                "存在" if rs.get("proportional_bias_exists") else ("无" if rs.get("proportional_bias_exists") is False else "—"),
                f"{pct:+.2f}%" if pct is not None else "—",
                "是" if rs.get("acceptable") else ("否" if rs.get("acceptable") is False else "—"),
                rs.get("ba_p") or "—",
                "是" if rs.get("ba_consistent") else "否",
                _num(rs.get("ba_max_abs_within"), 3),
                "能" if rs.get("can_replace") else "否",
            ])
        _table(doc, header, rows, size=8)

    if qual:
        build_qualitative_summary_table(doc, qual)

    _sign_block(doc, first)

    _h(doc, "二、方法学比对原始结果汇总")
    for r in recs:
        det = r.get("details") or {}
        pairs = det.get("per_sample") or []
        rs = r.get("result_summary") or {}
        if not pairs:
            continue
        _para(doc, f"{r.get('project_name')}（{r.get('ref_instrument')} vs {r.get('test_instrument')}）",
              indent=False, size=10)
        if (r.get("compare_type") or rs.get("compare_type")) == "qualitative":
            qrows = [[p.get("no"), p.get("a"), p.get("b"), "一致" if p.get("same") else "不一致"]
                     for p in pairs]
            _table(doc, ["样本号", f"方法A（{r.get('ref_instrument') or ''}）",
                         f"方法B（{r.get('test_instrument') or ''}）", "是否一致"],
                   qrows, widths=[2.2, 4.0, 4.0, 3.0], size=8)
        else:
            data_rows = [[p.get("no"), _num(p.get("a"), 3), _num(p.get("b"), 3),
                          _num(p.get("diff"), 3),
                          f"{_num(p.get('rel_pct'), 2)}%" if p.get("rel_pct") is not None else "—"]
                         for p in pairs]
            _table(doc, ["样本号", f"方法A（{r.get('ref_instrument') or ''}）",
                         f"方法B（{r.get('test_instrument') or ''}）", "绝对偏差", "相对偏差"],
                   data_rows, widths=[1.8, 4.4, 4.4, 2.8, 2.8], size=8)
        _para(doc, f"结论：{rs.get('conclusion') or '—'}", indent=False, size=9)

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ─────────────────────────── 定性项目报告 ───────────────────────────
def build_qualitative_report(rec: dict) -> bytes:
    """定性项目方法学比对报告：2×2 列联表 + 符合率 + Kappa + 结论 + 原始结果。"""
    rs = rec.get("result_summary") or {}
    det = rec.get("details") or {}
    if not rs.get("valid"):
        raise ValueError(rs.get("message") or "比对结果无效，无法生成报告")

    doc = _new_doc()
    _title(doc, "方法学比对报告——定性项目（符合率法）")
    _subtitle(doc, f"（{rec.get('ref_instrument') or '方法A'} vs {rec.get('test_instrument') or '方法B'}"
                   f"——{rec.get('project_name') or ''}）")
    _info_block(doc, rec)

    tp, fn = rs.get("tp", 0), rs.get("fn", 0)
    fp, tn = rs.get("fp", 0), rs.get("tn", 0)
    n = rs.get("n_used", 0)

    _h(doc, "一、检测结果列联表")
    _para(doc, f"共纳入 {n} 例有效样本，两种方法检测结果交叉列联如下：")
    _table(doc,
           ["", f"方法B 阳性（{rec.get('test_instrument') or ''}）",
            f"方法B 阴性（{rec.get('test_instrument') or ''}）", "合计"],
           [[f"方法A 阳性（{rec.get('ref_instrument') or ''}）", tp, fn, tp + fn],
            [f"方法A 阴性（{rec.get('ref_instrument') or ''}）", fp, tn, fp + tn],
            ["合计", tp + fp, fn + tn, n]],
           widths=[6.4, 3.6, 3.6, 2.6], size=9)

    _h(doc, "二、符合率分析")
    ppa_ci = det.get("ppa_ci") or (None, None)
    npa_ci = det.get("npa_ci") or (None, None)
    rows = [
        ["阳性符合率", f"{tp}/{tp + fn}" if (tp + fn) else "—",
         f"{_num(rs.get('ppa'), 2)}%" if rs.get("ppa") is not None else "—",
         f"（{_num(ppa_ci[0], 1)}%，{_num(ppa_ci[1], 1)}%）" if ppa_ci[0] is not None else "—"],
        ["阴性符合率", f"{tn}/{tn + fp}" if (tn + fp) else "—",
         f"{_num(rs.get('npa'), 2)}%" if rs.get("npa") is not None else "—",
         f"（{_num(npa_ci[0], 1)}%，{_num(npa_ci[1], 1)}%）" if npa_ci[0] is not None else "—"],
        ["总符合率", f"{tp + tn}/{n}",
         f"{_num(rs.get('total_rate'), 2)}%", "—"],
    ]
    _table(doc, ["指标", "符合例数", "符合率", "95% 置信区间（Wilson）"], rows,
           widths=[3.6, 3.6, 3.6, 5.4], size=9)
    _para(doc, f"不一致样本 {rs.get('inconsistent_count', 0)} 例"
               + (f"：第 {'、'.join(str(v['no']) for v in (det.get('inconsistent') or []))} 号"
                  if det.get("inconsistent") else "，未发现不一致结果")
               + "。")

    _h(doc, "三、一致性评价")
    _table(doc, ["Kappa 值", "一致性强度", "判定标准", "是否可接受"],
           [[_num(rs.get("kappa"), 4), rs.get("kappa_text") or "—",
             "总符合率≥90% 且 Kappa≥0.75",
             "是" if rs.get("acceptable") else "否"]],
           widths=[3.2, 4.0, 6.0, 3.0], size=9)

    _h(doc, "四、方法学比对结论")
    for line in (rs.get("conclusion_lines") or [rs.get("conclusion", "")]):
        if line:
            _para(doc, line)

    per = det.get("per_sample") or []
    if per:
        _h(doc, "五、原始结果")
        _table(doc, ["样本号", f"方法A（{rec.get('ref_instrument') or ''}）",
                     f"方法B（{rec.get('test_instrument') or ''}）", "是否一致"],
               [[p.get("no"), p.get("a"), p.get("b"), "一致" if p.get("same") else "不一致"] for p in per],
               widths=[2.4, 4.6, 4.6, 3.4], size=9)

    _sign_block(doc, rec)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def build_qualitative_summary_table(doc, recs: list):
    """汇总报告中的定性项目表。"""
    _h(doc, "定性项目符合率汇总")
    header = ["序号", "项目", "方法A", "方法B", "例数", "阳性符合率", "阴性符合率",
              "总符合率", "Kappa", "是否一致", "能否直接替换"]
    rows = []
    for i, r in enumerate(recs, 1):
        rs = r.get("result_summary") or {}
        rows.append([
            i, r.get("project_name") or "", r.get("ref_instrument") or "", r.get("test_instrument") or "",
            rs.get("n_used") or "—",
            f"{_num(rs.get('ppa'), 1)}%" if rs.get("ppa") is not None else "—",
            f"{_num(rs.get('npa'), 1)}%" if rs.get("npa") is not None else "—",
            f"{_num(rs.get('total_rate'), 1)}%" if rs.get("total_rate") is not None else "—",
            _num(rs.get("kappa"), 3),
            "是" if rs.get("acceptable") else "否",
            "能" if rs.get("can_replace") else "否",
        ])
    _table(doc, header, rows, size=8)


# ─────────────────────────── 图表对外接口（详情页用） ───────────────────────────
def _qual_bar_chart(rs):
    """定性项目：符合率条形图（含 90% 判定线）。"""
    if not _PIL_OK:
        return None
    img, d = _canvas("Concordance rate (%)")
    L, R, T, B = 70, 24, 40, 52
    pw, ph = CHART_W - L - R, CHART_H - T - B
    items = [("PPA", rs.get("ppa")), ("NPA", rs.get("npa")), ("Total", rs.get("total_rate"))]
    vals = [v if v is not None else 0 for _, v in items]
    ymax = 105.0

    def sy(v):
        return T + ph - v / ymax * ph

    for i in range(1, 5):
        gv = ymax * i / 5
        d.line([(L, sy(gv)), (L + pw, sy(gv))], fill=COLOR_GRID)
        d.text((8, sy(gv) - 5), f"{gv:.0f}", fill=COLOR_AXIS)
    d.line([(L, T), (L, T + ph)], fill=COLOR_AXIS)
    d.line([(L, T + ph), (L + pw, T + ph)], fill=COLOR_AXIS)
    # 90% 判定线
    d.line([(L, sy(90)), (L + pw, sy(90))], fill=COLOR_ALT, width=2)
    d.text((L + 4, sy(90) - 13), "90%", fill=COLOR_ALT)

    n = len(items)
    slot = pw / n
    bw = slot * 0.42
    for i, ((label, _), v) in enumerate(zip(items, vals)):
        cx = L + slot * (i + 0.5)
        top = sy(v)
        d.rectangle([cx - bw / 2, top, cx + bw / 2, T + ph], fill=COLOR_MAIN)
        d.text((cx - 14, top - 16), f"{v:.1f}", fill=COLOR_AXIS)
        d.text((cx - 12, T + ph + 10), label, fill=COLOR_AXIS)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def build_charts_for(rec: dict) -> dict:
    """按记录返回 {图key: PNG bytes}；定性返回 U 图，定量返回 A/B/C/E。"""
    rs = rec.get("result_summary") or {}
    det = rec.get("details") or {}
    if not rs.get("valid"):
        return {}
    if (rec.get("compare_type") or rs.get("compare_type")) == "qualitative":
        img = _qual_bar_chart(rs)
        return {"U": img} if img else {}
    pairs = det.get("per_sample") or []
    if not pairs:
        return {}
    charts = _charts(pairs, {"pb": det.get("pb") or {}}, det.get("ba") or {})
    return {k: v for k, v in charts.items() if v}
