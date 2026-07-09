from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


NOTIFY_LEVELS = ["info", "warning", "danger"]


class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(primary_key=True)
    module: Mapped[str] = mapped_column(String(50), default="")  # 所属模块
    ref_type: Mapped[str] = mapped_column(String(50), default="")  # 关联类型（如 instrument）
    ref_id: Mapped[int] = mapped_column(default=0)  # 关联记录 id
    title: Mapped[str] = mapped_column(String(200), default="")
    message: Mapped[str] = mapped_column(String(500), default="")
    due_date: Mapped[str] = mapped_column(String(30), default="")  # 到期日
    level: Mapped[str] = mapped_column(String(20), default="info")  # info/warning/danger
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
