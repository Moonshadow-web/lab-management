"""室间比对：结果计算 + 报告生成（docx）+ HTML 预览 + 候选项目解析。

模板参照 BG-SM-CZ-019（定量）/ BG-SM-CZ-018（定性）。
每个项目测 5 个水平的样本，每个水平录我室值 X + 比较系统1/2 的 Y1/Y2/均值Y。
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
# 工具函数
# ---------------------------------------------------------------------------
def _parse_float(x):
    try:
        return float(str(x).strip())
    except Exception:
        return None


def _compute_bias(our, ref, te, mode):
    """返回 (偏倚值或None, 是否合格或None)。mode: relative(相对%) / absolute(绝对)"""
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


def _norm_pn(v):
    """阴阳判定归一化。"""
    s = (str(v or "").strip()).upper()
    if s in ("阳", "阳性", "POS", "POSITIVE", "P", "+", "1"):
        return "positive"
    if s in ("阴", "阴性", "NEG", "NEGATIVE", "N", "-", "0", "阴性(-)"):
        return "negative"
    return None


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
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
    fam_id_to_name = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    lut = {}
    for m in db.query(InstrumentFamilyMember).all():
        nm = fam_id_to_name.get(m.family_id, "")
        if nm:
            lut.setdefault(nm, set()).add(m.instrument_id)
    return lut


# ---------------------------------------------------------------------------
# 候选 / 必做项目
# ---------------------------------------------------------------------------
def candidate_projects(db, instrument_id: int):
    """返回该仪器可参与室间比对的项目（has_eqa=0 且 has_interlab=1）。"""
    inst = db.get(Instrument, instrument_id) if instrument_id else None
    if not inst:
        return []
    from ..models.instrument_family import InstrumentFamily, InstrumentFamilyMember
    fam_lut = _family_name_to_ids(db)
    fam_ids_names = {f.id: (f.name or "").strip() for f in db.query(InstrumentFamily).all()}
    inst_families: dict = {}
    for m in db.query(InstrumentFamilyMember).all():
        inst_families.setdefault(m.instrument_id, set()).add(m.family_id)
    fam_names = {fam_ids_names.get(fid, "") for fid in inst_families.get(instrument_id, set())}
    fam_names.discard("")
    extra_tokens = set()
    for t in _split_tokens(inst.name or ""):
        extra_tokens.add(t)
    if inst.model:
        extra_tokens.add(inst.model.strip())

    out = []
    seen = set()
    for ti in db.query(TestItem).all():
        he = getattr(ti, "has_eqa", None)
        if he is not None and int(he) == 1:
            continue
        hi = getattr(ti, "has_interlab", None)
        if hi is not None and int(hi) != 1:
            continue
        run_ids = set()
        for tok in _split_tokens(ti.instrument_group):
            run_ids |= fam_lut.get(tok, set())
        if not run_ids:
            run_ids |= fam_lut.get((ti.instrument or "").strip(), set())
        expanded = run_ids
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
            "mandatory": True,
        })
    return out


def mandatory_projects(db):
    """指导用：返回所有「无室间质评、需做室间比对」的必做项目及所属仪器。"""
    fam_lut = _family_name_to_ids(db)
    inst_lut = {i.id: i for i in db.query(Instrument).all()}
    out = []
    for ti in db.query(TestItem).all():
        he = getattr(ti, "has_eqa", None)
        if he is not None and int(he) == 1:
            continue
        hi = getattr(ti, "has_interlab", None)
        if hi is not None and int(hi) != 1:
            continue
        run_ids = set()
        for tok in _split_tokens(ti.instrument_group):
            run_ids |= fam_lut.get(tok, set())
        if not run_ids:
            run_ids |= fam_lut.get((ti.instrument or "").strip(), set())
        insts = []
        for iid in sorted(run_ids):
            inst = inst_lut.get(iid)
            if not inst:
                continue
            if inst.status and "停用" in (inst.status or ""):
                continue
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
# 计算结果（5 水平）
# ---------------------------------------------------------------------------
def compute_data(db, plan, items, levels_map: dict):
    """items: list[InterlabItem]; levels_map: {item_id -> list[InterlabLevel]}。
    返回每个项目的 5 水平计算结果。"""
    project_rows = []
    all_ok = True
    has_qual = False
    has_quan = False

    for it in items:
        kind = getattr(it, "kind", None) or "定量"
        levels = sorted(levels_map.get(it.id, []), key=lambda x: x.level_num)

        level_results = []
        if kind == "定性":
            has_qual = True
            for lv in levels:
                matched, pn = _qualitative_eval(lv.our_value, lv.ref1_y1)
                acc = matched
                if acc is False:
                    all_ok = False
                level_results.append({
                    "level": lv.level_num,
                    "our": lv.our_value, "ref": lv.ref1_y1,
                    "match": matched, "pn": pn, "accepted": acc,
                })
        else:
            has_quan = True
            for lv in levels:
                # 默认用比较系统1的均值作为参比值
                ref_val = lv.ref1_mean or lv.ref1_y1 or ""
                of = _parse_float(lv.our_value)
                rf = _parse_float(ref_val)
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
                level_results.append({
                    "level": lv.level_num,
                    "our": lv.our_value,
                    "ref_y1": lv.ref1_y1, "ref_y2": lv.ref1_y2, "ref_mean": lv.ref1_mean,
                    "abs_bias": round(abs_bias, 3) if abs_bias is not None else None,
                    "rel_bias": round(rel_bias, 2) if rel_bias is not None else None,
                    "bias": bias, "accepted": accepted,
                })

        project_rows.append({
            "item": it.item, "unit": it.unit,
            "te": it.te, "mode": it.mode, "kind": kind, "note": it.note,
            "levels": level_results,
        })

    return {"projects": project_rows, "all_ok": all_ok, "has_qual": has_qual, "has_quan": has_quan}


def _qualitative_eval(our, ref):
    a, b = _norm_pn(our), _norm_pn(ref)
    if a is None or b is None:
        return None, f"{our or '—'} / {ref or '—'}"
    matched = (a == b)
    label = "阳性" if a == "positive" else "阴性"
    return matched, f"{label} / {label if matched else ('阴性' if a == 'positive' else '阳性')}"


# ---------------------------------------------------------------------------
# HTML 预览
# ---------------------------------------------------------------------------
def build_html(plan, data: dict, instrument_name: str, ref_lab: str):
    css = """
    <style>
      .rep { font-family:'Microsoft YaHei','SimSun',serif; color:#222; max-width:960px; margin:0 auto; padding:16px; }
      .rep h1 { text-align:center; font-size:20px; margin:6px 0; }
      .rep .sub { text-align:center; font-size:12px; color:#555; margin-bottom:10px; }
      .rep h2 { font-size:14px; margin:14px 0 6px; border-left:4px solid #1a365d; padding-left:8px; }
      .rep .note { font-size:12px; color:#666; margin:4px 0; }
      .rep table { border-collapse:collapse; width:100%; font-size:12px; margin:8px 0; }
      .rep th, .rep td { border:1px solid #444; padding:4px 6px; text-align:center; }
      .rep th { background:#eef2f8; }
      .rep .item { text-align:left; font-weight:bold; background:#f8fafe; }
      .rep .no { color:#c0392b; font-weight:700; }
      .rep .yes { color:#27ae60; font-weight:700; }
      .rep .concl { margin-top:6px; font-size:13px; }
      .rep .proj-sep { margin-top:14px; }
    </style>"""
    half = "上半年" if plan.half == 1 else "下半年"
    yn = plan.year or ""

    if data["has_qual"] and not data["has_quan"]:
        title = "定性项目室间比对结果记录及分析报告表"
    elif data["has_quan"] and not data["has_qual"]:
        title = "定量项目室间比对结果记录及分析报告表"
    else:
        title = "室间比对结果记录及分析报告表"

    html = [f'<div class="rep">{css}<h1>{title}</h1>']
    html.append(f'<div class="sub">民航总医院检验科　　部门：生化免疫组　　{yn}年{half}</div>')
    html.append("<h2>基本信息</h2>")
    html.append(f"<p>我室仪器：{instrument_name or '　　　　'}　　参比实验室：{ref_lab or '　　　　'}</p>")
    html.append(f"<p>比对日期：{plan.compared_at or '　　　　'}　　操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}</p>")

    # ---- 定量（BG-SM-CZ-019 结构：每项目一张 5 水平表） ----
    if data["has_quan"]:
        html.append("<h2>定量项目室间比对结果</h2>")
        html.append('<p class="note">注：80%样本（4/5）的相对偏倚需低于允许总误差认为合格，允许总误差参照行标及国家卫健委室间质评要求，无相应要求的按照30%计算。</p>')
        for proj in data["projects"]:
            if proj["kind"] != "定量":
                continue
            html.append(f'<p style="margin:8px 0 2px;font-weight:bold;">项目：{proj["item"]}（单位：{proj["unit"]}，允许TE：{proj["te"]}{"%" if proj["mode"]=="relative" else ""}）</p>')
            html.append('<table><thead><tr>'
                        '<th>水平</th><th>参比值Y</th>'
                        '<th>我室值(X)</th>'
                        '<th>偏倚</th><th>相对偏倚</th><th>是否合格</th>'
                        '</tr></thead><tbody>')
            ok_count = 0
            for lv in proj["levels"]:
                abs_s = f"{lv['abs_bias']}" if lv.get("abs_bias") is not None else "—"
                rel_s = f"{lv['rel_bias']}%" if lv.get("rel_bias") is not None else "—"
                acc = lv["accepted"]
                if acc is True: ok_count += 1
                acc_cls = "yes" if acc is True else ("no" if acc is False else "")
                acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
                html.append(
                    f'<tr><td>{lv["level"]}</td><td>{lv["ref_y1"]}</td>'
                    f'<td>{lv["our"]}</td>'
                    f'<td>{abs_s}</td><td>{rel_s}</td>'
                    f'<td class="{acc_cls}">{acc_s}</td></tr>'
                )
            html.append("</tbody></table>")
            html.append(f'<p class="concl">5个水平中合格{ok_count}个（4/5即通过），项目{proj["item"]}室间比对一致性'
                        f'{"可接受" if ok_count >= 4 else "不可接受"}。</p>')

    # ---- 定性（BG-SM-CZ-018 结构） ----
    if data["has_qual"]:
        html.append("<h2>定性项目室间比对结果</h2>")
        for proj in data["projects"]:
            if proj["kind"] != "定性":
                continue
            html.append(f'<p style="margin:8px 0 2px;font-weight:bold;">项目：{proj["item"]}</p>')
            html.append('<table><thead><tr>'
                        '<th>水平</th><th>本院结果</th><th>参比结果</th><th>阴阳判定</th><th>符合</th><th>是否合格</th>'
                        '</tr></thead><tbody>')
            matched = 0
            for lv in proj["levels"]:
                m = lv.get("match")
                acc = lv["accepted"]
                if acc is True: matched += 1
                acc_cls = "yes" if acc is True else ("no" if acc is False else "")
                acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
                m_s = {True: "是", False: "否", None: "-"}[m]
                html.append(
                    f'<tr><td>{lv["level"]}</td><td>{lv["our"]}</td><td>{lv["ref"]}</td>'
                    f'<td>{lv["pn"]}</td><td>{m_s}</td>'
                    f'<td class="{acc_cls}">{acc_s}</td></tr>'
                )
            html.append("</tbody></table>")
            rate = round(matched / max(len(proj["levels"]), 1) * 100, 1)
            html.append(f'<p class="concl">5个水平符合{matched}/{len(proj["levels"])}，符合率{rate}%。</p>')

    html.append(f'<h2>结果分析</h2><p>{plan.summary or "各项目室间比对结果均在允许范围内，比对可接受。"}</p>')
    html.append(f'<h2>处理方案（如不合格）</h2><p>{plan.handle_plan or "无"}</p>')
    concl = plan.conclusion or ("可接受" if data["all_ok"] else "不可接受")
    html.append(f'<p>结论：<b>{concl}</b></p>')
    html.append(f'<div class="foot" style="margin-top:18px;">操作者：{plan.operator or "　　　　"}　　审核者：{plan.reviewer or "　　　　"}　　日期：{plan.compared_at or "　　　　"}</div>')
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


def _add_basic_info(doc, instrument_name, ref_lab, plan):
    _heading(doc, "基本信息")
    for line in [
        f"我室仪器：{instrument_name or '　　　　'}　　参比实验室：{ref_lab or '　　　　'}",
        f"比对日期：{plan.compared_at or '　　　　'}　　操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}",
    ]:
        p = doc.add_paragraph()
        rr = p.add_run(line)
        rr.font.size = Pt(11)
        rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")


def _add_footer(doc, plan):
    p = doc.add_paragraph()
    rf = p.add_run(f"操作者：{plan.operator or '　　　　'}　　审核者：{plan.reviewer or '　　　　'}　　日期：{plan.compared_at or '　　　　'}")
    rf.font.size = Pt(11)
    rf.font.name = "SimSun"
    rf._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")


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

    _add_basic_info(doc, instrument_name, ref_lab, plan)

    # ---- 定量表 ----
    if has_n:
        _heading(doc, "定量项目室间比对结果")
        pn = doc.add_paragraph()
        rr = pn.add_run("注：80%样本（4/5）的相对偏倚需低于允许总误差认为合格，允许总误差参照行标及国家卫健委室间质评要求，无相应要求的按照30%计算。")
        rr.font.size = Pt(9.5); rr.font.color.rgb = RGBColor(0x66, 0x66, 0x66); rr.font.name = "SimSun"
        rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

        for proj in data["projects"]:
            if proj["kind"] != "定量":
                continue
            # 项目标题行
            p = doc.add_paragraph()
            pr = p.add_run(f"项目：{proj['item']}（单位：{proj['unit']}，允许TE：{proj['te']}{'%' if proj['mode']=='relative' else ''}）")
            pr.font.size = Pt(10.5); pr.font.bold = True; pr.font.name = "SimSun"
            pr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

            t = doc.add_table(rows=1, cols=6)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = t.rows[0].cells
            for i, ht in enumerate(["水平", "参比值Y", "我室值(X)", "偏倚", "相对偏倚", "是否合格"]):
                _fill(hdr[i], ht, bold=True)

            ok_count = 0
            for lv in proj["levels"]:
                cells = t.add_row().cells
                abs_s = f"{lv['abs_bias']}" if lv.get("abs_bias") is not None else "—"
                rel_s = f"{lv['rel_bias']}%" if lv.get("rel_bias") is not None else "—"
                acc = lv["accepted"]
                if acc is True: ok_count += 1
                acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
                _fill(cells[0], str(lv["level"]))
                _fill(cells[1], lv["ref_y1"])
                _fill(cells[2], lv["our"])
                _fill(cells[3], abs_s)
                _fill(cells[4], rel_s)
                col = RGBColor(0x27, 0xae, 0x60) if acc is True else (RGBColor(0xc0, 0x39, 0x2b) if acc is False else None)
                _fill(cells[5], acc_s, color=col, bold=True)

            p = doc.add_paragraph()
            pr = p.add_run(f"结论：5个水平中合格{ok_count}个（4/5即通过），项目{proj['item']}室间比对一致性{'可接受' if ok_count >= 4 else '不可接受'}。")
            pr.font.size = Pt(10.5); pr.font.name = "SimSun"
            pr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    # ---- 定性表 ----
    if has_q:
        _heading(doc, "定性项目室间比对结果")
        for proj in data["projects"]:
            if proj["kind"] != "定性":
                continue
            p = doc.add_paragraph()
            pr = p.add_run(f"项目：{proj['item']}")
            pr.font.size = Pt(10.5); pr.font.bold = True; pr.font.name = "SimSun"
            pr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

            t = doc.add_table(rows=1, cols=6)
            t.style = "Table Grid"
            t.alignment = WD_TABLE_ALIGNMENT.CENTER
            hdr = t.rows[0].cells
            for i, ht in enumerate(["水平", "本院结果", "参比结果", "阴阳判定", "符合", "是否合格"]):
                _fill(hdr[i], ht, bold=True)

            matched = 0
            for lv in proj["levels"]:
                cells = t.add_row().cells
                m = lv.get("match")
                acc = lv["accepted"]
                if acc is True: matched += 1
                acc_s = {True: "合格", False: "不合格", None: "-"}[acc]
                m_s = {True: "是", False: "否", None: "-"}[m]
                _fill(cells[0], str(lv["level"]))
                _fill(cells[1], lv["our"])
                _fill(cells[2], lv["ref"])
                _fill(cells[3], lv["pn"])
                _fill(cells[4], m_s)
                col = RGBColor(0x27, 0xae, 0x60) if acc is True else (RGBColor(0xc0, 0x39, 0x2b) if acc is False else None)
                _fill(cells[5], acc_s, color=col, bold=True)

            rate = round(matched / max(len(proj["levels"]), 1) * 100, 1)
            p = doc.add_paragraph()
            pr = p.add_run(f"结论：5个水平符合{matched}/{len(proj['levels'])}，符合率{rate}%。")
            pr.font.size = Pt(10.5); pr.font.name = "SimSun"
            pr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "结果分析")
    p = doc.add_paragraph()
    rr = p.add_run(plan.summary or "各项目室间比对结果均在允许范围内，比对可接受。")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _heading(doc, "处理方案（如不合格）")
    p = doc.add_paragraph()
    rr = p.add_run(plan.handle_plan or "无")
    rr.font.size = Pt(11); rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    concl = plan.conclusion or ("可接受" if data["all_ok"] else "不可接受")
    p = doc.add_paragraph()
    rr = p.add_run(f"结论：{concl}")
    rr.font.size = Pt(11); rr.font.bold = True; rr.font.name = "SimSun"
    rr._element.rPr.rFonts.set(qn("w:eastAsia"), "SimSun")

    _add_footer(doc, plan)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    doc.save(out_path)
