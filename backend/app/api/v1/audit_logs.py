"""审计日志查询接口：仅管理员可访问，支持按用户/操作/表名/时间范围过滤。"""
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.audit_log import AuditLog
from ...models.user import User

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


@router.get("")
def list_audit_logs(
    page: int = 1,
    page_size: int = 50,
    user_id: int | None = None,
    action: str | None = None,
    table_name: str | None = None,
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    query = db.query(AuditLog)
    if user_id is not None:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if start_date:
        try:
            sd = datetime.strptime(start_date, "%Y-%m-%d")
            query = query.filter(AuditLog.created_at >= sd)
        except ValueError:
            pass
    if end_date:
        try:
            ed = datetime.strptime(end_date, "%Y-%m-%d").replace(hour=23, minute=59, second=59)
            query = query.filter(AuditLog.created_at <= ed)
        except ValueError:
            pass
    total = query.count()
    items = query.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size if page_size else 0
    # 关联用户名
    user_ids = {i.user_id for i in items if i.user_id}
    user_map = {u.id: u.full_name for u in db.query(User).filter(User.id.in_(user_ids)).all()} if user_ids else {}
    result = []
    for i in items:
        result.append({
            "id": i.id,
            "user_id": i.user_id,
            "user_name": user_map.get(i.user_id, "—"),
            "action": i.action,
            "table_name": i.table_name,
            "record_id": i.record_id,
            "detail": i.detail,
            "ip": i.ip,
            "created_at": i.created_at.strftime("%Y-%m-%d %H:%M:%S") if i.created_at else "",
        })
    return {"items": result, "total": total, "page": page, "pages": pages, "page_size": page_size}


@router.get("/actions")
def list_actions(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """返回所有已出现的操作类型（用于前端筛选下拉）。"""
    rows = db.query(AuditLog.action).distinct().all()
    return [r[0] for r in rows if r[0]]


@router.get("/tables")
def list_tables(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """返回所有已出现的表名（用于前端筛选下拉）。"""
    rows = db.query(AuditLog.table_name).distinct().all()
    return [r[0] for r in rows if r[0]]
