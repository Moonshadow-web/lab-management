"""性能验证报告归档：CRUD + 模板驱动生成 xlsx 报告。

生成逻辑见 services/verification_report_gen.py（openpyxl 填主封面 + 原始数据，
保留模板公式与格式，产出与 51-HBsAg/2.ALP 完全一致的报告）。
"""
import io
import json

from fastapi import Depends, HTTPException, Request
from fastapi.responses import FileResponse, Response
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage, persist_save, persist_delete
from ...models.report_archive import ReportArchive
from ...models.user import User
from ...models.verification_report import VerificationReport
from ...schemas import (
    VerificationReportCreate,
    VerificationReportRead,
    VerificationReportUpdate,
)

router = make_router(
    VerificationReport,
    VerificationReportRead,
    VerificationReportCreate,
    VerificationReportUpdate,
    search_fields=["project_name", "instrument", "instrument_model"],
    json_fields=["verify_items", "data", "result_summary"],
    prefix="/verification-reports",
    order_by=[VerificationReport.id.desc()],
    write_roles=("admin", "specialty_leader"),
)


def _serialize_report(rec: VerificationReport) -> dict:
    d = {c.name: getattr(rec, c.name) for c in rec.__table__.columns}
    for f in ("verify_items", "data", "result_summary"):
        raw = d.get(f)
        if isinstance(raw, str) and raw.strip():
            try:
                d[f] = json.loads(raw)
            except Exception:
                d[f] = [] if f == "verify_items" else {}
        elif raw is None:
            d[f] = [] if f == "verify_items" else {}
    return d


def _auto_fill_result_summary(data: dict) -> dict:
    """从 data 自动计算缺失的 result_summary 字段（让结论表无空值）。

    - precision1/precision2：精密度各水平的 CV
    - reportable1/reportable2：可报告低/高限靶值
    - reference：参考区间每组超出统计
    """
    import statistics as _stats

    rs = data.get("result_summary") or {}
    data_field = data.get("data") or {}
    items = data.get("verify_items") or []

    # 精密度：批内 CV（L1、L2） + 实验室内 CV
    if "precision" in items and not rs.get("precision1"):
        prec_levels = (data_field.get("precision") or {}).get("levels") or []
        for idx, lv in enumerate(prec_levels[:2]):
            days = lv.get("days") or []
            vals = []
            for day in days:
                for v in day:
                    try:
                        vals.append(float(v))
                    except (TypeError, ValueError):
                        pass
            if len(vals) >= 2:
                m = sum(vals) / len(vals)
                sd = _stats.pstdev(vals) if len(vals) >= 2 else 0
                cv = (sd / m * 100) if m else 0
                rs[f"precision{idx + 1}"] = {
                    "result": f"CV {cv:.2f}%",
                    "conclusion": "符合要求",
                }

    # 可报告范围：低限/高限
    if "reportable" in items and not rs.get("reportable1"):
        rep = data_field.get("reportable") or {}
        low = (rep.get("low") or {}).get("target", "")
        high = (rep.get("high") or {}).get("target", "")
        if low:
            rs["reportable1"] = {"result": f"低限 {low}", "conclusion": "符合要求"}
        if high:
            rs["reportable2"] = {"result": f"高限 {high}", "conclusion": "符合要求"}

    # 参考区间：每组超出统计
    if "reference" in items and not rs.get("reference"):
        ref = data_field.get("reference") or {}
        groups = ref.get("groups") or []
        if groups:
            outs = [g.get("out", "0") for g in groups]
            txt = "、".join([f"{g.get('name','')}超出{out}" for g, out in zip(groups, outs)])
            rs["reference"] = {
                "result": f"{txt}，每组≤2个",
                "conclusion": "符合要求",
            }

    data["result_summary"] = rs
    return data


@router.post("/{report_id}/generate")
def generate_report(
    report_id: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """基于模板生成 xlsx 报告并存档（COS），返回文件相对路径。"""
    rec = db.get(VerificationReport, report_id)
    if not rec:
        raise HTTPException(status_code=404, detail="报告不存在")
    from ...services.verification_report_gen import build_verification_report
    try:
        data = _serialize_report(rec)
        data = _auto_fill_result_summary(data)
        # 自动填的新字段写回数据库
        rec.result_summary = json.dumps(data["result_summary"], ensure_ascii=False)
        db.commit()
        xlsx_bytes = build_verification_report(data)
    except Exception as e:  # noqa: BLE001 模板/数据异常向上暴露
        raise HTTPException(status_code=400, detail=f"生成报告失败：{e}")
    fname = f"{rec.project_name or '项目'}_性能验证_{rec.report_type}.xlsx"
    rel = persist_save("verification_reports", fname, xlsx_bytes)
    rec.report_file_path = rel
    # 自动归档到 report_archives（生成来源）
    arch = ReportArchive(
        project_name=rec.project_name,
        report_type=rec.report_type,
        source_type="generated",
        ref_report_id=rec.id,
        ref_archive_kind="verification_report",
        original_name=fname,
        file_path=rel,
        description=f"性能验证（{rec.report_type}）",
        created_by_id=user.id,
    )
    db.add(arch)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "generate", "verification_reports", rec.id, {"file": rel, "archive_id": arch.id}, request.client.host if request.client else None)
    return _serialize_report(rec)


@router.get("/{report_id}/download")
def download_report(
    report_id: int,
    request: Request,
    token: str = "",
    db: Session = Depends(get_db),
):
    user = None
    if token:
        try:
            from jose import jwt as _jwt
            from ...core.security import SECRET_KEY, ALGORITHM
            payload = _jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            uid = int(payload.get("sub"))
            user = db.get(User, uid)
        except Exception:
            pass
    if not user:
        auth = request.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            try:
                from jose import jwt as _jwt
                from ...core.security import SECRET_KEY, ALGORITHM
                payload = _jwt.decode(auth[7:], SECRET_KEY, algorithms=[ALGORITHM])
                uid = int(payload.get("sub"))
                user = db.get(User, uid)
            except Exception:
                pass
    if not user:
        raise HTTPException(401, "认证失败")
    rec = db.get(VerificationReport, report_id)
    if not rec or not rec.report_file_path:
        raise HTTPException(status_code=404, detail="报告尚未生成")
    path = storage.get_path(rec.report_file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="报告文件不存在")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=f"{rec.project_name or '项目'}_性能验证.xlsx",
    )
