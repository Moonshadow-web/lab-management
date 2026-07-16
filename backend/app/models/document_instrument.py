"""文档(documents) ↔ 仪器(instruments) 的关联关系表。

用于把「操作/保养记录」等文档挂到对应仪器，使仪器档案页能反向展示该仪器
关联的文档（如某台分析仪的操作+保养记录）。一份文档可关联多台仪器（如
「贝克曼DXI800 1+2操作记录」同时属于 DXI800 1 与 DXI800 2），一台仪器也可
关联多份文档，故为多对多关联行。
"""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class DocumentInstrument(Base):
    __tablename__ = "document_instruments"
    __table_args__ = (
        UniqueConstraint("document_id", "instrument_id", name="uq_document_instrument"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"), index=True)
    instrument_id: Mapped[int] = mapped_column(Integer, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
