"""室内质控计算服务：Westgard 多规则失控判定、聚合统计、质量目标查询。

Westgard 在「按日期排序的每日测值序列」上做多规则判定（检验科常见简化：
对同一水平(level)的一条时间序列应用规则）。命中以下任一规则即判为失控点：
  1-3s : 单点超出 ±3s
  2-2s : 连续两点同侧超出 ±2s
  R-4s : 连续两点差值 > 4s
  4-1s : 连续四点同侧超出 ±1s
  10-x : 连续十点同侧（均值同侧）
1-2s 仅作警示、不计入失控（如需可在此扩展）。
"""
import json
import statistics
from pathlib import Path

_QUALITY_GOALS_PATH = Path(__file__).resolve().parent.parent / "data" / "qc_quality_goals.json"
_goals_cache: dict | None = None


def _load_goals() -> dict:
    global _goals_cache
    if _goals_cache is not None:
        return _goals_cache
    data: dict = {}
    try:
        with open(_QUALITY_GOALS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
        if isinstance(raw, list):
            for item in raw:
                name = item.get("name") or item.get("项目")
                if name:
                    data[name] = item.get("imprecision") or item.get("allowable_cv") or item.get("allowable_imprecision") or ""
        elif isinstance(raw, dict):
            for k, v in raw.items():
                data[k] = v.get("imprecision") if isinstance(v, dict) else v
    except Exception:
        data = {}
    _goals_cache = data
    return data


def lookup_quality_goal(test_item: str) -> str:
    """按项目名查允许不精密度（质量目标）。

    匹配优先级：精确 → 本项目名是某条目名的一部分（如「甲胎蛋白」命中
    「甲胎蛋白(AFP)」、「AFP」/「HCG」也命中）。同名下可能存在多条（如某条目
    注明「试验(尿液)」其允许不精密度为「/」非适用），故优先选非空（非「/」）
    的命中，避免误取无效的「/」。
    """
    if not test_item:
        return ""
    goals = _load_goals()
    if test_item in goals:
        return _fmt(goals[test_item])
    candidates = []
    for name, val in goals.items():
        if name and test_item in name:
            candidates.append((name, _fmt(val)))
    if candidates:
        # 优先选非空（非 "/"）值；同为有效值时优先名字更短（更精确）
        non_empty = [c for c in candidates if c[1] not in ("", "/")]
        pool = non_empty if non_empty else candidates
        pool.sort(key=lambda c: len(c[0]))
        return pool[0][1]
    return ""


def _fmt(v) -> str:
    if v in (None, "", "/"):
        return ""
    s = str(v).strip()
    if s.endswith("%"):
        return s
    try:
        return f"{float(s):g}%"
    except ValueError:
        return s


def _join(existing: str, rule: str) -> str:
    return (existing + ";" + rule) if existing else rule


def evaluate_westgard(values: list[float], mean: float, sd: float) -> dict[int, str]:
    """返回 {失控点索引: 触发规则(...)}。"""
    ooc: dict[int, str] = {}
    n = len(values)
    if n == 0 or sd <= 0:
        return ooc
    # 1-3s
    for i, v in enumerate(values):
        if v > mean + 3 * sd or v < mean - 3 * sd:
            ooc[i] = _join(ooc.get(i, ""), "1-3s")
    # 2-2s
    for i in range(n - 1):
        a, b = values[i], values[i + 1]
        if (a > mean + 2 * sd and b > mean + 2 * sd) or (a < mean - 2 * sd and b < mean - 2 * sd):
            ooc[i] = _join(ooc.get(i, ""), "2-2s")
            ooc[i + 1] = _join(ooc.get(i + 1, ""), "2-2s")
    # R-4s
    for i in range(n - 1):
        if abs(values[i] - values[i + 1]) > 4 * sd:
            ooc[i] = _join(ooc.get(i, ""), "R-4s")
            ooc[i + 1] = _join(ooc.get(i + 1, ""), "R-4s")
    # 4-1s
    for i in range(n - 3):
        w = values[i : i + 4]
        if all(v > mean + sd for v in w) or all(v < mean - sd for v in w):
            for j in range(i, i + 4):
                ooc[j] = _join(ooc.get(j, ""), "4-1s")
    # 10-x
    for i in range(n - 9):
        w = values[i : i + 10]
        if all(v > mean for v in w) or all(v < mean for v in w):
            for j in range(i, i + 10):
                ooc[j] = _join(ooc.get(j, ""), "10-x")
    return ooc


def aggregate(values: list[float], target_mean: float, target_sd: float):
    """由每日测值聚合月结统计；target_mean/target_sd 用于 Westgard 判定。"""
    n = len(values)
    if n == 0:
        return {
            "mean": 0.0, "sd": 0.0, "cv": 0.0, "n": 0,
            "out_of_control_count": 0, "in_control_rate": 0.0,
            "ooc": {},
        }
    mean = sum(values) / n
    sd = statistics.stdev(values) if n > 1 else 0.0
    cv = (sd / mean * 100) if mean else 0.0
    # Westgard 判定：优先用靶值（target_mean/target_sd）；若缺失则退化为本批实测
    # 均值/标准差，保证未提供靶值的导入数据也能真实判定失控（不影响已带靶值的数据）。
    if target_mean and target_sd:
        eff_mean, eff_sd = target_mean, target_sd
    else:
        eff_mean, eff_sd = mean, sd
    ooc = evaluate_westgard(values, eff_mean, eff_sd)
    ooc_count = len(ooc)
    in_control_rate = (n - ooc_count) / n if n else 0.0
    return {
        "mean": mean, "sd": sd, "cv": cv, "n": n,
        "out_of_control_count": ooc_count, "in_control_rate": in_control_rate,
        "ooc": ooc,
    }


# 月质控频次达标默认阈值（次/月）。可由检验组在文字段中改写。
DEFAULT_MONTHLY_QC_MIN = 20


def _parse_goal_pct(s):
    if not s:
        return None
    try:
        return float(str(s).replace("%", "").strip())
    except (ValueError, TypeError):
        return None


def draft_report(instrument: str, year: int, month: int, summaries: list, daily_by_summary: dict) -> dict:
    """由月结明细自动草拟 CZ-012 文字部分的五段说明。返回可直接落库的字典。

    summaries: 该 (仪器,年,月) 下的 QCMonthlySummary 行列表
    daily_by_summary: {summary_id: [QCDailyValue]}  用于判定漂移/趋势
    """
    projects = []
    total_ooc = 0
    for s in summaries:
        goal = _parse_goal_pct(s.quality_goal)
        dvs = daily_by_summary.get(s.id, []) or []
        rules = set()
        for dv in dvs:
            if dv.rule_violated:
                for r in str(dv.rule_violated).split(";"):
                    r = r.strip()
                    if r:
                        rules.add(r)
        projects.append({
            "name": s.test_item, "level": s.level,
            "cv": s.cv, "target_cv": s.target_cv, "goal": goal,
            "n": s.n, "ooc": s.out_of_control_count, "rules": rules,
        })
        total_ooc += s.out_of_control_count

    # 一、仪器运行情况
    if total_ooc > 0:
        operation_status = (
            f"本月共出现 {total_ooc} 个失控点，均按 Westgard 规则判定并处置"
            f"（详见各项目失控处理说明），处置后已恢复在控；仪器总体运行正常。"
        )
    else:
        operation_status = "本仪器本月运行正常，各项质控在控，未出现失控。"

    # 二、各项目是否出现漂移或趋势性改变
    drift_lines = []
    for p in projects:
        if p["rules"]:
            trend = any(r in ("4-1s", "10-x") for r in p["rules"])
            shift = any(r in ("2-2s", "22s", "R-4s") for r in p["rules"])
            occ = any(r in ("1-3s",) for r in p["rules"])
            tags = []
            if trend:
                tags.append("趋势性改变(4-1s/10-x)")
            if shift:
                tags.append("漂移/偏移(2-2s/R-4s)")
            if occ:
                tags.append("偶发失控(1-3s)")
            drift_lines.append(f"{p['name']}({p['level']})：{'、'.join(tags)}")
    drift_trend = ("；".join(drift_lines) + "。") if drift_lines else "各项目未见明显漂移或趋势性改变，质控稳定。"

    # 三、各项目CV%设置是否达标（靶值CV% vs 质量目标）
    cv_set_lines = []
    for p in projects:
        if p["goal"] is None:
            cv_set_lines.append(f"{p['name']}({p['level']})：无质量目标，无法判定")
        elif p["target_cv"] <= p["goal"]:
            cv_set_lines.append(f"{p['name']}({p['level']})：设置CV% {p['target_cv']:.2f}% ≤ 允许 {p['goal']:.2f}%，达标")
        else:
            cv_set_lines.append(f"{p['name']}({p['level']})：设置CV% {p['target_cv']:.2f}% > 允许 {p['goal']:.2f}%，不达标")
    cv_setting_ok = ("；".join(cv_set_lines) + "。") if cv_set_lines else "无项目数据。"

    # 四、各项目计算CV%是否达标
    cv_calc_lines = []
    for p in projects:
        if p["goal"] is None:
            cv_calc_lines.append(f"{p['name']}({p['level']})：无质量目标，无法判定")
        elif p["cv"] <= p["goal"]:
            cv_calc_lines.append(f"{p['name']}({p['level']})：计算CV% {p['cv']:.2f}% ≤ 允许 {p['goal']:.2f}%，达标")
        else:
            cv_calc_lines.append(f"{p['name']}({p['level']})：计算CV% {p['cv']:.2f}% > 允许 {p['goal']:.2f}%，不达标")
    cv_calc_ok = ("；".join(cv_calc_lines) + "。") if cv_calc_lines else "无项目数据。"

    # 五、各项目质控频次是否达标（默认 ≥ DEFAULT_MONTHLY_QC_MIN 次/月）
    freq_lines = []
    for p in projects:
        if p["n"] >= DEFAULT_MONTHLY_QC_MIN:
            freq_lines.append(f"{p['name']}({p['level']})：本月检测 {p['n']} 次 ≥ {DEFAULT_MONTHLY_QC_MIN} 次/月，达标")
        else:
            freq_lines.append(f"{p['name']}({p['level']})：本月检测 {p['n']} 次 < {DEFAULT_MONTHLY_QC_MIN} 次/月，不达标")
    freq_ok = ("；".join(freq_lines) + "。") if freq_lines else "无项目数据。"

    return {
        "operation_status": operation_status,
        "drift_trend": drift_trend,
        "cv_setting_ok": cv_setting_ok,
        "cv_calc_ok": cv_calc_ok,
        "freq_ok": freq_ok,
    }
