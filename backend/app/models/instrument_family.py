"""项目「使用仪器」总型号(family) → 仪器档案(instruments) 的关联关系表。

项目表 `test_items.instrument` 存的是用户填的「总型号」（如「罗氏 Cobas6000」
「AU生化仪」「DxI800」），一台总型号往往对应多台具体仪器（罗氏 Cobas6000 =
e601/e602/e411）。本模块把这种「一对多」关系固化成数据库关联表，替代原先写死在
代码里的 FAMILY_MAP，并提供管理界面维护。

- `instrument_families`：总型号定义（name 唯一，对应 test_items.instrument 取值）。
- `instrument_family_members`：总型号 ↔ 具体仪器 的关联行。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class InstrumentFamily(Base):
    __tablename__ = "instrument_families"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, default="")
    description: Mapped[str] = mapped_column(String(200), default="")  # 备注说明
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InstrumentFamilyMember(Base):
    __tablename__ = "instrument_family_members"
    __table_args__ = (
        UniqueConstraint("family_id", "instrument_id", name="uq_family_instrument"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    family_id: Mapped[int] = mapped_column(ForeignKey("instrument_families.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
