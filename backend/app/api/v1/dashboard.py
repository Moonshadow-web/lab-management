"""工作台统计接口——一次请求返回所有模块计数，避免前端并发 9 个 list 接口。"""

from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.test_item import TestItem
from app.models.instrument import Instrument
from app.models.document import Document
from app.models.notification import Notification
from app.models.qc import QCRecord
from app.models.reagent import Reagent
from app.models.training import TrainingRecord
from app.models.verification import VerificationRecord
from app.models.nonconformity import Nonconformity

router = APIRouter(tags=["dashboard"])

_STATS_MODELS = [
    ("test_items", TestItem),
    ("instruments", Instrument),
    ("documents", Document),
    ("qc_records", QCRecord),
    ("reagents", Reagent),
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

    # 待办提醒：未读数
    unread_stmt = (
        select(func.count())
        .select_from(Notification)
        .where(Notification.is_read == False)  # noqa: E712
    )
    unread = db.execute(unread_stmt).scalar() or 0
    result["unread_notifications"] = unread

    return result
