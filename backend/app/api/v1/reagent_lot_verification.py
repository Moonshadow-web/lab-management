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
#   允许偏倚解析
# ═══════════════════════════════════════════════════════════════
def _pct(text: str) -> float:
    """从「6.5%」「0.32 mmol/L 或 8%」「正常:6.5% / 异常:10%」中取第一个百分数。"""
    if not text:
        return 0.0
    m = re.search(r"(\d+(?:\.\d+)?)\s*%", str(text))
    return float(m.group(1)) if m else 0.0


def _core(name: str) -> str:
    """取项目中文主体，去括号内容：「白蛋白（ALB）」→「白蛋白」。"""
    if not name:
        return ""
    core = re.sub(r"[（(][^（）()]{0,20}[）)]", "", str(name)).strip()
    return core or str(name).strip()


def _norm(s: str) -> str:
    return re.sub(r"[\s\-‐—()（）\[\]【】　/]", "", str(s or "")).lower()


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
def compute_samples(samples: list, allow_pct: float, need: int) -> tuple:
    """计算每个样本的相对偏倚并判定，返回 (新样本列表, 合格数, 结论)。"""
    out, passed = [], 0
    for s in samples or []:
        ov, nv = s.get("old_value"), s.get("new_value")
        bias, ok = None, None
        try:
            if ov is not None and nv is not None and str(ov) != "" and str(nv) != "":
                f_ov, f_nv = float(ov), float(nv)
                if abs(f_ov) > 1e-12:
                    bias = round((f_nv - f_ov) / abs(f_ov) * 100.0, 2)
                    if allow_pct and allow_pct > 0:
                        ok = abs(bias) <= allow_pct + 1e-9
                        if ok:
                            passed += 1
        except (TypeError, ValueError):
            bias, ok = None, None
        out.append({
            "name": s.get("name", ""),
            "kind": s.get("kind", "样本"),
            "old_value": ov,
            "new_value": nv,
            "bias_pct": bias,
            "passed": ok,
        })
    if not allow_pct or allow_pct <= 0:
        conclusion = "待完成"
    else:
        conclusion = "符合要求" if passed >= need else "不符合要求"
    return out, passed, conclusion


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
    n = int(v.sample_count or 5)
    need = max(1, n - 1)  # 默认 5 个里 ≥4 个
    samples, passed, conclusion = compute_samples(_load_samples(v), allow, need)
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
@router.get("/criteria", response_model=dict)
def get_criteria(
    item_id: int = Query(..., description="试剂目录 id"),
    test_item_name: str = Query("", description="检验项目名（不传则用试剂名匹配）"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    """按项目自动解析允许偏倚（WS/T 403 允许偏倚 > 卫健委 EQA TEa 的 1/2）。"""
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
    rows = base.order_by(
        ReagentLotVerification.change_date.desc().nullslast(),
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
        samples_json=json.dumps(
            [s.model_dump() if hasattr(s, "model_dump") else s
             for s in (data.samples or [])], ensure_ascii=False),
        sample_count=data.sample_count or 5,
        operator=data.operator or (user.full_name if hasattr(user, "full_name") else ""),
        remark=data.remark or "",
    )
    # 未指定判定标准时自动解析
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
              "criterion_label", "allow_bias_pct", "sample_count", "operator",
              "remark"):
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
        exists = db.query(ReagentLotVerification).filter(
            ReagentLotVerification.item_id == g.item_id,
            ReagentLotVerification.old_batch_no == (g.old_batch_no or ""),
            ReagentLotVerification.new_batch_no == (g.new_batch_no or ""),
        ).first()
        if exists:
            skipped.append({"item_id": g.item_id, "reason": "已存在", "id": exists.id})
            continue
        tname = g.test_item_name or ""
        if g.test_item_id and not tname:
            ti = db.query(TestItem).get(g.test_item_id)
            tname = ti.name if ti else ""
        v = ReagentLotVerification(
            item_id=g.item_id, library=it.library or "",
            item_type=it.type or "试剂",
            reagent_name=it.name, spec=it.spec or "", brand=it.brand or "",
            old_batch_no=g.old_batch_no or "",
            old_expiry_date=g.old_expiry_date,
            new_batch_no=g.new_batch_no or "",
            new_expiry_date=g.new_expiry_date,
            change_date=g.change_date,
            test_item_id=g.test_item_id, test_item_name=tname,
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
                        "criterion_label": v.criterion_label})
    db.commit()
    return {"created": created, "created_count": len(created),
            "skipped": skipped, "skipped_count": len(skipped)}
