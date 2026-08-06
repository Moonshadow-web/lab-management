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

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ...core.cos_storage import cos_storage
from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.docx_utils import accept_all_track_changes, is_docx, update_docx_header_table
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
    "reagent_manager", "it_manager", "specialty_leader", "leader",
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
# 评审计划删除必须级联：移除 make_router 自带的非级联 DELETE（计划有分配时会因外键约束 500），
# 改由下方 /review/campaigns/{cid} 与 /review/campaigns/{cid}/cascade 统一级联处理，避免旧前端缓存误调标准删除而失败。
campaign_router.routes = [
    r for r in campaign_router.routes
    if not (getattr(r, "path", "") in ("/{item_id}", "/review/campaigns/{item_id}")
            and "DELETE" in getattr(r, "methods", set()))
]
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
    - 文件评审范围仅限三类 SOP（通用SOP/项目SOP/仪器SOP），非 SOP 类（如「项目说明书」）
      不在评审范围内，直接拒绝分配并回执 rejected 列表。
    """
    doc_ids = [int(it["document_id"]) for it in items if it.get("document_id")]
    docs = (
        {d.id: d for d in db.query(Document).filter(Document.id.in_(doc_ids)).all()}
        if doc_ids else {}
    )
    all_assigns = db.query(ReviewAssignment).filter(ReviewAssignment.campaign_id == cid).all()
    existing = {
        (a.document_id, a.reviewer_id, a.reviewer)
        for a in all_assigns
    }
    # 已释放（空审核人）的分配行，按文档去重：重新分配时复用，避免重复创建行
    released_map: dict[int, int] = {}
    for a in all_assigns:
        if a.reviewer_id is None and not (a.reviewer or "").strip():
            released_map.setdefault(a.document_id, a.id)
    created = []
    rejected = []
    for it in items:
        doc_id = it.get("document_id")
        if not doc_id:
            continue
        doc_id = int(doc_id)
        rid = it.get("reviewer_id")
        rname = it.get("reviewer", "") or ""
        d = docs.get(doc_id)
        if d and d.category not in REVIEW_DOC_CATEGORIES:
            rejected.append({
                "document_id": doc_id,
                "title": d.title or "",
                "reason": "非SOP类文档（%s），不在文件评审范围内" % (d.category or "未知"),
            })
            continue
        if (doc_id, rid, rname) in existing:
            continue
        # 复用该文档已释放（空审核人）的分配行，而非新建重复行
        rel_id = released_map.get(doc_id)
        if rel_id is not None:
            a = db.get(ReviewAssignment, rel_id)
            a.reviewer = rname
            a.reviewer_id = rid
            a.status = "待评审"
            db.flush()
            created.append(a.id)
            existing.add((doc_id, rid, rname))
            released_map.pop(doc_id, None)
            continue
        a = ReviewAssignment(
            campaign_id=cid,
            document_id=doc_id,
            reviewer=rname,
            reviewer_id=rid,
            status="待评审",
        )
        db.add(a)
        db.flush()
        created.append(a.id)
        existing.add((doc_id, rid, rname))
    db.commit()
    write_audit(db, user, "create", "review_assignments", cid, {"count": len(created), "rejected": len(rejected)})
    return {"ok": True, "created": created, "rejected": rejected}


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


@review_router.get("/review/assignments/{aid}/opinion")
def get_assignment_opinion(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查看某分配项对应的审核人 A-027 评审意见（按文档）。

    - 审核人本人可查看；
    - 管理员/各线管理员/专业组长可查看（便于审阅）。
    """
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    user_roles = (user.roles or "").split(",")
    can_view = (
        a.reviewer_id == user.id
        or _is_admin(user)
        or user.role in WRITE_ROLES
        or any(r in WRITE_ROLES for r in user_roles)
    )
    if not can_view:
        raise HTTPException(403, "无权查看")

    d = db.get(Document, a.document_id)
    doc_title = d.title if d else ""

    rec = (
        db.query(ReviewRecord)
        .filter(ReviewRecord.campaign_id == a.campaign_id, ReviewRecord.reviewer_id == a.reviewer_id)
        .first()
    )

    files = []
    record_status = rec.status if rec else "待提交"
    submitted_at = rec.submitted_at.isoformat() if rec and rec.submitted_at else None
    if rec and rec.record_json:
        try:
            data = json.loads(rec.record_json)
            files = data.get("files", []) or []
        except Exception:
            files = []

    file_opinion = next(
        (f for f in files if str(f.get("document_id")) == str(a.document_id)),
        {},
    )

    return {
        "assignment_id": a.id,
        "document_id": a.document_id,
        "document_title": doc_title,
        "reviewer": a.reviewer,
        "reviewer_id": a.reviewer_id,
        "record_status": record_status,
        "record_submitted_at": submitted_at,
        "comment": file_opinion.get("comment", "") if file_opinion else "",
        "conclusion": file_opinion.get("conclusion", "") if file_opinion else "",
    }


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
    file: UploadFile | None = File(None),
    new_version: str = Form("2.0"),
    revision_no: str = Form("0"),
    audit_date: str = Form(""),
    approve_date: str = Form("2026-09-01"),
    effective_date: str = Form("2026-09-01"),
    accept_revisions: bool = Form(False),
    approver: str = Form(""),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """管理员审阅后接收修订，生成文档新版本。

    - file: 管理员如上传终稿，则优先用该文件；否则用成员上传的 revised_cloud_key。
    - accept_revisions=True 时，对 docx 执行「接受所有修订」。
    - 同步更新文件管理详情与 docx 首页表头：版本号/修订号/审核日期/审核人/批准日期/实施日期。
    """
    a = db.get(ReviewAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    d = db.get(Document, a.document_id)
    if not d:
        raise HTTPException(404, "关联文档不存在")

    # 取终稿字节（管理员上传 > 成员修订）
    if file is not None:
        content = file.file.read()
        fname = file.filename or a.revised_filename or d.title or "doc"
    else:
        if not a.revised_cloud_key:
            raise HTTPException(400, "成员尚未上传修订文件，请上传终稿")
        content = cos_storage.get_bytes(a.revised_cloud_key)
        if not content:
            raise HTTPException(400, "修订文件读取失败")
        fname = a.revised_filename or d.title or "doc"
    if not content:
        raise HTTPException(400, "文件内容为空")

    # 审核日期默认取成员提交日期
    if not audit_date:
        if a.submitted_at:
            audit_date = a.submitted_at.strftime("%Y-%m-%d")
        else:
            audit_date = datetime.utcnow().strftime("%Y-%m-%d")

    # 批准者：优先用户指定，其次保留原文档批准者，缺省 王学晶
    final_approver = approver or d.approver or "王学晶"
    final_reviewer = a.reviewer or d.reviewer or ""

    # docx 处理：接受修订 + 改写表头
    if is_docx(content):
        if accept_revisions:
            try:
                content = accept_all_track_changes(content)
            except Exception:
                # 接受修订失败不影响后续保存，仅记录警告
                pass
        try:
            updates = {
                "版本号": str(new_version),
                "修订号": str(revision_no),
                "审核日期": audit_date,
                "审核者": final_reviewer,
                "批准日期": approve_date,
                "实施日期": effective_date,
            }
            # 若表头是 "批准者" 而非 "批准日期"，把批准日期仍按关键词处理；
            # 但 "批准者" 不应被覆盖，只在单元格含 "批准日期" 时改值。
            content = update_docx_header_table(content, updates)
        except Exception:
            pass

    key = cos_storage.save("documents", fname, content)
    rel = storage.save("docs", fname, content)

    # 更新文件管理详情
    d.version = new_version
    d.doc_version = new_version
    d.revision = revision_no
    d.audit_date = audit_date
    d.reviewer = final_reviewer
    d.approve_date = approve_date
    d.effective_date = effective_date
    d.approver = final_approver
    d.file_path = rel
    d.cloud_key = key
    d.data = None
    d.original_filename = fname
    d.updated_at = datetime.utcnow()

    dv = DocumentVersion(
        document_id=d.id, version=new_version, file_path=rel, cloud_key=key,
        data=None, uploader=user.full_name or user.username,
        note=f"内审文件评审接收（分配项#{a.id}）",
    )
    # 版本记录也同步元数据，便于追溯
    dv.doc_version = new_version
    dv.revision = revision_no
    dv.reviewer = final_reviewer
    dv.approver = final_approver
    db.add(dv)

    a.status = "管理员已接收"
    a.document_new_version = new_version
    a.admin_received_at = datetime.utcnow()
    db.commit()
    write_audit(db, user, "update", "documents", d.id, {
        "version": new_version, "revision": revision_no, "source": "review"
    })
    return {"ok": True, "id": aid, "document_id": d.id, "new_version": new_version, "status": a.status}


@review_router.delete("/review/campaigns/{cid}")
@review_router.delete("/review/campaigns/{cid}/cascade")
def delete_campaign_cascade(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """管理员删除文件评审计划，级联删除其分配项与 A-027 记录。"""
    camp = db.get(ReviewCampaign, cid)
    if not camp:
        raise HTTPException(404, "未找到评审计划")
    db.query(ReviewRecord).filter(ReviewRecord.campaign_id == cid).delete(synchronize_session=False)
    db.query(ReviewAssignment).filter(ReviewAssignment.campaign_id == cid).delete(synchronize_session=False)
    db.delete(camp)
    db.commit()
    write_audit(db, user, "delete", "review_campaigns", cid, {"cascade": True})
    return {"ok": True}


@review_router.get("/review/campaigns/{cid}/stats-by-reviewer")
def stats_by_reviewer(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """按审核人统计当前活动的分配/提交/接收进度。作废文档不参与统计。"""
    assigns = db.query(ReviewAssignment).filter(ReviewAssignment.campaign_id == cid).all()
    # 作废文档不参与评审，跳过其分配项的统计
    doc_ids = [a.document_id for a in assigns]
    doc_status = {}
    if doc_ids:
        for d in db.query(Document.id, Document.status).filter(Document.id.in_(doc_ids)).all():
            doc_status[d.id] = d.status
    stats: dict[str, dict] = {}
    for a in assigns:
        if doc_status.get(a.document_id) == "作废":
            continue
        name = a.reviewer or "未分配"
        if name not in stats:
            stats[name] = {
                "reviewer": name,
                "reviewer_id": a.reviewer_id,
                "total": 0,
                "submitted": 0,
                "received": 0,
                "finished": 0,
            }
        stats[name]["total"] += 1
        if a.status == "已提交":
            stats[name]["submitted"] += 1
        elif a.status == "管理员已接收":
            stats[name]["received"] += 1
        elif a.status == "已完成":
            stats[name]["finished"] += 1
    # 合并 A-027 提交状态（每人一份）
    records = db.query(ReviewRecord).filter(ReviewRecord.campaign_id == cid).all()
    rec_submitted = {r.reviewer_id for r in records if r.status == "已提交"}
    for s in stats.values():
        s["a027_submitted"] = s.get("reviewer_id") in rec_submitted
    return list(stats.values())


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
            if d and d.status == "作废":
                continue
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
