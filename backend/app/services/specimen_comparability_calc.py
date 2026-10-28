"""样本类型可比性验证（如血清 vs 血浆）。

判定依据：CNAS-CL02:2023 第 7.3.7.4 条（检验结果的可比性）
- 允许偏倚 = 1/2 TEa（TEa 取 WS/T 403-2024）
- 判定：达到允许偏倚的样本比例 ≥ 80%（"5 份中至少 4 份"口径）
- 定量项目有效样本不少于 5 例（常规建议 20 例）
- 斜率、相关系数仅作展示，不作为判定依据

统计复用 method_comparison_calc 中已实现的纯标准库算法。
"""
import math
from statistics import mean, stdev

from .method_comparison_calc import (
    _bootstrap_ci,
    _fmt_p,
    _num,
    bland_altman,
    deming_xy,
    parse_pairs,
    pb_xy,
    pearson,
    t_ppf,
)

# 验证类型（前端下拉，同时作为报告"验证类型"字段）
SPECIMEN_TYPES = [
    ("serum_vs_plasma", "血清 vs 血浆"),
    ("plasma_anticoagulant", "血浆-肝素 vs 血浆-EDTA"),
    ("different_tube", "不同采血管"),
    ("standing_time", "不同放置时间"),
    ("other", "其他（自定义）"),
]

PASS_RATE_REQUIRED = 0.80   # CNAS 7.3.7.4：至少 80% 样本偏差在允许偏倚内
MIN_SAMPLES = 5             # 定量项目不少于 5 例
REQUIRED_SAMPLES = 20       # 常规建议 20 例


def _ci_mean(values):
    """均值的 95% 置信区间（t 分布）。"""
    n = len(values)
    if n < 2:
        return None, None
    m = mean(values)
    sd = stdev(values)
    half = t_ppf(0.975, n - 1) * sd / math.sqrt(n)
    return m - half, m + half


def compute_specimen_comparability(data: dict) -> dict:
    """主入口。返回 {"result_summary": {...}, "details": {...}}。"""
    pairs, skipped = parse_pairs(data.get("pairs"))
    n = len(pairs)
    if n < 3:
        return {
            "result_summary": {"valid": False, "message": "有效样本对不足 3 例，无法计算"},
            "details": {},
        }

    xs = [p["a"] for p in pairs]
    ys = [p["b"] for p in pairs]
    diffs = [ys[i] - xs[i] for i in range(n)]
    rels_pct = [((ys[i] - xs[i]) / xs[i] * 100) if xs[i] else None for i in range(n)]
    valid_rels = [r for r in rels_pct if r is not None]

    tea = _num(data.get("tea"))
    allow = tea / 2.0 if tea else None

    # ── CNAS 7.3.7.4 主判据：达到允许偏倚的样本比例 ──
    pass_n = None
    pass_rate = None
    pass_needed = None
    if allow is not None:
        pass_n = sum(1 for r in valid_rels if abs(r) <= allow)
        pass_rate = pass_n / n if n else None
        pass_needed = math.ceil(PASS_RATE_REQUIRED * n)

    # ── 展示用统计 ──
    mean_diff = mean(diffs)
    mean_bias_pct = (mean_diff / mean(xs) * 100) if mean(xs) else None
    d_lo, d_hi = _ci_mean(diffs)
    p_lo, p_hi = _ci_mean(valid_rels)
    max_abs_rel = max((abs(r) for r in valid_rels), default=None)

    ci_pb = _bootstrap_ci(pb_xy, xs, ys)
    slope, intercept = pb_xy(xs, ys)
    pb = {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "equation": f"y = {intercept:.6g} + {slope:.6g} x",
        "slope_ci": list(ci_pb["slope_ci"]) if ci_pb else None,
        "intercept_ci": list(ci_pb["intercept_ci"]) if ci_pb else None,
    }
    pr = pearson(xs, ys)
    ba = bland_altman(xs, ys)
    dslope, dintercept = deming_xy(xs, ys)
    deming = {"slope": round(dslope, 6), "intercept": round(dintercept, 6),
              "equation": f"y = {dintercept:.6g} + {dslope:.6g} x"}

    # ── 判定（三态）──
    type_a = data.get("specimen_a") or "标本A"
    type_b = data.get("specimen_b") or "标本B"
    project = data.get("project_name") or "该项目"
    if allow is None:
        verdict = None
        reason = "未设置允许总误差（TEa），无法按 CNAS-CL02 7.3.7.4 判定允许偏倚。建议补充 TEa 后复评。"
    elif n < MIN_SAMPLES:
        verdict = None
        reason = f"有效样本 {n} 例，少于 CNAS-CL02 7.3.7.4 要求的定量项目最少 {MIN_SAMPLES} 例，结论待定。"
    else:
        passed = pass_rate is not None and pass_rate >= PASS_RATE_REQUIRED
        verdict = passed
        ratio_txt = f"{pass_n}/{n}"
        reason = (
            f"{ratio_txt} 例偏差在允许偏倚 ±{allow:g}%（1/2 TEa）内，通过率 {pass_rate*100:.1f}%"
            f"（CNAS-CL02 7.3.7.4 要求 ≥80%，需 ≥{pass_needed} 例）"
            + ("，符合要求。" if passed else "，未达要求。")
        )

    if verdict is True:
        concl = [
            f"{type_a}与{type_b}对{project}的检测结果，{reason}",
            f"平均偏倚 {mean_bias_pct:+.2f}%（95%CI {p_lo:+.2f}%~{p_hi:+.2f}%），"
            f"Passing-Bablok 斜率 {slope:.4f}"
            + (f"（95%CI {pb['slope_ci'][0]:.4f}~{pb['slope_ci'][1]:.4f}）" if pb["slope_ci"] else "")
            + (f"，相关系数 r={pr['r']:.4f}" if pr else "")
            + "（斜率与 r 仅作参考，不参与判定）。",
            f"结论：{type_a}与{type_b}两种标本类型对该项目的检测结果**可比**，可按现有参考区间报告。",
        ]
    elif verdict is False:
        concl = [
            f"{type_a}与{type_b}对{project}的检测结果，{reason}",
            f"平均偏倚 {mean_bias_pct:+.2f}%（95%CI {p_lo:+.2f}%~{p_hi:+.2f}%），"
            f"Passing-Bablok 斜率 {slope:.4f}"
            + (f"（95%CI {pb['slope_ci'][0]:.4f}~{pb['slope_ci'][1]:.4f}）" if pb["slope_ci"] else "")
            + (f"，相关系数 r={pr['r']:.4f}" if pr else "")
            + "。",
            f"结论：{type_a}与{type_b}两种标本类型对该项目的检测结果**不可比**，应固定使用其中一种标本类型；"
            f"如必须替代，需评估对参考区间与医学决定水平的影响，并告知临床。",
        ]
    else:
        concl = [f"{type_a}与{type_b}对{project}的检测结果可比性**待定**。", reason]

    per_sample = []
    for i, p in enumerate(pairs):
        r = rels_pct[i]
        per_sample.append({
            "no": p["no"], "a": p["a"], "b": p["b"],
            "diff": round(diffs[i], 6),
            "rel_pct": round(r, 2) if r is not None else None,
            "pass": (abs(r) <= allow) if (allow is not None and r is not None) else None,
        })

    details = {
        "n_input": len(pairs) + len(skipped),
        "n_used": n,
        "skipped_nos": skipped,
        "allow_bias": allow,
        "pass_n": pass_n,
        "pass_needed": pass_needed,
        "pass_rate": pass_rate,
        "mean_diff": mean_diff,
        "mean_bias_pct": mean_bias_pct,
        "bias_ci": (d_lo, d_hi),
        "bias_pct_ci": (p_lo, p_hi),
        "max_abs_rel_pct": max_abs_rel,
        "pb": pb,
        "deming": deming,
        "pearson": pr,
        "ba": ba,
        "per_sample": per_sample,
        "verdict": verdict,
        "reason": reason,
    }

    rs = {
        "valid": True,
        "specimen_a": type_a,
        "specimen_b": type_b,
        "project_name": project,
        "n_used": n,
        "tea": tea,
        "allow_bias": allow,
        "pass_n": pass_n,
        "pass_needed": pass_needed,
        "pass_rate": round(pass_rate * 100, 2) if pass_rate is not None else None,
        "mean_bias_pct": round(mean_bias_pct, 2) if mean_bias_pct is not None else None,
        "bias_pct_ci": [round(p_lo, 2), round(p_hi, 2)] if p_lo is not None else None,
        "max_abs_rel_pct": round(max_abs_rel, 2) if max_abs_rel is not None else None,
        "slope": round(slope, 6),
        "slope_ci": pb["slope_ci"],
        "intercept": round(intercept, 6),
        "pearson_r": round(pr["r"], 4) if pr else None,
        "ba_p": ba["p_text"],
        "ba_consistent": ba["consistent"],
        "verdict": verdict,
        "reason": reason,
        "conclusion": "\n".join(concl),
        "conclusion_lines": concl,
    }
    return {"result_summary": rs, "details": details}
