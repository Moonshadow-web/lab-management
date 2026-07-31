"""文件评审子模块 API：活动管理 + 分配 + 成员修订提交 + 管理员接收生成新版本 + 按人 A-027 记录。

流程：
  管理员建活动 → 选在用文档（仅 通用SOP/项目SOP/仪器SOP）分配给成员（可视化批量，可指定单人/多人自动均分）→
  成员下载文档、本地修订（改审核人署名）→ 上传修订文件 →
  每人填写一份 A-027「文件评审记录」（评审组成员=全部被分配人、评审文件=本人分配范围、记录人=本人、审批人默认金子铮）→ 提交 →
  管理员「接收并生成新版本」→ 调用 documents 的版本逻辑更新文件版本。
"""
import json
from datetime import datetime
from io import BytesIO
from urllib.parse import quote

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...core.cos_storage import cos_storage
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...core.storage import storage
from ...models.document import Document, DocumentVersion
from ...models.iso15189 import ReviewAssignment, ReviewCampaign, ReviewRecord
from ...models.user import User
from ...schemas import (
    ReviewAssignmentCreate,
    ReviewAssignmentRead,
    ReviewAssignmentUpdate,
    ReviewCampaignCreate,
    ReviewCampaignRead,
    ReviewCampaignUpdate,
    ReviewRecordCreate,
    ReviewRecordRead,
    ReviewRecordUpdate,
)
from ...models.iso15189 import REVIEW_DOC_CATEGORIES

WRITE_ROLES = (
    "admin", "quality_manager", "qc_manager", "training_manager",
    "reagent_manager", "it_manager", "specialty_leader",
)
DEFAULT_APPROVER = "金子铮"


def _is_admin(user: User) -> bool:
    return user.role == "admin" or "admin" in (user.roles or "").split(",")


def _to_read(obj) -> ReviewAssignmentRead:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    raw = d.get("record_json")
    if isinstance(raw, str) and raw.strip():
        try:
            d["record_json"] = json.loads(raw)
        except Exception:
            d["record_json"] = {}
    else:
        d["record_json"] = raw or {}
    return ReviewAssignmentRead.model_validate(d)


review_router = APIRouter(tags=["review"])

campaign_router = make_router(
    ReviewCampaign, ReviewCampaignRead, ReviewCampaignCreate, ReviewCampaignUpdate,
    search_fields=["title", "year", "note"],
    prefix="/review/campaigns",
    write_roles=WRITE_ROLES,
)
assignment_router = make_router(
    ReviewAssignment, ReviewAssignmentRead, ReviewAssignmentCreate, ReviewAssignmentUpdate,
    search_fields=["reviewer", "note"],
    filter_fields=["campaign_id", "document_id", "status", "reviewer_id"],
    json_fields=["record_json"],
    prefix="/review/assignments",
    write_roles=WRITE_ROLES,
)
record_router = make_router(
    ReviewRecord, ReviewRecordRead, ReviewRecordCreate, ReviewRecordUpdate,
    search_fields=["reviewer", "status"],
    filter_fields=["campaign_id", "reviewer_id", "status"],
    json_fields=["record_json"],
    prefix="/review/records",
    write_roles=WRITE_ROLES,
)
review_router.include_router(campaign_router)
review_router.include_router(assignment_router)
review_router.include_router(record_router)


@review_router.post("/review/campaigns/{cid}/assign-batch")
def assign_batch(
    cid: int,
    items: list[dict],
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """批量把文档分配给审核人。items: [{document_id, reviewer, reviewer_id}]。

    - 同一 (campaign, document, reviewer) 已存在则跳过，避免重复分配。
    - reviewer_id 为空时按 reviewer 名字去重。
    """
    existing = {
        (a.document_id, a.reviewer_id, a.reviewer)
        for a in db.query(ReviewAssignment).filter(ReviewAssignment.campaign_id == cid).all()
    }
    created = []
    for it in items:
        doc_id = it.get("document_id")
        if not doc_id:
            continue
        rid = it.get("reviewer_id")
        rname = it.get("reviewer", "") or ""
        if (int(doc_id), rid, rname) in existing:
            continue
        a = ReviewAssignment(
            campaign_id=cid,
            document_id=int(doc_id),
            reviewer=rname,
            reviewer_id=rid,
            status="待评审",
        )
        db.add(a)
        db.flush()
        created.append(a.id)
        existing.add((int(doc_id), rid, rname))
    db.commit()
    write_audit(db, user, "create", "review_assignments", cid, {"count": len(created)})
    return {"ok": True, "created": created}


@review_router.get("/review/my-assignments")
def my_assignments(
    campaign_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(ReviewAssignment).filter(ReviewAssignment.reviewer_id == user.id)
    if campaign_id:
        q = q.filter(ReviewAssignment.campaign_id == campaign_id)
    items = q.order_by(ReviewAssignment.id.desc()).all()
    return [_to_read(a) for a in items]


@review_router.get("/review/my-record")
def get_my_record(
    campaign_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """取本人本活动的 A-027「文件评审记录」；自动填充评审组成员/本人评审文件/记录人/审批人默认金子铮。"""
    rec = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.campaign_id == campaign_id, ReviewRecord.reviewer_id == user.id)
        .first()
    )
    assigns = db.query(ReviewAssignment).filter(ReviewAssignment.campaign_id == campaign_id).all()
    members = []
    for a in assigns:
        if a.reviewer and a.reviewer not in members:
            members.append(a.reviewer)
    my_files = []
    for a in assigns:
        if a.reviewer_id == user.id:
            d = db.get(Document, a.document_id)
            if d:
                my_files.append({
                    "document_id": a.document_id,
                    "title": d.title or "",
                    "doc_number": getattr(d, "doc_number", "") or "",
                    "version": str(getattr(d, "version", "") or ""),
                })
    existing = {}
    if rec and rec.record_json:
        try:
            existing = json.loads(rec.record_json)
        except Exception:
            existing = {}
    return {
        "id": rec.id if rec else None,
        "status": rec.status if rec else "待提交",
        "review_group": existing.get("review_group") or "生免组",
        "review_date": existing.get("review_date") or "",
        "review_members": existing.get("review_members") or "、".join(members),
        "recorder": existing.get("recorder") or (user.full_name or user.username),
        "approver": existing.get("approver") or DEFAULT_APPROVER,
        "record_date": existing.get("record_date") or "",
        "approve_date": existing.get("approve_date") or "",
        "problems": existing.get("problems") or "",
        "files": existing.get("files") or my_files,
        "submitted_at": rec.submitted_at.isoformat() if rec and rec.submitted_at else None,
    }


@review_router.post("/review/my-record")
def upsert_my_record(
    campaign_id: int,
    body: dict = {},
    submit: bool = False,
    reviewer_id: int | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按人 upsert A-027「文件评审记录」。submit=True 时标记已提交。

    - 默认按当前登录用户写入（本人填自己的）。
    - 管理员可传 reviewer_id 代填他人（如成员忘记提交时管理员补录）。
    """
    target = user
    if reviewer_id and _is_admin(user):
        t = db.get(User, reviewer_id)
        if t:
            target = t
    data = body.get("record_json", body) if isinstance(body, dict) else {}
    if not isinstance(data, dict):
        data = {}
    js = json.dumps(data, ensure_ascii=False)
    rec = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.campaign_id == campaign_id, ReviewRecord.reviewer_id == target.id)
        .first()
    )
    if not rec:
        rec = ReviewRecord(campaign_id=campaign_id, reviewer_id=target.id, reviewer=target.full_name or target.username)
        db.add(rec)
    rec.record_json = js
    rec.status = "已提交" if submit else "已填写"
    if submit:
        rec.submitted_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "id": rec.id, "status": rec.status}


@review_router.post("/review/assignments/{aid}/upload-revision")
def upload_revision(
    aid: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    if a.reviewer_id and a.reviewer_id != user.id and not _is_admin(user):
        raise HTTPException(403, "仅被分配人或管理员可上传修订文件")
    content = file.file.read()
    if not content:
        raise HTTPException(400, "文件内容为空")
    if not cos_storage.ready:
        raise HTTPException(400, "云存储未配置，无法上传修订文件")
    key = cos_storage.save("review", file.filename or f"revised-{aid}", content)
    a.revised_cloud_key = key
    a.revised_filename = file.filename or f"revised-{aid}"
    db.commit()
    return {"ok": True, "cloud_key": key, "filename": a.revised_filename}


@review_router.get("/review/assignments/{aid}/download-revision")
def download_revision(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    if not a.revised_cloud_key:
        raise HTTPException(404, "无修订文件")
    content = cos_storage.get_bytes(a.revised_cloud_key)
    if not content:
        raise HTTPException(404, "文件读取失败")
    fname = a.revised_filename or f"revised-{aid}"
    ascii_name = fname.encode("ascii", "ignore").decode("ascii") or "download"
    return StreamingResponse(
        BytesIO(content),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(fname)}',
            "Content-Length": str(len(content)),
            "Cache-Control": "no-store",
        },
    )


@review_router.post("/review/assignments/{aid}/submit")
def submit_review(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """成员提交其修订（仅标记该分配项已提交，A-027 另由 /review/my-record 提交）。"""
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    if a.reviewer_id and a.reviewer_id != user.id and not _is_admin(user):
        raise HTTPException(403, "仅被分配人或管理员可提交")
    a.status = "已提交"
    a.submitted_at = datetime.utcnow()
    db.commit()
    return {"ok": True, "id": aid, "status": a.status}


@review_router.post("/review/assignments/{aid}/receive")
def receive_revision(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """管理员接收成员修订，并据此为该文档生成新版本（复用 documents 版本逻辑）。"""
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    if not a.revised_cloud_key:
        raise HTTPException(400, "成员尚未上传修订文件")
    content = cos_storage.get_bytes(a.revised_cloud_key)
    if not content:
        raise HTTPException(400, "修订文件读取失败")
    d = db.get(Document, a.document_id)
    if not d:
        raise HTTPException(404, "关联文档不存在")
    try:
        maj, minor = str(d.version).split(".")
        new_ver = f"{maj}.{int(minor) + 1}"
    except Exception:
        new_ver = f"{d.version}.1"
    fname = a.revised_filename or d.title or "doc"
    key = cos_storage.save("documents", fname, content)
    rel = storage.save("docs", fname, content)
    d.version = new_ver
    d.file_path = rel
    d.cloud_key = key
    d.data = None
    d.original_filename = fname
    d.updated_at = datetime.utcnow()
    dv = DocumentVersion(
        document_id=d.id, version=new_ver, file_path=rel, cloud_key=key,
        data=None, uploader=user.full_name or user.username,
        note=f"内审文件评审接收（分配项#{a.id}）",
    )
    db.add(dv)
    a.status = "管理员已接收"
    a.document_new_version = new_ver
    a.admin_received_at = datetime.utcnow()
    db.commit()
    write_audit(db, user, "update", "documents", d.id, {"version": new_ver, "source": "review"})
    return {"ok": True, "id": aid, "document_id": d.id, "new_version": new_ver, "status": a.status}


@review_router.get("/review/campaigns/{cid}/summary")
def review_summary(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """按人汇总 A-027「文件评审记录」（每人一份），并附其被分配文件的接收情况。"""
    recs = db.query(ReviewRecord).filter(ReviewRecord.campaign_id == cid).all()
    out = []
    for r in recs:
        data = {}
        if r.record_json:
            try:
                data = json.loads(r.record_json)
            except Exception:
                data = {}
        assigns = (
            db.query(ReviewAssignment)
            .filter(ReviewAssignment.campaign_id == cid, ReviewAssignment.reviewer_id == r.reviewer_id)
            .all()
        )
        assign_files = []
        for a in assigns:
            d = db.get(Document, a.document_id)
            assign_files.append({
                "document_id": a.document_id,
                "title": d.title if d else "",
                "status": a.status,
                "new_version": a.document_new_version,
            })
        out.append({
            "reviewer": r.reviewer,
            "status": r.status,
            "review_members": data.get("review_members", ""),
            "review_files": data.get("files", []),
            "problems": data.get("problems", ""),
            "recorder": data.get("recorder", ""),
            "approver": data.get("approver", ""),
            "record_date": data.get("record_date", ""),
            "approve_date": data.get("approve_date", ""),
            "assign_files": assign_files,
            "submitted_at": r.submitted_at.isoformat() if r.submitted_at else None,
        })
    return out
