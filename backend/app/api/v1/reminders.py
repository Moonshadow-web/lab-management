"""提醒设置 API：发送人管理、提醒类型管理、立即运行、发送记录。"""
from datetime import date, datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.reminder import NotifyRecipient, ReminderRule, ReminderSendLog
from ...models.user import User
from ...services.reminder_engine import ensure_reminder_defaults, run_reminders

router = APIRouter(prefix="/reminders", tags=["reminders"])


# ---------------- 发送人 ----------------
class RecipientIn(BaseModel):
    name: str
    email: str = ""
    phone: str = ""
    channels: str = "email"
    enabled: bool = True
    rule_categories: str = ""   # 订阅的提醒分类(CSV)；空=不接收
    note: str = ""


class RecipientUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    channels: Optional[str] = None
    enabled: Optional[bool] = None
    rule_categories: Optional[str] = None
    note: Optional[str] = None


@router.get("/recipients")
def list_recipients(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    rows = db.query(NotifyRecipient).order_by(NotifyRecipient.id).all()
    return rows


@router.post("/recipients")
def create_recipient(body: RecipientIn, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    r = NotifyRecipient(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/recipients/{rid}")
def update_recipient(rid: int, body: RecipientUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    r = db.get(NotifyRecipient, rid)
    if not r:
        raise HTTPException(status_code=404, detail="接收人不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return r


@router.delete("/recipients/{rid}")
def delete_recipient(rid: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    r = db.get(NotifyRecipient, rid)
    if not r:
        raise HTTPException(status_code=404, detail="接收人不存在")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ---------------- 提醒类型 ----------------
class RuleIn(BaseModel):
    category: str = ""
    label: str
    ref_kind: str = "eqa"          # eqa / calibration
    enabled: bool = True
    lead_days: int = 14
    escalate_days_left: str = "7"
    scope_kind: str = "group"       # group / all
    scope_values: str = ""
    note: str = ""


class RuleUpdate(BaseModel):
    label: Optional[str] = None
    ref_kind: Optional[str] = None
    enabled: Optional[bool] = None
    lead_days: Optional[int] = None
    escalate_days_left: Optional[str] = None
    scope_kind: Optional[str] = None
    scope_values: Optional[str] = None
    note: Optional[str] = None


@router.get("/rules")
def list_rules(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    rows = db.query(ReminderRule).order_by(ReminderRule.id).all()
    return rows


@router.post("/rules")
def create_rule(body: RuleIn, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    if body.category:
        if db.query(ReminderRule).filter(ReminderRule.category == body.category).first():
            raise HTTPException(status_code=400, detail="该 category 已存在")
    r = ReminderRule(**body.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/rules/{rid}")
def update_rule(rid: int, body: RuleUpdate, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    r = db.get(ReminderRule, rid)
    if not r:
        raise HTTPException(status_code=404, detail="规则不存在")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    r.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(r)
    return r


@router.delete("/rules/{rid}")
def delete_rule(rid: int, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    r = db.get(ReminderRule, rid)
    if not r:
        raise HTTPException(status_code=404, detail="规则不存在")
    db.delete(r)
    db.commit()
    return {"ok": True}


# ---------------- 运行 / 预览 / 记录 ----------------
@router.post("/run")
def run_now(
    as_of: Optional[str] = None,
    dry_run: bool = False,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles("admin")),
):
    """立即评估并发送（或 dry_run 只预览）。as_of=YYYY-MM-DD 便于测试升级逻辑。"""
    as_of_date = None
    if as_of:
        try:
            as_of_date = datetime.strptime(as_of, "%Y-%m-%d").date()
        except Exception:
            raise HTTPException(status_code=400, detail="as_of 格式应为 YYYY-MM-DD")
    stats = run_reminders(db, as_of=as_of_date, dry_run=dry_run)
    return stats


@router.get("/send-log")
def send_log(limit: int = 50, db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    rows = (
        db.query(ReminderSendLog)
        .order_by(ReminderSendLog.last_sent_at.desc(), ReminderSendLog.id.desc())
        .limit(limit)
        .all()
    )
    return rows


@router.post("/init-defaults")
def init_defaults(db: Session = Depends(get_db), _: User = Depends(require_roles("admin"))):
    """（重新）写入默认规则与默认接收人（若库为空）。"""
    ensure_reminder_defaults(db)
    return {"ok": True}
