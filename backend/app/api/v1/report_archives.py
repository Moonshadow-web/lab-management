"""性能验证报告归档（独立文件库）。来源：generated（由新建验证生成）/ uploaded（手动上传）。"""
import os

from fastapi import Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user
from ...core.storage import persist_get_path, persist_save, persist_delete
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
            # 上传即生成报告：自动生成模板化 xlsx 报告，用户无需手动点"生成报告"
            if vrep_id:
                try:
                    from ...models.verification_report import VerificationReport
                    from ...services.verification_report_gen import build_verification_report
                    from ...api.v1.verification_reports import _serialize_report, _auto_fill_result_summary
                    rec = db.get(VerificationReport, vrep_id)
                    if rec:
                        data = _serialize_report(rec)
                        data = _auto_fill_result_summary(data)
                        rec.result_summary = json.dumps(data["result_summary"], ensure_ascii=False)
                        xlsx_bytes = build_verification_report(data)
                        fname = f"{rec.project_name or '项目'}_性能验证_{rec.report_type}.xlsx"
                        gen_rel = persist_save("verification_reports", fname, xlsx_bytes)
                        rec.report_file_path = gen_rel
                        gen_arch = ReportArchive(
                            project_name=rec.project_name,
                            report_type=rec.report_type,
                            source_type="generated",
                            ref_report_id=rec.id,
                            ref_archive_kind="verification_report",
                            original_name=fname,
                            file_path=gen_rel,
                            description="性能验证报告（自动生成）",
                            created_by_id=user.id,
                        )
                        db.add(gen_arch)
                        db.commit()
                except Exception as ge:
                    print(f"[upload] auto generate failed: {ge}")
                    try: db.rollback()
                    except: pass
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


@router.post("/{aid}/reparse")
def reparse_archive(
    aid: int,
    request: Request,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """对已上传的归档重新解析 → 新建 verification_reports 记录并关联。

    用于老数据回填（先前上传时未接自动解析逻辑导致性能验证记录页看不到）。
    """
    rec = db.get(ReportArchive, aid)
    if not rec or not rec.file_path:
        raise HTTPException(status_code=404, detail="归档不存在")
    # 强制重新解析：删除旧 ref 记录（外键 CASCADE 不会自动删 verification_reports，需要手动）
    if rec.ref_report_id:
        from ...models.verification_report import VerificationReport
        old_vrep = db.get(VerificationReport, rec.ref_report_id)
        if old_vrep:
            db.delete(old_vrep)
            db.flush()
    # 从 COS 或本地读回文件
    path = persist_get_path(rec.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="归档文件本体不存在（本地+COS）")
    body = path.read_bytes()
    if not body:
        raise HTTPException(status_code=400, detail="归档文件为空")
    try:
        from ...services.vrf_parser import parse_and_store
        host = request.client.host if request.client else ""
        parsed = parse_and_store(body, db, user, host)
        vrep_id = parsed.get("id")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"解析失败：{e}")
    if not vrep_id:
        raise HTTPException(status_code=400, detail="解析未生成 verification_reports 记录")
    rec.ref_report_id = vrep_id
    rec.ref_archive_kind = "verification_report"
    if not rec.project_name or rec.project_name == "未命名":
        rec.project_name = parsed.get("project_name") or rec.project_name
    db.add(rec)
    db.commit()
    db.refresh(rec)
    write_audit(db, user, "reparse", "report_archives", rec.id, {"verification_id": vrep_id}, host)
    return {
        "ok": True, "ref_report_id": vrep_id, "verification_id": vrep_id,
        "project_name": parsed.get("project_name"),
        "msg": "已强制重新解析并替换旧记录",
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
    # 使用 persist_get_path：本地优先 + COS 兜底（容器重启本地磁盘被清时仍可下载）
    path = persist_get_path(rec.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="归档文件不存在（本地+COS 均未找到）")
    return FileResponse(
        path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=rec.original_name or f"report_{aid}.xlsx",
    )
