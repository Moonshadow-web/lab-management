"""测量不确定度评估（对应 BG-SM-CZ-072 评定报告）。

数据模型 UncertaintyAssessment：输入 L1/L2 室内质控数据，后端存原始数据与
计算结果（均值/SD/CV%、合成与扩展不确定度、判定）；报告 HTML 由前端生成
（单项目报告 + 汇总表），支持预览/下载/存档。

批量端点 POST /uncertainty/batch：接收一批记录（人工/质控软件批量录入），
逐条存库 + 生成报告（自动归档）+ 返回汇总报告链接与计算结果。
"""
import json
from datetime import datetime

from fastapi import Body, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage
from ...models.report_archive import ReportArchive
from ...models.uncertainty import UncertaintyAssessment
from ...models.user import User
from ...schemas import (
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentUpdate,
)

router = make_router(
    UncertaintyAssessment,
    UncertaintyAssessmentRead,
    UncertaintyAssessmentCreate,
    UncertaintyAssessmentUpdate,
    search_fields=["project_name", "project_code", "instrument"],
    json_fields=["l1_values", "l2_values"],
    prefix="/uncertainty",
    order_by=[UncertaintyAssessment.id.desc()],
)


def _stats(values):
    vals = [float(v) for v in (values or []) if v not in (None, "")]
    if not vals:
        return None
    n = len(vals)
    mean = sum(vals) / n
    if n < 2:
        return {"mean": mean, "sd": 0.0, "cv": 0.0, "n": n}
    var = sum((v - mean) ** 2 for v in vals) / (n - 1)
    sd = var ** 0.5
    return {"mean": mean, "sd": sd, "cv": (sd / mean) * 100, "n": n}


def _calc(values, ucal, pt_result):
    s = _stats(values)
    if not s:
        return {"uc": 0, "U": 0, "passed": True}
    uBias = 0 if pt_result == "合格" else 0
    uc = (s["cv"] ** 2 + uBias ** 2 + (ucal or 0) ** 2) ** 0.5
    return {"uc": uc, "U": 2 * uc, "passed": (2 * uc) < 15}


def _calc_record(payload: dict) -> dict:
    """根据输入计算统计结果并合并到 payload。"""
    l1 = _stats(payload.get("l1_values") or [])
    l2 = _stats(payload.get("l2_values") or [])
    if l1:
        payload["l1_mean"] = l1["mean"]
        payload["l1_sd"] = l1["sd"]
        payload["l1_cv"] = l1["cv"]
    if l2:
        payload["l2_mean"] = l2["mean"]
        payload["l2_sd"] = l2["sd"]
        payload["l2_cv"] = l2["cv"]
    pt = payload.get("pt_result") or "合格"
    ucal = float(payload.get("ucal") or 0)
    p1 = _calc(payload.get("l1_values") or [], ucal, pt)
    p2 = _calc(payload.get("l2_values") or [], ucal, pt)
    payload["l1_u"] = p1["U"]
    payload["l2_u"] = p2["U"]
    payload["l1_passed"] = p1["passed"]
    payload["l2_passed"] = p2["passed"]
    return payload


@router.post("/batch")
def batch_uncertainty(
    request: Request,
    records: list = Body(..., embed=True),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """批量接收入参（records 数组），逐条计算+存+生成报告归档，返回 records 与汇总报告路径。

    入参每条：{project_name, project_code, instrument, reagent, eval_date, cycle_months,
    prepared_by, reviewed_by, l1_values, l2_values, ucal, pt_result}
    """
    if not isinstance(records, list) or not records:
        raise HTTPException(status_code=400, detail="records 数组为空")
    from ...services.uncertainty_report_gen import build_uncertainty_html, build_summary_html

    created = []
    valid_records = []
    for idx, raw in enumerate(records):
        if not isinstance(raw, dict):
            continue
        payload = dict(raw)
        payload = _calc_record(payload)
        rec = UncertaintyAssessment(**{k: payload.get(k, "") for k in [
            "project_name", "project_code", "instrument", "reagent", "eval_date",
            "cycle_months", "prepared_by", "reviewed_by",
            "l1_values", "l2_values",
            "l1_mean", "l1_sd", "l1_cv", "l2_mean", "l2_sd", "l2_cv",
            "bias_rms", "ucal", "pt_result", "l1_u", "l2_u", "l1_passed", "l2_passed",
        ]})
        rec.created_by_id = user.id
        db.add(rec)
        db.flush()
        # 生成报告 HTML + 归档
        try:
            html = build_uncertainty_html(payload)
            fname = f"{rec.project_name or '项目'}_测量不确定度_{rec.id}.html"
            rel = storage.save("uncertainty_reports", fname, html)
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
        except Exception as e:  # noqa
            rel = ""
        created.append({
            "id": rec.id, "project_name": rec.project_name,
            "l1_u": rec.l1_u, "l2_u": rec.l2_u,
            "l1_passed": rec.l1_passed, "l2_passed": rec.l2_passed,
            "archive_id": arch.id if 'arch' in locals() else None,
        })
        valid_records.append(rec)
    if valid_records:
        # 汇总报告（合成第三条：汇总表）
        try:
            summary_html = build_summary_html([{
                "project_name": r.project_name, "instrument": r.instrument,
                "l1_u": r.l1_u, "l2_u": r.l2_u, "eval_date": r.eval_date,
                "prepared_by": r.prepared_by,
                "l1_passed": r.l1_passed, "l2_passed": r.l2_passed,
            } for r in valid_records])
            sname = f"测量不确定度汇总表_{datetime.now().strftime('%Y%m%d')}.html"
            srel = storage.save("uncertainty_reports", sname, summary_html)
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
    else:
        db.commit()
        srel = ""
    return {
        "count": len(valid_records),
        "results": created,
        "summary_path": srel,
    }


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
    html = build_uncertainty_html(payload)
    fname = f"{rec.project_name or '项目'}_测量不确定度_{rec.id}.html"
    rel = storage.save("uncertainty_reports", fname, html)
    rec.report_file_path = rel
    # 归档
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
