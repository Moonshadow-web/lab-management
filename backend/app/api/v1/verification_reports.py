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
from ...core.storage import storage
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
        xlsx_bytes = build_verification_report(data)
    except Exception as e:  # noqa: BLE001 模板/数据异常向上暴露
        raise HTTPException(status_code=400, detail=f"生成报告失败：{e}")
    fname = f"{rec.project_name or '项目'}_性能验证_{rec.report_type}.xlsx"
    rel = storage.save("verification_reports", fname, xlsx_bytes)
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
