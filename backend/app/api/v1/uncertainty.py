"""测量不确定度评估（对应 BG-SM-CZ-072 评定报告，2026-08-18 重构）。

支持两种模式：
  - single：单个测量系统，输入 L1/L2 各自的均值/SD/测试数（≥6 个月 IQC）
            → u_Rw = sqrt((RSD1²·(n1-1) + RSD2²·(n2-1)) / (n1+n2-2))
  - multi：多个测量系统，每个系统录 L1/L2 数据
            → u_Rw = sqrt(u²_均值 + u²_系统内不精密度)
            → 合并后 u_c = sqrt(u_Rw² + u_cal²)
            → 扩展不确定度 U = 2 × u_c
最终与"项目质量要求"库的允许偏倚比较（行标 > 北京市 > 1/2 EQA TE）。
"""
import json
import re
from datetime import datetime
from statistics import pstdev

from fastapi import APIRouter, Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import persist_save
from ...models.quality_requirement import QualityRequirement
from ...models.report_archive import ReportArchive
from ...models.uncertainty import UncertaintyAssessment
from ...models.user import User
from ...schemas import (
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentUpdate,
)
# 质量目标模糊匹配：复用"项目质量要求"模块的归一化/同义词/安全包含逻辑
from ...api.v1.quality_requirements import _SYNONYMS
from ...services.quality_requirements_seed import contains_same_item

router = make_router(
    UncertaintyAssessment,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentUpdate,
    search_fields=["project_name", "project_code", "instrument"],
    json_fields=["l1_values", "l2_values", "multi_systems", "bias_levels"],
    prefix="/uncertainty",
    order_by=[UncertaintyAssessment.id.desc()],
)

# ── 独立 APIRouter：避免被 make_router 的 {item_id} 路由抢匹配 ──
custom_router = APIRouter(prefix="/uncertainty", tags=["uncertainty"])


# ═══════════════════════════════════════════════════════════════
#   计算核心
# ═══════════════════════════════════════════════════════════════
def _parse_bias_to_pct(text: str) -> float:
    """把允许偏倚/总误差文本解析为百分比数值（支持 "0.32 mmol/L 或 8%" / "6.5%" / "10%" 等）。

    优先级：取第一个出现的纯百分数（>0 且 <=100），否则取以 mmoL/L 为单位
    后的等效百分比（不常见，暂返 0）。
    """
    if not text:
        return 0.0
    s = str(text)
    # 多个百分数（"正常6.5% 异常10%"）取第一个
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", s)
    if m:
        return float(m.group(1))
    return 0.0


def _extract_core_name(name: str) -> str:
    """提取项目名中文主体，去掉括号（全角/半角）及其英文缩写。

    "白蛋白（ALB）" -> "白蛋白"；"丙氨酸氨基转移酶（ALT）" -> "丙氨酸氨基转移酶"
    便于与卫健委 EQA（nccl-2026）里的纯中文项目名精确匹配。
    """
    if not name:
        return ""
    core = re.sub(r"[（(][^（）()]{0,12}[）)]", "", name).strip()
    return core or name.strip()


def _norm(s: str) -> str:
    """归一化：去空格/连字符/括号/全角后统一小写，打通"葡萄糖"↔"葡萄 糖"↔"C-肽"↔"C肽"等写法差异。"""
    return re.sub(r"[\s\-‐—()（）\[\]【】　]", "", s).lower()


def _expand_query_names(q: str):
    """把查询词扩展为一组候选标准名（含同义词正向 + 反向）。

    _SYNONYMS 是"项目库名 → 标准源同义叫法"的单向映射；当用户直接敲缩写
    （如 CK-MB / BNP / TSH）时，需反向查到所属项目名，再并入该项目的全部同义词，
    才能匹配到标准源里的 "肌酸激酶-MB(μg/L)" 等条目。
    """
    core = _extract_core_name(q)
    terms = {q, core}
    # 正向：查询词/核心名 的同义词
    for t in list(terms):
        for s in _SYNONYMS.get(t, []):
            terms.add(s)
    # 反向：若查询词本身就是某项目名的同义词（如 CK-MB），并入该项目名及其全部同义词
    for key, syns in _SYNONYMS.items():
        if q == key or core == key or q in syns or core in syns:
            terms.add(key)
            for s in syns:
                terms.add(s)
    return terms


def _search_nccl_targets(db, q: str):
    """模糊搜索卫健委 EQA 质量目标（搜索即输即筛）。

    匹配策略（宽松，用于搜索下拉）：
      1) 归一化精确匹配（项目名/同义词/核心名）；
      2) 归一化子串匹配（支持前缀/片段搜索，如"葡萄"→"葡萄糖"）；
      3) 安全包含匹配 contains_same_item（处理缩写/英文代码，如 CK-MB ↔ 肌酸激酶同工酶）。
    返回匹配到的 QualityRequirement 行（去重，按'精确优先'排序）。
    """
    if not q or not q.strip():
        return []
    core = _extract_core_name(q)
    candidates = list(_expand_query_names(q))
    norm_cands = {_norm(c) for c in candidates if c}
    rows = (
        db.query(QualityRequirement)
        .filter(QualityRequirement.source == "nccl-2026")
        .all()
    )
    exact, fuzzy = [], []
    seen = set()
    for r in rows:
        item = r.item_name or ""
        rn = _norm(item)
        if rn in norm_cands:
            if r.id not in seen:
                seen.add(r.id)
                exact.append(r)
            continue
        hit = False
        for nc in norm_cands:
            if nc and (nc in rn or rn in nc):
                hit = True
                break
        if not hit:
            for c in candidates:
                if c and contains_same_item(c, item):
                    hit = True
                    break
        if hit and r.id not in seen:
            seen.add(r.id)
            fuzzy.append(r)
    return exact + fuzzy


def _find_best_nccl(db, name: str):
    """精确匹配某项目名到卫健委 EQA 质量目标（用于选中项目后自动取 TEa）。

    匹配策略（严格，避免误匹配），沿用"项目质量要求"模块的 5 级匹配：
      1) 候选（项目名/核心名/同义词）精确匹配；
      2) 候选与标准名双向安全包含（修饰性差异视为同一项目）；
      3) 归一化精确匹配；
      4) 归一化同义词精确匹配；
      5) 归一化安全包含兜底。
    """
    if not name or not name.strip():
        return None
    core = _extract_core_name(name)
    candidates = list(_expand_query_names(name))
    rows = (
        db.query(QualityRequirement)
        .filter(QualityRequirement.source == "nccl-2026")
        .all()
    )
    qr_maps = {r.item_name: r for r in rows}
    qr_norm = {_norm(r.item_name): r for r in rows}
    # 1) 精确匹配
    for c in candidates:
        if c in qr_maps:
            return qr_maps[c]
    # 2) 双向安全包含
    for c in candidates:
        for r in rows:
            if contains_same_item(c, r.item_name):
                return r
    # 3) 归一化精确匹配
    n_name = _norm(name)
    if n_name in qr_norm:
        return qr_norm[n_name]
    for c in candidates:
        nc = _norm(c)
        if nc in qr_norm:
            return qr_norm[nc]
    # 4) 归一化安全包含兜底
    for c in candidates:
        nc = _norm(c)
        for nk, r in qr_norm.items():
            if contains_same_item(nc, nk):
                return r
    return None


def calc_single_u_rw(l1_mean, l1_sd, l1_n, l2_mean, l2_sd, l2_n):
    """单个测量系统的不精密度 u_Rw(%)（图1公式）。

    RSD1 = SD1/Mean1 * 100; RSD2 = SD2/Mean2 * 100
    u_Rw = sqrt((RSD1²*(n1-1) + RSD2²*(n2-1)) / (n1+n2-2))
    """
    if l1_n < 2 or l2_n < 2 or l1_mean <= 0 or l2_mean <= 0:
        return 0.0
    rsd1 = l1_sd / l1_mean * 100
    rsd2 = l2_sd / l2_mean * 100
    return ((rsd1 ** 2 * (l1_n - 1) + rsd2 ** 2 * (l2_n - 1)) / (l1_n + l2_n - 2)) ** 0.5


def calc_multi_u_rw(systems):
    """多个测量系统的不精密度 u_Rw(%)（图2公式）。

    对每个系统：分别算 RSD1, RSD2（RSD = SD/Mean * 100）
    u²_系统内不精密度(A,B,C) = mean(RSD1²) 或 (RSD1²+RSD2²)/2（也可各水平单独算）
    u²_系统均值方差 = 多个系统水平的均值的方差（按 RSD 算）
    u(pooled) = sqrt(u²_均值方差 + u²_系统内不精密度)
    u_Rw(%) = u(pooled) / 总均值 * 100
    """
    if not systems or len(systems) < 2:
        return 0.0
    # 每个系统：先算 L1/L2 的 RSD，作为该系统的"系统内 RSD 平方均值"
    per_sys_rsd_sq = []   # 每个系统的"系统内相对不精密度"（取 L1/L2 平方均值）
    l1_means = []
    l2_means = []
    for s in systems:
        if s.get("l1_mean", 0) <= 0 or s.get("l2_mean", 0) <= 0:
            continue
        rsd1 = s.get("l1_sd", 0) / s["l1_mean"] * 100
        rsd2 = s.get("l2_sd", 0) / s["l2_mean"] * 100
        # u²_Rw(系统) = (rsd1² + rsd2²) / 2（图2示例：0.16²+0.14²+0.18²)/3）
        per_sys_rsd_sq.append((rsd1 ** 2 + rsd2 ** 2) / 2)
        l1_means.append(s["l1_mean"])
        l2_means.append(s["l2_mean"])
    if not per_sys_rsd_sq:
        return 0.0
    # u²_系统内不精密度(多系统) = 各系统 RSD² 均值（图2公式）
    u2_within = sum(per_sys_rsd_sq) / len(per_sys_rsd_sq)
    # u²_系统均值方差 = 各系统 L1 均值的方差 + 各系统 L2 均值的方差（水平合并）
    # 为符合"每个水平质控均值的方差"：用相对 RSD 来衡量（按"均值水平的相对变化"）
    # 简化：分别对 L1/L2 算"多系统均值的 RSD 平方"，再求平均
    def _mean_var_pct(means):
        if len(means) < 2:
            return 0.0
        avg = sum(means) / len(means)
        if avg <= 0:
            return 0.0
        # 相对标准差
        return pstdev(means) / avg * 100
    l1_rsd = _mean_var_pct(l1_means)
    l2_rsd = _mean_var_pct(l2_means)
    u2_between = (l1_rsd ** 2 + l2_rsd ** 2) / 2
    # 合并：u(pooled)(%) = sqrt(u²_within + u²_between)
    return (u2_within + u2_between) ** 0.5


def lookup_target_bias(db: Session, project_name: str) -> dict:
    """查找项目的质量目标允许总误差（TEa）——卫健委 EQA（NCCL）。

    判定标准：扩展不确定度 U < 允许总误差 TEa。
    数据源：nccl-2026（国家卫健委临检中心室间质评允许总误差）。
    匹配：沿用"项目质量要求"模块的严格匹配（精确→安全包含→归一化→同义词）。
    """
    if not project_name or not project_name.strip():
        return {"bias": 0, "text": "", "source": ""}
    row = _find_best_nccl(db, project_name.strip())
    if row and row.tea:
        v = _parse_bias_to_pct(row.tea)
        if v > 0:
            return {"bias": v, "text": row.tea, "source": "卫健委 EQA（允许总误差）"}
    return {"bias": 0, "text": "", "source": ""}


def compute_record(payload: dict) -> dict:
    """根据 mode 计算 u_Rw / u_c / U / target_bias / passed。"""
    ucal = float(payload.get("ucal") or 0)
    mode = payload.get("mode") or "single"
    if mode == "single":
        u_rw = calc_single_u_rw(
            float(payload.get("l1_mean") or 0),
            float(payload.get("l1_sd") or 0),
            int(payload.get("l1_n") or 0),
            float(payload.get("l2_mean") or 0),
            float(payload.get("l2_sd") or 0),
            int(payload.get("l2_n") or 0),
        )
    else:
        systems = payload.get("multi_systems") or []
        if isinstance(systems, str):
            try:
                systems = json.loads(systems)
            except Exception:
                systems = []
        u_rw = calc_multi_u_rw(systems)
    payload["u_rw"] = round(u_rw, 4)
    # 室间质评偏倚：EQA 合格 → 偏倚已含于精密度，bias_rms=0；
    # EQA 不合格 → 用 5 水平（靶值/测量值）算 RMS 相对偏倚，纳入合成不确定度。
    pt_result = payload.get("pt_result") or "合格"
    bias_levels = payload.get("bias_levels") or []
    if isinstance(bias_levels, str):
        try:
            bias_levels = json.loads(bias_levels)
        except Exception:
            bias_levels = []
    bias_rms = 0.0
    if pt_result == "不合格" and isinstance(bias_levels, list) and bias_levels:
        sq = []
        for lv in bias_levels:
            if not isinstance(lv, dict):
                continue
            target = float(lv.get("target") or 0)
            measured = float(lv.get("measured") or 0)
            if target > 0:
                sq.append(((measured - target) / target * 100.0) ** 2)
        if sq:
            bias_rms = (sum(sq) / len(sq)) ** 0.5
    payload["bias_rms"] = round(bias_rms, 4)
    u_c = (u_rw ** 2 + ucal ** 2 + bias_rms ** 2) ** 0.5
    payload["u_c"] = round(u_c, 4)
    u_ext = 2 * u_c
    payload["u_extended"] = round(u_ext, 4)
    # 患者结果换算
    pv = float(payload.get("patient_value") or 0)
    if pv > 0:
        payload["patient_extended_value"] = round(pv * u_ext / 100.0, 4)
    else:
        payload["patient_extended_value"] = 0
    # 判定（默认未查到目标时按 U<15% 兜底；目标在创建/更新时单独写入）
    return payload


def _calc_backward_compat(payload: dict) -> None:
    """老字段回写（保证旧报告模板仍能渲染 l1_u/l2_u/l1_passed/l2_passed）。"""
    l1u = float(payload.get("l1_u") or 0)
    l2u = float(payload.get("l2_u") or 0)
    if not l1u and payload.get("u_extended"):
        payload["l1_u"] = payload["u_extended"]
        payload["l1_passed"] = bool(payload.get("passed"))
    if not l2u and payload.get("u_extended"):
        payload["l2_u"] = payload["u_extended"]
        payload["l2_passed"] = bool(payload.get("passed"))


# ═══════════════════════════════════════════════════════════════
#   端点
# ═══════════════════════════════════════════════════════════════


@custom_router.get("/_lookup_target_bias")
def api_lookup_target_bias(
    project_name: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """根据项目名查找允许总误差（卫健委 EQA TEa）。"""
    return lookup_target_bias(db, project_name)


@custom_router.get("/_search_targets")
def api_search_targets(
    q: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """模糊搜索卫健委 EQA 质量目标（项目名 + TEa），供前端手动选择。

    复用"项目质量要求"模块的模糊检索（归一化 + 同义词 + 安全包含），
    支持前缀/片段/缩写搜索，如"葡萄"→"葡萄糖"、"CK-MB"→"肌酸激酶同工酶"。

    返回 [{id, item_name, tea, tea_pct}]，tea_pct 已解析成数值百分比。
    """
    if not q or not q.strip():
        return {"items": []}
    rows = _search_nccl_targets(db, q)[:20]
    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "item_name": r.item_name,
            "tea": r.tea,
            "tea_pct": _parse_bias_to_pct(r.tea),
        })
    return {"items": items}


@custom_router.post("/_preview")
def api_preview(
    payload: dict = Body(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """实时预览计算（不存库），用于前端实时显示。"""
    p = dict(payload)
    p = compute_record(p)
    # 质量目标：前端手动选择优先（已带 target_bias 则不动）；否则自动查卫健委 EQA TEa
    if p.get("project_name") and not p.get("target_bias"):
        tg = lookup_target_bias(db, p["project_name"])
        p["target_bias"] = tg["bias"]
        p["target_bias_text"] = tg["text"]
        p["target_bias_source"] = tg["source"]
    if p.get("target_bias") and p.get("u_extended"):
        p["passed"] = p["u_extended"] < p["target_bias"]
    elif p.get("u_extended"):
        # 兜底：没找到目标时按 U<15% 算
        p["passed"] = p["u_extended"] < 15
    return p


# ═══════════════════════════════════════════════════════════════
#   CRUD override：保存时自动计算 + 查目标
# ═══════════════════════════════════════════════════════════════
@router.post("")
def create_uncertainty_assessment(
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """POST /uncertainty — 新建。读取 body，按 mode 计算，写库。"""
    body = request.json() if hasattr(request, 'json') else None
    from fastapi import Request as _Req
    # 直接复用 make_router 提供的 schema 入口（crud_base 已有标准 POST）
    # 这里拦截：调 compute_record + 查目标，写库后返回完整 record
    raise HTTPException(501, "use standard POST /uncertainty payload")


@router.post("/batch")
def batch_uncertainty(
    request: Request,
    records: list = Body(..., embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量接收入参（records 数组），逐条计算+查目标+存+生成报告归档。"""
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="records 数组为空")
    from ...services.uncertainty_report_gen import build_uncertainty_html, build_summary_html

    created = []
    valid_records = []
    for idx, raw in enumerate(records):
        if not isinstance(raw, dict):
            continue
        payload = dict(raw)
        payload = compute_record(payload)
        # 批量时也查目标偏倚
        if payload.get("project_name"):
            tg = lookup_target_bias(db, payload["project_name"])
            payload["target_bias"] = tg["bias"]
            payload["target_bias_text"] = tg["text"]
            payload["target_bias_source"] = tg["source"]
        if payload.get("target_bias") and payload.get("u_extended"):
            payload["passed"] = payload["u_extended"] < payload["target_bias"]
        _calc_backward_compat(payload)
        # 保存到 DB
        rec = UncertaintyAssessment(
            project_name=payload.get("project_name", ""),
            project_code=payload.get("project_code", ""),
            instrument=payload.get("instrument", ""),
            reagent=payload.get("reagent", ""),
            eval_date=payload.get("eval_date", ""),
            cycle_months=int(payload.get("cycle_months") or 6),
            prepared_by=payload.get("prepared_by", ""),
            reviewed_by=payload.get("reviewed_by", ""),
            mode=payload.get("mode", "single"),
            ucal=float(payload.get("ucal") or 0),
            ucal_source=payload.get("ucal_source", "厂家"),
            l1_mean=float(payload.get("l1_mean") or 0),
            l1_sd=float(payload.get("l1_sd") or 0),
            l1_n=int(payload.get("l1_n") or 0),
            l2_mean=float(payload.get("l2_mean") or 0),
            l2_sd=float(payload.get("l2_sd") or 0),
            l2_n=int(payload.get("l2_n") or 0),
            multi_systems=json.dumps(payload.get("multi_systems") or [], ensure_ascii=False),
            u_rw=float(payload.get("u_rw") or 0),
            u_c=float(payload.get("u_c") or 0),
            u_extended=float(payload.get("u_extended") or 0),
            target_bias=float(payload.get("target_bias") or 0),
            target_bias_text=payload.get("target_bias_text", ""),
            target_bias_source=payload.get("target_bias_source", ""),
            passed=bool(payload.get("passed")),
            patient_value=float(payload.get("patient_value") or 0),
            patient_unit=payload.get("patient_unit", ""),
            patient_extended_value=float(payload.get("patient_extended_value") or 0),
            l1_values=json.dumps(payload.get("l1_values") or []),
            l2_values=json.dumps(payload.get("l2_values") or []),
            l1_cv=float(payload.get("l1_cv") or 0),
            l2_cv=float(payload.get("l2_cv") or 0),
            l1_u=float(payload.get("l1_u") or 0),
            l2_u=float(payload.get("l2_u") or 0),
            l1_passed=bool(payload.get("l1_passed")),
            l2_passed=bool(payload.get("l2_passed")),
            bias_rms=float(payload.get("bias_rms") or 0),
            pt_result=payload.get("pt_result", "合格"),
            created_by_id=user.id,
        )
        db.add(rec)
        db.flush()
        # 生成 HTML 报告 + 归档
        try:
            html = build_uncertainty_html(payload)
            fname = f"{rec.project_name or '项目'}_测量不确定度_{rec.id}.html"
            rel = persist_save("uncertainty_reports", fname, html)
            rec.report_file_path = rel
            arch = ReportArchive(
                project_name=rec.project_name,
                report_type="uncertainty",
                source_type="generated",
                ref_report_id=rec.id,
                ref_archive_kind="uncertainty",
                original_name=fname,
                file_path=rel,
                description=f"测量不确定度评估（{rec.project_name}）",
                created_by_id=user.id,
            )
            db.add(arch)
            db.flush()
        except Exception:
            arch = None
        created.append({
            "id": rec.id, "project_name": rec.project_name,
            "u_extended": rec.u_extended, "u_rw": rec.u_rw,
            "target_bias": rec.target_bias, "target_bias_source": rec.target_bias_source,
            "passed": rec.passed,
            "archive_id": arch.id if arch else None,
        })
        valid_records.append(rec)
    # 汇总报告
    srel = ""
    if valid_records:
        try:
            summary_html = build_summary_html([{
                "project_name": r.project_name, "instrument": r.instrument,
                "u_extended": r.u_extended, "target_bias": r.target_bias,
                "target_bias_source": r.target_bias_source, "passed": r.passed,
                "eval_date": r.eval_date, "prepared_by": r.prepared_by,
            } for r in valid_records])
            sname = f"测量不确定度汇总表_{datetime.now().strftime('%Y%m%d')}.html"
            srel = persist_save("uncertainty_reports", sname, summary_html)
            arch_sum = ReportArchive(
                project_name="汇总表",
                report_type="uncertainty",
                source_type="generated",
                ref_report_id=None,
                ref_archive_kind="uncertainty_summary",
                original_name=sname,
                file_path=srel,
                description=f"测量不确定度汇总（共 {len(valid_records)} 项）",
                created_by_id=user.id,
            )
            db.add(arch_sum)
        except Exception:
            srel = ""
    db.commit()
    write_audit(db, user, "batch", "uncertainty_assessments", 0, {"count": len(valid_records)}, request.client.host if request.client else None)
    return {"count": len(valid_records), "results": created, "summary_path": srel}


@router.post("/{aid}/generate")
def generate_uncertainty(
    aid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """单条生成 HTML 报告并存档（用于前端生成单报告）。"""
    rec = db.get(UncertaintyAssessment, aid)
    if not rec:
        raise HTTPException(status_code=404, detail="记录不存在")
    from ...services.uncertainty_report_gen import build_uncertainty_html
    payload = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    # JSON 字段还原
    for f in ("l1_values", "l2_values", "multi_systems", "bias_levels"):
        try:
            payload[f] = json.loads(payload.get(f) or "[]")
        except Exception:
            payload[f] = []
    # 用记录自身的目标偏倚判定
    if payload.get("u_extended") and payload.get("target_bias"):
        payload["passed"] = payload["u_extended"] < payload["target_bias"]
    html = build_uncertainty_html(payload)
    fname = f"{rec.project_name or '项目'}_测量不确定度_{rec.id}.html"
    rel = persist_save("uncertainty_reports", fname, html)
    rec.report_file_path = rel
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type="uncertainty",
        source_type="generated",
        ref_report_id=rec.id,
        ref_archive_kind="uncertainty",
        original_name=fname,
        file_path=rel,
        description=f"测量不确定度评估（{rec.project_name}）",
        created_by_id=user.id,
    )
    db.add(arch)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "generate", "uncertainty_assessments", rec.id, {"file": rel}, request.client.host if request.client else None)
    return {"id": rec.id, "report_file_path": rel, "archive_id": arch.id}
