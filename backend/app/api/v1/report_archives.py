"""性能验证报告归档（独立文件库）。来源：generated（由新建验证生成）/ uploaded（手动上传）。"""
import os

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import storage, persist_save, persist_delete
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
    project_name: str = Form(""),
    report_type: str = Form("qualitative"),
    description: str = Form(""),
    ref_report_id: int = Form(-1),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """上传性能验证报告 xlsx 归档，自动解析并创建验证记录（显示在性能验证记录页）。"""
    body = await file.read()
    if len(body) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"文件过大（>{MAX_UPLOAD_BYTES//1024//1024}MB）")
    original = file.filename or "report.xlsx"
    safe = os.path.basename(original)

    # 尝试解析 xlsx → 创建 verification_report
    parsed_info = None
    vrep_id = None
    if original.lower().endswith(('.xlsx', '.xls')):
        try:
            from ...services.vrf_parser import parse_and_store
            host = request.client.host if request.client else ""
            parsed = parse_and_store(body, db, user, host)
            vrep_id = parsed.get("id")
            parsed_info = parsed
        except Exception:
            pass  # 非标准格式，退化为普通文件归档

    if parsed_info:
        project_name = parsed_info.get("project_name") or project_name
        report_type = parsed_info.get("report_type") or report_type
    rel = persist_save("report_archives", safe, body)
    rec = ReportArchive(
        project_name=project_name or "未命名",
        report_type=report_type,
        source_type="uploaded",
        ref_report_id=vrep_id if vrep_id else (ref_report_id if ref_report_id > 0 else None),
        ref_archive_kind="verification_report" if (vrep_id or ref_report_id > 0) else "",
        original_name=safe,
        file_path=rel,
        description=description,
        created_by_id=user.id,
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "upload", "report_archives", rec.id, {"file": rel, "parsed": bool(parsed_info)}, request.client.host if request.client else None)
    return {
        "id": rec.id, "project_name": rec.project_name, "report_type": rec.report_type,
        "source_type": rec.source_type, "ref_report_id": rec.ref_report_id,
        "original_name": rec.original_name, "file_path": rec.file_path,
        "description": rec.description, "created_at": rec.created_at,
        "parsed": bool(parsed_info),
        "verification_id": vrep_id,
    }


@router.get("/{aid}/download")
def download_archive(
    aid: int,
    request: Request,
    token: str = "",
    db: Session = Depends(get_db),
):
    """支持 URL token + Authorization header 双认证。"""
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
        raise HTTPException(status_code=401, detail="认证失败")
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
