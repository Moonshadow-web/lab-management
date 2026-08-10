"""性能验证报告归档（独立文件库）。来源：generated（由新建验证生成）/ uploaded（手动上传）。"""
import os

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage
from ...models.report_archive import ReportArchive
from ...models.user import User
from ...schemas import (
    ReportArchiveCreate,
    ReportArchiveRead,
    ReportArchiveUpdate,
)

router = make_router(
    ReportArchive,
    ReportArchiveRead,
    ReportArchiveCreate,
    ReportArchiveUpdate,
    search_fields=["project_name", "original_name", "description"],
    prefix="/report-archives",
    order_by=[ReportArchive.id.desc()],
    write_roles=("admin", "specialty_leader"),
)


MAX_UPLOAD_BYTES = 60 * 1024 * 1024  # 60 MB


@router.post("/upload")
async def upload_archive(
    request: Request,
    project_name: str = Form(...),
    report_type: str = Form("qualitative"),
    description: str = Form(""),
    ref_report_id: int = Form(-1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传性能验证报告 xlsx 归档（关联到归档库）。"""
    body = await file.read()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"文件过大（>{MAX_UPLOAD_BYTES//1024//1024}MB）")
    original = file.filename or "report.xlsx"
    safe = os.path.basename(original)
    rel = storage.save("report_archives", safe, body)
    rec = ReportArchive(
        project_name=project_name,
        report_type=report_type,
        source_type="uploaded",
        ref_report_id=ref_report_id if ref_report_id > 0 else None,
        ref_archive_kind="verification_report" if ref_report_id > 0 else "",
        original_name=safe,
        file_path=rel,
        description=description,
        created_by_id=user.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "upload", "report_archives", rec.id, {"file": rel}, request.client.host if request.client else None)
    return {
        "id": rec.id, "project_name": rec.project_name, "report_type": rec.report_type,
        "source_type": rec.source_type, "ref_report_id": rec.ref_report_id,
        "original_name": rec.original_name, "file_path": rec.file_path,
        "description": rec.description, "created_at": rec.created_at,
    }


@router.get("/{aid}/download")
def download_archive(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    rec = db.get(ReportArchive, aid)
    if not rec or not rec.file_path:
        raise HTTPException(status_code=404, detail="归档不存在")
    path = storage.get_path(rec.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="归档文件不存在")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=rec.original_name or f"report_{aid}.xlsx",
    )
