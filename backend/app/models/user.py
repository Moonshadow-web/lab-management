from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(100), default="")
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="member")  # 粗粒度权限级别: admin / leader / member
    roles: Mapped[str] = mapped_column(String(200), default="")  # 详细组织角色,逗号分隔: admin,specialty_leader,qc_manager...
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=True)  # 首次登录强制改密
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)  # 连续登录失败次数
    locked_until: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 锁定截止时间
    department: Mapped[str] = mapped_column(String(100), default="")
    email: Mapped[str] = mapped_column(String(120), default="")  # 接收提醒邮件的邮箱
    notify_email: Mapped[bool] = mapped_column(Boolean, default=True)  # 是否接收邮件提醒
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
