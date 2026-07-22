"""室内质控计算服务：Westgard 多规则失控判定、聚合统计、质量目标查询。

Westgard 在「按日期排序的每日测值序列」上做多规则判定（检验科常见简化：
对同一水平(level)的一条时间序列应用规则）。命中以下任一规则即判为失控点：
  1-3s : 单点超出 ±3s
  2-2s : 连续两点同侧超出 ±2s
  R-4s : 连续两点差值 > 4s
  10-x : 连续十点同侧（均值同侧）
1-2s 仅作警示、不计入失控（如需可在此扩展）。
"""
import json
import re
import statistics
from pathlib import Path

from sqlalchemy.orm import Session

from ..models.test_item import TestItem
from ..models.quality_requirement import QualityRequirement

_QUALITY_GOALS_PATH = Path(__file__).resolve().parent.parent / "data" / "qc_quality_goals.json"
_goals_cache: dict | None = None


def _norm(s: str) -> str:
    """归一化字符串：去除空格、统一括号，用于中文匹配。"""
    return (s or "").strip().replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "").lower()


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


def _alias_words(aliases: str) -> set[str]:
    """从 aliases 字段中拆出所有候选词（逗号/空格/斜杠分隔）。"""
    words = set()
    raw = (aliases or "").replace("，", ",")
    for seg in re.split(r"[,，/\\/\s]+", raw):
        seg = seg.strip()
        if seg:
            words.add(seg)
            words.add(_norm(seg))
    return words


def find_test_item_by_name(db: Session, name: str, instrument: str = "") -> TestItem | None:
    """按项目名或别名匹配 test_items 表；返回最相似的一条或 None。

    若提供 instrument，则优先在该仪器（含 instrument_group）名下做过的项目中匹配，
    以利用「仪器档案的检验项目」来对应质控项目——同名项目跨仪器时定位更精准，
    取到的规范名/别名也更贴近该仪器实际使用的项目叫法。
    """
    if not name:
        return None
    norm = _norm(name)
    inst_norm = _norm(instrument or "")
    rows = db.query(TestItem).all()

    def _matches(r: TestItem) -> bool:
        rn = _norm(r.name)
        if rn == norm:
            return True
        if norm in rn or rn in norm:
            return True
        for w in _alias_words(r.aliases or ""):
            if w == norm or norm in w or w in norm:
                return True
        for seg in re.split(r"[\s+]", name.strip()):
            sn = _norm(seg)
            if sn and (sn in rn or rn in sn):
                return True
        return False

    # 优先：本仪器（含 instrument_group）名下的项目
    if inst_norm:
        for r in rows:
            ri = _norm(r.instrument or "")
            rg = _norm(r.instrument_group or "")
            if (ri and (ri == inst_norm or inst_norm in ri or ri in inst_norm)) or \
               (rg and (rg == inst_norm or inst_norm in rg or rg in inst_norm)):
                if _matches(r):
                    return r
    # 兜底：全局匹配（与原逻辑一致）
    for r in rows:
        if _matches(r):
            return r
    return None


def _paren_code(name: str) -> str:
    """提取名称中括号里的代码，如「乙肝病毒表面抗原(HBsAg)」→「HBsAG」。
    用于按仪器档案检验项目的别名/代码去对应质量目标条目。"""
    if not name:
        return ""
    m = re.search(r"\(([^()]+)\)", name)
    return m.group(1).strip().upper() if m else ""


def _extract_first_pct(s: str) -> float | None:
    """从字符串中提取第一个百分比数值。
    支持 "2.5%", "靶值 ±20% 或 ±5μg/L", "正常6.5%/异常10.0%" 等。
    返回 float（如 2.5, 20），提取失败返回 None。
    """
    if not s:
        return None
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1))
    return None


def _lookup_qr_goal(db: Session, test_item: str, aliases: str) -> str | None:
    """从 QualityRequirement 表中按项目名查找质量目标。

    优先级：wst403-2024.cv > bj-hr-2025.cv > nccl-2026.tea/3。
    匹配策略：精确匹配 > 子串含（主名或别名中有一段）。
    """
    from .comparison_report import WST403_2024

    def _match(items, source: str, field: str):
        """在 items 中匹配第一条非空的目标字段值。"""
        for r in items:
            if r.source == source:
                val = getattr(r, field, None)
                if val and str(val).strip() not in ("", "/"):
                    return str(val).strip()
        return None

    def _all(name: str) -> list:
        """查询指定名称的所有 quality_requirements 记录。"""
        from .quality_requirements_seed import contains_same_item
        all_qr = db.query(QualityRequirement).all()
        # 精确匹配
        rows = [r for r in all_qr if r.item_name == name]
        # 安全包含匹配（双向），避免「钙」误入「降钙素原」等短字/前缀误匹配
        if not rows:
            rows = [r for r in all_qr if r.item_name and contains_same_item(name, r.item_name)]
        # 再试别名中的每个词（同样用安全包含）
        if not rows:
            for a in (aliases or "").replace("，", ",").split(","):
                a = a.strip()
                if not a:
                    continue
                rows = [r for r in all_qr if r.item_name and contains_same_item(a, r.item_name)]
                if rows:
                    break
        # 用「仪器档案检验项目」的别名/代码匹配质量目标条目的括号代码（如 HBsAg / HCV / HIV）。
        # 即按本仪器实际做过的项目去对应质控项目；定性标志物（如 HBsAg）原先仅存定性 tea，
        # 其规范名带括号代码，用此路径即可命中（前提：条目已补 cv）。
        if not rows:
            ti_codes = {(name or "").strip().upper()}
            for w in _alias_words(aliases or ""):
                if w:
                    ti_codes.add(w.upper())
            for r in all_qr:
                rc = _paren_code(r.item_name)
                if rc and rc in ti_codes:
                    rows.append(r)
                    break
        return rows or []

    items = _all(test_item)
    if not items:
        return None

    # 1) wst403-2024.cv
    v = _match(items, "wst403-2024", "cv")
    if v:
        pct = _extract_first_pct(v)
        if pct is not None:
            return f"{pct:g}%"

    # 2) bj-hr-2025.cv
    v = _match(items, "bj-hr-2025", "cv")
    if v:
        pct = _extract_first_pct(v)
        if pct is not None:
            return f"{pct:g}%"

    # 3) nccl-2026.tea/3
    v = _match(items, "nccl-2026", "tea")
    if v:
        pct = _extract_first_pct(v)
        if pct is not None:
            return f"{pct / 3:.1f}%"

    # 4) 尝试 WST403_2024 TE/3（通过别名匹配英文代码）
    for a in (aliases or "").replace("，", ",").split(","):
        a = a.strip().upper()
        if a and a in WST403_2024:
            te = WST403_2024[a]
            if isinstance(te, tuple):
                te_val, mode = te
            else:
                te_val, mode = te, "relative"
            if mode == "relative":
                return f"{te_val / 3:.1f}%"

    return None


def lookup_quality_goal(test_item: str, aliases: str = "", db: Session = None) -> str:
    """按项目名/别名查允许不精密度（质量目标）。

    优先级：
    1. quality_requirements 表：wst403-2024.cv > bj-hr-2025.cv > nccl-2026.tea/3
    2. 原有 qc_quality_goals.json 精确/子串匹配（保留兼容）
    3. WST403_2024 TE 字典 / 3
    4. 默认 "10%"
    """
    if not test_item:
        return ""

    # Step 1: QualityRequirement 表查询
    if db is not None:
        try:
            qr_goal = _lookup_qr_goal(db, test_item, aliases)
            if qr_goal:
                return qr_goal
        except Exception:
            pass  # QR 表查询失败不影响主流程，回退到 JSON 文件

    # Step 2: 原有 JSON 文件匹配（保留兼容）
    goals = _load_goals()
    keys = {test_item}
    for a in (aliases or "").replace("，", ",").split(","):
        a = a.strip()
        if a:
            keys.add(a)
    # 精确匹配
    for k in keys:
        if k in goals:
            return _fmt(goals[k])
    # 子串匹配
    candidates = []
    for k in keys:
        for name, val in goals.items():
            if name and (k in name or name in k):
                candidates.append((name, _fmt(val)))
    if candidates:
        non_empty = [c for c in candidates if c[1] not in ("", "/")]
        pool = non_empty if non_empty else candidates
        pool.sort(key=lambda c: len(c[0]))
        return pool[0][1]

    # Step 3: WST403_2024 TE/3（兜底，通过别名匹配英文代码）
    try:
        from .comparison_report import WST403_2024
        for a in (aliases or "").replace("，", ",").split(","):
            a = a.strip().upper()
            if a and a in WST403_2024:
                te = WST403_2024[a]
                if isinstance(te, tuple):
                    te_val, mode = te
                else:
                    te_val, mode = te, "relative"
                if mode == "relative":
                    return f"{te_val / 3:.1f}%"
    except ImportError:
        pass

    # Step 4: 默认 "10%"
    return "10%"


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
    # 浮点容差：判定「超过」阈值时使用，避免恰好等于阈值（如相邻差恰好 = 4sd）被误判为失控。
    eps = 1e-9 * (abs(mean) + abs(sd) + 1)
    # 1-3s
    for i, v in enumerate(values):
        if v > mean + 3 * sd + eps or v < mean - 3 * sd - eps:
            ooc[i] = _join(ooc.get(i, ""), "1-3s")
    # 2-2s
    for i in range(n - 1):
        a, b = values[i], values[i + 1]
        if (a > mean + 2 * sd + eps and b > mean + 2 * sd + eps) or (a < mean - 2 * sd - eps and b < mean - 2 * sd - eps):
            ooc[i] = _join(ooc.get(i, ""), "2-2s")
            ooc[i + 1] = _join(ooc.get(i + 1, ""), "2-2s")
    # R-4s：失控点本身不参与相邻判定（避免已判失控的点级联误判其前后点也 R-4s）。
    # 即：仅当两个相邻点都尚未被 1-3s / 2-2s / 10-x 等规则判为失控时，才用二者差值判 R-4s。
    base_ooc = set(ooc.keys())
    for i in range(n - 1):
        if i in base_ooc or i + 1 in base_ooc:
            continue
        if abs(values[i] - values[i + 1]) > 4 * sd + eps:
            ooc[i] = _join(ooc.get(i, ""), "R-4s")
            ooc[i + 1] = _join(ooc.get(i + 1, ""), "R-4s")
    # 4-1s 已禁用
    # 10-x
    for i in range(n - 9):
        w = values[i : i + 10]
        if all(v > mean for v in w) or all(v < mean for v in w):
            for j in range(i, i + 10):
                ooc[j] = _join(ooc.get(j, ""), "10-x")
    return ooc


def _robust_stats(values: list[float]):
    """靶值缺失时估计均值/SD：用中位数 + MAD（对极端值稳健）迭代剔除外点，避免失控点抬高 SD 而漏判。

    返回的 (mean, sd) 用于 Westgard 判定；被剔除的极端点在 aggregate 中进一步从统计量中排除。
    """
    vals = list(values)
    for _ in range(4):
        if len(vals) < 3:
            break
        med = statistics.median(vals)
        mad = statistics.median([abs(v - med) for v in vals]) or 0.0
        if mad <= 0:
            # 无离散度时无法稳健估计，退回普通均值/SD
            m = sum(vals) / len(vals)
            s = statistics.stdev(vals) if len(vals) > 1 else 0.0
            return m, s
        rsd = 1.4826 * mad  # MAD → 近似正态 SD
        if rsd <= 0:
            break
        thr = 3.5 * rsd
        outs = [v for v in vals if abs(v - med) > thr]
        if not outs:
            break
        extreme = max(outs, key=lambda v: abs(v - med))
        vals = [v for v in vals if abs(v - extreme) > 1e-12]
        if len(vals) < 3:
            break
    if len(vals) < 2:
        return sum(values) / len(values), (statistics.stdev(values) if len(values) > 1 else 0.0)
    return sum(vals) / len(vals), statistics.stdev(vals)


def aggregate(values: list[float], target_mean: float, target_sd: float):
    """由每日测值聚合月结统计；target_mean/target_sd 用于 Westgard 判定。

    返回的 mean/sd/cv 为**剔除失控点后**的「在控统计量」（用户要求：导入核算须去除失控点）。
    原始全量统计量另存 all_mean/all_sd/all_cv 供追溯。Westgard 判定仍基于靶值（或缺失时本批全量），
    不受剔除影响。
    """
    n = len(values)
    if n == 0:
        return {
            "mean": 0.0, "sd": 0.0, "cv": 0.0, "n": 0,
            "all_mean": 0.0, "all_sd": 0.0, "all_cv": 0.0,
            "out_of_control_count": 0, "in_control_rate": 0.0,
            "ooc": {},
        }
    mean = sum(values) / n
    sd = statistics.stdev(values) if n > 1 else 0.0
    cv = (sd / mean * 100) if mean else 0.0
    # Westgard 判定：优先用靶值（target_mean/target_sd）；若缺失则退化为「迭代剔除极端点」后估计的
    # 均值/标准差，避免失控点抬高 SD 而漏判（不影响已带靶值的数据）。
    if target_mean and target_sd:
        eff_mean, eff_sd = target_mean, target_sd
    else:
        eff_mean, eff_sd = _robust_stats(values)
    ooc = evaluate_westgard(values, eff_mean, eff_sd)
    ooc_count = len(ooc)
    in_control_rate = (n - ooc_count) / n if n else 0.0
    # 剔除失控点后在控统计量（用户要求：均值/SD/CV 去除失控点重算）
    in_control = [v for i, v in enumerate(values) if i not in ooc]
    if in_control:
        ic_mean = sum(in_control) / len(in_control)
        ic_sd = statistics.stdev(in_control) if len(in_control) > 1 else 0.0
        ic_cv = (ic_sd / ic_mean * 100) if ic_mean else 0.0
    else:
        # 全部失控时退化为全量，避免无值
        ic_mean, ic_sd, ic_cv = mean, sd, cv
    return {
        "mean": ic_mean, "sd": ic_sd, "cv": ic_cv, "n": n,
        "all_mean": mean, "all_sd": sd, "all_cv": cv,
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
        ooc_details = []
        for dv in dvs:
            if dv.rule_violated:
                for r in str(dv.rule_violated).split(";"):
                    r = r.strip()
                    if r:
                        rules.add(r)
            if dv.is_out_of_control and (dv.violate_reason or dv.violate_deal or dv.rule_violated):
                why = (dv.violate_reason or "").strip()
                how = (dv.violate_deal or "").strip()
                rule = (dv.rule_violated or "").strip()
                seg = f"{s.test_item}({s.level}) {dv.qc_date}"
                sub = []
                if rule:
                    sub.append(f"规则：{rule}")
                if why:
                    sub.append(f"原因：{why}")
                if how:
                    sub.append(f"处理：{how}")
                ooc_details.append(seg + ("；".join(sub) if sub else ""))
        projects.append({
            "name": s.test_item, "level": s.level,
            "cv": s.cv, "target_cv": s.target_cv, "goal": goal,
            "n": s.n, "ooc": s.out_of_control_count, "rules": rules,
            "ooc_details": ooc_details,
        })
        total_ooc += s.out_of_control_count

    # 一、仪器运行情况（末尾固定追加运行维护结论，供人工在此基础上修改）
    RUN_SUFFIX = "仪器运行良好，日常维护保养按时完成，无维修。"
    if total_ooc > 0:
        all_details = [d for p in projects for d in p["ooc_details"]]
        reason_text = ("失控明细：" + "；".join(all_details) + "。") if all_details else ""
        operation_status = (
            f"本月共出现 {total_ooc} 个失控点，均按 Westgard 规则判定"
            f"{('，' + reason_text) if reason_text else ''}；处置后已恢复在控；仪器总体运行正常。"
            + RUN_SUFFIX
        )
    else:
        operation_status = "本仪器本月运行正常，各项质控在控，未出现失控。" + RUN_SUFFIX

    # 二、各项目是否出现漂移或趋势性改变
    drift_lines = []
    for p in projects:
        if p["rules"]:
            trend = any(r in ("10-x",) for r in p["rules"])
            shift = any(r in ("2-2s", "22s", "R-4s") for r in p["rules"])
            occ = any(r in ("1-3s",) for r in p["rules"])
            tags = []
            if trend:
                tags.append("趋势性改变(10-x)")
            if shift:
                tags.append("漂移/偏移(2-2s/R-4s)")
            if occ:
                tags.append("偶发失控(1-3s)")
            drift_lines.append(f"{p['name']}({p['level']})：{'、'.join(tags)}")
    drift_trend = ("；".join(drift_lines) + "。") if drift_lines else "各项目未见明显漂移或趋势性改变，质控稳定。"

    # 三、四：CV% 达标判定 —— 汇总式：只列不合格项，后接「其余项目均已达标」
    def _fmt_cv_section(projects, kind):
        """kind='set' 用设置CV%；kind='calc' 用计算CV%。

        返回汇总文字：列出不达标（及无质量目标无法判定）项，其余合并为「其余项目均已达标」。
        """
        bad = []      # 不达标项
        unknown = []  # 无质量目标，无法判定
        good = 0
        for p in projects:
            val = p["target_cv"] if kind == "set" else p["cv"]
            if p["goal"] is None:
                unknown.append(f"{p['name']}({p['level']})：无质量目标，无法判定")
                continue
            if val > p["goal"]:
                word = "设置" if kind == "set" else "计算"
                bad.append(f"{p['name']}({p['level']}) {word}CV% {val:.2f}% > 允许 {p['goal']:.2f}%，不达标")
            else:
                good += 1
        if bad or unknown:
            parts = list(bad) + unknown
            text = "；".join(parts)
            text += "；其余项目均已达标。" if good > 0 else "。"
            return text
        # 无不合格项
        if kind == "set":
            return "各项目CV%设置均达标。"
        return "各项目计算CV%均达标。"

    cv_setting_ok = _fmt_cv_section(projects, "set") if projects else "无项目数据。"
    cv_calc_ok = _fmt_cv_section(projects, "calc") if projects else "无项目数据。"

    # 五、各项目质控频次是否达标（不由系统自动判定，留空模板「是」供人工手录）
    freq_ok = "是"

    return {
        "operation_status": operation_status,
        "drift_trend": drift_trend,
        "cv_setting_ok": cv_setting_ok,
        "cv_calc_ok": cv_calc_ok,
        "freq_ok": freq_ok,
    }
