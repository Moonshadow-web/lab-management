"""性能验证后端计算引擎（核心统计 + 自动判定）。

把原本写在 Excel 模板单元格公式里的统计计算，改用后端 Python 实现：
- 精密度：批内 CV（EP15 组内方差平均）、批间 CV、实验室内 CV
- 正确度：总均值、相对偏倚（与定值靶值比），判定 ≤ 1/2 TEA
- 线性范围：各点均值、理论值（线性外推）、相对偏倚、线性回归 R²/斜率/截距
- 方法符合率（定性）：阳性/阴性符合率 ≥ 95%
- 方法检出限（定性）：检出限浓度阳性率 ≥ 95%
- 可报告范围：低限/高限相对偏倚判定（低限 ≤ TEA，高限 ≤ 1/2 TEA）
- 参考区间：每组超出数 ≤ 2 判定
- 分析特异性：干扰物实测偏倚 ≤ 10%（或尊重用户判定）

产出 result_summary 片段（写入 verification_reports.result_summary）+ detail
（供报告生成器把核心指标静态写入模板单元格，报告不依赖 Excel 公式）。
"""
import re

# 定性精密度可接受标准（CNAS-GL038 / 卫健委推荐）
QUAL_WITHIN_CV = 7.5   # 批内 CV ≤ 7.5%
QUAL_LAB_CV = 10.0     # 实验室内 CV ≤ 10.0%
# 定性符合率 / 检出限阳性率
QUAL_RATE = 95.0
# 参考区间：每组超出 ≤ 2 个即通过
REF_OUT_LIMIT = 2
# 特异性：实测偏倚 ≤ 10%
SPEC_BIAS_LIMIT = 10.0


def _nums(vals):
    out = []
    for v in vals or []:
        if v is None or v == "":
            continue
        try:
            out.append(float(v))
        except (TypeError, ValueError):
            continue
    return out


def _mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def _sd(xs):
    """样本标准差（n-1）。"""
    n = len(xs)
    if n < 2:
        return 0.0
    m = _mean(xs)
    return (sum((x - m) ** 2 for x in xs) / (n - 1)) ** 0.5


def _fmt2(v, suffix="%"):
    return f"{v:.2f}{suffix}" if v or v == 0 else "—"


def _extract_first_pct(text):
    """从文本提取第一个百分比数值（返回 float）。"""
    if not text:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text))
    return float(m.group(1)) if m else None


# ──────────────────────────────────────────────────────────────────
# 精密度
# ──────────────────────────────────────────────────────────────────
def _precision_level_metrics(days):
    """单个水平：返回 {mean, within_cv, between_cv, lab_cv, within_sd, lab_sd}。

    算法（EP15-A3 简化版）：
    - 每天 3 次重复 → 每天均值 m_i、每天 SD s_i（n-1）
    - 批内方差 Vr = Σs_i² / D
    - 批间方差 Vb = SD(m_i)² - Vr/n（n 为每天重复次数，负值取 0）
    - 实验室内方差 VT = Vr + Vb
    - CV = SD / 总均值
    """
    day_data = [_nums(d) for d in days]
    day_data = [d for d in day_data if len(d) >= 2]
    if not day_data:
        return None
    n = min(len(d) for d in day_data)  # 每天重复次数
    day_means = [_mean(d) for d in day_data]
    day_sds = [_sd(d) for d in day_data]
    total = [x for d in day_data for x in d]
    mean = _mean(total)

    vr = sum(s * s for s in day_sds) / len(day_sds)       # 批内方差
    vb_raw = _sd(day_means) ** 2 - vr / n                  # 批间方差
    vb = max(vb_raw, 0.0)
    vt = vr + vb                                           # 实验室内方差
    within_sd = vr ** 0.5
    between_sd = vb ** 0.5
    lab_sd = vt ** 0.5
    return {
        "mean": mean,
        "within_cv": (within_sd / mean * 100) if mean else 0.0,
        "between_cv": (between_sd / mean * 100) if mean else 0.0,
        "lab_cv": (lab_sd / mean * 100) if mean else 0.0,
    }


def calc_precision(data, report_type="quantitative", tea=None,
                   within_cv_target=None, lab_cv_target=None):
    """精密度：返回 {result_text, conclusion, passed, detail}。"""
    import statistics as st
    prec = (data or {}).get("precision") or {}
    levels = prec.get("levels") or []
    within_vals, lab_vals = [], []
    details = []
    for lv in levels[:2]:
        days = lv.get("days") or lv.get("rows") or []
        m = _precision_level_metrics(days)
        if not m:
            continue
        within_vals.append(m["within_cv"])
        lab_vals.append(m["lab_cv"])
        details.append({"level": lv.get("name") or "", **m})

    # 判定标准
    if report_type == "qualitative":
        w_target = within_cv_target if within_cv_target else QUAL_WITHIN_CV
        l_target = lab_cv_target if lab_cv_target else QUAL_LAB_CV
    else:
        tea_v = float(tea) if tea else 0.0
        w_target = within_cv_target if within_cv_target else (tea_v / 4 if tea_v else 0.0)
        l_target = lab_cv_target if lab_cv_target else (tea_v / 3 if tea_v else 0.0)

    def _fmt_pair(vals):
        a = f"低值{vals[0]:.2f}%" if len(vals) > 0 and vals[0] else ""
        b = f"高值{vals[1]:.2f}%" if len(vals) > 1 and vals[1] else ""
        return " ".join(filter(None, [a, b]))

    passed = all(
        (within_vals[i] < w_target and lab_vals[i] < l_target)
        for i in range(len(within_vals))
    ) if within_vals else False

    conclusion = "符合要求" if passed else "不符合要求"
    return {
        "result": f"批内CV {_fmt_pair(within_vals)} 实验室内CV {_fmt_pair(lab_vals)}" if within_vals else "",
        "conclusion": conclusion,
        "passed": passed,
        "detail": {
            "within_cv_list": within_vals,
            "lab_cv_list": lab_vals,
            "within_target": w_target,
            "lab_target": l_target,
            "levels": details,
        },
    }


# ──────────────────────────────────────────────────────────────────
# 正确度
# ──────────────────────────────────────────────────────────────────
def calc_trueness(data, tea=None):
    """正确度：每水平总均值、相对偏倚（与靶值比），判定 |偏倚| ≤ 1/2 TEA。"""
    tru = (data or {}).get("trueness") or {}
    levels = tru.get("levels") or []
    biases, details = [], []
    for lv in levels[:2]:
        rows = lv.get("days") or lv.get("rows") or []
        vals = []
        for r in rows:
            vals.extend(_nums(r))
        target = None
        try:
            target = float(lv.get("target")) if lv.get("target") not in (None, "") else None
        except (TypeError, ValueError):
            target = None
        if not vals:
            continue
        mean = _mean(vals)
        bias = ((mean - target) / target * 100) if (target and target != 0) else 0.0
        biases.append(bias)
        details.append({"level": lv.get("name") or "", "mean": mean, "target": target, "bias_pct": bias})

    tea_v = float(tea) if tea else 0.0
    limit = tea_v / 2 if tea_v else 0.0
    passed = all(abs(b) <= limit for b in biases) if biases else False
    conclusion = "符合要求" if passed else "不符合要求"
    return {
        "result": " ".join(f"水平{i + 1}偏倚 {b:.2f}%" for i, b in enumerate(biases)) if biases else "",
        "conclusion": conclusion,
        "passed": passed,
        "detail": {"bias_list": biases, "limit": limit, "levels": details},
    }


# ──────────────────────────────────────────────────────────────────
# 线性范围
# ──────────────────────────────────────────────────────────────────
def _linreg(xs, ys):
    """最小二乘线性回归 → {slope, intercept, r2}。"""
    n = len(xs)
    if n < 2:
        return {"slope": 0.0, "intercept": 0.0, "r2": 0.0}
    mx, my = _mean(xs), _mean(ys)
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    slope = sxy / sxx if sxx else 0.0
    intercept = my - slope * mx
    syy = sum((y - my) ** 2 for y in ys)
    r2 = (sxy ** 2 / (sxx * syy)) if (sxx and syy) else 0.0
    return {"slope": slope, "intercept": intercept, "r2": r2}


def calc_linearity(data, tea=None, linear_low=None, linear_high=None):
    """线性范围：各点均值 vs 理论值（端点外推），相对偏倚 ≤ 1/2 TEA。

    理论值 = 线性范围下限 × 该点低浓度比例 + 线性范围上限 × 该点高浓度比例；
    若上下限未填，用首末点实测均值外推（模板两点法同逻辑）。
    """
    lin = (data or {}).get("linearity") or {}
    points = lin.get("points") or []
    lows = lin.get("low_ratios") or [p.get("low") for p in points]
    highs = lin.get("high_ratios") or [p.get("high") for p in points]

    means, details = [], []
    for p in points:
        vals = _nums([p.get("v1"), p.get("v2"), p.get("v3")])
        means.append(_mean(vals) if vals else None)

    # 端点（理论浓度基准）
    try:
        lo = float(linear_low) if linear_low not in (None, "") else None
    except (TypeError, ValueError):
        lo = None
    try:
        hi = float(linear_high) if linear_high not in (None, "") else None
    except (TypeError, ValueError):
        hi = None

    valid_means = [m for m in means if m is not None]
    if not valid_means:
        return {"result": "", "conclusion": "不符合要求", "passed": False,
                "detail": {"levels": []}}

    biases, theoretical = [], []
    for i, m in enumerate(means):
        if m is None:
            continue
        try:
            low_r = float(lows[i]) if i < len(lows) and lows[i] not in (None, "") else 0.0
        except (TypeError, ValueError):
            low_r = 0.0
        try:
            high_r = float(highs[i]) if i < len(highs) and highs[i] not in (None, "") else 0.0
        except (TypeError, ValueError):
            high_r = 0.0
        if lo is not None and hi is not None:
            theo = lo * low_r + hi * high_r
        else:
            # 两点法：理论值 = 首点均值×低比例 + 末点均值×高比例
            theo = valid_means[0] * low_r + valid_means[-1] * high_r
        if not theo:
            biases.append(0.0)
        else:
            biases.append((m - theo) / theo * 100)
        theoretical.append(theo)
        details.append({"point": i + 1, "mean": m, "theory": theo, "bias_pct": biases[-1]})

    tea_v = float(tea) if tea else 0.0
    limit = tea_v / 2 if tea_v else 0.0
    passed = all(abs(b) <= limit for b in biases) if biases else False
    conclusion = "符合要求" if passed else "不符合要求"

    # 回归（理论值为 x，实测为 y）
    xv = [d["theory"] for d in details]
    yv = [d["mean"] for d in details]
    reg = _linreg(xv, yv)
    return {
        "result": "各浓度点相对偏倚均≤1/2TEA" if passed else
                  f"存在点偏倚超限（最大 {max(abs(b) for b in biases):.2f}%）",
        "conclusion": conclusion,
        "passed": passed,
        "detail": {"levels": details, "regression": reg, "limit": limit},
    }


# ──────────────────────────────────────────────────────────────────
# 方法符合率（定性）
# ──────────────────────────────────────────────────────────────────
def calc_conformity(data):
    """方法符合率：阳性/阴性符合率 ≥ 95%。"""
    conf = (data or {}).get("conformity") or {}
    samples = conf.get("samples") or []
    valid = [s for s in samples if s.get("ref") and s.get("mresult")]
    pos = [s for s in valid if s["ref"] == "P"]
    neg = [s for s in valid if s["ref"] == "N"]
    pos_rate = (sum(1 for s in pos if s["mresult"] == "P") / len(pos) * 100) if pos else None
    neg_rate = (sum(1 for s in neg if s["mresult"] == "N") / len(neg) * 100) if neg else None
    passed = True
    if pos_rate is not None:
        passed = passed and pos_rate >= QUAL_RATE
    if neg_rate is not None:
        passed = passed and neg_rate >= QUAL_RATE
    if pos_rate is None and neg_rate is None:
        passed = False
    parts = []
    if pos_rate is not None:
        parts.append(f"阳性符合率{pos_rate:.0f}%")
    if neg_rate is not None:
        parts.append(f"阴性符合率{neg_rate:.0f}%")
    return {
        "result": " ".join(parts),
        "conclusion": "符合要求" if passed else "不符合要求",
        "passed": passed,
        "detail": {"pos_rate": pos_rate, "neg_rate": neg_rate},
    }


# ──────────────────────────────────────────────────────────────────
# 方法检出限（定性）
# ──────────────────────────────────────────────────────────────────
def calc_lod(data):
    """方法检出限：检出限浓度样品阳性率 ≥ 95%。"""
    lod = (data or {}).get("lod") or {}
    samples = lod.get("samples") or []
    valid = [s for s in samples if s.get("mresult")]
    if not valid:
        return {"result": "", "conclusion": "不符合要求", "passed": False, "detail": {}}
    pos = sum(1 for s in valid if s["mresult"] == "P")
    rate = pos / len(valid) * 100
    passed = rate >= QUAL_RATE
    return {
        "result": f"阳性率 {pos}/{len(valid)}（{rate:.0f}%）",
        "conclusion": "符合要求" if passed else "不符合要求",
        "passed": passed,
        "detail": {"pos": pos, "total": len(valid), "rate": rate},
    }


# ──────────────────────────────────────────────────────────────────
# 可报告范围（定量）
# ──────────────────────────────────────────────────────────────────
def calc_reportable(data, tea=None):
    """可报告范围：低限 |偏倚| ≤ TEA，高限 |偏倚| ≤ 1/2 TEA。"""
    rep = (data or {}).get("reportable") or {}
    tea_v = float(tea) if tea else 0.0

    def _one(key, limit_ratio, label):
        item = rep.get(key) or {}
        target = _nums([item.get("target")])
        measured = _nums([item.get("measured")])
        # 用户手动填的偏倚优先
        dev = None
        try:
            if item.get("deviation") not in (None, ""):
                dev = float(str(item.get("deviation")).replace("%", ""))
        except (TypeError, ValueError):
            dev = None
        if dev is None and target and measured:
            dev = (measured[0] - target[0]) / target[0] * 100
        limit = tea_v * limit_ratio if tea_v else 0.0
        if item.get("passed"):
            passed = item["passed"] == "符合要求"
        elif dev is None:
            passed = False
        else:
            passed = abs(dev) <= limit
        return {
            "label": label, "target": target[0] if target else None,
            "measured": measured[0] if measured else None,
            "deviation": dev, "limit": limit, "passed": passed,
        }

    low = _one("low", 1.0, "低限")
    high = _one("high", 0.5, "高限")
    passed = low["passed"] and high["passed"]
    parts = []
    for item in (low, high):
        if item["deviation"] is not None:
            parts.append(f"{item['label']}偏倚 {item['deviation']:.2f}%")
    return {
        "result": " ".join(parts),
        "conclusion": "符合要求" if passed else "不符合要求",
        "passed": passed,
        "detail": {"low": low, "high": high},
    }


# ──────────────────────────────────────────────────────────────────
# 参考区间
# ──────────────────────────────────────────────────────────────────
def calc_reference(data):
    """参考区间：每组超出数 ≤ 2 判定。"""
    ref = (data or {}).get("reference") or {}
    groups = ref.get("groups") or []
    outs, passed = [], True
    for g in groups:
        try:
            out = int(g.get("out")) if g.get("out") not in (None, "") else None
        except (TypeError, ValueError):
            out = None
        if out is None:
            outs.append(None)
        else:
            outs.append(out)
            if out > REF_OUT_LIMIT:
                passed = False
    if not groups:
        passed = False
    range_text = ((data or {}).get("reference") or {}).get("range_text") or ""
    parts = [f"{g.get('name', '')}超出{outs[i]}" for i, g in enumerate(groups) if outs[i] is not None]
    main = "、".join(parts) + ("，每组≤2个" if parts else "")
    text = f"参考区间：{range_text}；{main}" if range_text else main
    return {
        "result": text,
        "conclusion": "符合要求" if passed else "不符合要求",
        "passed": passed,
        "detail": {"outs": outs, "range_text": range_text},
    }


# ──────────────────────────────────────────────────────────────────
# 分析特异性
# ──────────────────────────────────────────────────────────────────
def calc_specificity(data):
    """分析特异性：干扰物实测偏倚 ≤ 10%（或尊重用户判定）。"""
    spec = (data or {}).get("specificity") or {}
    items = spec.get("items") or []
    passed, parts = True, []
    for it in items:
        nm = (it.get("name") or "").strip()
        ms = (it.get("measured") or "").strip()
        pct = _extract_first_pct(ms)
        if it.get("passed"):
            ok = it["passed"] == "符合要求"
        elif pct is not None:
            ok = abs(pct) <= SPEC_BIAS_LIMIT
        else:
            ok = True  # 无数据不判定为失败，留由用户填
        if not ok:
            passed = False
        seg = nm
        if it.get("limit"):
            seg += f" {it['limit']}"
        if ms:
            seg += f" 实测{ms}"
        parts.append(seg)
    if not items:
        passed = False
    return {
        "result": "；".join(parts) or "抗干扰能力符合厂家声明",
        "conclusion": "符合要求" if passed else "不符合要求",
        "passed": passed,
        "detail": {},
    }


# ──────────────────────────────────────────────────────────────────
# 总入口：根据 verify_items 计算全部，返回 {result_summary, details}
# ──────────────────────────────────────────────────────────────────
def compute_verification(data_field, verify_items, report_type="quantitative",
                         tea=None, within_cv_target=None, lab_cv_target=None,
                         linear_low=None, linear_high=None, dilution=None, unit=None):
    items = verify_items or []
    rs, details = {}, {}

    def _fmt_num(v):
        """数值友好显示：整数去小数，其余保留 2 位。"""
        if v is None:
            return ""
        try:
            f = float(v)
        except (TypeError, ValueError):
            return str(v)
        if f == int(f):
            return str(int(f))
        return str(round(f, 2))

    unit_suffix = f" {unit}" if unit else ""
    if "precision" in items:
        r = calc_precision(data_field, report_type, tea, within_cv_target, lab_cv_target)
        rs["precision1"] = {"result": f"批内CV {_fmt_pair_from(r['detail']['within_cv_list'])}",
                            "conclusion": r["conclusion"]}
        rs["precision2"] = {"result": f"实验室内CV {_fmt_pair_from(r['detail']['lab_cv_list'])}",
                            "conclusion": r["conclusion"]}
        details["precision"] = r["detail"]
    if report_type == "quantitative" and "trueness" in items:
        r = calc_trueness(data_field, tea)
        biases = r["detail"]["bias_list"]
        rs["trueness"] = {"result": f"相对偏倚 {_fmt_pair_from(biases)}", "conclusion": r["conclusion"]}
        details["trueness"] = r["detail"]
    if report_type == "quantitative" and "linearity" in items:
        r = calc_linearity(data_field, tea, linear_low, linear_high)
        # 验证结果展示为「声称线性范围 + 单位」，而非偏倚判定文字
        lin_txt = f"{linear_low}-{linear_high}{unit_suffix}" if (linear_low and linear_high) else r["result"]
        rs["linearity"] = {"result": lin_txt, "conclusion": r["conclusion"]}
        details["linearity"] = r["detail"]
    if report_type == "qualitative" and "conformity" in items:
        r = calc_conformity(data_field)
        rs["conformity1"] = {"result": f"阳性 {r['detail'].get('pos_rate') or 0:.0f}%",
                             "conclusion": r["conclusion"]}
        rs["conformity2"] = {"result": f"阴性 {r['detail'].get('neg_rate') or 0:.0f}%",
                             "conclusion": r["conclusion"]}
        details["conformity"] = r["detail"]
    if report_type == "qualitative" and "lod" in items:
        r = calc_lod(data_field)
        rs["lod"] = {"result": r["result"], "conclusion": r["conclusion"]}
        details["lod"] = r["detail"]
    if "reportable" in items:
        r = calc_reportable(data_field, tea)
        lo = r["detail"]["low"]["target"]
        hi = r["detail"]["high"]["target"]
        if dilution == "/":
            # 无稀释倍数：可报告范围等同于线性范围，不做验证
            lin_lo = linear_low
            lin_hi = linear_high
            rs["reportable"] = {
                "result": f"{lin_lo}-{lin_hi}{unit_suffix}" if (lin_lo and lin_hi) else "",
                "conclusion": "无",
            }
        else:
            lo_s = _fmt_num(lo)
            hi_s = _fmt_num(hi)
            rs["reportable"] = {
                "result": f"{lo_s}-{hi_s}{unit_suffix}" if (lo_s and hi_s) else "",
                "conclusion": r["conclusion"],
            }
        # 保留 subKey 供 Excel 模板（低限/高限分列）使用
        if dilution == "/":
            rs["reportable1"] = {"result": "等同线性范围", "conclusion": "无"}
            rs["reportable2"] = {"result": "", "conclusion": "无"}
        else:
            rs["reportable1"] = {"result": f"低限 {lo_s}", "conclusion": rs["reportable"]["conclusion"]}
            rs["reportable2"] = {"result": f"高限 {hi_s}", "conclusion": rs["reportable"]["conclusion"]}
        details["reportable"] = r["detail"]
    if "reference" in items:
        r = calc_reference(data_field)
        rs["reference"] = {"result": r["result"], "conclusion": r["conclusion"]}
        details["reference"] = r["detail"]
    if "specificity" in items:
        r = calc_specificity(data_field)
        rs["specificity"] = {"result": r["result"], "conclusion": r["conclusion"]}
        details["specificity"] = r["detail"]
    return {"result_summary": rs, "details": details}


def _to_pct(text: str) -> str:
    """把文本中 0<v<1 的无%小数转为百分数（如 0.0059 -> 0.59%）；已带%或非纯小数不动。"""
    if not text or '%' in text:
        return text

    def _repl(m):
        v = float(m.group(0))
        if 0 < v < 1:
            s = f"{v * 100:.4f}".rstrip('0').rstrip('.')
            return f"{s}%"
        return m.group(0)

    return re.sub(r'\d+\.\d+', _repl, text)


def _auto_conclusion(result_text: str, tea) -> str:
    """result 含 % 数字时，按 |最大数字| < 0.5*TEA 兜底「符合要求」。

    典型场景：1号机 vs 靶机比对的正确度/精密度（vrf_parser 未提取到"符合"文字，结果文本只有数字百分比）。
    """
    if not result_text or not isinstance(tea, (int, float)) or tea <= 0:
        return ""
    nums = []
    for m in re.finditer(r"(\d+(?:\.\d+)?)%", result_text):
        try:
            v = float(m.group(1))
        except ValueError:
            continue
        nums.append(v)
    if not nums:
        return ""
    if max(nums) / 100 < tea * 0.5:
        return "符合要求"
    return "不符合要求"


def normalize_conclusion_summary(rs, unit="", dilution=None, linear_low=None, linear_high=None, report_type="quantitative", tea=None):
    """把存储/计算得到的 result_summary 规范化为统一展示格式。

    兼容两种来源，输出完全一致，供「性能验证记录」与「验证报告归档」两页复用：
    - 后端 compute_verification 输出（已带前缀/单位/合并范围，本函数幂等）；
    - vrf_parser 上传解析输出（precision/trueness 为「低值X% 高值Y%」无前缀，
      linearity 含判定文字无单位，reportable 拆为 reportable1/2 纯数字）。

    统一输出：
      precision1/2 → 「批内CV / 实验室内CV」前缀；
      trueness     → 「相对偏倚 低值X% 高值Y%」；
      linearity    → 「范围+单位」（去判定文字）；
      reportable   → 合并「low-high+单位」；dilution='/' 时等同线性范围、结论「无」。
    """
    out = {}
    unit_suffix = f" {unit}" if unit else ""

    def _ensure_prefix(text, prefix):
        if not text:
            return text
        return text if text.startswith(prefix) else f"{prefix} {text}"

    # 精密度
    for sk, prefix in (("precision1", "批内CV"), ("precision2", "实验室内CV")):
        it = rs.get(sk)
        if it and it.get("result"):
            res_text = _ensure_prefix(it["result"], prefix)
            cons = it.get("conclusion", "") or _auto_conclusion(res_text, tea)
            out[sk] = {"result": res_text, "conclusion": cons}

    # 正确度（parser 用 trueness1/2；后端用 trueness）
    if rs.get("trueness") and rs["trueness"].get("result"):
        tr_res = _to_pct(_ensure_prefix(rs["trueness"]["result"], "相对偏倚"))
        tr_conc = rs["trueness"].get("conclusion", "") or _auto_conclusion(tr_res, tea)
        out["trueness"] = {"result": tr_res, "conclusion": tr_conc}
    else:
        t1 = rs.get("trueness1") or {}
        t2 = rs.get("trueness2") or {}
        base = (t1.get("result") or t2.get("result") or "").strip()
        if base:
            tr_res = _to_pct(_ensure_prefix(base, "相对偏倚"))
            tr_conc = t1.get("conclusion") or t2.get("conclusion") or _auto_conclusion(tr_res, tea)
            out["trueness"] = {"result": tr_res, "conclusion": tr_conc}

    # 线性范围：提取「范围」+ 单位（去掉判定文字/换行）
    it = rs.get("linearity")
    if it and it.get("result"):
        raw = it["result"]
        m = re.search(r"(\d+(?:\.\d+)?)\s*-\s*(\d+(?:\.\d+)?)", raw)
        if m and unit:
            out["linearity"] = {"result": f"{m.group(1)}-{m.group(2)}{unit_suffix}",
                                "conclusion": it.get("conclusion", "")}
        else:
            out["linearity"] = {"result": raw.replace("\n", " ").strip(),
                                "conclusion": it.get("conclusion", "")}

    # 可报告范围：合并 low-high + 单位；dilution='/' → 等同线性范围、结论「无」
    rep = rs.get("reportable")
    if rep and rep.get("result"):
        out["reportable"] = {"result": rep["result"], "conclusion": rep.get("conclusion", "")}
    else:
        if dilution == "/":
            out["reportable"] = {
                "result": f"{linear_low}-{linear_high}{unit_suffix}" if (linear_low and linear_high) else "",
                "conclusion": "无",
            }
        else:
            low = ((rs.get("reportable1") or {}).get("result") or "").strip()
            high = ((rs.get("reportable2") or {}).get("result") or "").strip()
            c1 = (rs.get("reportable1") or {}).get("conclusion") or ""
            c2 = (rs.get("reportable2") or {}).get("conclusion") or ""
            if low and high:
                out["reportable"] = {"result": f"{low}-{high}{unit_suffix}",
                                     "conclusion": c1 if c1 == c2 else (f"{c1}/{c2}" if (c1 and c2) else (c1 or c2))}
            elif low:
                out["reportable"] = {"result": f"{low}{unit_suffix}", "conclusion": c1}
            elif high:
                out["reportable"] = {"result": f"{high}{unit_suffix}", "conclusion": c2}

    # 其余项（参考区间/分析特异性/方法符合率/检出限）原样保留（去换行）
    for k in ("reference", "specificity", "conformity1", "conformity2", "lod"):
        it = rs.get(k)
        if it and (it.get("result") or it.get("conclusion")):
            out[k] = {"result": (it.get("result") or "").replace("\n", " ").strip(),
                      "conclusion": it.get("conclusion", "")}
    return out


def _fmt_pair_from(vals):
    a = f"低值{vals[0]:.2f}%" if len(vals) > 0 and vals[0] else ""
    b = f"高值{vals[1]:.2f}%" if len(vals) > 1 and vals[1] else ""
    return " ".join(filter(None, [a, b]))
