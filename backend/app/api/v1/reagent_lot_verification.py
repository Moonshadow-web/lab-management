"""试剂验收：试剂/质控品换批号时的批间性能验证。

业务规则（用户科室约定，参照 WS/T 407/408 批间比对通行做法）：
- 同一项目用**旧批号**与**新批号**各测 N 个样本（默认 5 个，可为质控品 + 患者样本）
- 相对偏倚 bias% =（新批号结果 − 旧批号结果）/ 旧批号结果 × 100%
- 允许偏倚来源优先级：
    1) WS/T 403—2024 的「允许偏倚」(bias)
    2) 卫健委临检中心 EQA 的「允许总误差」(tea) 的 **1/2**
    3) 手工填写
- **N 个样本中 ≥ N-1 个（默认 5 个里 ≥4 个）|相对偏倚| ≤ 允许偏倚 → 符合要求**
"""
import json
import math
import re
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.quality_requirement import QualityRequirement
from ...models.reagent_management import (
    ReagentItem, ReagentLotVerification, ReagentStock,
    Receiving, ReceivingItem, TestItemReagent,
)
from ...models.test_item import TestItem
from ...schemas.reagent_management import (
    ReagentLotVerificationCreate, ReagentLotVerificationRead,
    ReagentLotVerificationUpdate,
)

router = APIRouter(prefix="/reagent/lot-verifications", tags=["reagent-lot-verification"])

SOURCE_LABEL = {
    "wst403-2024": "WS/T 403—2024",
    "bj-hr-2025": "北京互认 2025",
    "nccl-2026": "卫健委 EQA 2026",
    "manual": "手工填写",
}



# ═══════════════════════════════════════════════════════════════
#   验收范围：只针对「试剂」，不含校准品/质控品/耗材，也不含电解质类
# ═══════════════════════════════════════════════════════════════
EXCLUDE_KEYWORDS = ("电解质", "参比液", "内标液", "参比电极", "缓冲液",
                    # 科室明确不参与批间验证的项目
                    "特异性生长因子", "抗凝血酶", "狼疮抗凝物")


def in_scope(it: "ReagentItem") -> tuple:
    """判断某试剂是否属于批间性能验证范围，返回 (是否纳入, 排除原因)。"""
    if not it:
        return False, "试剂不存在"
    if (it.type or "") != "试剂":
        return False, f"类型为「{it.type}」，本表仅针对试剂（不含校准品/质控品/耗材）"
    nm = it.name or ""
    for kw in EXCLUDE_KEYWORDS:
        if kw in nm:
            return False, f"含「{kw}」，电解质/辅助试剂不做批间验证"
    return True, ""


# ═══════════════════════════════════════════════════════════════
#   允许偏倚解析
# ═══════════════════════════════════════════════════════════════
def _pct(text: str) -> float:
    """从「6.5%」「0.32 mmol/L 或 8%」「正常:6.5% / 异常:10%」中取第一个百分数。"""
    if not text:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text))
    return float(m.group(1)) if m else 0.0


def _core(name: str) -> str:
    """取项目中文主体：去货号前缀、去括号内容、清理残留括号。

    「33570/未结合雌三醇测定试剂盒（化学发光法））」→「未结合雌三醇测定试剂盒」
    「OSR6107-丙氨酸氨基转移酶测定试剂盒（乳酸脱氢酶法）」→「丙氨酸氨基转移酶测定试剂盒」
    「20007700/D-二聚体测定试剂盒（免疫比浊法）」→「D-二聚体测定试剂盒」（D 不能被吃掉）
    """
    if not name:
        return ""
    s = str(name).strip()
    # ① 斜杠分隔的货号前缀
    hit = False
    for sep in ("/", "／"):
        if sep in s:
            s = s.split(sep)[-1]
            hit = True
            break
    # ② 连字符分隔，且前缀像货号（长度≥3 且含数字）才去，避免误伤 D-二聚体
    if not hit:
        m = re.match(r"^([A-Za-z0-9][A-Za-z0-9.]*)[\-－]", s)
        if m and len(m.group(1)) >= 3 and any(c.isdigit() for c in m.group(1)):
            s = s[m.end():]
    s = re.sub(r"[（(][^（）()]{0,20}[）)]", "", s)
    s = re.sub(r"[（）()\[\]【】]", "", s)  # 清理未配对/多余括号
    # 去掉通用后缀：标准库里叫「醛固酮(ALD)」，试剂名却是「醛固酮检测试剂盒」，
    # 不去后缀就永远匹配不到（此前 23 项免疫项目全军覆没的根因）
    for kw in ("检测试剂盒", "测定试剂盒", "诊断试剂盒", "检测试剂", "测定试剂",
               "试剂盒", "试剂"):
        s = s.replace(kw, "")
    # 去掉系统名尾部的英文缩写（total P1NP / HBeAg / Anti-HBc 等），否则与标准库名对不上
    s = re.sub(r"(TOTAL-?P1NP|P1NP|HBEAG|ANTI-?HBS|ANTI-?HBC|ANTI-?HBE|HBSAG|HBCAB|HBSAB)$",
               "", s, flags=re.I)
    return s.strip() or str(name).strip()


_ROMAN = {"Ⅰ": "I", "Ⅱ": "II", "Ⅲ": "III", "Ⅳ": "IV", "Ⅴ": "V", "Ⅵ": "VI"}


def _norm(s: str) -> str:
    t = str(s or "")
    for k, v in _ROMAN.items():
        t = t.replace(k, v)     # 罗马数字→拉丁字母：总Ⅰ型 ↔ 总I型
    return re.sub(r"[\s\-‐—()（）\[\]【】　/]", "", t).lower()


def _find_qr(db: Session, source: str, names: list) -> Optional[QualityRequirement]:
    """按候选名称在指定来源里找质量要求（先精确后包含）。"""
    if not names:
        return None
    rows = db.query(QualityRequirement).filter(
        QualityRequirement.source == source).all()
    for n in names:
        nn = _norm(n)
        if not nn:
            continue
        for r in rows:
            if _norm(r.item_name) == nn or _norm(r.item_code) == nn:
                return r
    for n in names:
        nn = _norm(n)
        if len(nn) < 3:
            continue
        for r in rows:
            rn = _norm(r.item_name)
            if rn and (nn in rn or rn in nn):
                return r
    return None


def candidate_names(db: Session, item_id: int, test_item_name: str = "") -> list:
    """为某试剂构造「标准源项目名」候选：优先关联检验项目名，其次试剂名主体。"""
    names = []
    if test_item_name:
        names += [test_item_name, _core(test_item_name)]
    it = db.query(ReagentItem).get(item_id)
    if it and it.name:
        names += [_core(it.name), it.name]
    out, seen = [], set()
    for n in names:
        n = (n or "").strip()
        if n and n not in seen:
            seen.add(n)
            out.append(n)
    return out


def resolve_allow_bias(db: Session, item_id: int,
                       test_item_name: str = "") -> dict:
    """自动解析允许相对偏倚（%）。

    返回 {source, label, pct, raw}；都取不到时返回 source='' 让前端提示手填。
    """
    names = candidate_names(db, item_id, test_item_name)
    # 1) 行标允许偏倚
    qr = _find_qr(db, "wst403-2024", names)
    if qr and qr.bias:
        v = _pct(qr.bias)
        if v > 0:
            return {"source": "wst403-2024",
                    "label": f"{SOURCE_LABEL['wst403-2024']} 允许偏倚 {v:g}%",
                    "pct": v, "raw": qr.bias}
    # 2) 卫健委 EQA 允许总误差的 1/2
    qr2 = _find_qr(db, "nccl-2026", names)
    if qr2 and qr2.tea:
        v = _pct(qr2.tea) / 2.0
        if v > 0:
            return {"source": "nccl-2026",
                    "label": f"{SOURCE_LABEL['nccl-2026']} 允许总误差 {_pct(qr2.tea):g}% 的 1/2 = {v:g}%",
                    "pct": round(v, 2), "raw": qr2.tea}
    return {"source": "", "label": "", "pct": 0.0, "raw": ""}


# ═══════════════════════════════════════════════════════════════
#   相对偏倚计算与判定
# ═══════════════════════════════════════════════════════════════
def compute_samples(samples: list, allow_pct: float, need: int,
                   mode: str = "relative", allow_abs: float = 0.0) -> tuple:
    """计算每个样本的定量偏倚 + 定性一致性并判定。

    **双轨判读**（科室需求）：定量相对/绝对偏倚合格 **或** 新旧批号阴阳性一致，
    任一满足即视为该样本合格 —— 定性项目（乙肝/丙肝/梅毒/HIV/戊肝等）用阴阳性判读更贴切，
    定量项目仍按偏倚判读，两轨可同时填写、也可只填其一。

    结论规则（避免「样本还没填就判不符合」）：
      - 允许偏倚未填、且无定性结果  → 待完成
      - 有效样本数为 0（完全未录入）→ 待完成
      - 合格数 ≥ 需合格数            → 符合要求
      - 样本已全部录入但仍不达标     → 不符合要求
      - 其余（录了一部分）           → 待完成
    """
    out, passed, valid = [], 0, 0
    for s in samples or []:
        ov, nv = s.get("old_value"), s.get("new_value")
        oq = str(s.get("old_qual") or "").strip()
        nq = str(s.get("new_qual") or "").strip()

        # ── 轨一：定量偏倚（**每行可各自选相对/绝对**，留空则用记录级默认）──
        # 科室实际场景：同一批 5 个样本可能 1 个按绝对、4 个按相对（如低值样本用绝对）
        row_mode = str(s.get("bias_mode") or "").strip() or mode
        # 该行用哪个允许值：绝对模式用 allow_abs，相对模式用 allow_pct
        row_allow = allow_abs if row_mode == "absolute" else allow_pct
        bias, bias_ok = None, None
        try:
            if ov is not None and nv is not None and str(ov) != "" and str(nv) != "":
                f_ov, f_nv = float(ov), float(nv)
                if row_mode == "absolute":
                    bias = round(f_nv - f_ov, 4)     # 与结果同单位，旧值为 0 也有效
                elif abs(f_ov) > 1e-12:
                    bias = round((f_nv - f_ov) / abs(f_ov) * 100.0, 2)
                if bias is not None and row_allow and row_allow > 0:
                    bias_ok = abs(bias) <= row_allow + 1e-9
        except (TypeError, ValueError):
            bias, bias_ok = None, None

        # ── 轨二：定性阴阳性一致性 ──
        qual_ok = None
        if oq and nq:
            qual_ok = (oq == nq)

        # ── 综合：任一轨满足即合格 ──
        if bias_ok is None and qual_ok is None:
            ok = None
        else:
            ok = bool(bias_ok) or bool(qual_ok)
            valid += 1
            if ok:
                passed += 1

        out.append({
            "name": s.get("name", ""),
            "kind": s.get("kind", "样本"),
            "old_value": ov, "new_value": nv,
            "bias_pct": bias, "bias_ok": bias_ok, "bias_mode": row_mode,
            "row_allow": row_allow or None,
            "old_qual": oq, "new_qual": nq, "qual_ok": qual_ok,
            "passed": ok,
        })

    total = len(samples or [])
    has_any_criterion = bool((allow_pct and allow_pct > 0) or (allow_abs and allow_abs > 0))
    if valid == 0:
        conclusion = "待完成"
    elif passed >= need:
        conclusion = "符合要求"
    elif total > 0 and valid >= total:
        conclusion = "不符合要求"       # 全部录完仍不达标
    elif not has_any_criterion:
        conclusion = "待完成"
    else:
        conclusion = "待完成"          # 只录了一部分
    return out, passed, conclusion, valid


def _to_read(v: ReagentLotVerification) -> dict:
    try:
        samples = json.loads(v.samples_json or "[]")
    except Exception:
        samples = []
    return {
        "id": v.id, "item_id": v.item_id, "library": v.library,
        "item_type": v.item_type, "reagent_name": v.reagent_name,
        "spec": v.spec, "brand": v.brand,
        "old_batch_no": v.old_batch_no, "old_expiry_date": v.old_expiry_date,
        "new_batch_no": v.new_batch_no, "new_expiry_date": v.new_expiry_date,
        "change_date": v.change_date,
        "test_item_id": v.test_item_id, "test_item_name": v.test_item_name,
        "criterion_source": v.criterion_source,
        "criterion_label": v.criterion_label,
        "allow_bias_pct": v.allow_bias_pct,
        "allow_bias_abs": getattr(v, "allow_bias_abs", "") or "",
        "bias_mode": v.bias_mode or "relative",
        "judge_mode": v.judge_mode or "quantitative",
        "samples": samples, "sample_count": v.sample_count,
        "samples_json": v.samples_json or "",
        "pass_count": v.pass_count, "conclusion": v.conclusion,
        "status": v.status, "operator": v.operator,
        "verified_at": v.verified_at, "remark": v.remark,
        "created_at": v.created_at, "updated_at": v.updated_at,
    }


def _apply_calc(v: ReagentLotVerification) -> None:
    """按当前 samples / allow_bias_pct 重算并写回。"""
    try:
        allow = float(str(v.allow_bias_pct or "").strip() or 0)
    except ValueError:
        allow = 0.0
    # 注：allow=0 时定量轨不判，但仍可用定性轨判定（定性项目无需允许偏倚）
    n = int(v.sample_count or 5)
    need = max(1, n - 1)  # 默认 5 个里 ≥4 个
    mode = (v.bias_mode or "relative").strip() or "relative"
    try:
        allow_abs = float(str(getattr(v, "allow_bias_abs", "") or "").strip() or 0)
    except ValueError:
        allow_abs = 0.0
    samples, passed, conclusion, _valid = compute_samples(
        _load_samples(v), allow, need, mode, allow_abs)
    v.samples_json = json.dumps(samples, ensure_ascii=False)
    v.pass_count = passed
    v.conclusion = conclusion
    if conclusion in ("符合要求", "不符合要求"):
        v.status = "已完成"
        if not v.verified_at:
            v.verified_at = datetime.utcnow()
    else:
        v.status = "待验证"
        v.verified_at = None


def _load_samples(v: ReagentLotVerification) -> list:
    try:
        return json.loads(v.samples_json or "[]")
    except Exception:
        return []


# ═══════════════════════════════════════════════════════════════
#   API
# ═══════════════════════════════════════════════════════════════
@router.get("/_prepare", response_model=dict)
def prepare_verification(
    item_id: int = Query(..., description="试剂目录 id"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """表单预填：该试剂自动关联的检验项目、库存批号、最近到货批号、允许偏倚。

    前端选完试剂调一次即可把「项目 / 旧批号 / 新批号候选 / 允许偏倚」都带出来，
    不用手工再选项目、也不用手敲批号。
    """
    it = db.query(ReagentItem).get(item_id)
    if not it:
        raise HTTPException(404, "试剂未找到")

    # ① 自动关联的检验项目（test_item_reagents 里 role=试剂）
    links = (
        db.query(TestItemReagent, TestItem)
        .join(TestItem, TestItem.id == TestItemReagent.test_item_id)
        .filter(TestItemReagent.reagent_item_id == item_id,
                TestItemReagent.role == "试剂")
        .all()
    )
    test_items = [{"id": ti.id, "name": ti.name} for _l, ti in links]

    # ② 库存批号（旧批号 = 现存数量最大的批次，即当前在用的）
    stock_rows = (db.query(ReagentStock)
                  .filter(ReagentStock.item_id == item_id).all())
    batches = sorted(
        [{"batch_no": (s.batch_no or "").strip(),
          "expiry_date": str(s.expiry_date) if s.expiry_date else "",
          "quantity": int(s.quantity or 0)} for s in stock_rows if (s.batch_no or "").strip()],
        key=lambda x: -x["quantity"])
    old_batch = batches[0] if batches else None

    # ③ 最近到货批号（已确认收货单，按收货日期倒序取不同批号，排除已在库的同批号）
    in_stock = {(b["batch_no"] or "").upper() for b in batches}
    recv_rows = (
        db.query(ReceivingItem, Receiving)
        .join(Receiving, Receiving.id == ReceivingItem.receiving_id)
        .filter(ReceivingItem.item_id == item_id, Receiving.is_confirmed == True)
        .order_by(Receiving.receipt_date.desc(), Receiving.id.desc())
        .limit(50).all()
    )
    # 同时纳入**未确认**的收货单（货可能已到、只是还没点确认），标注 confirmed 便于区分
    pending = (
        db.query(ReceivingItem, Receiving)
        .join(Receiving, Receiving.id == ReceivingItem.receiving_id)
        .filter(ReceivingItem.item_id == item_id, Receiving.is_confirmed == False)
        .order_by(Receiving.receipt_date.desc(), Receiving.id.desc())
        .limit(20).all()
    )
    new_cands, seen = [], set()
    for li, rec in list(recv_rows) + list(pending):
        b = (li.batch_no or "").strip()
        if not b or b.upper() in seen:
            continue
        seen.add(b.upper())
        new_cands.append({
            "batch_no": b,
            "expiry_date": str(li.expiry_date) if li.expiry_date else "",
            "receipt_date": str(rec.receipt_date),
            "receipt_no": rec.receipt_no,
            "confirmed": bool(rec.is_confirmed),
            "already_in_stock": b.upper() in in_stock,
        })
    # 优先展示「尚未入库」的批号（那才是待验证的新批号）
    new_cands.sort(key=lambda x: (x["already_in_stock"], not x["confirmed"],
                                  x["receipt_date"]), reverse=False)
    new_cands = new_cands[:8]

    # ④ 允许偏倚（优先用关联项目名匹配）
    r = resolve_allow_bias(db, item_id, test_items[0]["name"] if test_items else "")

    ok, why = in_scope(it)
    return {
        "item_id": item_id, "reagent_name": it.name, "spec": it.spec or "",
        "brand": it.brand or "", "library": it.library or "", "item_type": it.type or "",
        "in_scope": ok, "exclude_reason": why,
        "test_items": test_items,
        "stock_batches": batches,
        "old_batch": old_batch,
        "new_batch_candidates": new_cands,
        "allow_bias": r,
    }


@router.get("/criteria", response_model=dict)
def get_criteria(
    item_id: int = Query(..., description="试剂目录 id"),
    test_item_name: str = Query("", description="检验项目名（不传则自动取关联项目/试剂名）"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """按项目自动解析允许偏倚（WS/T 403 允许偏倚 > 卫健委 EQA TEa 的 1/2）。

    不传 test_item_name 时，自动反查该试剂关联的检验项目名。
    """
    if not test_item_name:
        link = (db.query(TestItem)
                .join(TestItemReagent, TestItemReagent.test_item_id == TestItem.id)
                .filter(TestItemReagent.reagent_item_id == item_id,
                        TestItemReagent.role == "试剂")
                .first())
        if link:
            test_item_name = link.name
    r = resolve_allow_bias(db, item_id, test_item_name)
    return r


@router.get("", response_model=dict)
def list_verifications(
    library: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    conclusion: Optional[str] = Query(None),
    q: str = Query("", description="搜索试剂名/批号/项目名"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    base = db.query(ReagentLotVerification)
    if library:
        base = base.filter(ReagentLotVerification.library == library)
    if status:
        base = base.filter(ReagentLotVerification.status == status)
    if conclusion:
        base = base.filter(ReagentLotVerification.conclusion == conclusion)
    if q.strip():
        kw = f"%{q.strip()}%"
        base = base.filter(
            ReagentLotVerification.reagent_name.like(kw)
            | ReagentLotVerification.new_batch_no.like(kw)
            | ReagentLotVerification.old_batch_no.like(kw)
            | ReagentLotVerification.test_item_name.like(kw)
        )
    total = base.count()
    # 注意：不能用 .nullslast()，MySQL 不支持 NULLS LAST 语法（会直接 500）。
    # MySQL 里 DESC 排序时 NULL 天然排在最后，用 desc() 即可。
    rows = base.order_by(
        ReagentLotVerification.change_date.desc(),
        ReagentLotVerification.id.desc(),
    ).offset((page - 1) * page_size).limit(page_size).all()
    return {"total": total, "page": page, "page_size": page_size,
            "items": [_to_read(r) for r in rows]}


@router.get("/{vid}", response_model=dict)
def get_verification(vid: int, db: Session = Depends(get_db),
                     _=Depends(get_current_user)):
    v = db.query(ReagentLotVerification).get(vid)
    if not v:
        raise HTTPException(404, "验收记录未找到")
    return _to_read(v)


@router.post("", response_model=dict)
def create_verification(
    data: ReagentLotVerificationCreate, db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "reagent_manager", "lab_technician")),
):
    it = db.query(ReagentItem).get(data.item_id)
    if not it:
        raise HTTPException(404, "试剂未找到")
    ok, why = in_scope(it)
    if not ok:
        raise HTTPException(400, f"不在试剂批间验证范围：{why}")
    v = ReagentLotVerification(
        item_id=data.item_id,
        library=data.library or it.library or "",
        item_type=data.item_type or it.type or "试剂",
        reagent_name=data.reagent_name or it.name,
        spec=data.spec or it.spec or "",
        brand=data.brand or it.brand or "",
        old_batch_no=data.old_batch_no or "",
        old_expiry_date=data.old_expiry_date,
        new_batch_no=data.new_batch_no or "",
        new_expiry_date=data.new_expiry_date,
        change_date=data.change_date,
        test_item_id=data.test_item_id,
        test_item_name=data.test_item_name or "",
        criterion_source=data.criterion_source or "",
        criterion_label=data.criterion_label or "",
        allow_bias_pct=data.allow_bias_pct or "",
        allow_bias_abs=data.allow_bias_abs or "",
        bias_mode=(data.bias_mode or "relative"),
        judge_mode=(data.judge_mode or "quantitative"),
        samples_json=json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else s
             for s in (data.samples or [])], ensure_ascii=False),
        sample_count=data.sample_count or 5,
        operator=data.operator or (user.full_name if hasattr(user, "full_name") else ""),
        remark=data.remark or "",
    )
    # 未指定检验项目时自动关联；再自动解析判定标准
    if not v.test_item_name:
        link = (db.query(TestItem)
                .join(TestItemReagent, TestItemReagent.test_item_id == TestItem.id)
                .filter(TestItemReagent.reagent_item_id == v.item_id,
                        TestItemReagent.role == "试剂")
                .first())
        if link:
            v.test_item_id = link.id
            v.test_item_name = link.name
    if not v.allow_bias_pct:
        r = resolve_allow_bias(db, v.item_id, v.test_item_name)
        if r["pct"] > 0:
            v.criterion_source = r["source"]
            v.criterion_label = r["label"]
            v.allow_bias_pct = f"{r['pct']:g}"
    _apply_calc(v)
    db.add(v)
    db.commit()
    db.refresh(v)
    return _to_read(v)


@router.put("/{vid}", response_model=dict)
def update_verification(
    vid: int, data: ReagentLotVerificationUpdate,
    db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "reagent_manager", "lab_technician")),
):
    v = db.query(ReagentLotVerification).get(vid)
    if not v:
        raise HTTPException(404, "验收记录未找到")
    for f in ("item_id", "library", "item_type", "reagent_name", "spec", "brand",
              "old_batch_no", "old_expiry_date", "new_batch_no", "new_expiry_date",
              "change_date", "test_item_id", "test_item_name", "criterion_source",
              "criterion_label", "allow_bias_pct", "allow_bias_abs",
              "bias_mode", "judge_mode",
              "sample_count", "operator", "remark"):
        val = getattr(data, f, None)
        if val is not None:
            setattr(v, f, val)
    if data.samples is not None:
        v.samples_json = json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else s
             for s in data.samples], ensure_ascii=False)
    # 标准来源被清空时重新解析
    if data.allow_bias_pct == "" or (data.test_item_name and not data.allow_bias_pct):
        r = resolve_allow_bias(db, v.item_id, v.test_item_name)
        if r["pct"] > 0:
            v.criterion_source = r["source"]
            v.criterion_label = r["label"]
            v.allow_bias_pct = f"{r['pct']:g}"
    _apply_calc(v)
    db.commit()
    db.refresh(v)
    return _to_read(v)


@router.post("/{vid}/calc", response_model=dict)
def recalc_verification(
    vid: int, db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "reagent_manager", "lab_technician")),
):
    """重算相对偏倚与结论。"""
    v = db.query(ReagentLotVerification).get(vid)
    if not v:
        raise HTTPException(404, "验收记录未找到")
    _apply_calc(v)
    db.commit()
    db.refresh(v)
    return _to_read(v)


@router.delete("/{vid}")
def delete_verification(
    vid: int, db: Session = Depends(get_db),
    _=Depends(require_roles("admin", "reagent_manager")),
):
    v = db.query(ReagentLotVerification).get(vid)
    if not v:
        raise HTTPException(404, "验收记录未找到")
    db.delete(v)
    db.commit()
    return {"ok": True}


class _GenItem(BaseModel):
    item_id: int
    old_batch_no: str = ""
    new_batch_no: str = ""
    old_expiry_date: Optional[date] = None
    new_expiry_date: Optional[date] = None
    change_date: Optional[date] = None
    test_item_id: Optional[int] = None
    test_item_name: str = ""


class _GenPayload(BaseModel):
    items: list[_GenItem]
    sample_count: int = 5


@router.post("/_generate", response_model=dict)
def generate_verifications(
    body: _GenPayload, db: Session = Depends(get_db),
    user=Depends(require_roles("admin", "reagent_manager")),
):
    """批量生成待验收记录（批号变更时调用）。

    已存在相同 (item_id, 旧批号, 新批号) 的记录会跳过，不会重复生成。
    """
    created, skipped = [], []
    for g in body.items:
        it = db.query(ReagentItem).get(g.item_id)
        if not it:
            skipped.append({"item_id": g.item_id, "reason": "试剂未找到"})
            continue
        # 范围校验：仅试剂，排除校准品/质控品/耗材与电解质类
        ok, why = in_scope(it)
        if not ok:
            skipped.append({"item_id": g.item_id, "reason": why,
                            "reagent_name": it.name})
            continue
        exists = db.query(ReagentLotVerification).filter(
            ReagentLotVerification.item_id == g.item_id,
            ReagentLotVerification.old_batch_no == (g.old_batch_no or ""),
            ReagentLotVerification.new_batch_no == (g.new_batch_no or ""),
        ).first()
        if exists:
            skipped.append({"item_id": g.item_id, "reason": "已存在", "id": exists.id})
            continue
        tname = g.test_item_name or ""
        tid = g.test_item_id
        if g.test_item_id and not tname:
            ti = db.query(TestItem).get(g.test_item_id)
            tname = ti.name if ti else ""
        if not tname:
            # 自动关联：按 test_item_reagents 里 role=试剂 的第一个项目
            # （此前批量生成漏了这步，导致 95 条记录的「检验项目」全为空）
            link = (db.query(TestItem)
                    .join(TestItemReagent, TestItemReagent.test_item_id == TestItem.id)
                    .filter(TestItemReagent.reagent_item_id == it.id,
                            TestItemReagent.role == "试剂")
                    .order_by(TestItem.id)
                    .first())
            if link:
                tid = link.id
                tname = link.name
        v = ReagentLotVerification(
            item_id=g.item_id, library=it.library or "",
            item_type=it.type or "试剂",
            reagent_name=it.name, spec=it.spec or "", brand=it.brand or "",
            old_batch_no=g.old_batch_no or "",
            old_expiry_date=g.old_expiry_date,
            new_batch_no=g.new_batch_no or "",
            new_expiry_date=g.new_expiry_date,
            change_date=g.change_date,
            test_item_id=tid, test_item_name=tname,
            sample_count=body.sample_count or 5,
            samples_json=json.dumps(
                [{"name": f"样本{i+1}", "kind": "样本",
                  "old_value": None, "new_value": None}
                 for i in range(body.sample_count or 5)], ensure_ascii=False),
            operator=(user.full_name if hasattr(user, "full_name") else "") or "",
        )
        r = resolve_allow_bias(db, v.item_id, v.test_item_name)
        if r["pct"] > 0:
            v.criterion_source = r["source"]
            v.criterion_label = r["label"]
            v.allow_bias_pct = f"{r['pct']:g}"
        _apply_calc(v)
        db.add(v)
        db.flush()
        created.append({"id": v.id, "item_id": v.item_id,
                        "reagent_name": v.reagent_name,
                        "old_batch_no": v.old_batch_no,
                        "new_batch_no": v.new_batch_no,
                        "allow_bias_pct": v.allow_bias_pct,
        "allow_bias_abs": getattr(v, "allow_bias_abs", "") or "",
        "bias_mode": v.bias_mode or "relative",
        "judge_mode": v.judge_mode or "quantitative",
                        "criterion_label": v.criterion_label})
    db.commit()
    return {"created": created, "created_count": len(created),
            "skipped": skipped, "skipped_count": len(skipped)}
