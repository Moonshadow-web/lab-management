"""室内质控计算服务：Westgard 多规则失控判定、聚合统计、质量目标查询。

Westgard 多规则判定（检验科常见简化：对同一项目、同一仪器、同年月、同批号下
所有水平的每日测值应用规则）。命中以下任一规则即判为失控点：
  1-3s : 单点超出 ±3s
  2-2s : 连续两点同侧超出 ±2s
  R-4s : 相邻两测值（SD 归一化后）差值 > 4s（跨水平、跨天均算；归一化后高低浓度可比）
  10-x : 连续十点同侧（均值同侧）
1-2s 仅作警示（warning）、不计入失控；警告仅由 1-2s 规则产生（R-4s 不再给前点标警告）。R-4s 触发时：同一天两水平都判失控；跨天相邻则只标后点（当天）失控，前点不标任何 R-4s 标记。

R-4s 判定说明（按 2026-07-24 需求，2026-07-22 修订同天判定，2026-07-25 修订为
SD 归一化 + 冻结）：把同一项目全部水平的每日测值按 (date, level) 排成一条时间线，
任意「相邻两点」——无论同一天不同水平、还是跨天同/不同水平——都参与 R-4s
判定；每个测值先按各自水平的靶值归一化为 z=(value-target_mean)/target_sd，
再判 |z_前 - z_后| > 4 即触发（高低浓度被拉到同一尺度，只反映偏离各自靶值的
程度，避免浓度差误报，如甲肝 IgM 水平1≠水平2）。触发规则：同一天两水平 →
两个都判失控(R-4s)；跨天相邻 → 只标后点(当天)失控(R-4s)、前点不标任何 R-4s
标记。已失控(ooc)点（含单点规则已判/本轮已判）冻结，不参与本对及后续相邻对。
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

# 精确名覆盖：少数项目的 LIS 原名会被模糊解析「截胡」到同名血清项（如半角「白蛋白(A)」
# 被解析成血清「白蛋白」2.5%，但它是糖化白蛋白 GA 的配套试剂，目标应为 6.7%；pH 的
# 实际「质量目标」按 0.02/靶值 逐水平计算，查表仅保留标记串）。这些项按原始 LIS 名
# 精确命中、优先于任何模糊匹配返回，避免被串扰。
QC_GOAL_EXACT_OVERRIDES: dict[str, str] = {
    "pH": "0.02/靶值",
    "pH（血气）": "0.02/靶值",
    "白蛋白(A)": "6.7%",
    "白蛋白（A）": "6.7%",
    "OxLDL": "6%",
    "CER": "8%",
}


def _norm(s: str) -> str:
    """归一化字符串：去除空格、统一括号，用于中文匹配。"""
    s = (s or "").strip().replace("（", "(").replace("）", ")").replace("　", " ").replace(" ", "").lower()
    # 去掉 LIS 自动/自动质控 前缀（仅当去掉后还有内容才剥离，避免空串）
    for p in ("(自动质控)", "(自动)"):
        if s.startswith(p) and len(s) > len(p):
            s = s[len(p):]
    return s


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


# ---------------- LIS 导出常用简称/缩写 → 系统规范名 ----------------
# 打通「直胆红素↔直接胆红素」「转肽酶↔γ-谷氨酰基转移酶」「GGT↔γ-谷氨酰基转移酶」
# 「谷草转氨酶↔天门冬氨酸氨基转移酶」「AST/AST↔…」「低密脂蛋白↔低密度脂蛋白胆固醇」
# 等。规范名需与 quality_requirements 种子使用的 item_name 一致，才能命中质量目标。
# 仅做「原名 → 规范名」单向桥接；已在 TestItem/QualityRequirement 中的原名不受影响。
_LIS_ITEM_ALIASES = {
    "直胆红素": "直接胆红素",
    "结合胆红素": "直接胆红素",
    "腺苷酸脱氨酶": "腺苷脱氨酶",
    "腺苷脱氨酶": "腺苷脱氨酶",
    "ada": "腺苷脱氨酶",
    "转肽酶": "γ-谷氨酰基转移酶",
    "γ-谷氨酰转移酶": "γ-谷氨酰基转移酶",
    "ggt": "γ-谷氨酰基转移酶",
    "谷草转氨酶": "天门冬氨酸氨基转移酶",
    "ast": "天门冬氨酸氨基转移酶",
    "谷丙转氨酶": "丙氨酸氨基转移酶",
    "alt": "丙氨酸氨基转移酶",
    "低密脂蛋白": "低密度脂蛋白胆固醇",
    "ldl": "低密度脂蛋白胆固醇",
    "高密脂蛋白": "高密度脂蛋白胆固醇",
    "hdl": "高密度脂蛋白胆固醇",
    # 凝血（LIS 常见标签 → test_items.name；取自线上 test_items 实际 name/别名）
    # 仅做「原名 → 规范名」单向桥接；规范名需与 test_items.name 完全一致，才能精确命中项目。
    "pt": "凝血酶原时间",
    "pt%": "凝血酶原时间",
    "inr": "凝血酶原时间",
    "inrratio": "凝血酶原时间",
    "ratio": "凝血酶原时间",
    "rat": "凝血酶原时间",
    "aptt": "活化部分凝血活酶时间",
    "tt": "凝血酶时间",
    "fib": "纤维蛋白原",
    "fdp": "纤维蛋白（原）降解产物",
    "pc": "血浆蛋白C活性",
    "蛋白c": "血浆蛋白C活性",
    "atiii": "抗凝血酶III",
    "抗凝血酶iii": "抗凝血酶III",
    "sct": "狼疮抗凝物SCT试验",
    "sct标准化比值": "狼疮抗凝物SCT试验",
    "drvvt": "狼疮抗凝物DRVVT试验",
    "d-dimer": "血浆D-二聚体",
    "d二聚体": "血浆D-二聚体",
    # 2026-07-27 用户指定 LIS 名 → 规范名映射
    "c-反应蛋白": "C反应蛋白",
    "apo-b": "载脂蛋白B",
    "apo-a": "载脂蛋白A",
    "碱磷酶": "碱性磷酸酶",
    "抗链-o": "抗链球菌溶血素 O",
    "λ轻链测定": "λ轻链（血清）",
    "κ轻链测定": "κ轻链（血清）",
    # 2026-07-27 免疫项目（去掉(自动)/(自动质控)前缀后映射）
    "tpab": "梅毒特异性抗体",
    "hcv": "丙型肝炎病毒抗体",
    "hbsag": "乙型肝炎病毒表面抗原",
    "hiv": "人类免疫缺陷病毒抗原及抗体",
    "ct": "降钙素",
    "il-6": "白介素-6",
    # 2026-07-27 血脂类
    "sdldl-c": "小而密低密度脂蛋白胆固醇",
}


def _canon_item_name(name: str) -> str:
    """把 LIS 常用简称/缩写桥接为系统规范名；无映射则返回原名。"""
    return _LIS_ITEM_ALIASES.get(_norm(name), name)


def _token_match(word_norm: str, qnorm: str) -> bool:
    """别名词与查询词的「安全」匹配：精确相等，或带词边界的子串。

    避免 "pt" 命中 "GPT"（gpt 含 pt 但非独立词）这类缩写截胡：
    仅当查询词在别名词内且前后均为非字母数字边界（或端点）时才算命中。
    """
    if not qnorm or not word_norm:
        return False
    if word_norm == qnorm:
        return True
    if qnorm in word_norm:
        i = word_norm.index(qnorm)
        before_ok = (i == 0) or (not word_norm[i - 1].isalnum())
        after_ok = (i + len(qnorm) == len(word_norm)) or (not word_norm[i + len(qnorm)].isalnum())
        return before_ok and after_ok
    return False


def find_test_item_by_name(db: Session, name: str, instrument: str = "") -> TestItem | None:
    """按项目名或别名匹配 test_items 表；返回最相似的一条或 None。

    若提供 instrument，则优先在该仪器（含 instrument_group）名下做过的项目中匹配，
    以利用「仪器档案的检验项目」来对应质控项目——同名项目跨仪器时定位更精准，
    取到的规范名/别名也更贴近该仪器实际使用的项目叫法。

    匹配顺序（均先做「本仪器名下」再「全局兜底」）：
      0) LIS 别名/缩写桥接表（_LIS_ITEM_ALIASES）精确命中规范名——可避免 "PT" 被
         "GPT" 子串截胡，也能把无对应别名的 "PT% / INR RATIO / SCT标准化比值" 桥接到正确项目；
      1) 原名（精确名 + 名称子串 + 带词边界的别名词子串）；
      2) 规范名兜底。
    """
    if not name:
        return None
    inst_norm = _norm(instrument or "")
    rows = db.query(TestItem).all()
    qnorm0 = _norm(name)
    canon = _LIS_ITEM_ALIASES.get(qnorm0)

    def _matches(r: TestItem, qnorm: str, qraw: str) -> bool:
        rn = _norm(r.name)
        if rn == qnorm:                      # 精确名称
            return True
        if qnorm in rn or rn in qnorm:       # 名称子串（中文全名，风险低）
            return True
        for w in _alias_words(r.aliases or ""):
            if _token_match(w, qnorm):       # 别名词：精确 / 带词边界子串
                return True
        for seg in re.split(r"[\s+]", qraw.strip()):
            sn = _norm(seg)
            if sn and (sn in rn or rn in sn):
                return True
        return False

    def _exact(r: TestItem, qnorm: str, qraw: str = "") -> bool:
        """仅精确匹配名称或某个别名词（用于别名桥接的规范名定位）。"""
        if _norm(r.name) == qnorm:
            return True
        return any(w == qnorm for w in _alias_words(r.aliases or ""))

    def _scan(qname: str, qnorm: str, pred) -> TestItem | None:
        """按 pred 扫描：先本仪器名下，再全局兜底。"""
        if inst_norm:
            for r in rows:
                ri = _norm(r.instrument or "")
                rg = _norm(r.instrument_group or "")
                if (ri and (ri == inst_norm or inst_norm in ri or ri in inst_norm)) or \
                   (rg and (rg == inst_norm or inst_norm in rg or rg in inst_norm)):
                    if pred(r, qnorm, qname):
                        return r
        for r in rows:
            if pred(r, qnorm, qname):
                return r
        return None

    def _try(qname: str, exact: bool = False) -> TestItem | None:
        qnorm = _norm(qname)
        if exact:
            return _scan(qname, qnorm, _exact)
        # 精确优先：名称/别名词完全相等者必先于模糊子串命中，
        # 避免「白蛋白」前缀截胡「白蛋白（A）」之类的同根项。
        hit = _scan(qname, qnorm, _exact)
        if hit:
            return hit
        return _scan(qname, qnorm, _matches)

    # 0) 别名/缩写桥接表：用规范名做「精确」定位，优先级最高
    if canon and canon != name:
        hit = _try(canon, exact=True)
        if hit:
            return hit
    # 1) 原名
    hit = _try(name)
    if hit:
        return hit
    # 2) 规范名兜底
    if canon and canon != name:
        hit = _try(canon)
        if hit:
            return hit
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


def _parse_cv_levels(cv_text: str) -> dict | None:
    """解析「正常X%/异常Y%」形式的水平区分质量目标。

    返回 {'正常': float, '异常': float}；无此写法返回 None。
    用于凝血等「正常水平/异常水平允许不精密度不同」的项目。
    """
    if not cv_text:
        return None
    m = re.search(r"正常\s*([\d.]+)\s*%?\s*/\s*异常\s*([\d.]+)\s*%?", cv_text)
    if m:
        try:
            return {"正常": float(m.group(1)), "异常": float(m.group(2))}
        except ValueError:
            return None
    return None


def _is_level2(level) -> bool:
    """判断质控水平是否为「异常 / 水平2」。

    水平字符串形如 '水平1' '水平2' '水平3' 或 '1' '2'；含「异常」或核心数字为 2 视为异常水平。
    """
    if not level:
        return False
    s = str(level).strip()
    if "异常" in s:
        return True
    core = s.replace("水平", "").replace("Level", "").replace("level", "").strip()
    return core == "2"


def _extract_level_pct(cv_text: str, level=None) -> float | None:
    """按水平提取质量目标百分比。

    - 有「正常X%/异常Y%」区分时：水平2(异常)取 Y，其余(正常/水平1/水平3)取 X；
    - 单一数值（如 D-二聚体 10%、FDP 11.7%）则原样返回，与水平无关。
    """
    parsed = _parse_cv_levels(cv_text)
    if parsed:
        if _is_level2(level):
            return parsed.get("异常", parsed["正常"])
        return parsed.get("正常", next(iter(parsed.values())))
    return _extract_first_pct(cv_text)


def _lookup_qr_goal(db: Session, test_item: str, aliases: str, level=None) -> str | None:
    """从 QualityRequirement 表中按项目名查找质量目标。

    优先级：wst403-2024.cv > bj-hr-2025.cv > nccl-2026.tea/3。
    匹配策略：精确匹配 > 子串含（主名或别名中有一段）。
    level：质控水平（'水平1'/'水平2'/'水平3' 等）；cv 字段含「正常X%/异常Y%」时据此取对应值。
    """
    from .comparison_report import WST403_2024

    def _match(items, source: str, field: str, level=None):
        """在 items 中匹配第一条非空的目标字段值（cv 字段按水平区分正常/异常）。"""
        for r in items:
            if r.source == source:
                val = getattr(r, field, None)
                if val and str(val).strip() not in ("", "/"):
                    sval = str(val).strip()
                    if field == "cv":
                        # 单一干净百分比（如 5.0% / 6.7% / 10%）原样保留作者写法，
                        # 避免 5.0%→5%、6.5%→6.5% 等精度丢失；「正常X%/异常Y%」才转数值按水平取。
                        if re.match(r"^\d+(?:\.\d+)?%$", sval):
                            return sval
                        pct = _extract_level_pct(sval, level)
                    else:
                        pct = _extract_first_pct(sval)
                    if pct is not None:
                        return f"{pct:g}%"
        return None

    def _all(name: str) -> list:
        """查询指定名称的所有 quality_requirements 记录（并集所有匹配策略，去重）。

        注意：必须并集「精确 / 安全包含 / 别名词 / 括号代码」全部策略命中的行，
        不能在某一步命中后短路——否则精确命中 NCCL（仅 tea、无 cv）行时会把
        携带 cv 的 BJHR 行排除，导致凝血等项目只取到 NCCL tea/3 而非正确的
        北京互认 cv（如 APTT 正常6.5%/异常10%）。
        """
        from .quality_requirements_seed import contains_same_item
        all_qr = db.query(QualityRequirement).all()
        nname = _norm(name)
        rows: list = []
        seen = set()

        def _add(r):
            if id(r) not in seen:
                seen.add(id(r))
                rows.append(r)

        # 1) 精确匹配（归一化括号/大小写，使 白蛋白（A）与 白蛋白(A) 互通）
        for r in all_qr:
            if _norm(r.item_name) == nname:
                _add(r)
        # 2) 安全包含匹配（双向，归一化），避免「钙」误入「降钙素原」等短字/前缀误匹配
        for r in all_qr:
            if r.item_name and contains_same_item(nname, _norm(r.item_name)):
                _add(r)
        # 3) 别名中的每个词（同样用安全包含）
        for a in (aliases or "").replace("，", ",").split(","):
            a = a.strip()
            if not a:
                continue
            na = _norm(a)
            for r in all_qr:
                if r.item_name and contains_same_item(na, _norm(r.item_name)):
                    _add(r)
        # 4) 用「仪器档案检验项目」的别名/代码匹配质量目标条目的括号代码
        #    （如 HBsAg / HCV / HIV / D-Dimer）。仅做精确匹配，禁止子串包含——
        #    否则 "PT"⊂"APTT"、"T"⊂"APTT"、"P"⊂"(P)" 会把凝血酶原时间/凝血酶时间/磷 等
        #    无关项目误拉进来，导致 _match 按 DB 行序先取到错误的 cv。
        ti_codes = {(name or "").strip().upper()}
        for w in _alias_words(aliases or ""):
            if w:
                ti_codes.add(w.upper())
        for r in all_qr:
            rc = _paren_code(r.item_name)
            if rc and rc in ti_codes:
                _add(r)
        return rows or []

    items = _all(test_item)
    if not items:
        return None

    # 1) wst403-2024.cv
    v = _match(items, "wst403-2024", "cv", level)
    if v:
        return v

    # 2) bj-hr-2025.cv
    v = _match(items, "bj-hr-2025", "cv", level)
    if v:
        return v

    # 3) nccl-2026.tea/3
    v = _match(items, "nccl-2026", "tea", level)
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


def lookup_quality_goal(test_item: str, aliases: str = "", db: Session = None, level=None) -> str:
    """按项目名/别名查允许不精密度（质量目标）。

    优先级：
    1. quality_requirements 表：wst403-2024.cv > bj-hr-2025.cv > nccl-2026.tea/3
    2. 原有 qc_quality_goals.json 精确/子串匹配（保留兼容）
    3. WST403_2024 TE 字典 / 3
    4. 默认 "10%"

    level：质控水平（'水平1'/'水平2'/'水平3'），用于 cv 含「正常X%/异常Y%」时取对应水平目标。
    """
    if not test_item:
        return ""
    # 精确名覆盖优先（见 QC_GOAL_EXACT_OVERRIDES 说明）
    if test_item in QC_GOAL_EXACT_OVERRIDES:
        return QC_GOAL_EXACT_OVERRIDES[test_item]

    # Step 1: QualityRequirement 表查询
    if db is not None:
        try:
            canon = _canon_item_name(test_item)
            # canon（规范名）优先于原始 LIS 缩写：缩写可能被别的项目「截胡」
            # （如 "PT" 会被「甲状旁腺激素(PTH)」的括号代码 PT 子串命中）。
            cands = [canon, test_item] if canon != test_item else [test_item]
            # 优先返回非默认（非 10%）结果
            for nm in cands:
                qr_goal = _lookup_qr_goal(db, nm, aliases, level)
                if qr_goal and qr_goal != "10%":
                    return qr_goal
            # 兜底：若候选都只能得到默认 10%（确有项目目标即为 10%），取首个有值者
            for nm in cands:
                qr_goal = _lookup_qr_goal(db, nm, aliases, level)
                if qr_goal:
                    return qr_goal
        except Exception:
            pass  # QR 表查询失败不影响主流程，回退到 JSON 文件

    # Step 2: 原有 JSON 文件匹配（保留兼容）
    goals = _load_goals()
    keys = {test_item}
    canon = _canon_item_name(test_item)
    if canon != test_item:
        keys.add(canon)
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


# ===== 上传表格「规则列」解析与优先级（2026-07-26） =====
# 失控级规则（一律判失控 ooc）；1-2s 为警告级（不计入失控）。
_OOC_RULES = {"1-3s", "2-2s", "R-4s", "10-x", "4-1s"}
_WARN_RULES = {"1-2s"}
# 严重度（越大越严重），用于同单元格多规则时取最严重者、并决定显示顺序
_RULE_SEVERITY = {"1-2s": 0, "10-x": 1, "R-4s": 2, "4-1s": 2, "2-2s": 3, "1-3s": 4}


def _normalize_rule_token(tok: str) -> str | None:
    """把单条规则 token 归一化为规范名；无法识别返回 None。

    兼容 LIS 导出常见的写法变体：
    - 全角/异形标点转半角：1－3S / 1～3S / 1–3S / 1:3S → 1-3s
    - 去最外层括号：(1-3S) / （1-3S） → 1-3s
    - 含中文说明的子串提取：1-3S(失控) / 失控1-3S / 1-3s失控 → 1-3s
    - 无空格连写：13S / 22S / 10X → 1-3s / 2-2s / 10-x
    """
    if not tok:
        return None
    s = (tok or "").strip().lower()
    # 全角/异形标点 → 半角，统一成连字符
    s = s.replace("（", "(").replace("）", ")").replace("【", "[").replace("】", "]")
    s = s.replace("－", "-").replace("—", "-").replace("–", "-").replace("～", "-").replace("~", "-")
    s = s.replace("：", "-").replace(":", "-")
    s = s.replace(" ", "").replace("_", "-")
    # 去最外层括号（如 (1-3S) / [1-3S]）
    s = s.strip("()[]")
    tbl = {
        "1-2s": "1-2s", "12s": "1-2s",
        "1-3s": "1-3s", "13s": "1-3s",
        "2-2s": "2-2s", "22s": "2-2s",
        "r-4s": "R-4s", "r4s": "R-4s",
        "4-1s": "4-1s", "41s": "4-1s",
        "10-x": "10-x", "10x": "10-x",
    }
    if s in tbl:
        return tbl[s]
    # 子串提取：单元格里嵌了已知规则码（如 "1-3S(失控)"、"失控1-3S"）
    for key, val in tbl.items():
        if key in s:
            return val
    return None


def _parse_rule_cell(cell: str) -> list[str]:
    """把上传表格的规则单元格解析为规范规则名列表（去重、保序、忽略无法识别项）。

    支持分隔符：; , / 、 空格 以及中文连接词「和」「与」。
    例：'1-2S, 1-3S' → ['1-2s', '1-3s']
    """
    if not cell:
        return []
    raw = re.split(r"[;,\/、\s和或与]+", str(cell).strip())
    out: list[str] = []
    for r in raw:
        r = r.strip()
        if not r:
            continue
        norm = _normalize_rule_token(r)
        if norm:
            out.append(norm)
    seen: set[str] = set()
    return [x for x in out if not (x in seen or seen.add(x))]


def _resolve_uploaded_rules(parsed: list[str]) -> tuple[str, str]:
    """把解析后的规则列表解析为 (分类, 规则串)。

    分类：'ooc'（失控）/ 'warning'（警告）/ ''（无有效规则）。
    规则串：失控时按严重度降序拼接多规则（1-2s 被更严重的规则覆盖，不写入）；
           警告时固定 '1-2s'。
    即：同一单元格同时有 1-2S 与 1-3S 时，用 1-3S 覆盖（判失控，不标警告）。
    """
    ooc_rules = [r for r in parsed if r in _OOC_RULES]
    warn_rules = [r for r in parsed if r in _WARN_RULES]
    if ooc_rules:
        # 防御性：严重度字典若漏项也不崩溃（未知规则排到最后，仍保留在结果串中）
        ordered = sorted(set(ooc_rules), key=lambda x: -_RULE_SEVERITY.get(x, -1))
        return "ooc", ";".join(ordered)
    if warn_rules:
        return "warning", "1-2s"
    return "", ""


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
    # 10-x：连续十点同侧（均值同侧）。已失控(ooc)点打断计数——失控点只留存，
    # 不参与后续统计，故遇到 ooc 点重置连续计数，从下一个在控点重新开始累计。
    run = 0  # 当前连续同侧计数（+n 上侧 / -n 下侧）
    for i, v in enumerate(values):
        if i in ooc:
            run = 0
            continue
        if v > mean + eps:
            run = run + 1 if run > 0 else 1
        elif v < mean - eps:
            run = run - 1 if run < 0 else -1
        else:
            run = 0  # 等于均值不打断也不计入连续同侧
        if run >= 10:
            for j in range(i - run + 1, i + 1):
                if "10-x" not in ooc.get(j, ""):
                    ooc[j] = _join(ooc.get(j, ""), "10-x")
        elif run <= -10:
            for j in range(i + run, i + 1):
                if "10-x" not in ooc.get(j, ""):
                    ooc[j] = _join(ooc.get(j, ""), "10-x")
    # 已被判失控的点不再单独标 1-2s 警告（避免警告与失控重复）
    for k in list(warnings):
        if k in ooc:
            del warnings[k]
    return ooc, warnings


def evaluate_r4s_project(points: list[dict]) -> dict:
    """跨「项目(同仪器/年/月/批号)」全部水平、按时间排序的相邻两测值 R-4s 判定（SD 归一化，2026-07-25）。

    points: list of {level, idx, value, mean, sd, date, ooc}
      level: 水平标识；idx: 该水平 values 中的下标；value: 测值；
      mean/sd: 该水平的靶值均值/靶SD（缺失时用稳健估计，均 >0）；
      date: qc_date 字符串（ISO，可排序）；
      ooc:  该点是否已因『其它规则』判失控（1-3s/2-2s/10-x）→ 冻结，不参与 R-4s。
    返回 ooc_add: {(level, idx): "R-4s"}  触发 R-4s 的失控点。

    规则（按 2026-07-24 需求，2026-07-22 修订同天判定，2026-07-25 修订为 SD 归一化 + 冻结）：
      - 把同一项目所有水平的每日测值按 (date, level) 排成一条时间线；
      - 相邻两点各自按本水平靶值归一化为 SD 倍数：z = (value - mean) / sd；
        再判 |z_前 - z_后| > 4 即触发（高低浓度拉到同一尺度，只反映波动幅度）；
      - 已失控(ooc)点冻结：前点若已 ooc 则跳过本对（不再作为 R-4s 的参与点），
        后点若已 ooc 则本对不触发（前点在控、不再给前点标任何 R-4s 标记）；
        本轮已判 R-4s 的点也即时加入冻结集，互不级联；
      - 触发时：同一天（prev.date == curr.date）两个水平都判失控(R-4s)；
        跨天相邻：只标后点(当天)判失控(R-4s)，前点不标任何 R-4s 标记
        （警告仅由 1-2s 规则产生）。
    """
    # 按 (date, level) 稳定排序，保留原始 (level, idx) 用于回写
    pts = sorted(points, key=lambda p: (p["date"], str(p["level"])))
    ooc_add: dict = {}
    # 冻结集：单点规则已判失控的 + 本轮已判 R-4s 的，均不参与后续相邻对
    frozen = {(p["level"], p["idx"]) for p in pts if p.get("ooc")}
    m = len(pts)
    for i in range(m - 1):
        prev, curr = pts[i], pts[i + 1]
        if (prev["level"], prev["idx"]) in frozen or (curr["level"], curr["idx"]) in frozen:
            continue
        mpi, mpj = prev.get("mean"), curr.get("mean")
        sdi, sdj = prev["sd"], curr["sd"]
        # 无靶值/无 SD（或估出 0）→ 该点无法归一化，跳过本对 R-4s
        if not mpi or not mpj or sdi <= 0 or sdj <= 0:
            continue
        z_prev = (prev["value"] - mpi) / sdi
        z_curr = (curr["value"] - mpj) / sdj
        eps = 1e-9 * (abs(z_prev) + abs(z_curr) + 1)
        if abs(z_prev - z_curr) > 4 + eps:
            if prev["date"] == curr["date"]:
                # 同一天两个水平触发：两个都判失控，并冻结
                ooc_add[(prev["level"], prev["idx"])] = "R-4s"
                ooc_add[(curr["level"], curr["idx"])] = "R-4s"
                frozen.add((prev["level"], prev["idx"]))
                frozen.add((curr["level"], curr["idx"]))
            else:
                # 跨天相邻：只标后点(当天)失控，前点不标任何 R-4s 标记
                ooc_add[(curr["level"], curr["idx"])] = "R-4s"
                frozen.add((curr["level"], curr["idx"]))
    return ooc_add


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
        任意相邻两点（同天不同水平、跨天同/不同水平）先各自按本水平靶值归一化为
        z=(value-mean)/sd，再判 |z_前 - z_后| > 4
        → 同天两水平都判失控(R-4s)、跨天只标后点(当天)失控(R-4s)/前点不标 R-4s；
        **已失控点冻结**：单点规则已判失控的点不参与 R-4s 相邻对及后续统计；
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
        r4s_mean = em  # 跨水平 R-4s 归一化用靶均值（缺失则用稳健估计均值）
        per[lv["level"]] = {
            "values": values, "dates": lv["dates"],
            "ooc": ooc, "warnings": warnings, "r4s_sd": r4s_sd, "r4s_mean": r4s_mean,
        }

    # 1.5) 上传表格「规则列」覆盖（若提供）：有上传规则的点以「上传规则」为准，
    #      不再采用后端计算的 Westgard；同单元格多规则按严重度取最严重者
    #      （1-3S 覆盖 1-2S）。
    #      - 本次上传含「规则列」(rule_column_present=True) 时，**真正空**的单元格一律视为在控
    #        （清空后端计算的 ooc / 警告），因为空即代表 LIS 未标注失控；
    #      - 有内容但解析不出有效规则码的单元格（如 LIS 用了后端不认识的写法）：
    #        **绝不能当成空单元格清零**——保持后端 Westgard 计算，避免把 LIS 标过的失控点误翻成在控；
    #      - 本次上传不含「规则列」时，全部单元格回落到后端 Westgard 计算（保持兼容）。
    #      带成功解析的上传规则的点（无论失控/警告）整体冻结，不参与后续跨水平 R-4s。
    #      【关键修复 2026-07-26】之前把「解析失败」与「空单元格」混为一谈，导致含规则列但写法
    #      不被识别的失控点被强制清零；现仅在「真正空」时清零。
    uploaded_present: set[tuple] = set()
    for lv in levels:
        vr = lv.get("violate_rules") or []
        values = lv["values"]
        ooc = per[lv["level"]]["ooc"]
        warnings = per[lv["level"]]["warnings"]
        rule_col = bool(lv.get("rule_column_present", False))
        for idx in range(len(values)):
            cell = vr[idx] if idx < len(vr) else ""
            raw = (cell or "").strip()
            if not raw:
                # 真正空单元格
                if rule_col:
                    # 含规则列 → 空即 LIS 未标注失控 → 一律在控，并冻结 R-4s
                    ooc.pop(idx, None)
                    warnings.pop(idx, None)
                    uploaded_present.add((lv["level"], idx))
                # 无规则列 → 保持后端计算
                continue
            # 有内容：尝试解析上传规则
            parsed = _parse_rule_cell(cell)
            if parsed:
                uploaded_present.add((lv["level"], idx))
                cls, resolved = _resolve_uploaded_rules(parsed)
                if cls == "ooc":
                    ooc[idx] = resolved
                    warnings.pop(idx, None)
                elif cls == "warning":
                    warnings[idx] = resolved
                    ooc.pop(idx, None)
                # cls == ""：解析出但均无法识别 → 保持后端计算（不强行清零！）
            # 有内容但解析不出有效规则 → 保持后端 Westgard（不误翻成在控）

    # 2) 跨水平 R-4s：把全部水平的每日测值按 (date, level) 排成一条时间线，
    #    任意「相邻两点」都参与 R-4s 判定（同天不同水平 或 跨天同/不同水平）。
    #    每个点带上各自水平的 (mean, sd)，供 evaluate_r4s_project 做 SD 归一化；
    #    已因单点规则失控(ooc)的点冻结，不参与 R-4s 相邻对。
    all_points = []
    for lv in levels:
        p = per[lv["level"]]
        for idx, (v, d) in enumerate(zip(p["values"], p["dates"])):
            all_points.append({
                "level": lv["level"], "idx": idx,
                "value": v, "mean": p["r4s_mean"], "sd": p["r4s_sd"], "date": d,
                "ooc": idx in p["ooc"] or (lv["level"], idx) in uploaded_present,
            })
    ooc_add = evaluate_r4s_project(all_points)
    for (level, idx), rule in ooc_add.items():
        po = per[level]["ooc"]
        po[idx] = _join(po.get(idx, ""), rule)

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
            warn = any(r in ("1-2s",) for r in p["rules"])
            tags = []
            if trend:
                tags.append("趋势性改变(10-x)")
            if shift:
                tags.append("漂移/偏移(2-2s/R-4s)")
            if occ:
                tags.append("偶发失控(1-3s)")
            if warn:
                tags.append("偶发警告(1-2s)")
            # tags 为空（理论上不会发生：rules 已非空则必含上述之一）则不输出空冒号行
            if tags:
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
