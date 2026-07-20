from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, UniqueConstraint
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


class NotificationRead(Base):
    """每用户维度的「已读」记录。

    保留 Notification.is_read(全局字段)作兼容兜底，但所有已读判定/写入
    都走本表，实现「账号A已读不影响账号B」的隔离。
    """

    __tablename__ = "notification_reads"
    __table_args__ = (
        UniqueConstraint("user_id", "notification_id", name="uq_notif_read_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(default=0, index=True)  # 已读用户
    notification_id: Mapped[int] = mapped_column(default=0, index=True)  # 对应通知
    read_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
