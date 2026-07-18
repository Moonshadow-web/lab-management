from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class RefreshToken(Base):
    """refresh token 吊销登记表。

    refresh token 本身是带 exp/jti 的 JWT（无状态），这里仅记录 jti 以便：
    - 登出时吊销（使已签发的 refresh token 立即失效，避免被盗用）
    - 改密时吊销该用户全部 refresh token（强制重新登录）
    不做轮换（reuse），多个标签页共享同一 refresh token 不会互相踢下线。
    """

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    revoked: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
