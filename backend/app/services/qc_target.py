"""批号累积靶值：即刻法 / 常规法 累计算法。

即刻法（Grubbs/Crubbs 衍生，临床实验室常用）：
- 将测定值从小到大排列，计算均值 x̄ 与标准差 s；
- SI上限 = (x_max - x̄) / s，SI下限 = (x̄ - x_min) / s；
- 按当前样本量 n 查 SI 界值表：SI 上限、下限均 < n2s → 在控；
  其一处于 (n2s, n3s] → 警告；其一 > n3s → 失控；
- 失控数据保留标记、不自动舍去（由人工决定删/留），但累计统计默认排除被标记值。
- 累计到 n=20 后转常规 ±2s/±3s 判定并确立靶值。
"""
from statistics import mean
import math

# 即刻法 SI 界值表（n=3..20）：n2s=警戒限、n3s=失控限
# 来源：临床检验室内质控资料（多来源一致）
SI_TABLE = {
    3: (1.15, 1.15),
    4: (1.46, 1.49),
    5: (1.67, 1.75),
    6: (1.82, 1.94),
    7: (1.94, 2.10),
    8: (2.03, 2.22),
    9: (2.11, 2.32),
    10: (2.20, 2.41),
    11: (2.23, 2.48),
    12: (2.29, 2.55),
    13: (2.33, 2.61),
    14: (2.37, 2.66),
    15: (2.41, 2.71),
    16: (2.44, 2.75),
    17: (2.47, 2.79),
    18: (2.50, 2.82),
    19: (2.53, 2.85),
    20: (2.56, 2.88),
}

# 确立所需最少次数（常规法暂定）与自动确立次数
CONVENTIONAL_MIN = 10
CONVENTIONAL_ESTABLISH = 20
IMMEDIATE_START = 3
IMMEDIATE_ESTABLISH = 20


def stddev(vals: list[float]) -> float:
    n = len(vals)
    if n < 2:
        return 0.0
    m = mean(vals)
    return math.sqrt(sum((x - m) ** 2 for x in vals) / (n - 1))


def classify_immediate(values: list[float]):
    """对当前在控（未标记 is_out）的测定值序列（含刚加入的值）做即刻法判定。

    返回 dict：n/mean/sd/si_upper/si_lower/n2s/n3s/status。
    n<3 时返回 status='累计中'。s=0（全部相同）按在控处理。
    """
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "si_upper": None, "si_lower": None,
                "n2s": None, "n3s": None, "status": "累计中"}
    if n < IMMEDIATE_START:
        return {"n": n, "mean": mean(values), "sd": 0.0, "si_upper": None,
                "si_lower": None, "n2s": None, "n3s": None, "status": "累计中"}
    m = mean(values)
    s = stddev(values)
    if s == 0:
        n2s, n3s = SI_TABLE.get(n, (None, None))
        return {"n": n, "mean": m, "sd": 0.0, "si_upper": 0.0, "si_lower": 0.0,
                "n2s": n2s, "n3s": n3s, "status": "在控"}
    xmax, xmin = max(values), min(values)
    si_up = (xmax - m) / s
    si_lo = (m - xmin) / s
    n2s, n3s = SI_TABLE.get(n, (None, None))
    if n2s is None:
        # n>20：转常规 ±2s/±3s 判定
        status = "在控"
    elif si_up > n3s or si_lo > n3s:
        status = "失控"
    elif si_up > n2s or si_lo > n2s:
        status = "警告"
    else:
        status = "在控"
    return {"n": n, "mean": m, "sd": s, "si_upper": round(si_up, 4),
            "si_lower": round(si_lo, 4), "n2s": n2s, "n3s": n3s, "status": status}


def classify_conventional(value: float, target_mean: float, target_sd: float):
    """常规法确立后，对新测定值按 ±2s(警告)/±3s(失控) 判定。"""
    if target_sd == 0:
        return "在控"
    z = abs(value - target_mean) / target_sd
    if z > 3:
        return "失控"
    if z > 2:
        return "警告"
    return "在控"


def compute_analyte(values: list[float], method: str, established: bool):
    """计算某个 analyte 的累计统计。

    values：该 analyte 当前「未标记 is_out」的测定值（按插入顺序）。
    返回 dict：n/mean/sd/cv/status/established/可确立。
    """
    n = len(values)
    if n == 0:
        return {"n": 0, "mean": 0.0, "sd": 0.0, "cv": 0.0, "status": "累计中",
                "established": established, "can_establish": False}
    m = mean(values)
    s = stddev(values)
    cv = round(s / m * 100, 2) if m else 0.0
    if method == "immediate":
        info = classify_immediate(values)
        status = info["status"]
        can_establish = (n >= IMMEDIATE_ESTABLISH)
        est = established or can_establish
        return {"n": n, "mean": round(m, 4), "sd": round(s, 4), "cv": cv,
                "status": status, "established": est, "can_establish": can_establish,
                "si_upper": info.get("si_upper"), "si_lower": info.get("si_lower"),
                "n2s": info.get("n2s"), "n3s": info.get("n3s")}
    else:  # conventional
        if established:
            status = "已确立"
        elif n >= CONVENTIONAL_ESTABLISH:
            status = "可确立"
        elif n >= CONVENTIONAL_MIN:
            status = "可暂定"
        else:
            status = "累计中"
        can_establish = (n >= CONVENTIONAL_MIN)
        est = established or (n >= CONVENTIONAL_ESTABLISH)
        return {"n": n, "mean": round(m, 4), "sd": round(s, 4), "cv": cv,
                "status": status, "established": est, "can_establish": can_establish}
