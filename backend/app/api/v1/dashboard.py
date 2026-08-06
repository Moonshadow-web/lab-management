"""工作台统计接口——一次请求返回所有模块计数，避免前端并发 9 个 list 接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.test_item import TestItem
from app.models.instrument import Instrument
from app.models.document import Document
from app.models.notification import Notification, NotificationRead
from app.models.qc import QCRecord
from app.models.reagent_management import ReagentItem
from app.models.training import TrainingRecord
from app.models.verification import VerificationRecord
from app.models.nonconformity import Nonconformity

router = APIRouter(tags=["dashboard"])

_STATS_MODELS = [
    ("test_items", TestItem),
    ("instruments", Instrument),
    ("documents", Document),
    ("qc_records", QCRecord),
    ("training_records", TrainingRecord),
    ("verification_records", VerificationRecord),
    ("nonconformities", Nonconformity),
]


@router.get("/dashboard/stats")
async def dashboard_stats(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    """返回工作台各模块的记录总数 + 未读提醒数。"""
    result = {}

    for key, model in _STATS_MODELS:
        stmt = select(func.count()).select_from(model)
        count = db.execute(stmt).scalar() or 0
        result[key] = count

    # 试剂目录：按类型统计（仅启用），用于工作台试剂统计卡片
    reagent_counts = {"试剂": 0, "校准品": 0, "耗材": 0, "质控品": 0}
    rows = db.execute(
        select(ReagentItem.type, func.count())
        .where(ReagentItem.is_active == True)
        .group_by(ReagentItem.type)
    ).all()
    for t, n in rows:
        if t in reagent_counts:
            reagent_counts[t] = n
    result["reagents"] = sum(reagent_counts.values())
    result["reagent_counts"] = reagent_counts

    # 待办提醒：当前用户「可见且未读」数（私密消息 recipient_user_id=本人，广播 NULL 对所有人可见）
    read_subq = (
        select(NotificationRead.notification_id)
        .where(NotificationRead.user_id == user.id)
        .subquery()
    )
    unread_stmt = (
        select(func.count())
        .select_from(Notification)
        .outerjoin(read_subq, Notification.id == read_subq.c.notification_id)
        .where(
            (Notification.recipient_user_id.is_(None))
            | (Notification.recipient_user_id == user.id),
            read_subq.c.notification_id.is_(None),
        )
    )
    unread = db.execute(unread_stmt).scalar() or 0
    result["unread_notifications"] = unread

    return result
