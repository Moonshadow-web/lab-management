"""样本类型可比性验证：CRUD + 计算 + docx 报告 + 图表 + 汇总。

判定依据 CNAS-CL02:2023 7.3.7.4（允许偏倚 1/2 TEa，达标率 ≥80%）。
"""
import base64
import json

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core._auth_helpers import get_current_group
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import persist_get_path, persist_save
from ...models.report_archive import ReportArchive
from ...models.specimen_comparability import SpecimenComparabilityRecord
from ...models.user import User
from ...schemas import (
    SpecimenComparabilityCreate,
    SpecimenComparabilityRead,
    SpecimenComparabilityUpdate,
)
from ...services.specimen_comparability_calc import compute_specimen_comparability

_JSON_FIELDS = ("pairs", "result_summary")

router = make_router(
    SpecimenComparabilityRecord,
    SpecimenComparabilityRead,
    SpecimenComparabilityCreate,
    SpecimenComparabilityUpdate,
    search_fields=["project_name", "batch_name", "specimen_a", "specimen_b", "instrument"],
    json_fields=list(_JSON_FIELDS),
    prefix="/specimen-comparability",
    order_by=[SpecimenComparabilityRecord.id.desc()],
    write_roles=("admin", "specialty_leader"),
    group_scoped=True,
)

summary_router = APIRouter(prefix="/specimen-comparability", tags=["specimen-comparability"])


def _serialize(rec: SpecimenComparabilityRecord) -> dict:
    d = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for f in _JSON_FIELDS:
        raw = d.get(f)
        if isinstance(raw, str) and raw.strip():
            try:
                d[f] = json.loads(raw)
            except Exception:
                d[f] = [] if f == "pairs" else {}
        elif raw is None:
            d[f] = [] if f == "pairs" else {}
    return d


def _lookup_tea(db: Session, project_name: str) -> str:
    """从质量要求库取 TEa（WS/T 403-2024 优先），支持常见别名。"""
    if not db or not project_name:
        return ""
    from sqlalchemy import or_
    from ...models.quality_requirement import QualityRequirement
    from .method_comparison import _PROJECT_TEA_ALIASES  # 复用别名表
    from ...services.verification_calc import _extract_first_pct

    names = [project_name] + _PROJECT_TEA_ALIASES.get(project_name, [])
    conds = []
    for n in names:
        conds.append(QualityRequirement.item_name == n)
        conds.append(QualityRequirement.item_name.like(f"%{n}%"))
    try:
        rows = db.query(QualityRequirement).filter(or_(*conds)).all()
    except Exception:
        return ""
    for src in ("wst403-2024", "bj-hr-2025", "nccl-2026"):
        for r in rows:
            if r.source == src and r.tea:
                pct = _extract_first_pct(r.tea)
                if pct is not None:
                    return f"{pct:g}"
    return ""


def _check_group(rec, group: str):
    if not rec:
        raise HTTPException(404, "验证记录不存在")
    if rec.group_code and rec.group_code != group:
        raise HTTPException(404, "验证记录不存在")


def _compute(rec: SpecimenComparabilityRecord, db: Session = None, persist: bool = True) -> dict:
    if db is not None and not (rec.tea or "").strip():
        try:
            tea = _lookup_tea(db, rec.project_name)
            if tea:
                rec.tea = tea
        except Exception:
            pass
    d = _serialize(rec)
    res = compute_specimen_comparability(d)
    d["result_summary"] = res.get("result_summary") or {}
    d["details"] = res.get("details") or {}
    if persist:
        rec.result_summary = json.dumps(d["result_summary"], ensure_ascii=False)
        rec.conclusion = d["result_summary"].get("conclusion", "") or ""
    return d


@router.post("/{rid}/compute")
def compute_one(
    rid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    rec = db.get(SpecimenComparabilityRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, db=db, persist=True)
    db.commit()
    db.refresh(rec)
    rs = d["result_summary"]
    if not rs.get("valid"):
        raise HTTPException(400, rs.get("message") or "计算失败，请检查样本数据")
    write_audit(db, user, "compute", "specimen_comparability_records", rec.id,
                {"n_used": rs.get("n_used"), "pass_rate": rs.get("pass_rate")},
                request.client.host if request.client else None)
    return d


@router.post("/{rid}/generate")
def generate_report(
    rid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    rec = db.get(SpecimenComparabilityRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, db=db, persist=True)
    if not d["result_summary"].get("valid"):
        db.commit()
        raise HTTPException(400, d["result_summary"].get("message") or "验证结果无效，无法生成报告")
    db.commit()
    db.refresh(rec)

    from ...services.specimen_comparability_report_gen import build_specimen_report
    try:
        content = build_specimen_report(d)
    except Exception as e:  # noqa: BLE001
        raise HTTPException(400, f"生成报告失败：{e}")

    fname = (f"{rec.project_name or '项目'}_样本类型可比性_"
             f"{rec.specimen_a or 'A'}vs{rec.specimen_b or 'B'}.docx")
    rel = persist_save("specimen_comparability_reports", fname, content)
    rec.report_file_path = rel
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type="specimen_comparability",
        source_type="generated",
        ref_report_id=rec.id,
        ref_archive_kind="specimen_comparability",
        original_name=fname,
        file_path=rel,
        description=f"样本类型可比性验证（{rec.specimen_a} vs {rec.specimen_b}）",
        created_by_id=user.id,
    )
    db.add(arch)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "generate", "specimen_comparability_records", rec.id,
                {"file": rel, "archive_id": arch.id},
                request.client.host if request.client else None)
    return {"ok": True, "report_file_path": rel, "archive_id": arch.id, "record": _serialize(rec)}


@router.get("/{rid}/download")
def download_report(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    rec = db.get(SpecimenComparabilityRecord, rid)
    _check_group(rec, group)
    if not rec.report_file_path:
        raise HTTPException(404, "报告尚未生成")
    path = persist_get_path(rec.report_file_path)
    if not path.exists():
        raise HTTPException(404, "报告文件不存在（本地+COS 均未找到）")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        filename=f"{rec.project_name or '项目'}_样本类型可比性报告.docx",
    )


@router.get("/{rid}/charts")
def charts(
    rid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    rec = db.get(SpecimenComparabilityRecord, rid)
    _check_group(rec, group)
    d = _compute(rec, db=db, persist=False)
    from ...services.specimen_comparability_report_gen import _charts as build_charts
    imgs = build_charts(d.get("details") or {})
    return {"charts": [{"key": k, "png": base64.b64encode(v).decode("ascii")} for k, v in imgs.items() if v]}


def _query_records(db: Session, group: str, ids: str = "", batch: str = "", limit: int = 200):
    q = db.query(SpecimenComparabilityRecord)
    if group != "all_group_view":
        from sqlalchemy import or_
        q = q.filter(or_(SpecimenComparabilityRecord.group_code == group,
                         SpecimenComparabilityRecord.group_code == "sm",
                         SpecimenComparabilityRecord.group_code.is_(None),
                         SpecimenComparabilityRecord.group_code == ""))
    if ids:
        try:
            id_list = [int(x) for x in ids.split(",") if x.strip()]
        except ValueError:
            raise HTTPException(400, "ids 参数格式错误")
        q = q.filter(SpecimenComparabilityRecord.id.in_(id_list))
    elif batch:
        q = q.filter(SpecimenComparabilityRecord.batch_name == batch)
    return q.order_by(SpecimenComparabilityRecord.id.asc()).limit(limit).all()


@summary_router.get("/summary")
def summary(
    ids: str = "",
    batch: str = "",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    group: str = Depends(get_current_group),
):
    recs = _query_records(db, group, ids, batch)
    items = []
    for r in recs:
        rs = _serialize(r).get("result_summary") or {}
        items.append({
            "id": r.id, "batch_name": r.batch_name, "verify_type": r.verify_type,
            "project_name": r.project_name, "unit": r.unit,
            "specimen_a": r.specimen_a, "specimen_b": r.specimen_b,
            "sample_count": r.sample_count, "verify_date": r.verify_date,
            "operator": r.operator, "reviewer": r.reviewer,
            "n_used": rs.get("n_used"), "tea": rs.get("tea"), "allow_bias": rs.get("allow_bias"),
            "pass_n": rs.get("pass_n"), "pass_needed": rs.get("pass_needed"),
            "pass_rate": rs.get("pass_rate"), "mean_bias_pct": rs.get("mean_bias_pct"),
            "verdict": rs.get("verdict"), "reason": rs.get("reason"),
            "report_file_path": r.report_file_path,
        })
    return {"items": items, "total": len(items)}
