"""仪器间比对：结果计算 + 报告生成（docx，保留表格编号）+ HTML 预览。

计算逻辑：
- 定量：偏倚 = (val - ref)/ref × 100（relative）或 val - ref（absolute）；
  是否允许 = |偏倚| ≤ 允许TE。
- 定性：以参照仪器 5 例样本为基准，逐台比对仪器计算阴阳符合率。

报告版式严格参照对应 SOP 表单（BG-SM-CZ-021/022/024~027/071），保留表格编号。
"""

import json
import os
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_ORIENT
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Pt, Cm, RGBColor

from ..models.comparison import ComparisonGroup, ComparisonPlan, ComparisonResult, ComparisonQualResult
from ..models.instrument import Instrument

REPORT_DIR = None  # 由 main 注入（DATA_DIR/comparison_reports）


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _load_json(s, default):
    try:
        v = json.loads(s) if isinstance(s, str) else s
        return v if v is not None else default
    except Exception:
        return default


def disp_name(inst: Instrument) -> str:
    """人可识别的仪器显示名：优先规格型号(model)，其次名称。

    仪器档案里 name 多为通用名（如"全自动生化分析仪"），model 才是可识别的
    具体型号（如"贝克曼AU5821 A"、"TOP700A"）。比对模块统一用 model 展示。
    """
    if not inst:
        return ""
    model = (inst.model or "").strip()
    name = (inst.name or "").strip()
    if model and len(model) <= 40:
        return model
    return name or model or f"仪器{inst.id}"


def _instruments_of(db, group: ComparisonGroup):
    ids = _load_json(group.instrument_ids, [])
    ref_id = group.reference_instrument_id
    out = []
    seen = set()
    for iid in ids:
        if iid in seen:
            continue
        inst = db.get(Instrument, iid)
        if inst:
            seen.add(iid)
            out.append({"id": inst.id, "name": disp_name(inst), "model": inst.model or "",
                        "is_reference": inst.id == ref_id})
    if not any(x["is_reference"] for x in out) and ref_id and ref_id not in seen:
        inst = db.get(Instrument, ref_id)
        if inst:
            out.insert(0, {"id": inst.id, "name": disp_name(inst), "model": inst.model or "",
                           "is_reference": True})
    return out


def _compared_ids(group: ComparisonGroup):
    ids = _load_json(group.instrument_ids, [])
    return [i for i in ids if i != group.reference_instrument_id]


def _parse_float(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _compute_bias(ref, val, te, mode):
    """返回 (偏倚值或None, 是否允许或None)。"""
    rf = _parse_float(ref)
    vf = _parse_float(val)
    tf = _parse_float(te)
    if rf is None or vf is None or tf is None:
        return None, None
    if mode == "absolute":
        bias = vf - rf
    else:
        if rf == 0:
            return None, None
        bias = (vf - rf) / rf * 100.0
    accepted = abs(bias) <= tf + 1e-9
    return round(bias, 2), accepted


# ---------------------------------------------------------------------------
# 计算
# ---------------------------------------------------------------------------
def compute_data(db, group: ComparisonGroup, plan: ComparisonPlan):
    instruments = _instruments_of(db, group)
    ref_id = group.reference_instrument_id
    compared = _compared_ids(group)
    items = _load_json(group.items, [])

    if group.category == "定性":
        quals = {
            q.item: q
            for q in db.query(ComparisonQualResult).filter_by(plan_id=plan.id).all()
        }
        all_ids = [ins["id"] for ins in instruments]

        def _qual_applicable(it):
            ids = it.get("instrument_ids") or []
            if not ids:
                return set(all_ids)
            return {i for i in all_ids if i in set(ids)}

        matrix = []
        overall_min = 100.0
        for it in items:
            qr = quals.get(it["name"])
            rj = _load_json(qr.results_json, {}) if qr else {}
            ref_res = rj.get(str(ref_id))
            app = _qual_applicable(it)
            insts = {}
            for ins in instruments:
                if ins["id"] not in app:
                    insts[ins["id"]] = {"name": ins["name"], "results": [], "agreement": None, "masked": True}
                    continue
                res = rj.get(str(ins["id"])) or []
                agreement = None
                if res and ref_res and len(res) == len(ref_res):
                    valid = sum(1 for a in res if a in ("P", "N"))
                    matches = sum(1 for a, b in zip(res, ref_res) if a == b and a in ("P", "N"))
                    agreement = round(matches / valid * 100, 1) if valid else None
                insts[ins["id"]] = {"name": ins["name"], "results": res, "agreement": agreement, "masked": False}
            matrix.append({"item": it["name"], "insts": insts})
        return {
            "category": "定性",
            "instruments": instruments,
            "compared": compared,
            "matrix": matrix,
            "ref_id": ref_id,
        }

    # 定量
    results = {
        (r.item, r.level): r
        for r in db.query(ComparisonResult).filter_by(plan_id=plan.id).all()
    }
    levels = group.levels or 5

    def _applicable(it):
        """该项目适用的比对仪器 id 集合；未配置(空)=组内全部比对仪器。"""
        ids = it.get("instrument_ids") or []
        if not ids:
            return set(compared)
        return {c for c in compared if c in set(ids)}

    matrix = []
    for lv in range(1, levels + 1):
        rows = []
        for it in items:
            r = results.get((it["name"], lv))
            ref_val = r.reference_value if r else ""
            app = _applicable(it)
            insts = {}
            for cid in compared:
                if cid not in app:
                    insts[str(cid)] = {"value": "", "bias": None, "accepted": None, "masked": True}
                    continue
                v = _load_json(r.values_json, {}).get(str(cid), "") if r else ""
                bias, accepted = _compute_bias(ref_val, v, it.get("te", "0"), it.get("mode", "relative"))
                insts[str(cid)] = {"value": v, "bias": bias, "accepted": accepted, "masked": False}
            rows.append({
                "item": it["name"],
                "label": it.get("label", ""),
                "te": it.get("te", "0"),
                "mode": it.get("mode", "relative"),
                "ref": ref_val,
                "insts": insts,
            })
        matrix.append({"level": lv, "rows": rows})

    # 汇总：每项目各水平是否全部允许（仅统计适用仪器）
    summary = []
    for it in items:
        app = _applicable(it)
        level_ok = []
        for lv in range(1, levels + 1):
            r = results.get((it["name"], lv))
            ok = True
            for cid in compared:
                if cid not in app:
                    continue
                v = _load_json(r.values_json, {}).get(str(cid), "") if r else ""
                _, accepted = _compute_bias(r.reference_value if r else "", v, it.get("te", "0"), it.get("mode", "relative"))
                if accepted is not True:
                    ok = False
                    break
            level_ok.append(ok)
        summary.append({"item": it["name"], "label": it.get("label", ""), "levels": level_ok, "ok": all(level_ok)})
    return {
        "category": "定量",
        "instruments": instruments,
        "compared": compared,
        "matrix": matrix,
        "summary": summary,
        "ref_id": ref_id,
    }


# ---------------------------------------------------------------------------
# HTML 预览
# ---------------------------------------------------------------------------
def build_html(group: ComparisonGroup, plan: ComparisonPlan, data: dict):
    css = """
    <style>
      .rep { font-family: 'Microsoft YaHei','SimSun',serif; color:#222; max-width:960px; margin:0 auto; padding:16px; }
      .rep h1 { text-align:center; font-size:20px; margin:6px 0; }
      .rep .sub { text-align:center; font-size:12px; color:#555; margin-bottom:10px; }
      .rep h2 { font-size:14px; margin:14px 0 6px; border-left:4px solid #1a365d; padding-left:8px; }
      .rep p { font-size:13px; line-height:1.7; margin:4px 0; }
      .rep table { border-collapse:collapse; width:100%; font-size:12px; margin:6px 0; }
      .rep th, .rep td { border:1px solid #444; padding:4px 6px; text-align:center; }
      .rep th { background:#eef2f8; }
      .rep .item { text-align:left; }
      .rep .no { color:#c0392b; font-weight:700; }
      .rep .yes { color:#27ae60; font-weight:700; }
      .rep .mask { background:#f0f0f0; color:#aaa; }
      .rep .foot { margin-top:18px; font-size:13px; }
      .rep .summary-ok { color:#27ae60; }
    </style>"""
    title = group.form_title or ("定性室内比对结果记录及分析报告表" if group.category == "定性" else "定量室内比对结果记录分析表")
    form_code = group.form_code or ""
    year = plan.year or ""
    html = [f'<div class="rep">{css}<h1>{title}</h1>']
    html.append(f'<div class="sub">表格编号 {form_code}　　民航总医院检验科生化免疫组　　生效日期：{year}.01.01</div>')

    if data["category"] == "定性":
        html.append("<h2>比对结果</h2>")
        html.append('<table><thead><tr><th class="item">检验项目</th>')
        for ins in data["instruments"]:
            tag = "（参照）" if ins["is_reference"] else ""
            html.append(f'<th>{ins["name"]}{tag}</th><th>符合率</th>')
        html.append("</tr></thead><tbody>")
        for row in data["matrix"]:
            html.append(f'<tr><td class="item">{row["item"]}</td>')
            for ins in data["instruments"]:
                c = row["insts"].get(ins["id"], {})
                if c.get("masked"):
                    html.append('<td class="mask">/</td><td class="mask">/</td>')
                    continue
                cell = c.get("results") or []
                samples = " ".join(cell) if isinstance(cell, list) and cell else "-"
                agr = c.get("agreement")
                agr_s = f"{agr}%" if agr is not None else "-"
                html.append(f"<td>{samples}</td><td>{agr_s}</td>")
            html.append("</tr>")
        html.append("</tbody></table>")
        _qual_vals = [i["agreement"] for row in data["matrix"] for i in row["insts"].values()
                      if not i.get("masked")]
        _qual_ok = _qual_vals and all(a is not None and a >= 80 for a in _qual_vals)
        html.append(f'<p>总结：使用5例样本进行室内比对，结果阴阳符合率见上表，结果一致性{"可接受" if _qual_ok else "待评估"}。</p>')
    else:
        # 比对方案
        ref = next((i for i in data["instruments"] if i["is_reference"]), None)
        compared_names = "、".join(i["name"] for i in data["instruments"] if not i["is_reference"])
        item_names = "、".join(it["item"] for it in data["matrix"][0]["rows"]) if data["matrix"] else ""
        n_inst = len(data["instruments"])
        n_item = len(data["matrix"][0]["rows"]) if data["matrix"] else 0
        html.append("<h2>比对方案</h2>")
        html.append(f"<p>1.样本：{group.sample_desc or '5个不同浓度水平的室间质评样本'}。</p>")
        html.append(f"<p>2.仪器：{ref['name'] if ref else ''}、{compared_names}。</p>")
        html.append(f"<p>3.试验内容：将{group.levels or 5}份样本分别在{n_inst}台仪器上测定共有项目。</p>")
        html.append(f"<p>4.项目：{item_names}，共{n_item}项。</p>")
        html.append(f"<p>5.评价标准：允许偏倚参照行标/国家临检中心EQA评价准则，本实验室以{ref['name'] if ref else ''}结果为参照，"
                    f"{'绝对' if any(it['mode']=='absolute' for it in data['matrix'][0]['rows']) else '相对'}偏倚绝对值应小于允许偏倚。是否可接受用Y/N表示。各项目成绩&gt;80%代表比对可接受。</p>")

        # 数据表（按水平）
        for blk in data["matrix"]:
            html.append(f"<h2>水平{blk['level']}</h2>")
            html.append('<table><thead><tr><th class="item">项目</th>'
                        f'<th>{ref["name"] if ref else "标准"}</th><th>允许TE%</th>')
            for ins in data["instruments"]:
                if ins["is_reference"]:
                    continue
                html.append(f'<th>{ins["name"]}</th><th>偏倚%</th><th>是否允许</th>')
            html.append("</tr></thead><tbody>")
            for r in blk["rows"]:
                html.append(f'<tr><td class="item">{r["item"]}</td><td>{r["ref"]}</td><td>{r["te"]}</td>')
                for ins in data["instruments"]:
                    if ins["is_reference"]:
                        continue
                    c = r["insts"].get(str(ins["id"]), {})
                    if c.get("masked"):
                        html.append('<td class="mask">/</td><td class="mask">/</td><td class="mask">/</td>')
                        continue
                    bias = c.get("bias")
                    acc = c.get("accepted")
                    bias_s = f"{bias}%" if bias is not None else "-"
                    acc_cls = "yes" if acc is True else ("no" if acc is False else "")
                    acc_s = {True: "Y", False: "N", None: "-"}[acc]
                    html.append(f'<td>{c.get("value","")}</td><td>{bias_s}</td><td class="{acc_cls}">{acc_s}</td>')
                html.append("</tr>")
            html.append("</tbody></table>")

        # 汇总
        html.append("<h2>汇总</h2>")
        html.append('<table><thead><tr><th class="item">项目</th>')
        for lv in range(1, (group.levels or 5) + 1):
            html.append(f"<th>水平{lv}</th>")
        html.append("</tr></thead><tbody>")
        for s in data["summary"]:
            html.append(f'<tr><td class="item">{s["item"]}</td>')
            for ok in s["levels"]:
                cls = "yes" if ok else "no"
                html.append(f'<td class="{cls}">{"Y" if ok else "N"}</td>')
            html.append("</tr>")
        html.append("</tbody></table>")

    html.append(f'<h2>结果分析</h2><p>{plan.summary or "各仪器上述所有项目均比对合格。"}</p>')
    html.append('<h2>处理方案（如不合格）</h2><p>{}</p>'.format(plan.handle_plan or "无"))
    html.append(f'<div class="foot">操作者：{plan.operator or "　　　　"}　　审核者：{plan.reviewer or "　　　　"}　　日期：{plan.compared_at or "　　　　"}</div>')
    html.append("</div>")
    return "".join(html)


# ---------------------------------------------------------------------------
# DOCX 生成
# ---------------------------------------------------------------------------
def _set_cell_font(cell, size=10.5, bold=False, align="center"):
    for p in cell.paragraphs:
        p.alignment = {"center": WD_ALIGN_PARAGRAPH.CENTER, "left": WD_ALIGN_PARAGRAPH.LEFT,
                       "right": WD_ALIGN_PARAGRAPH.RIGHT}.get(align, WD_ALIGN_PARAGRAPH.CENTER)
        for run in p.runs:
            run.font.size = Pt(size)
            run.font.bold = bold
            run.font.name = "SimSun"
            r = run._element
            r.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")


def _fill(cell, text, size=10.5, bold=False, align="center", color=None):
    cell.text = str(text)
    _set_cell_font(cell, size, bold, align)
    if color:
        for p in cell.paragraphs:
            for run in p.runs:
                run.font.color.rgb = color


def _heading(doc, text, size=13):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.name = "SimSun"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    return p


def build_docx(db, group: ComparisonGroup, plan: ComparisonPlan, data: dict, out_path: str):
    doc = Document()
    # 页边距
    for s in doc.sections:
        s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8)
        s.left_margin = Cm(1.8); s.right_margin = Cm(1.8)

    title = group.form_title or ("定性室内比对结果记录及分析报告表" if group.category == "定性" else "定量室内比对结果记录分析表")
    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run(title)
    r.font.size = Pt(16); r.font.bold = True; r.font.name = "SimSun"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = sub.add_run(f"表格编号 {group.form_code or ''}　　民航总医院检验科生化免疫组　　生效日期：{plan.year or ''}.01.01")
    rs.font.size = Pt(10.5); rs.font.name = "SimSun"
    rs._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    if data["category"] == "定性":
        _heading(doc, "比对结果")
        insts = data["instruments"]
        cols = 1 + len(insts) * 2
        t = doc.add_table(rows=1, cols=cols)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0].cells
        _fill(hdr[0], "检验项目", bold=True)
        for i, ins in enumerate(insts):
            _fill(hdr[1 + i * 2], f'{ins["name"]}（参照）' if ins["is_reference"] else ins["name"], bold=True)
            _fill(hdr[2 + i * 2], "符合率", bold=True)
        all_ok = True
        for row in data["matrix"]:
            cells = t.add_row().cells
            _fill(cells[0], row["item"], align="left")
            for i, ins in enumerate(insts):
                c = row["insts"].get(ins["id"], {})
                if c.get("masked"):
                    _fill(cells[1 + i * 2], "/"); _fill(cells[2 + i * 2], "/")
                    continue
                res = c.get("results") or []
                samples = " ".join(res) if isinstance(res, list) and res else "-"
                agr = c.get("agreement")
                agr_s = f"{agr}%" if agr is not None else "-"
                if agr is not None and agr < 80:
                    all_ok = False
                _fill(cells[1 + i * 2], samples)
                _fill(cells[2 + i * 2], agr_s)
        p = doc.add_paragraph()
        rp = p.add_run(f"总结：使用5例样本进行室内比对，结果阴阳符合率见上表，结果一致性{'可接受' if all_ok else '需关注'}。")
        rp.font.size = Pt(11); rp.font.name = "SimSun"
        rp._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    else:
        ref = next((i for i in data["instruments"] if i["is_reference"]), None)
        compared = [i for i in data["instruments"] if not i["is_reference"]]
        compared_names = "、".join(i["name"] for i in compared)
        n_inst = len(data["instruments"])
        item_names = "、".join(r["item"] for r in data["matrix"][0]["rows"]) if data["matrix"] else ""
        n_item = len(data["matrix"][0]["rows"]) if data["matrix"] else 0
        has_abs = any(r["mode"] == "absolute" for blk in data["matrix"] for r in blk["rows"])

        _heading(doc, "比对方案")
        for line in [
            f"1.样本：{group.sample_desc or '5个不同浓度水平的室间质评样本'}。",
            f"2.仪器：{ref['name'] if ref else ''}、{compared_names}。",
            f"3.试验内容：将{group.levels or 5}份样本分别在{n_inst}台仪器上测定共有项目。",
            f"4.项目：{item_names}，共{n_item}项。",
            f"5.评价标准：允许偏倚参照行标/国家临检中心EQA评价准则，本实验室以{ref['name'] if ref else ''}结果为参照，"
            f"{'绝对' if has_abs else '相对'}偏倚绝对值应小于允许偏倚。是否可接受用Y/N表示。各项目成绩>80%代表比对可接受。",
        ]:
            pp = doc.add_paragraph(); rr = pp.add_run(line)
            rr.font.size = Pt(11); rr.font.name = "SimSun"
            rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

        for blk in data["matrix"]:
            _heading(doc, f"水平{blk['level']}")
            ncol = 3 + len(compared) * 3
            t = doc.add_table(rows=1, cols=ncol)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = t.rows[0].cells
            _fill(hdr[0], "项目", bold=True)
            _fill(hdr[1], ref["name"] if ref else "标准", bold=True)
            _fill(hdr[2], "允许TE%", bold=True)
            ci = 3
            for ins in compared:
                _fill(hdr[ci], ins["name"], bold=True); _fill(hdr[ci + 1], "偏倚%", bold=True); _fill(hdr[ci + 2], "是否允许", bold=True)
                ci += 3
            for r in blk["rows"]:
                cells = t.add_row().cells
                _fill(cells[0], r["item"], align="left")
                _fill(cells[1], r["ref"])
                _fill(cells[2], r["te"])
                ci = 3
                for ins in compared:
                    c = r["insts"].get(str(ins["id"]), {})
                    if c.get("masked"):
                        _fill(cells[ci], "/"); _fill(cells[ci + 1], "/"); _fill(cells[ci + 2], "/")
                        ci += 3
                        continue
                    bias = c.get("bias"); acc = c.get("accepted")
                    bias_s = f"{bias}%" if bias is not None else "-"
                    acc_s = {True: "Y", False: "N", None: "-"}[acc]
                    _fill(cells[ci], c.get("value", ""))
                    _fill(cells[ci + 1], bias_s)
                    col = RGBColor(0x27, 0xae, 0x60) if acc is True else (RGBColor(0xc0, 0x39, 0x2b) if acc is False else None)
                    _fill(cells[ci + 2], acc_s, color=col, bold=True)
                    ci += 3

        _heading(doc, "汇总")
        ncol = 1 + (group.levels or 5)
        t = doc.add_table(rows=1, cols=ncol)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0].cells
        _fill(hdr[0], "项目", bold=True)
        for lv in range(1, (group.levels or 5) + 1):
            _fill(hdr[lv], f"水平{lv}", bold=True)
        for s in data["summary"]:
            cells = t.add_row().cells
            _fill(cells[0], s["item"], align="left")
            for j, ok in enumerate(s["levels"]):
                col = RGBColor(0x27, 0xae, 0x60) if ok else RGBColor(0xc0, 0x39, 0x2b)
                _fill(cells[1 + j], "Y" if ok else "N", color=col, bold=True)

    _heading(doc, "结果分析")
    p = doc.add_paragraph(); rr = p.add_run(plan.summary or "各仪器上述所有项目均比对合格。")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "处理方案（如不合格）")
    p = doc.add_paragraph(); rr = p.add_run(plan.handle_plan or "无")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    foot = doc.add_paragraph()
    rf = foot.add_run(f"操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}　　日期：{plan.compared_at or '　　　　'}")
    rf.font.size = Pt(11); rf.font.name = "SimSun"
    rf._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)


# ---------------------------------------------------------------------------
# 默认分组种子（参照 SOP 表单 BG-SM-CZ-021/024~027/071）
# ---------------------------------------------------------------------------
def _items_quant(pairs):
    return [{"name": n, "te": str(te), "mode": m} for n, te, m in pairs]


BIOTH_ITEM = _items_quant([
    ("ALB", 2, "relative"), ("ALP", 10, "relative"), ("ALT", 5, "relative"), ("AMY", 7.5, "relative"),
    ("APA", 10, "relative"), ("APB", 10, "relative"), ("ASO", 10, "relative"), ("AST", 5, "relative"),
    ("BUN", 3, "relative"), ("C3", 8, "relative"), ("C4", 10, "relative"), ("CA", 2, "relative"),
    ("CHE", 8, "relative"), ("CHOL", 4, "relative"), ("CK", 5.5, "relative"), ("CL", 1.5, "relative"),
    ("CO2", 3, "relative"), ("CRE", 5.5, "relative"), ("CRP", 10, "relative"), ("CYSC", 8, "relative"),
    ("DBIL", 6.7, "relative"), ("FE", 4.5, "relative"), ("GA", 10, "relative"), ("GGT", 5.5, "relative"),
    ("GLU", 2, "relative"), ("HCY", 10, "relative"), ("HDL", 8, "relative"), ("Hp", 12, "relative"),
    ("Ig-A", 10, "relative"), ("Ig-G", 8, "relative"), ("Ig-M", 8, "relative"), ("K", 2, "relative"),
    ("LAC", 12, "relative"), ("LDH", 4, "relative"), ("LDL", 8, "relative"), ("LPa", 10, "relative"),
    ("LPS", 10, "relative"), ("Mg", 5.5, "relative"), ("NA", 1.5, "relative"), ("P", 3, "relative"),
    ("PA", 10, "relative"), ("RF", 10, "relative"), ("SAA", 15, "relative"), ("sd-LDL", 10, "relative"),
    ("TBA", 12, "relative"), ("TBIL", 5, "relative"), ("TG", 5, "relative"), ("TP", 2, "relative"),
    ("UA", 4.5, "relative"), ("UIBC", 10, "relative"), ("Zn", 10, "relative"), ("β2mg", 10, "relative"),
    ("β-HBDH", 15, "relative"),
])

DXI_ITEM = _items_quant([
    ("FERR", 0.1, "relative"), ("叶酸", 0.1, "relative"), ("B12", 0.1, "relative"), ("sTfR", 0.1, "relative"),
    ("IFA", 0.1, "relative"), ("PCT", 0.1, "relative"), ("IL-6", 0.1, "relative"), ("cTnI", 0.1, "relative"),
    ("MYO", 0.1, "relative"), ("CK-MB", 0.1, "relative"), ("BNP", 0.1, "relative"),
])

COAG_ITEM = _items_quant([
    ("D-D", 25, "relative"), ("APTT", 8, "relative"), ("AT-III", 8, "relative"),
    ("TT", 10, "relative"), ("PT", 8, "relative"), ("FDP", 7, "relative"), ("FIB", 10, "relative"),
])

PREG_ITEM = _items_quant([("HCG", 25, "relative"), ("孕酮", 25, "relative"), ("雌二醇", 25, "relative")])

BLOODGAS_ITEM = [
    {"name": "PH", "te": "0.02", "mode": "absolute"},
    {"name": "PCO2", "te": "5", "mode": "absolute"},
    {"name": "pO2", "te": "0.05", "mode": "relative"},
    {"name": "Na+", "te": "0.04", "mode": "relative"},
    {"name": "K+", "te": "0.06", "mode": "relative"},
    {"name": "Ca2+", "te": "0.05", "mode": "relative"},
    {"name": "Cl-", "te": "0.04", "mode": "relative"},
]

QUAL_ITEM = [
    {"name": "乙肝表面抗原", "te": "0", "mode": "relative"},
    {"name": "乙肝表面抗体", "te": "0", "mode": "relative"},
    {"name": "乙肝e抗原", "te": "0", "mode": "relative"},
    {"name": "乙肝e抗体", "te": "0", "mode": "relative"},
    {"name": "乙肝核心抗体", "te": "0", "mode": "relative"},
    {"name": "丙肝抗体", "te": "0", "mode": "relative"},
    {"name": "梅毒抗体", "te": "0", "mode": "relative"},
    {"name": "HIV抗体", "te": "0", "mode": "relative"},
]


# ---------------------------------------------------------------------------
# 从仪器档案解析共有项目（项目↔仪器关联）+ 每项适用仪器（用于遮蔽）
# ---------------------------------------------------------------------------
def _build_te_lookup():
    """合并各专业种子的允许TE，按项目代码(大写)索引，供自动填充默认TE。"""
    lut = {}
    for tbl in (BIOTH_ITEM, DXI_ITEM, COAG_ITEM, PREG_ITEM, BLOODGAS_ITEM):
        for it in tbl:
            lut[it["name"].upper()] = (it["te"], it["mode"])
    return lut


TE_LOOKUP = _build_te_lookup()


def _split_tokens(s: str):
    """把 instrument_group 文本拆成子型号 token，如 'AU58-1 / AU58-2/AU5800'。"""
    if not s:
        return []
    out = []
    for part in str(s).replace("／", "/").split("/"):
        t = part.strip()
        if t:
            out.append(t)
    return out


def resolve_common_items(db, instrument_ids, category="定量", min_count=2):
    """依据仪器档案里"项目↔仪器"关联，计算给定仪器组的共有项目。

    关联链：
    - test_items.instrument_group 里的子型号 token（如 AU58-1/AU5800）→ 小型号
      instrument_families(name) → members → 具体仪器 id；据此得到"每个项目实际装机的仪器"。
    - 若 instrument_group 为空，则回退用 test_items.instrument（总型号）→ family → members。

    返回：{items:[{name(代码), label(中文), te, mode, instrument_ids:[适用且在本组内]}],
           instruments:[{id,name,model}]}，仅保留在本组内适用仪器数 ≥ min_count 的项目。
    """
    from ..models.test_item import TestItem
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember

    cand = [int(i) for i in (instrument_ids or [])]
    cand_set = set(cand)
    if not cand_set:
        return {"items": [], "instruments": []}

    # family.name -> set(instrument_id)
    fam_name_to_ids = {}
    fam_id_to_name = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    for m in db.query(InstrumentFamilyMember).all():
        nm = fam_id_to_name.get(m.family_id, "")
        if nm:
            fam_name_to_ids.setdefault(nm, set()).add(m.instrument_id)

    def match_token_ids(token):
        """token 精确匹配小型号 family 名，返回其成员 id 集合。"""
        token = token.strip()
        if token in fam_name_to_ids:
            return set(fam_name_to_ids[token])
        # 宽松：忽略大小写/空格
        tl = token.lower().replace(" ", "")
        for nm, ids in fam_name_to_ids.items():
            if nm.lower().replace(" ", "") == tl:
                return set(ids)
        return set()

    items_out = []
    seen_names = set()
    for ti in db.query(TestItem).all():
        # 该项目装机仪器 id 集合
        run_ids = set()
        for tok in _split_tokens(ti.instrument_group):
            run_ids |= match_token_ids(tok)
        if not run_ids:
            # 回退：总型号 family
            run_ids |= fam_name_to_ids.get((ti.instrument or "").strip(), set())
        app = sorted(run_ids & cand_set)
        if len(app) < min_count:
            continue
        code = (ti.code or "").strip() or (ti.name or "").strip()
        label = (ti.name or "").strip() or code
        key = code.upper()
        if key in seen_names:
            continue
        seen_names.add(key)
        te, mode = TE_LOOKUP.get(key, ("", "relative"))
        items_out.append({
            "name": code, "label": label, "te": str(te), "mode": mode,
            "instrument_ids": app,
        })

    insts = []
    for iid in cand:
        inst = db.get(Instrument, iid)
        if inst:
            insts.append({"id": inst.id, "name": disp_name(inst), "model": inst.model or ""})
    return {"items": items_out, "instruments": insts}


def _find_instrument(db, *keywords, used=None):
    used = used or set()
    for inst in db.query(Instrument).all():
        nm = f"{inst.name or ''} {inst.model or ''}"
        for kw in keywords:
            if kw and kw.lower() in nm.lower() and inst.id not in used:
                return inst.id
    return 0


def ensure_comparison_defaults(db):
    """种子比对分组模板（幂等）。仪器按型号匹配在用机器且互不重复；
    定量组的项目清单与"每项适用仪器"由仪器档案自动解析（含遮蔽），解析不到时回退固定清单。"""
    seeds = [
        ("生化分析仪", "定量", "BG-SM-CZ-025", "定量室内比对结果记录分析表（生化分析仪）",
         ("AU5821 A", "AU5821 B", "AU5800急诊"), "AU5821 A", 5, BIOTH_ITEM,
         "5个不同浓度水平的室间质评样本"),
        ("DXI800分析仪", "定量", "BG-SM-CZ-024", "定量室内比对结果记录分析表（DXI800分析仪）",
         ("DXI800 1", "DXI800 2", "DXI800 3", "DXI800 4"), "DXI800 1", 5, DXI_ITEM,
         "5个不同浓度水平的新鲜血清样本"),
        ("凝血分析仪", "定量", "BG-SM-CZ-026", "定量室内比对结果记录分析表（凝血分析仪）",
         ("TOP700A", "TOP700B", "TOP700C"), "TOP700A", 5, COAG_ITEM,
         "5个不同浓度水平的新鲜血浆样本（至少包含2个凝血结果异常的样本）"),
        ("早孕系列", "定量", "BG-SM-CZ-027", "定量室内比对结果记录分析表（早孕系列）",
         ("DXI800 唐", "DXI800 急"), "DXI800 唐", 5, PREG_ITEM,
         "5个不同浓度水平的新鲜血清样本"),
        ("血气分析仪", "定量", "BG-SM-CZ-071", "定量室内比对结果记录分析表（血气分析仪）",
         ("RapidPoint1", "RapidPoint2"), "RapidPoint1", 2, BLOODGAS_ITEM,
         "2个浓度水平的血气专用质控物"),
        ("定性比对", "定性", "BG-SM-CZ-021", "定性室内比对结果记录及分析报告表",
         ("e601", "e602", "e411"), "e601", 0, QUAL_ITEM, "5例临床样本"),
    ]
    # 在用仪器 id 集合（用于判断旧种子是否失效）
    inuse = {i.id for i in db.query(Instrument).all()
             if (getattr(i, "status", "") or "") == "在用"}

    def _stale(ids_list):
        """旧的问题种子特征：有重复 id、为空、或含非在用仪器。"""
        if not ids_list:
            return True
        if len(ids_list) != len(set(ids_list)):
            return True
        if any(i not in inuse for i in ids_list):
            return True
        return False

    for name, cat, code, ftitle, inst_kw, ref_kw, levels, fallback_items, sample in seeds:
        existing = db.query(ComparisonGroup).filter_by(name=name).first()
        # 已存在且数据正常（非旧问题种子）→ 保留用户数据，不覆盖
        if existing and not _stale(_load_json(existing.instrument_ids, [])):
            continue

        # 计算正确的仪器组（按型号匹配在用机器且互不重复）
        used = set()
        ids = []
        for kw in inst_kw:
            iid = _find_instrument(db, kw, used=used)
            if iid:
                ids.append(iid)
                used.add(iid)
        ref_id = 0
        if ref_kw:
            ref_id = _find_instrument(db, ref_kw, used=used) or (ids[0] if ids else 0)
            if ref_id and ref_id not in ids:
                ids.insert(0, ref_id)
        # 定量组：优先用档案解析项目（带每项适用仪器/遮蔽）
        items = fallback_items
        if cat == "定量" and ids:
            resolved = resolve_common_items(db, ids, category=cat, min_count=2).get("items", [])
            if resolved:
                items = resolved

        if existing:
            # 修复旧问题种子（重复/失效 id）——仅刷新模板字段，保留 id 与关联计划
            existing.instrument_ids = json.dumps(ids)
            existing.reference_instrument_id = ref_id
            existing.items = json.dumps(items)
            existing.form_code = code
            existing.form_title = ftitle
            existing.sample_desc = sample
            existing.levels = levels
        else:
            db.add(ComparisonGroup(
                name=name, category=cat, form_code=code, form_title=ftitle,
                instrument_ids=json.dumps(ids), reference_instrument_id=ref_id,
                levels=levels, items=json.dumps(items), sample_desc=sample,
                created_by="system",
            ))
    db.commit()
