"""室内质控计算服务：Westgard 多规则失控判定、聚合统计、质量目标查询。

Westgard 多规则判定（检验科常见简化：对同一项目、同一仪器、同年月、同批号下
所有水平的每日测值应用规则）。命中以下任一规则即判为失控点：
  1-3s : 单点超出 ±3s
  2-2s : 连续两点同侧超出 ±2s
  R-4s : 相邻两测值差值 > 4s（跨水平、跨天均算）
  10-x : 连续十点同侧（均值同侧）
1-2s 仅作警示（warning）、不计入失控；R-4s 触发时较晚点判失控、较早点判警告。

R-4s 判定说明（按 2026-07-24 需求）：把同一项目全部水平的每日测值按
(date, level) 排成一条时间线，任意「相邻两点」——无论同一天不同水平、还是
跨天同水平/不同水平——都参与 R-4s 判定；|前点 - 后点| > 4×max(前sd, 后sd)
即触发，后点判失控(R-4s)、前点判警告(R-4s)。该判定仅依赖原始测值、互不级联。
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
                if not rc:
                    continue
                # 精确匹配括号代码（如 HBsAg）；并兼容「qHBsAg ⊃ HBsAG」「HCVAb ⊃ HCV」
                # 这类别名写法/大小写差异（LIS 简称经 find_test_item_by_name 命中定量项时别名不含 HBsAg）
                hit = rc in ti_codes
                if not hit:
                    for w in ti_codes:
                        if rc in w or w in rc:
                            hit = True
                            break
                if hit:
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


def evaluate_westgard(values: list[float], mean: float, sd: float):
    """单水平 Westgard 失控规则：1-3s / 2-2s / 10-x。

    1-2s 作为「警告（warning）」单独返回，不计入失控；R-4s 为跨水平规则
    （同一天两个不同水平之差），不在此处理（见 evaluate_r4s_run / aggregate_project）。

    返回 (ooc, warnings)：
      ooc:      {idx: "1-3s"/"2-2s"/"10-x" 串}  失控点
      warnings: {idx: "1-2s"}                   超出 ±2SD 但未超 ±3SD 且未被判失控的点
    """
    ooc: dict[int, str] = {}
    warnings: dict[int, str] = {}
    n = len(values)
    if n == 0 or sd <= 0:
        return ooc, warnings
    # 浮点容差：判定「超过」阈值时使用，避免恰好等于阈值（如相邻差恰好 = 4sd）被误判为失控。
    eps = 1e-9 * (abs(mean) + abs(sd) + 1)
    # 1-3s（同时标记 1-2s 警告：超出 ±2SD 但未超出 ±3SD）
    for i, v in enumerate(values):
        if v > mean + 3 * sd + eps or v < mean - 3 * sd - eps:
            ooc[i] = _join(ooc.get(i, ""), "1-3s")
        elif v > mean + 2 * sd + eps or v < mean - 2 * sd - eps:
            warnings[i] = "1-2s"
    # 2-2s
    for i in range(n - 1):
        a, b = values[i], values[i + 1]
        if (a > mean + 2 * sd + eps and b > mean + 2 * sd + eps) or (a < mean - 2 * sd - eps and b < mean - 2 * sd - eps):
            ooc[i] = _join(ooc.get(i, ""), "2-2s")
            ooc[i + 1] = _join(ooc.get(i + 1, ""), "2-2s")
    # 4-1s 已禁用
    # 10-x
    for i in range(n - 9):
        w = values[i : i + 10]
        if all(v > mean for v in w) or all(v < mean for v in w):
            for j in range(i, i + 10):
                ooc[j] = _join(ooc.get(j, ""), "10-x")
    # 已被判失控的点不再单独标 1-2s 警告（避免警告与失控重复）
    for k in list(warnings):
        if k in ooc:
            del warnings[k]
    return ooc, warnings


def evaluate_r4s_project(points: list[dict]) -> tuple[dict, dict]:
    """跨「项目(同仪器/年/月/批号)」全部水平、按时间排序的相邻两测值 R-4s 判定。

    points: list of {level, idx, value, sd, date}
      level: 水平标识；idx: 该水平 values 中的下标；value: 测值；
      sd:    该水平的靶值 SD（缺失/<=0 不参与）；date: qc_date 字符串（ISO，可排序）。
    返回 (ooc_add, warn_add)：
      ooc_add:  {(level, idx): "R-4s"}  触发 R-4s 的『后一点』（时间上较晚者）→ 判失控；
      warn_add: {(level, idx): "R-4s"}  触发 R-4s 的『前一点』（时间上较早者）→ 判警告（不计入失控）。

    规则（按 2026-07-24 需求）：
      - 把同一项目所有水平的每日测值按 (date, level) 排成一条时间线；
      - 任意『相邻两点』（无论同一天不同水平、还是跨天同/不同水平）都判 R-4s；
      - |前点 - 后点| > 4 × max(前sd, 后sd) 即触发；
      - 触发时：后点判失控(R-4s)、前点判警告(R-4s)；前点若已因其它规则失控则保持失控、不再改判警告。
    该判定仅依赖原始测值，互不级联（不会因前点已失控而把后点连带误判）。
    """
    # 按 (date, level) 稳定排序，保留原始 (level, idx) 用于回写
    pts = sorted(points, key=lambda p: (p["date"], str(p["level"])))
    ooc_add: dict = {}
    warn_add: dict = {}
    m = len(pts)
    for i in range(m - 1):
        prev, curr = pts[i], pts[i + 1]
        sdi, sdj = prev["sd"], curr["sd"]
        if sdi <= 0 or sdj <= 0:
            continue
        thr = 4 * max(sdi, sdj)
        eps = 1e-9 * (abs(prev["value"]) + abs(curr["value"]) + 1)
        if abs(prev["value"] - curr["value"]) > thr + eps:
            ooc_add[(curr["level"], curr["idx"])] = "R-4s"
            # 前点：若已因本轮（作为更早 pair 的后点）判失控则保持失控；否则标警告
            if (prev["level"], prev["idx"]) not in ooc_add:
                warn_add[(prev["level"], prev["idx"])] = "R-4s"
    return ooc_add, warn_add


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


def aggregate_project(levels: list[dict]):
    """跨水平 Westgard 聚合（同一项目、同一仪器、同年月下多个水平的月结）。

    levels: list of dict {level, values, dates, target_mean, target_sd}
      values: 按日期排序的每日测值；dates: 与 values 同序的 qc_date 字符串（用于跨水平按天分组）；
      target_mean/target_sd: 靶值/靶SD，可为 0（缺失→本水平稳健估计）。
    返回 {level: {mean, sd, cv, n, ooc, warnings, out_of_control_count, in_control_rate,
                  all_mean, all_sd, all_cv}}。

    规则：
      - 单水平：1-3s / 2-2s / 10-x（失控），1-2s（警告，不计入失控）；
      - 跨水平 R-4s：把本项目全部水平的每日测值按 (date, level) 排成时间线，
        任意相邻两点（同天不同水平、跨天同/不同水平）之差 > 4×max(sd_i, sd_j)
        → 后点判失控(R-4s)、前点判警告(R-4s)；
      - 统计量在剔除失控点（含 R-4s）后计算。
    """
    from collections import defaultdict

    if not levels:
        return {}

    per = {}
    # 1) 单水平规则（1-3s / 2-2s / 10-x / 1-2s 警告）
    for lv in levels:
        values = lv["values"]
        tm, ts = lv["target_mean"], lv["target_sd"]
        if tm and ts:
            em, es = tm, ts
        else:
            em, es = _robust_stats(values)
        ooc, warnings = evaluate_westgard(values, em, es)
        r4s_sd = ts if ts else es  # 跨水平 R-4s 用靶SD（缺失则用稳健估计 SD）
        per[lv["level"]] = {
            "values": values, "dates": lv["dates"],
            "ooc": ooc, "warnings": warnings, "r4s_sd": r4s_sd,
        }

    # 2) 跨水平 R-4s：把全部水平的每日测值按 (date, level) 排成一条时间线，
    #    任意「相邻两点」都参与 R-4s 判定（同天不同水平 或 跨天同/不同水平）。
    all_points = []
    for lv in levels:
        p = per[lv["level"]]
        for idx, (v, d) in enumerate(zip(p["values"], p["dates"])):
            all_points.append({
                "level": lv["level"], "idx": idx,
                "value": v, "sd": p["r4s_sd"], "date": d,
            })
    ooc_add, warn_add = evaluate_r4s_project(all_points)
    for (level, idx), rule in ooc_add.items():
        po = per[level]["ooc"]
        po[idx] = _join(po.get(idx, ""), rule)
    for (level, idx), rule in warn_add.items():
        # 前点若已因其它规则失控则保持失控，不再改判警告
        if idx in per[level]["ooc"]:
            continue
        pw = per[level]["warnings"]
        pw[idx] = _join(pw.get(idx, ""), rule)

    # 3) 统计量（剔除失控点后）
    result = {}
    for lv in levels:
        p = per[lv["level"]]
        values = p["values"]
        ooc = p["ooc"]
        n = len(values)
        if n == 0:
            result[lv["level"]] = {
                "mean": 0.0, "sd": 0.0, "cv": 0.0, "n": 0,
                "all_mean": 0.0, "all_sd": 0.0, "all_cv": 0.0,
                "out_of_control_count": 0, "in_control_rate": 0.0,
                "ooc": {}, "warnings": {},
            }
            continue
        mean = sum(values) / n
        sd = statistics.stdev(values) if n > 1 else 0.0
        cv = (sd / mean * 100) if mean else 0.0
        in_control = [v for i, v in enumerate(values) if i not in ooc]
        if in_control:
            ic_mean = sum(in_control) / len(in_control)
            ic_sd = statistics.stdev(in_control) if len(in_control) > 1 else 0.0
            ic_cv = (ic_sd / ic_mean * 100) if ic_mean else 0.0
        else:
            ic_mean, ic_sd, ic_cv = mean, sd, cv
        result[lv["level"]] = {
            "mean": ic_mean, "sd": ic_sd, "cv": ic_cv, "n": n,
            "all_mean": mean, "all_sd": sd, "all_cv": cv,
            "out_of_control_count": len(ooc), "in_control_rate": (n - len(ooc)) / n if n else 0.0,
            "ooc": ooc, "warnings": p["warnings"],
        }
    return result


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
