"""方法学比对（EP9-A3 方案）统计引擎。

纯 Python 标准库实现，不依赖 numpy / scipy / matplotlib：
- 广义 ESD（迭代 Grubbs）离群值检验
- Deming 回归（含 bootstrap 置信区间）
- Passing-Bablok 回归（Theil-Sen 中位斜率 + bootstrap 置信区间）
- Bland-Altman 一致性评价（偏差、95% 一致性界限、配对 t 检验）
- Pearson 相关（Fisher z 置信区间）
- 偏移判定 / 可接受性判定 / 结论文本生成

对外主入口：compute_method_comparison(data) -> dict
"""
import math
import random
from statistics import mean, median, stdev

BOOTSTRAP_B = 1000
BOOTSTRAP_SEED = 20251028


# ─────────────────────────── t 分布（自实现，无 scipy） ───────────────────────────
def _betacf(a, b, x):
    MAXIT, EPS, FPMIN = 200, 3e-12, 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, MAXIT + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        de = d * c
        h *= de
        if abs(de - 1.0) < EPS:
            break
    return h


def _betai(a, b, x):
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    bt = math.exp(math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                  + a * math.log(x) + b * math.log(1.0 - x))
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _betacf(a, b, x) / a
    return 1.0 - bt * _betacf(b, a, 1.0 - x) / b


def t_cdf(t, df):
    if df <= 0:
        return float("nan")
    x = df / (df + t * t)
    p = 0.5 * _betai(df / 2.0, 0.5, x)
    return 1.0 - p if t > 0 else p


def t_ppf(p, df):
    """t 分布分位数（二分法反解，精度足够判定用）。"""
    lo, hi = -1e4, 1e4
    for _ in range(120):
        mid = (lo + hi) / 2
        if t_cdf(mid, df) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def t_pvalue(t, df):
    """双侧 p 值。"""
    if df <= 0 or math.isnan(t):
        return 1.0
    return max(0.0, min(1.0, 2.0 * (1.0 - t_cdf(abs(t), df))))


def _fmt_p(p):
    if p < 0.0001:
        return "<0.0001"
    return f"{p:.4f}"


# ─────────────────────────── 离群值：迭代 Grubbs / ESD ───────────────────────────
def grubbs_crit(n, alpha=0.05):
    """Grubbs 单侧临界值 G = (n-1)/sqrt(n) * sqrt(t^2/(n-2+t^2))，t 取 Bonferroni 校正分位。"""
    if n < 3:
        return float("inf")
    p = 1.0 - alpha / (2.0 * n)
    t = t_ppf(p, n - 2)
    return (n - 1) / math.sqrt(n) * math.sqrt(t * t / (n - 2 + t * t))


def esd_check(xs, ys, alpha=0.05, max_rounds=3):
    """迭代 ESD 离群值检验，返回逐轮明细与剔除的样本序号（1-based）。"""
    n = len(xs)
    work = [(i + 1, xs[i], ys[i]) for i in range(n)]
    rounds, removed = [], []
    for r in range(1, max_rounds + 1):
        m = len(work)
        if m < 3:
            break
        rel = []
        for _, a, b in work:
            rel.append((b - a) / a if a else 0.0)
        mu = mean(rel)
        sd = stdev(rel) if m > 1 else 0.0
        if sd == 0:
            break
        devs = [abs(v - mu) for v in rel]
        k = max(range(m), key=lambda j: devs[j])
        esd_max = devs[k] / sd
        lam = grubbs_crit(m, alpha)
        is_out = esd_max > lam
        rounds.append({
            "round": r,
            "n": m,
            "mean_d": round(mu, 4),
            "sd_d": round(sd, 4),
            "esd_max": round(esd_max, 4),
            "lambda": round(lam, 4),
            "outlier_rel_pct": round(rel[k] * 100, 2),
            "outlier_no": work[k][0],
            "is_outlier": bool(is_out),
        })
        if not is_out:
            break
        removed.append(work[k][0])
        work.pop(k)
    kept = [w[0] for w in work]
    return {"rounds": rounds, "removed_nos": removed, "kept_nos": kept,
            "kept_n": len(work), "initial_n": n}


# ─────────────────────────── 回归模型 ───────────────────────────
def pearson(xs, ys):
    n = len(xs)
    if n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n))
    sxx = sum((v - mx) ** 2 for v in xs)
    syy = sum((v - my) ** 2 for v in ys)
    if sxx <= 0 or syy <= 0:
        return None
    r = sxy / math.sqrt(sxx * syy)
    r = max(-0.999999, min(0.999999, r))
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3) if n > 3 else float("inf")
    lo, hi = math.tanh(z - 1.96 * se), math.tanh(z + 1.96 * se)
    return {"r": r, "ci_low": lo, "ci_high": hi}


def deming_xy(xs, ys, lam=1.0):
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    sxx = sum((v - mx) ** 2 for v in xs) / (n - 1)
    syy = sum((v - my) ** 2 for v in ys) / (n - 1)
    sxy = sum((xs[i] - mx) * (ys[i] - my) for i in range(n)) / (n - 1)
    if abs(sxy) < 1e-15:
        slope = 0.0
    else:
        disc = (syy - lam * sxx) ** 2 + 4 * lam * sxy * sxy
        slope = (syy - lam * sxx + math.sqrt(disc)) / (2 * sxy)
    return slope, my - slope * mx


def pb_xy(xs, ys):
    """Passing-Bablok: 两两斜率中位数 + 截距中位数。"""
    n = len(xs)
    slopes = []
    for i in range(n):
        for j in range(i + 1, n):
            dx = xs[j] - xs[i]
            if dx != 0:
                slopes.append((ys[j] - ys[i]) / dx)
    if not slopes:
        return 0.0, mean(ys)
    slope = median(slopes)
    intercept = median([ys[i] - slope * xs[i] for i in range(n)])
    return slope, intercept


def _bootstrap_ci(fn, xs, ys, b=BOOTSTRAP_B, seed=BOOTSTRAP_SEED, alpha=0.05):
    n = len(xs)
    if n < 4:
        return None
    rng = random.Random(seed)
    slopes, ints = [], []
    for _ in range(b):
        idx = [rng.randrange(n) for _ in range(n)]
        bx = [xs[i] for i in idx]
        by = [ys[i] for i in idx]
        try:
            s, c = fn(bx, by)
        except Exception:
            continue
        if s is None or math.isnan(s) or math.isinf(s):
            continue
        slopes.append(s)
        ints.append(c)
    if len(slopes) < 20:
        return None
    slopes.sort()
    ints.sort()
    k_lo = int((alpha / 2) * (len(slopes) - 1))
    k_hi = int((1 - alpha / 2) * (len(slopes) - 1))
    return {
        "slope_ci": (round(slopes[k_lo], 6), round(slopes[k_hi], 6)),
        "intercept_ci": (round(ints[k_lo], 6), round(ints[k_hi], 6)),
        "slope": round(median(slopes), 6),
        "intercept": round(median(ints), 6),
    }


def _reg_model(fn, xs, ys, ci):
    slope, intercept = fn(xs, ys)
    return {
        "slope": round(slope, 6),
        "intercept": round(intercept, 6),
        "equation": f"y = {intercept:.6g} + {slope:.6g} x",
        "slope_ci": list(ci["slope_ci"]) if ci else None,
        "intercept_ci": list(ci["intercept_ci"]) if ci else None,
    }


# ─────────────────────────── Bland-Altman ───────────────────────────
def bland_altman(xs, ys):
    n = len(xs)
    ds = [ys[i] - xs[i] for i in range(n)]
    md = mean(ds)
    sd = stdev(ds) if n > 1 else 0.0
    lo, hi = md - 1.96 * sd, md + 1.96 * sd
    t = md / (sd / math.sqrt(n)) if sd > 0 else 0.0
    p = t_pvalue(t, n - 1)
    within = [abs(d) for d in ds if lo <= d <= hi]
    base = mean(xs)
    return {
        "n": n,
        "mean_diff": round(md, 6),
        "sd_diff": round(sd, 6),
        "loa_low": round(lo, 6),
        "loa_high": round(hi, 6),
        "max_abs_within": round(max(within), 6) if within else None,
        "t": round(t, 4),
        "p": round(p, 6),
        "p_text": _fmt_p(p),
        "bias_pct": round(md / base * 100, 2) if base else None,
        "consistent": bool(p >= 0.05),
    }


# ─────────────────────────── 主入口 ───────────────────────────
def _num(v):
    """把录入值转成 float；空 / 非数字返回 None。"""
    if v is None:
        return None
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip().replace(",", "")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_pairs(raw_pairs):
    """标准化样本对：只保留两侧都有数值的行。"""
    out, skipped = [], []
    for p in raw_pairs or []:
        x, y = _num(p.get("a")), _num(p.get("b"))
        no = p.get("no")
        if x is None or y is None:
            skipped.append(no)
            continue
        out.append({"no": no, "a": x, "b": y})
    return out, skipped


def compute_method_comparison(data: dict) -> dict:
    """核心计算。data 需含 pairs / tea / sample_count 等字段。

    返回 {"result_summary": {...}, "details": {...}}，可直接落库与喂给报告生成器。
    """
    pairs_all, skipped = parse_pairs(data.get("pairs"))
    x_all = [p["a"] for p in pairs_all]
    y_all = [p["b"] for p in pairs_all]

    if len(pairs_all) < 3:
        return {
            "result_summary": {"valid": False, "message": "有效样本对不足 3 例，无法计算"},
            "details": {},
        }

    esd = esd_check(x_all, y_all)
    removed = set(esd["removed_nos"])
    pairs = [p for p in pairs_all if p["no"] not in removed]
    xs = [p["a"] for p in pairs]
    ys = [p["b"] for p in pairs]
    n = len(pairs)
    if n < 3:
        return {
            "result_summary": {"valid": False, "message": "剔除离群值后样本不足 3 例"},
            "details": {"esd": esd},
        }

    tea = _num(data.get("tea"))
    tea_half = tea / 2.0 if tea else None

    ci_deming = _bootstrap_ci(deming_xy, xs, ys)
    ci_pb = _bootstrap_ci(pb_xy, xs, ys)
    deming = _reg_model(deming_xy, xs, ys, ci_deming)
    pb = _reg_model(pb_xy, xs, ys, ci_pb)
    pr = pearson(xs, ys)
    ba = bland_altman(xs, ys)

    # 偏移判定
    def _prop_bias(model):
        ci = model.get("slope_ci")
        if not ci:
            return {"exists": None, "pct": None, "text": "无法判定"}
        exists = not (ci[0] <= 1.0 <= ci[1])
        pct = (model["slope"] - 1.0) * 100
        if exists:
            direction = "高" if pct > 0 else "低"
            return {"exists": True, "pct": round(pct, 2),
                    "text": f"存在（{direction}约{abs(pct):.0f}%）"}
        return {"exists": False, "pct": round(pct, 2), "text": "不存在"}

    def _sys_bias(model):
        ci = model.get("intercept_ci")
        if not ci:
            return {"exists": None, "text": "无法判定"}
        exists = not (ci[0] <= 0.0 <= ci[1])
        return {"exists": exists,
                "text": f"存在（{model['intercept']:.4g}）" if exists else "不存在"}

    deming_prop, deming_sys = _prop_bias(deming), _sys_bias(deming)
    pb_prop, pb_sys = _prop_bias(pb), _sys_bias(pb)

    # 可接受性：平均偏倚（BA）与比例偏移联合判定，阈值 1/2 TEa
    judged = []
    if tea_half is not None:
        if ba.get("bias_pct") is not None:
            judged.append(abs(ba["bias_pct"]) <= tea_half)
        if pb_prop.get("pct") is not None:
            judged.append(abs(pb_prop["pct"]) <= tea_half)
    acceptable = all(judged) if judged else None

    can_replace = (ba["consistent"] and acceptable is not False) if acceptable is not None \
        else ba["consistent"]

    # 结论文本（对齐参考报告三段式）
    project = data.get("project_name") or "该项目"
    ref_name = data.get("ref_instrument") or "方法A"
    test_name = data.get("test_instrument") or "方法B"
    concl = []
    if pb_prop.get("exists"):
        direction = "高" if (pb_prop.get("pct") or 0) > 0 else "低"
        concl.append(
            f"{ref_name}和{test_name}两种方法对{project}的检测在统计学上存在比例偏移"
            f"（{test_name}结果比{ref_name}{direction}约{abs(pb_prop['pct']):.0f}%）。"
        )
    elif deming_sys.get("exists"):
        concl.append(f"{ref_name}和{test_name}两种方法对{project}的检测在统计学上存在系统偏移。")
    else:
        concl.append(f"{ref_name}和{test_name}两种方法对{project}的检测未发现明显系统偏移或比例偏移。")

    concl.append(
        f"两种方法对{project}的检测在统计学上{'不一致' if not ba['consistent'] else '一致'}"
        f"（Bland-Altman，P{ba['p_text']}）。"
    )

    if can_replace:
        concl.append(f"两种方法对{project}的检测在临床上可直接替代使用。")
    else:
        tail = "如必须替代，则需告知两种方法检测方法间的结果偏移程度"
        rl, rh = data.get("ref_range_low"), data.get("ref_range_high")
        tl, th = data.get("test_range_low"), data.get("test_range_high")
        if all([rl, rh, tl, th]):
            tail += f"，且涉及参考值变更（{test_name} {tl}-{th}；{ref_name} {rl}-{rh}）"
        concl.append(f"两种方法对{project}的检测在临床上不可直接替代使用。{tail}。")

    per_sample = []
    for p in pairs:
        d = p["b"] - p["a"]
        per_sample.append({
            "no": p["no"], "a": p["a"], "b": p["b"],
            "diff": round(d, 6),
            "rel_pct": round(d / p["a"] * 100, 2) if p["a"] else None,
        })

    me = {
        "project_name": project,
        "ref_instrument": ref_name,
        "test_instrument": test_name,
        "unit": data.get("unit") or "",
        "tea": tea,
        "sample_count_planned": data.get("sample_count"),
        "n_input": len(pairs_all),
        "n_used": n,
        "skipped_nos": skipped,
        "esd": esd,
        "deming": deming, "pb": pb, "pearson": pr, "ba": ba,
        "deming_prop": deming_prop, "deming_sys": deming_sys,
        "pb_prop": pb_prop, "pb_sys": pb_sys,
        "acceptable": acceptable,
        "can_replace": can_replace,
        "conclusion_lines": concl,
        "per_sample": per_sample,
    }

    result_summary = {
        "valid": True,
        "project_name": project,
        "n_input": len(pairs_all),
        "n_used": n,
        "outliers": esd["removed_nos"],
        "outlier_text": (
            f"最初{len(pairs_all)}份样本中包含{len(esd['removed_nos'])}个离群值"
            + (f"（第{'、'.join(str(v) for v in esd['removed_nos'])}号）" if esd["removed_nos"] else "")
            + ("，剔除后补充样本再分析，未发现离群值点。" if esd["removed_nos"] else "，未发现离群值点。")
        ),
        "slope": pb["slope"],
        "intercept": pb["intercept"],
        "proportional_bias_pct": pb_prop.get("pct"),
        "systematic_bias": pb_sys.get("text"),
        "pearson_r": round(pr["r"], 4) if pr else None,
        "ba_p": ba["p_text"],
        "ba_consistent": ba["consistent"],
        "ba_max_abs_within": ba["max_abs_within"],
        "bias_pct": ba["bias_pct"],
        "acceptable": acceptable,
        "can_replace": can_replace,
        "conclusion": "\n".join(concl),
        "conclusion_lines": concl,
    }
    return {"result_summary": result_summary, "details": me}


# ─────────────────────────── 定性项目（符合率 / Kappa） ───────────────────────────
_POS = {"阳性", "阳", "+", "++", "+++", "1", "pos", "positive", "reactive", "有反应", "检出"}
_NEG = {"阴性", "阴", "-", "0", "neg", "negative", "non-reactive", "nonreactive", "无反应", "未检出"}


def _norm_qual(v):
    if v is None:
        return None
    s = str(v).strip().lower().replace("＋", "+").replace("－", "-")
    if not s:
        return None
    if s in _POS:
        return "阳"
    if s in _NEG:
        return "阴"
    # 兼容 "阳性(+)" "阴性(-)" 之类写法
    if s.startswith("阳") or s in ("p", "+"):
        return "阳"
    if s.startswith("阴") or s in ("n", "-"):
        return "阴"
    return None


def _wilson(k, n, z=1.96):
    """Wilson 95% 置信区间。"""
    if n == 0:
        return (None, None)
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half) * 100, min(1.0, center + half) * 100)


def parse_qual_pairs(raw_pairs):
    out, skipped = [], []
    for p in raw_pairs or []:
        a, b = _norm_qual(p.get("a")), _norm_qual(p.get("b"))
        no = p.get("no")
        if a is None or b is None:
            skipped.append(no)
            continue
        out.append({"no": no, "a": a, "b": b})
    return out, skipped


def compute_qualitative_comparison(data: dict) -> dict:
    """定性项目方法学比对：2×2 列联表 + 阳性/阴性符合率 + 总符合率 + Kappa。"""
    pairs_all, skipped = parse_qual_pairs(data.get("pairs"))
    if len(pairs_all) < 3:
        return {
            "result_summary": {"valid": False, "compare_type": "qualitative",
                               "message": "有效样本对不足 3 例，无法计算"},
            "details": {},
        }

    tp = sum(1 for p in pairs_all if p["a"] == "阳" and p["b"] == "阳")
    fn = sum(1 for p in pairs_all if p["a"] == "阳" and p["b"] == "阴")
    fp = sum(1 for p in pairs_all if p["a"] == "阴" and p["b"] == "阳")
    tn = sum(1 for p in pairs_all if p["a"] == "阴" and p["b"] == "阴")
    n = tp + fn + fp + tn
    if n < 3:
        return {
            "result_summary": {"valid": False, "compare_type": "qualitative",
                               "message": "有效样本对不足 3 例，无法计算"},
            "details": {},
        }

    ppa = tp / (tp + fn) * 100 if (tp + fn) else None      # 阳性符合率
    npa = tn / (tn + fp) * 100 if (tn + fp) else None      # 阴性符合率
    total = (tp + tn) / n * 100                            # 总符合率
    ppa_ci = _wilson(tp, tp + fn)
    npa_ci = _wilson(tn, tn + fp)

    # Cohen's Kappa
    po = (tp + tn) / n
    pe = ((tp + fp) * (tp + fn) + (fn + tn) * (fp + tn)) / (n * n)
    kappa = (po - pe) / (1 - pe) if abs(1 - pe) > 1e-12 else 0.0
    if kappa >= 0.8:
        kappa_txt = "几乎完全一致"
    elif kappa >= 0.6:
        kappa_txt = "高度一致"
    elif kappa >= 0.4:
        kappa_txt = "中度一致"
    else:
        kappa_txt = "一致性较差"

    # 判定标准（默认，可在报告中注明）：总符合率 ≥90% 且 Kappa ≥0.75 视为可接受
    acceptable = bool(total >= 90.0 and kappa >= 0.75)

    project = data.get("project_name") or "该项目"
    ref_name = data.get("ref_instrument") or "方法A"
    test_name = data.get("test_instrument") or "方法B"

    concl = [
        f"{ref_name}和{test_name}两种方法对{project}的检测：阳性符合率 "
        f"{ppa:.1f}%（{tp}/{tp + fn}），阴性符合率 {npa:.1f}%（{tn}/{tn + fp}），"
        f"总符合率 {total:.1f}%（{tp + tn}/{n}）。" if ppa is not None and npa is not None
        else f"{ref_name}和{test_name}两种方法对{project}的检测：总符合率 {total:.1f}%（{tp + tn}/{n}）。",
        f"Kappa 值 {kappa:.3f}，一致性强度判定为{kappa_txt}。",
    ]
    if acceptable:
        concl.append(f"两种方法对{project}的检测结果一致性满足要求，临床上可考虑替代使用。")
    else:
        concl.append(
            f"两种方法对{project}的检测结果一致性未达判定标准（总符合率≥90% 且 Kappa≥0.75），"
            f"临床上不可直接替代使用；如必须替代，需评估不一致样本的临床影响并告知临床。"
        )

    inconsistent = [{"no": p["no"], "a": p["a"], "b": p["b"]}
                    for p in pairs_all if p["a"] != p["b"]]

    me = {
        "compare_type": "qualitative",
        "project_name": project, "ref_instrument": ref_name, "test_instrument": test_name,
        "sample_count_planned": data.get("sample_count"),
        "n_input": len(pairs_all), "n_used": n, "skipped_nos": skipped,
        "table": {"tp": tp, "fn": fn, "fp": fp, "tn": tn},
        "ppa": ppa, "ppa_ci": ppa_ci, "npa": npa, "npa_ci": npa_ci,
        "total_rate": total, "kappa": kappa,
        "acceptable": acceptable, "can_replace": acceptable,
        "conclusion_lines": concl, "inconsistent": inconsistent,
        "per_sample": [{"no": p["no"], "a": p["a"], "b": p["b"],
                        "same": p["a"] == p["b"]} for p in pairs_all],
    }
    rs = {
        "valid": True, "compare_type": "qualitative", "project_name": project,
        "n_input": len(pairs_all), "n_used": n, "skipped_nos": skipped,
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "ppa": round(ppa, 2) if ppa is not None else None,
        "npa": round(npa, 2) if npa is not None else None,
        "total_rate": round(total, 2),
        "kappa": round(kappa, 4),
        "kappa_text": kappa_txt,
        "acceptable": acceptable, "can_replace": acceptable,
        "inconsistent_count": len(inconsistent),
        "outliers": [],
        "conclusion": "\n".join(concl), "conclusion_lines": concl,
    }
    return {"result_summary": rs, "details": me}


def compute_comparison(data: dict) -> dict:
    """按 compare_type 分派：quantitative（默认）/ qualitative。"""
    if (data.get("compare_type") or "quantitative") == "qualitative":
        return compute_qualitative_comparison(data)
    out = compute_method_comparison(data)
    out["result_summary"].setdefault("compare_type", "quantitative")
    return out
