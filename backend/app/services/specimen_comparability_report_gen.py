"""样本类型可比性验证报告（docx）。

复用 method_comparison_report_gen 的排版工具与 Pillow 图表。
"""
import io
from statistics import mean

from docx import Document
from docx.shared import Cm, Pt

from .method_comparison_report_gen import (
    _cell,
    _figure,
    _h,
    _new_doc,
    _num,
    _para,
    _rank_chart,
    _scatter_chart,
    _sign_block,
    _subtitle,
    _table,
    _title,
)

_TYPE_TEXT = {
    "serum_vs_plasma": "血清 vs 血浆",
    "plasma_anticoagulant": "血浆-肝素 vs 血浆-EDTA",
    "different_tube": "不同采血管",
    "standing_time": "不同放置时间",
    "other": "其他（自定义）",
}


def _plan_block(doc, rec):
    rows = [
        ["项目名称", rec.get("project_name") or "—", "报告单位", rec.get("unit") or "—"],
        ["验证类型", _TYPE_TEXT.get(rec.get("verify_type"), rec.get("verify_type") or "—"),
         "计划例数", str(rec.get("sample_count") or "—")],
        ["标本类型 A", rec.get("specimen_a") or "—", "标本类型 B", rec.get("specimen_b") or "—"],
        ["采血管 A", rec.get("tube_a") or "—", "采血管 B", rec.get("tube_b") or "—"],
        ["离心条件", rec.get("centrifuge") or "—", "放置条件", rec.get("storage") or "—"],
        ["检测仪器", rec.get("instrument") or "—", "验证日期", rec.get("verify_date") or "—"],
        ["样本来源", rec.get("sample_source") or "—", "参考区间",
         f"{rec.get('ref_range_low') or '—'} ~ {rec.get('ref_range_high') or '—'}"],
    ]
    t = doc.add_table(rows=len(rows), cols=4)
    t.style = "Table Grid"
    for i, row in enumerate(rows):
        for j, v in enumerate(row):
            _cell(t.rows[i].cells[j], v, bold=(j % 2 == 0), size=9)
    for row in t.rows:
        row.cells[0].width = Cm(3.0)
        row.cells[1].width = Cm(6.2)
        row.cells[2].width = Cm(3.0)
        row.cells[3].width = Cm(4.8)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)


def _charts(det):
    out = {}
    try:
        xs = [p["a"] for p in det.get("per_sample") or []]
        ys = [p["b"] for p in det.get("per_sample") or []]
        diffs = [p["diff"] for p in det.get("per_sample") or []]
        rels = [p.get("rel_pct") or 0 for p in det.get("per_sample") or []]
        pb = det.get("pb") or {}
        if xs and pb.get("slope") is not None:
            out["A"] = _scatter_chart(xs, ys, "Specimen A", "Specimen B",
                                      fit=(pb["slope"], pb["intercept"]),
                                      title="Figure A  Paired results (A vs B)")
        out["B"] = _rank_chart(rels, "Figure B  Relative difference (%) sorted", "Percent (%)")
        ba = det.get("ba") or {}
        if xs:
            means = [(p["a"] + p["b"]) / 2 for p in det.get("per_sample") or []]
            hlines = [(ba.get("mean_diff") or 0, (60, 66, 78)),
                      (ba.get("loa_high") or 0, (217, 83, 79)),
                      (ba.get("loa_low") or 0, (217, 83, 79))]
            out["C"] = _scatter_chart(means, diffs, "Mean of A and B", "Difference (B-A)",
                                      hlines=hlines, title="Figure C  Bland-Altman plot")
    except Exception:
        pass
    return out


def build_specimen_report(rec: dict) -> bytes:
    rs = rec.get("result_summary") or {}
    det = rec.get("details") or {}
    if not rs.get("valid"):
        raise ValueError(rs.get("message") or "验证结果无效，无法生成报告")

    ta, tb = rs.get("specimen_a") or "标本A", rs.get("specimen_b") or "标本B"
    allow = rs.get("allow_bias")

    doc = _new_doc()
    _title(doc, "样本类型可比性验证报告")
    _subtitle(doc, f"（{ta} vs {tb}——{rs.get('project_name') or ''}）")
    _plan_block(doc, rec)

    # 一、验证方案
    _h(doc, "一、验证方案与判定标准")
    _para(doc,
          f"依据 CNAS-CL02:2023 第 7.3.7.4 条（检验结果的可比性），对不同标本类型但临床预期用途及单位相同的"
          f"项目，应在临床适宜区间内验证患者样品结果的可比性。本次对 {rs.get('project_name') or ''} 采用"
          f"同一患者同次采集的配对标本，{ta} 与 {tb} 在同一检测系统上平行测定，共纳入有效样本 "
          f"{rs.get('n_used')} 例。")
    _para(doc,
          f"判定标准：允许偏倚取 1/2 允许总误差（1/2 TEa）"
          + (f"＝±{allow:g}%" if allow else "（未设置 TEa）")
          + "，达到允许偏倚的样本比例 ≥ 80%（即“5 份中至少 4 份”口径）判定为可比；"
            "定量项目有效样本不少于 5 例，常规建议 20 例。回归斜率与相关系数仅作参考，不参与判定。")

    # 二、结果分析
    _h(doc, "二、结果分析")
    charts = _charts(det)
    _figure(doc, charts.get("A"), "图A　配对结果散点图（含 Passing-Bablok 回归线）")
    _figure(doc, charts.get("B"), "图B　相对偏差排序图")
    _figure(doc, charts.get("C"), "图C　Bland-Altman 一致性图")

    # 三、偏倚与达标率
    _h(doc, "三、偏倚与达标率分析")
    ci = rs.get("bias_pct_ci") or [None, None]
    rows = [
        ["有效样本数", str(rs.get("n_used")), "允许偏倚（1/2 TEa）",
         f"±{allow:g}%" if allow else "未设置"],
        ["平均偏倚", f"{rs.get('mean_bias_pct'):+.2f}%" if rs.get("mean_bias_pct") is not None else "—",
         "平均偏倚 95%CI",
         f"{ci[0]:+.2f}% ~ {ci[1]:+.2f}%" if ci[0] is not None else "—"],
        ["最大单例相对偏倚", f"{rs.get('max_abs_rel_pct'):.2f}%" if rs.get("max_abs_rel_pct") is not None else "—",
         "达标例数 / 要求",
         f"{rs.get('pass_n')}/{rs.get('n_used')}（需 ≥{rs.get('pass_needed')} 例）" if rs.get("pass_n") is not None else "—"],
        ["达标率", f"{rs.get('pass_rate'):.1f}%" if rs.get("pass_rate") is not None else "—",
         "是否满足 80%", "是" if (rs.get("pass_rate") or 0) >= 80 else "否"],
        ["Passing-Bablok 斜率", _num(rs.get("slope"), 4),
         "斜率 95%CI",
         f"{rs['slope_ci'][0]:.4f}~{rs['slope_ci'][1]:.4f}" if rs.get("slope_ci") else "—"],
        ["相关系数 r（参考）", _num(rs.get("pearson_r"), 4),
         "Bland-Altman P", rs.get("ba_p") or "—"],
    ]
    _table(doc, ["指标", "结果", "指标", "结果"], rows, widths=[3.6, 3.6, 3.6, 4.2], size=8.5)

    # 四、结论
    _h(doc, "四、验证结论")
    for line in (rs.get("conclusion_lines") or [rs.get("conclusion", "")]):
        if line:
            _para(doc, line.replace("**", ""))

    # 五、原始数据
    per = det.get("per_sample") or []
    if per:
        _h(doc, "五、原始数据")
        data_rows = []
        for p in per:
            flag = "—" if p.get("pass") is None else ("是" if p["pass"] else "否")
            data_rows.append([p.get("no"), _num(p.get("a"), 3), _num(p.get("b"), 3),
                              _num(p.get("diff"), 3),
                              f"{_num(p.get('rel_pct'), 2)}%" if p.get("rel_pct") is not None else "—",
                              flag])
        _table(doc, ["样本号", f"{ta}", f"{tb}", "绝对偏差", "相对偏差", "是否在允许偏倚内"],
               data_rows, widths=[1.8, 3.6, 3.6, 2.6, 2.6, 3.4], size=8.5)
        _para(doc, "注：本记录由授权签字人审核签字后归档，保存期不少于 2 年（CNAS-CL02:2023 7.3.7.4）。", size=9)

    _sign_block(doc, rec)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()
