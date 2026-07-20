from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.config import SYSTEM_NAME
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.notification import Notification, NotificationRead
from ...models.user import User
from ...services.email_service import send_email, send_notifications_email
from ...services.notification_service import get_email_recipients

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    page: int = 1,
    page_size: int = 50,
    unread_only: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # 当前用户已读通知 id 子查询（按用户维度，互不影响）
    read_subq = db.query(NotificationRead.notification_id).filter(
        NotificationRead.user_id == user.id
    ).subquery()

    query = db.query(Notification).outerjoin(
        read_subq, Notification.id == read_subq.c.notification_id
    )
    if unread_only:
        # 未读 = 该用户在 notification_reads 中无对应记录
        query = query.filter(read_subq.c.notification_id.is_(None))
    # 未读在前、已读在后；同级按等级、ID 倒序
    query = query.order_by(
        read_subq.c.notification_id.is_(None).desc(),
        Notification.level.desc(),
        Notification.id.desc(),
    )
    total = query.count()
    rows = query.offset((page - 1) * page_size).limit(page_size).all()

    read_ids = {
        rid for (rid,) in db.query(NotificationRead.notification_id)
        .filter(NotificationRead.user_id == user.id).all()
    }
    items = [{
        "id": n.id,
        "module": n.module,
        "ref_type": n.ref_type,
        "ref_id": n.ref_id,
        "title": n.title,
        "message": n.message,
        "due_date": n.due_date,
        "level": n.level,
        "is_read": n.id in read_ids,  # 按当前用户维度判定
        "created_at": n.created_at.isoformat() if n.created_at else None,
    } for n in rows]
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {"items": items, "total": total, "page": page, "pages": pages, "page_size": page_size}


@router.post("/{nid}/read")
def mark_read(nid: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    n = db.get(Notification, nid)
    if not n:
        raise HTTPException(status_code=404, detail="未找到提醒")
    # 仅记录「当前用户已读」，不影响其他账号
    exists = db.query(NotificationRead).filter(
        NotificationRead.user_id == user.id,
        NotificationRead.notification_id == nid,
    ).first()
    if not exists:
        db.add(NotificationRead(user_id=user.id, notification_id=nid))
        db.commit()
    return {"ok": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    # 取该用户尚未标记已读的通知，逐条写入 notification_reads
    already = db.query(NotificationRead.notification_id).filter(
        NotificationRead.user_id == user.id
    ).subquery()
    pending = (
        db.query(Notification.id)
        .outerjoin(already, Notification.id == already.c.notification_id)
        .filter(already.c.notification_id.is_(None))
        .all()
    )
    for (nid,) in pending:
        db.add(NotificationRead(user_id=user.id, notification_id=nid))
    db.commit()
    return {"ok": True}


@router.post("/send")
def send_notifications_by_email(
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """将当前所有未读提醒汇总，通过邮件发给接收人（role=admin/leader 且已配置邮箱并开启通知）。

    返回 {"sent": 已真正发送人数, "logged": 降级记录人数, "recipients": 接收人总数, "results": [...]}。
    """
    recipients = get_email_recipients(db)
    if not recipients:
        return {
            "sent": 0,
            "logged": 0,
            "recipients": 0,
            "detail": "无邮件接收人（需给用户配置邮箱、role 为 admin/leader 且开启通知）",
        }
    # 发「当前管理员（admin）未读」的通知，与列表判定一致
    read_subq = db.query(NotificationRead.notification_id).filter(
        NotificationRead.user_id == admin.id
    ).subquery()
    pending = (
        db.query(Notification)
        .outerjoin(read_subq, Notification.id == read_subq.c.notification_id)
        .filter(read_subq.c.notification_id.is_(None))
        .order_by(Notification.level.desc(), Notification.id.desc())
        .all()
    )
    if not pending:
        return {"sent": 0, "logged": 0, "recipients": len(recipients), "detail": "当前没有未读提醒"}
    return send_notifications_email([r.email for r in recipients], pending)


@router.post("/test-email")
def test_email(
    to: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """发送一封测试邮件，用于校验 SMTP 配置是否正确（仅管理员）。

    to 不传时发往当前管理员的邮箱；SMTP 未配置时走降级日志（返回 smtp_not_configured_logged）。
    """
    target = to or admin.email
    if not target:
        raise HTTPException(status_code=400, detail="未提供收件地址且当前管理员未配置邮箱")
    subject = f"【{SYSTEM_NAME}】邮件发送测试"
    body = "这是一封来自实验室管理系统的测试邮件。若您收到，说明 SMTP 邮件配置正确。"
    return send_email(target, subject, text=body, html=f"<p>{body}</p>")
