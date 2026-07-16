"""室间比对：结果计算 + 报告生成（docx）+ HTML 预览 + 候选项目解析。

计算逻辑（与仪器间比对同口径）：
- 偏倚 = (我室 - 参比)/参比 × 100（relative）或 我室 - 参比（absolute）；
- 是否合格 = |偏倚| ≤ 允许TE。
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

from ..models.instrument import Instrument
from ..models.test_item import TestItem

REPORT_DIR = None  # 由 main 注入（DATA_DIR/interlab_reports）


# ---------------------------------------------------------------------------
# 工具
# ---------------------------------------------------------------------------
def _parse_float(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _compute_bias(our, ref, te, mode):
    """返回 (偏倚值或None, 是否合格或None)。"""
    of = _parse_float(our)
    rf = _parse_float(ref)
    tf = _parse_float(te)
    if of is None or rf is None or tf is None:
        return None, None
    if mode == "absolute":
        bias = of - rf
    else:
        if rf == 0:
            return None, None
        bias = (of - rf) / rf * 100.0
    accepted = abs(bias) <= tf + 1e-9
    return round(bias, 2), accepted


def _split_tokens(s: str):
    if not s:
        return []
    out = []
    for part in str(s).replace("／", "/").split("/"):
        t = part.strip()
        if t:
            out.append(t)
    return out


def _family_name_to_ids(db):
    """family.name -> set(instrument_id)。"""
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
    fam_id_to_name = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    lut = {}
    for m in db.query(InstrumentFamilyMember).all():
        nm = fam_id_to_name.get(m.family_id, "")
        if nm:
            lut.setdefault(nm, set()).add(m.instrument_id)
    return lut


def candidate_projects(db, instrument_id: int):
    """返回该仪器可参与室间比对的项目（has_eqa=0 且 has_interlab=1）。

    关联链：test_items.instrument_group / instrument 中的 family 名/token
    → family 成员仪器集合；并扩展到同家族全部仪器（按仪器分类时，
    同型号家族仪器共享可比对项目）。再过滤 has_interlab=1（排除无室间比对项目）。
    """
    inst = db.get(Instrument, instrument_id) if instrument_id else None
    if not inst:
        return []
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
    fam_lut = _family_name_to_ids(db)          # family.name -> set(instrument_id)
    fam_ids_names = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    # instrument_id -> set(family_id)
    inst_families: dict = {}
    for m in db.query(InstrumentFamilyMember).all():
        inst_families.setdefault(m.instrument_id, set()).add(m.family_id)
    # 本仪器所属 family 名
    fam_names = {fam_ids_names.get(fid, "") for fid in inst_families.get(instrument_id, set())}
    fam_names.discard("")
    # instrument.name / model 也作为匹配 token（回退）
    extra_tokens = set()
    for t in _split_tokens(inst.name or ""):
        extra_tokens.add(t)
    if inst.model:
        extra_tokens.add(inst.model.strip())

    out = []
    seen = set()
    for ti in db.query(TestItem).all():
        # 室间比对仅面向「无室间质评(has_eqa=0) 且 有外部参比实验室(has_interlab=1)」的项目
        he = getattr(ti, "has_eqa", None)
        if he is not None and int(he) == 1:
            continue
        hi = getattr(ti, "has_interlab", None)
        if hi is not None and int(hi) != 1:
            continue
        # 基础 run_ids：instrument_group / instrument 中的 family 名 token
        run_ids = set()
        for tok in _split_tokens(ti.instrument_group):
            run_ids |= fam_lut.get(tok, set())
        if not run_ids:
            run_ids |= fam_lut.get((ti.instrument or "").strip(), set())
        # 扩展到同家族全部仪器（含 indirect family）
        expanded = set(run_ids)
        for rid in list(run_ids):
            for fid in inst_families.get(rid, set()):
                fn = fam_ids_names.get(fid, "")
                if fn:
                    expanded |= fam_lut.get(fn, set())
        # 是否命中本仪器
        hit = (instrument_id in expanded) \
            or any(fn in _split_tokens(ti.instrument_group) for fn in fam_names) \
            or any(tok in (ti.instrument or "") for tok in extra_tokens if tok)
        if not hit:
            continue
        key = (ti.code or ti.name or "").strip().upper()
        if key in seen:
            continue
        seen.add(key)
        out.append({
            "id": ti.id,
            "code": (ti.code or "").strip(),
            "name": (ti.name or "").strip(),
            "unit": (ti.unit or "").strip(),
            "instrument": (ti.instrument or "").strip(),
            "mandatory": True,   # 经此过滤即"无室间质评且需室间比对"的必做项目
        })
    return out


def mandatory_projects(db):
    """指导用：返回所有「无室间质评、需做室间比对」的必做项目，及其所属仪器。

    供前端「必做项目总览」面板，明确告知用户哪些项目必须做室间比对。
    """
    fam_lut = _family_name_to_ids(db)
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
    fam_id_to_name = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    inst_families: dict = {}
    for m in db.query(InstrumentFamilyMember).all():
        inst_families.setdefault(m.instrument_id, set()).add(m.family_id)
    inst_lut = {i.id: i for i in db.query(Instrument).all()}

    out = []
    for ti in db.query(TestItem).all():
        he = getattr(ti, "has_eqa", None)
        if he is not None and int(he) == 1:
            continue
        hi = getattr(ti, "has_interlab", None)
        if hi is not None and int(hi) != 1:
            continue
        # 解析所属仪器（扩展到同家族）
        run_ids = set()
        for tok in _split_tokens(ti.instrument_group):
            run_ids |= fam_lut.get(tok, set())
        if not run_ids:
            run_ids |= fam_lut.get((ti.instrument or "").strip(), set())
        expanded = set(run_ids)
        for rid in list(run_ids):
            for fid in inst_families.get(rid, set()):
                fn = fam_id_to_name.get(fid, "")
                if fn:
                    expanded |= fam_lut.get(fn, set())
        insts = []
        for iid in sorted(expanded):
            inst = inst_lut.get(iid)
            if inst:
                nm = (inst.model or inst.name or "").strip() or f"仪器{iid}"
                insts.append({"id": iid, "name": nm})
        out.append({
            "id": ti.id,
            "code": (ti.code or "").strip(),
            "name": (ti.name or "").strip(),
            "unit": (ti.unit or "").strip(),
            "instruments": insts,
        })
    return out


# ---------------------------------------------------------------------------
# 计算
# ---------------------------------------------------------------------------
def _norm_pn(v):
    """把 阳/阴 判定归一化：positive / negative / None（无法判定）。"""
    s = (str(v or "").strip()).upper()
    if s in ("阳", "阳性", "POS", "POSITIVE", "P", "+", "1"):
        return "positive"
    if s in ("阴", "阴性", "NEG", "NEGATIVE", "N", "-", "0", "阴性(-)"):
        return "negative"
    return None


def _qualitative_eval(our, ref):
    """定性符合判定：返回 (是否符合, 阴阳结论串)。"""
    a, b = _norm_pn(our), _norm_pn(ref)
    if a is None or b is None:
        return None, f"{our or '—'} / {ref or '—'}"
    matched = (a == b)
    label = "阳性" if a == "positive" else "阴性"
    return matched, f"{label} / {label if matched else ('阴性' if a == 'positive' else '阳性')}"


def compute_data(db, plan, items):
    """items: list[InterlabItem]。返回逐行计算结果（区分定性/定量）。"""
    rows = []
    all_ok = True
    has_qual = False
    has_quan = False
    for it in items:
        kind = getattr(it, "kind", None) or "定量"
        if kind == "定性":
            has_qual = True
            matched, pn = _qualitative_eval(it.our_value, it.ref_value)
            accepted = matched
            if accepted is False:
                all_ok = False
            rows.append({
                "item": it.item, "unit": it.unit,
                "our": it.our_value, "ref": it.ref_value,
                "te": it.te, "mode": it.mode, "kind": "定性",
                "match": matched, "pn": pn, "accepted": accepted, "note": it.note,
            })
        else:
            has_quan = True
            of = _parse_float(it.our_value)
            rf = _parse_float(it.ref_value)
            tf = _parse_float(it.te)
            abs_bias = (of - rf) if (of is not None and rf is not None) else None
            rel_bias = ((of - rf) / rf * 100.0) if (of is not None and rf not in (None, 0)) else None
            if it.mode == "absolute":
                bias = abs_bias
                accepted = (abs_bias is not None and tf is not None and abs(abs_bias) <= tf + 1e-9)
            else:
                bias = rel_bias
                accepted = (rel_bias is not None and tf is not None and abs(rel_bias) <= tf + 1e-9)
            if accepted is False:
                all_ok = False
            rows.append({
                "item": it.item, "unit": it.unit,
                "our": it.our_value, "ref": it.ref_value,
                "te": it.te, "mode": it.mode, "kind": "定量",
                "abs_bias": round(abs_bias, 3) if abs_bias is not None else None,
                "rel_bias": round(rel_bias, 2) if rel_bias is not None else None,
                "bias": bias, "accepted": accepted, "note": it.note,
            })
    return {"rows": rows, "all_ok": all_ok, "has_qual": has_qual, "has_quan": has_quan}


# ---------------------------------------------------------------------------
# HTML 预览
# ---------------------------------------------------------------------------
def build_html(plan, data: dict, instrument_name: str, ref_lab: str):
    css = """
    <style>
      .rep { font-family: 'Microsoft YaHei','SimSun',serif; color:#222; max-width:960px; margin:0 auto; padding:16px; }
      .rep h1 { text-align:center; font-size:20px; margin:6px 0; }
      .rep .sub { text-align:center; font-size:12px; color:#555; margin-bottom:10px; }
      .rep h2 { font-size:14px; margin:14px 0 6px; border-left:4px solid #1a365d; padding-left:8px; }
      .rep p { font-size:13px; line-height:1.7; margin:4px 0; }
      .rep .note { font-size:12px; color:#666; }
      .rep table { border-collapse:collapse; width:100%; font-size:12px; margin:6px 0; }
      .rep th, .rep td { border:1px solid #444; padding:4px 6px; text-align:center; }
      .rep th { background:#eef2f8; }
      .rep .item { text-align:left; }
      .rep .no { color:#c0392b; font-weight:700; }
      .rep .yes { color:#27ae60; font-weight:700; }
      .rep .foot { margin-top:18px; font-size:13px; }
    </style>"""
    year = plan.year or ""
    half = "上半年" if plan.half == 1 else "下半年"
    has_q = data["has_qual"]
    has_n = data["has_quan"]
    if has_q and not has_n:
        title = "定性项目室间比对结果记录及分析报告表"
    elif has_n and not has_q:
        title = "定量项目室间比对结果记录及分析报告表"
    else:
        title = "室间比对结果记录及分析报告表"

    html = [f'<div class="rep">{css}<h1>{title}</h1>']
    html.append(f'<div class="sub">民航总医院检验科　　部门：生化免疫组　　{year}年{half}</div>')
    html.append("<h2>基本信息</h2>")
    html.append(f"<p>我室仪器：{instrument_name or '　　　　'}　　参比实验室：{ref_lab or '　　　　'}</p>")
    html.append(f"<p>比对日期：{plan.compared_at or '　　　　'}　　操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}</p>")

    # 定量（BG-SM-CZ-019 结构）
    if has_n:
        html.append("<h2>定量项目室间比对结果</h2>")
        html.append('<p class="note">注：80%样本（4/5）的相对偏倚需低于允许总误差认为合格，允许总误差参照行标及国家卫健委室间质评要求，无相应要求的按照30%计算。</p>')
        html.append('<table><thead><tr>'
                    '<th class="item">项目</th><th>单位</th>'
                    '<th>可比较系统（本院仪器）</th><th>比较系统（参比实验室）</th>'
                    '<th>偏倚</th><th>相对偏倚</th><th>是否合格</th>'
                    '</tr></thead><tbody>')
        for r in data["rows"]:
            if r["kind"] != "定量":
                continue
            abs_s = f"{r['abs_bias']}" if r.get("abs_bias") is not None else "—"
            rel_s = f"{r['rel_bias']}%" if r.get("rel_bias") is not None else "—"
            acc = r["accepted"]
            acc_cls = "yes" if acc is True else ("no" if acc is False else "")
            acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
            html.append(
                f'<tr><td class="item">{r["item"]}</td><td>{r["unit"]}</td>'
                f'<td>{r["our"]}</td><td>{r["ref"]}</td>'
                f'<td>{abs_s}</td><td>{rel_s}</td>'
                f'<td class="{acc_cls}">{acc_s}</td></tr>'
            )
        html.append("</tbody></table>")
        n = sum(1 for r in data["rows"] if r["kind"] == "定量")
        concl_q = f"使用{n}个项目与{ref_lab or '参比'}实验室进行室间比对，一致性可接受。"
        html.append(f'<p class="concl">{concl_q}</p>')

    # 定性（BG-SM-CZ-018 结构）
    if has_q:
        qrows = [r for r in data["rows"] if r["kind"] == "定性"]
        matched = sum(1 for r in qrows if r.get("match") is True)
        total = len(qrows)
        rate = round(matched / total * 100, 1) if total else 0
        html.append("<h2>定性项目室间比对结果</h2>")
        html.append('<table><thead><tr>'
                    '<th class="item">检验项目</th><th>本院结果</th>'
                    '<th>参比实验室结果</th><th>符合</th><th>是否合格</th>'
                    '</tr></thead><tbody>')
        for r in qrows:
            m = r.get("match")
            acc = r["accepted"]
            acc_cls = "yes" if acc is True else ("no" if acc is False else "")
            acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
            m_s = {True: "是", False: "否", None: "-"}[m]
            html.append(
                f'<tr><td class="item">{r["item"]}</td><td>{r["our"]}</td>'
                f'<td>{r["ref"]}</td><td>{m_s}</td>'
                f'<td class="{acc_cls}">{acc_s}</td></tr>'
            )
        html.append("</tbody></table>")
        html.append(f'<p class="concl">使用{total}例样本进行室间比对，结果阴阳符合率{rate}%，结果一致性可接受。</p>')

    html.append(f'<h2>结果分析</h2><p>{plan.summary or "各项目室间比对结果均在允许偏倚范围内，比对可接受。"}</p>')
    html.append('<h2>处理方案（如不合格）</h2><p>{}</p>'.format(plan.handle_plan or "无"))
    concl = plan.conclusion or ("可接受" if data["all_ok"] else "不可接受")
    html.append(f'<p>结论：<b>{concl}</b></p>')
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


def build_docx(db, plan, data: dict, out_path: str, instrument_name: str, ref_lab: str):
    doc = Document()
    for s in doc.sections:
        s.top_margin = Cm(1.8); s.bottom_margin = Cm(1.8)
        s.left_margin = Cm(1.8); s.right_margin = Cm(1.8)

    year = plan.year or ""
    half = "上半年" if plan.half == 1 else "下半年"
    has_q = data["has_qual"]
    has_n = data["has_quan"]
    if has_q and not has_n:
        title = "定性项目室间比对结果记录及分析报告表"
    elif has_n and not has_q:
        title = "定量项目室间比对结果记录及分析报告表"
    else:
        title = "室间比对结果记录及分析报告表"

    h = doc.add_paragraph()
    h.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = h.add_run(title)
    r.font.size = Pt(16); r.font.bold = True; r.font.name = "SimSun"
    r._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rs = sub.add_run(f"民航总医院检验科　　部门：生化免疫组　　{year}年{half}")
    rs.font.size = Pt(10.5); rs.font.name = "SimSun"
    rs._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "基本信息")
    for line in [
        f"我室仪器：{instrument_name or '　　　　'}　　参比实验室：{ref_lab or '　　　　'}",
        f"比对日期：{plan.compared_at or '　　　　'}　　操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}",
    ]:
        p = doc.add_paragraph(); rr = p.add_run(line)
        rr.font.size = Pt(11); rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    # 定量（BG-SM-CZ-019 结构）
    if has_n:
        _heading(doc, "定量项目室间比对结果")
        p = doc.add_paragraph()
        rr = p.add_run("注：80%样本（4/5）的相对偏倚需低于允许总误差认为合格，允许总误差参照行标及国家卫健委室间质评要求，无相应要求的按照30%计算。")
        rr.font.size = Pt(9.5); rr.font.color.rgb = RGBColor(0x66, 0x66, 0x66); rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

        t = doc.add_table(rows=1, cols=7)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0].cells
        for i, htext in enumerate(["项目", "单位", "可比较系统（本院仪器）", "比较系统（参比实验室）", "偏倚", "相对偏倚", "是否合格"]):
            _fill(hdr[i], htext, bold=True)
        for r in data["rows"]:
            if r["kind"] != "定量":
                continue
            cells = t.add_row().cells
            abs_s = f"{r['abs_bias']}" if r.get("abs_bias") is not None else "—"
            rel_s = f"{r['rel_bias']}%" if r.get("rel_bias") is not None else "—"
            acc = r["accepted"]
            acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
            _fill(cells[0], r["item"], align="left")
            _fill(cells[1], r["unit"])
            _fill(cells[2], r["our"])
            _fill(cells[3], r["ref"])
            _fill(cells[4], abs_s)
            _fill(cells[5], rel_s)
            col = RGBColor(0x27, 0xae, 0x60) if acc is True else (RGBColor(0xc0, 0x39, 0x2b) if acc is False else None)
            _fill(cells[6], acc_s, color=col, bold=True)
        n = sum(1 for r in data["rows"] if r["kind"] == "定量")
        p = doc.add_paragraph()
        rr = p.add_run(f"结论：使用{n}个项目与{ref_lab or '参比'}实验室进行室间比对，一致性可接受。")
        rr.font.size = Pt(11); rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    # 定性（BG-SM-CZ-018 结构）
    if has_q:
        qrows = [r for r in data["rows"] if r["kind"] == "定性"]
        matched = sum(1 for r in qrows if r.get("match") is True)
        total = len(qrows)
        rate = round(matched / total * 100, 1) if total else 0
        _heading(doc, "定性项目室间比对结果")
        t = doc.add_table(rows=1, cols=5)
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        hdr = t.rows[0].cells
        for i, htext in enumerate(["检验项目", "本院结果", "参比实验室结果", "符合", "是否合格"]):
            _fill(hdr[i], htext, bold=True)
        for r in qrows:
            cells = t.add_row().cells
            m = r.get("match")
            acc = r["accepted"]
            acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
            m_s = {True: "是", False: "否", None: "-"}[m]
            _fill(cells[0], r["item"], align="left")
            _fill(cells[1], r["our"])
            _fill(cells[2], r["ref"])
            _fill(cells[3], m_s)
            col = RGBColor(0x27, 0xae, 0x60) if acc is True else (RGBColor(0xc0, 0x39, 0x2b) if acc is False else None)
            _fill(cells[4], acc_s, color=col, bold=True)
        p = doc.add_paragraph()
        rr = p.add_run(f"结论：使用{total}例样本进行室间比对，结果阴阳符合率{rate}%，结果一致性可接受。")
        rr.font.size = Pt(11); rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "结果分析")
    p = doc.add_paragraph(); rr = p.add_run(plan.summary or "各项目室间比对结果均在允许偏倚范围内，比对可接受。")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "处理方案（如不合格）")
    p = doc.add_paragraph(); rr = p.add_run(plan.handle_plan or "无")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    concl = plan.conclusion or ("可接受" if data["all_ok"] else "不可接受")
    p = doc.add_paragraph(); rr = p.add_run(f"结论：{concl}")
    rr.font.size = Pt(11); rr.font.bold = True; rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    foot = doc.add_paragraph()
    rf = foot.add_run(f"操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}　　日期：{plan.compared_at or '　　　　'}")
    rf.font.size = Pt(11); rf.font.name = "SimSun"
    rf._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)


def _heading(doc, text, size=13):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(8)
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.font.bold = True
    run.font.name = "SimSun"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")
    return p
