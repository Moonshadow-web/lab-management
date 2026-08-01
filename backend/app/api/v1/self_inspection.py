"""自查（条款内审）子模块 API：条款字典 + 活动 + 按分工分配条款给员工 + 员工逐条填写 + 汇总。

流程：
  管理员导入 CNAS-AL02-07 附表3 条款字典 → 建自查活动 → 按 2026.7.23 分工模板把条款分给员工 →
  员工登录看到自己分配的条款 → 参考内审检查表格式逐条填写（核查内容/结果/问题/措施）→ 提交 →
  管理员汇总。
"""
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.iso15189 import (
    AuditClause,
    SelfInspectionAssignment,
    SelfInspectionCampaign,
    SelfInspectionRecord,
)
from ...models.user import User
from ...schemas import (
    AuditClauseCreate,
    AuditClauseRead,
    AuditClauseUpdate,
    SelfInspectionAssignmentCreate,
    SelfInspectionAssignmentRead,
    SelfInspectionAssignmentUpdate,
    SelfInspectionCampaignCreate,
    SelfInspectionCampaignRead,
    SelfInspectionCampaignUpdate,
    SelfInspectionRecordCreate,
    SelfInspectionRecordRead,
    SelfInspectionRecordUpdate,
)

WRITE_ROLES = (
    "admin", "quality_manager", "qc_manager", "training_manager",
    "reagent_manager", "it_manager", "specialty_leader",
)
CLAUSE_WRITE_ROLES = ("admin", "quality_manager", "specialty_leader", "qc_manager", "training_manager")


def _is_admin(user: User) -> bool:
    return user.role == "admin" or "admin" in (user.roles or "").split(",")


def _assign_to_read(obj) -> SelfInspectionAssignmentRead:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    raw = d.get("clause_ids")
    if isinstance(raw, str) and raw.strip():
        try:
            d["clause_ids"] = json.loads(raw)
        except Exception:
            d["clause_ids"] = []
    else:
        d["clause_ids"] = raw or []
    return SelfInspectionAssignmentRead.model_validate(d)


def _rec_to_read(obj) -> SelfInspectionRecordRead:
    d = {c.name: getattr(obj, c.name) for c in obj.__table__.columns}
    return SelfInspectionRecordRead.model_validate(d)


si_router = APIRouter(tags=["self-inspection"])

clause_router = make_router(
    AuditClause, AuditClauseRead, AuditClauseCreate, AuditClauseUpdate,
    search_fields=["clause_no", "chapter", "title", "content"],
    filter_fields=["chapter"],
    order_by=[AuditClause.clause_no.asc()],
    prefix="/audit-clauses",
    write_roles=CLAUSE_WRITE_ROLES,
)
camp_router = make_router(
    SelfInspectionCampaign, SelfInspectionCampaignRead,
    SelfInspectionCampaignCreate, SelfInspectionCampaignUpdate,
    search_fields=["title", "year", "note"],
    prefix="/self-inspection/campaigns",
    write_roles=WRITE_ROLES,
)
assign_router = make_router(
    SelfInspectionAssignment, SelfInspectionAssignmentRead,
    SelfInspectionAssignmentCreate, SelfInspectionAssignmentUpdate,
    search_fields=["assignee", "note"],
    filter_fields=["campaign_id", "assignee_id", "status"],
    json_fields=["clause_ids"],
    prefix="/self-inspection/assignments",
    write_roles=WRITE_ROLES,
)
record_router = make_router(
    SelfInspectionRecord, SelfInspectionRecordRead,
    SelfInspectionRecordCreate, SelfInspectionRecordUpdate,
    search_fields=["assignee", "finding", "check_content"],
    filter_fields=["campaign_id", "assignment_id", "clause_id", "result"],
    prefix="/self-inspection/records",
    write_roles=WRITE_ROLES,
)
si_router.include_router(clause_router)
si_router.include_router(camp_router)
si_router.include_router(assign_router)
si_router.include_router(record_router)


@si_router.post("/audit-clauses/batch-import")
def batch_import_clauses(
    items: list[dict],
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*CLAUSE_WRITE_ROLES)),
):
    """批量导入条款字典。items: [{clause_no, chapter, title, content, check_point}]。"""
    created = []
    for it in items:
        if not it.get("clause_no") and not it.get("title"):
            continue
        c = AuditClause(
            clause_no=it.get("clause_no", "") or "",
            chapter=it.get("chapter", "") or "",
            title=it.get("title", "") or "",
            content=it.get("content", "") or "",
            check_point=it.get("check_point", "") or "",
        )
        db.add(c)
        db.flush()
        created.append(c.id)
    db.commit()
    write_audit(db, user, "create", "audit_clauses", 0, {"count": len(created)})
    return {"ok": True, "created": created}


@si_router.post("/self-inspection/campaigns/{cid}/assign-batch")
def assign_clauses_batch(
    cid: int,
    items: list[dict],
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """批量把条款分配给员工。items: [{assignee, assignee_id, clause_ids:[id...], clause_range}]。"""
    created = []
    for it in items:
        a = SelfInspectionAssignment(
            campaign_id=cid,
            assignee=it.get("assignee", "") or "",
            assignee_id=it.get("assignee_id"),
            clause_ids=json.dumps(it.get("clause_ids", []), ensure_ascii=False),
            clause_range=it.get("clause_range", "") or "",
            status="待自查",
        )
        db.add(a)
        db.flush()
        created.append(a.id)
    db.commit()
    write_audit(db, user, "create", "self_inspection_assignments", cid, {"count": len(created)})
    return {"ok": True, "created": created}


@si_router.delete("/self-inspection/campaigns/{cid}/cascade")
def delete_self_inspection_campaign_cascade(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """级联删除自查活动：先删记录、再删分配、最后删活动。"""
    camp = db.get(SelfInspectionCampaign, cid)
    if not camp:
        raise HTTPException(404, "活动不存在")
    db.query(SelfInspectionRecord).filter(SelfInspectionRecord.campaign_id == cid).delete(synchronize_session=False)
    db.query(SelfInspectionAssignment).filter(SelfInspectionAssignment.campaign_id == cid).delete(synchronize_session=False)
    db.delete(camp)
    db.commit()
    write_audit(db, user, "delete", "self_inspection_campaigns", cid, {"cascade": True})
    return {"ok": True, "id": cid}


@si_router.get("/self-inspection/my-assignments")
def my_assignments(
    campaign_id: Optional[int] = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    q = db.query(SelfInspectionAssignment).filter(SelfInspectionAssignment.assignee_id == user.id)
    if campaign_id:
        q = q.filter(SelfInspectionAssignment.campaign_id == campaign_id)
    items = q.order_by(SelfInspectionAssignment.id.desc()).all()
    return [_assign_to_read(a) for a in items]


@si_router.get("/self-inspection/assignments/{aid}/clauses")
def assignment_clauses(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.get(SelfInspectionAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    ids = a.clause_ids
    if isinstance(ids, str):
        try:
            ids = json.loads(ids)
        except Exception:
            ids = []
    ids = ids or []
    clauses = (
        db.query(AuditClause)
        .filter(AuditClause.id.in_(ids))
        .order_by(AuditClause.clause_no)
        .all()
    ) if ids else []
    recs = db.query(SelfInspectionRecord).filter(SelfInspectionRecord.assignment_id == aid).all()
    rec_map = {r.clause_id: r for r in recs}
    out = []
    for c in clauses:
        r = rec_map.get(c.id)
        out.append({
            "clause": {
                "id": c.id, "clause_no": c.clause_no, "chapter": c.chapter,
                "title": c.title, "content": c.content, "check_point": c.check_point,
            },
            "record": _rec_to_read(r) if r else None,
        })
    return out


@si_router.post("/self-inspection/records/upsert")
def upsert_record(
    payload: dict,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assignment_id = payload.get("assignment_id")
    clause_id = payload.get("clause_id")
    if not clause_id:
        raise HTTPException(400, "clause_id 必填")
    existing = db.query(SelfInspectionRecord).filter_by(
        assignment_id=assignment_id, clause_id=clause_id
    ).first()
    data = {
        "campaign_id": payload.get("campaign_id"),
        "assignment_id": assignment_id,
        "clause_id": clause_id,
        "assignee": user.full_name or user.username,
        "check_content": payload.get("check_content", "") or "",
        "result": payload.get("result", "") or "",
        "finding": payload.get("finding", "") or "",
        "action": payload.get("action", "") or "",
        "filled_at": datetime.utcnow(),
    }
    if existing:
        for k, v in data.items():
            setattr(existing, k, v)
        obj = existing
    else:
        obj = SelfInspectionRecord(**data)
        db.add(obj)
    db.commit()
    db.refresh(obj)
    return _rec_to_read(obj)


@si_router.post("/self-inspection/assignments/{aid}/submit")
def submit_assignment(
    aid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    a = db.get(SelfInspectionAssignment, aid)
    if not a:
        raise HTTPException(404, "未找到分配项")
    if a.assignee_id and a.assignee_id != user.id and not _is_admin(user):
        raise HTTPException(403, "仅被分配人或管理员可提交")
    a.status = "已提交"
    db.commit()
    return {"ok": True, "id": aid, "status": a.status}


@si_router.get("/self-inspection/campaigns/{cid}/summary")
def self_inspection_summary(
    cid: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    assigns = db.query(SelfInspectionAssignment).filter_by(campaign_id=cid).all()
    out = []
    for a in assigns:
        ids = a.clause_ids
        if isinstance(ids, str):
            try:
                ids = json.loads(ids)
            except Exception:
                ids = []
        ids = ids or []
        recs = db.query(SelfInspectionRecord).filter_by(assignment_id=a.id).all()
        rec_map = {r.clause_id: r for r in recs}
        clauses = (
            db.query(AuditClause)
            .filter(AuditClause.id.in_(ids))
            .order_by(AuditClause.clause_no)
            .all()
        ) if ids else []
        clause_out = []
        for c in clauses:
            r = rec_map.get(c.id)
            clause_out.append({
                "clause_no": c.clause_no, "chapter": c.chapter, "title": c.title,
                "content": c.content, "check_point": c.check_point,
                "result": r.result if r else "",
                "finding": r.finding if r else "",
                "action": r.action if r else "",
                "check_content": r.check_content if r else "",
            })
        out.append({
            "assignment_id": a.id, "assignee": a.assignee,
            "clause_range": a.clause_range, "clause_count": len(clause_out),
            "status": a.status, "clauses": clause_out,
        })
    return out
