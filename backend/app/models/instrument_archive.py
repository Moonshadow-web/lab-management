from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class InstrumentArchive(Base):
    """仪器档案文件：每个仪器对应一个档案文件（如 MHZYY-JYK-SM-xxxx-名称.docx）。"""

    __tablename__ = "instrument_archives"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(Integer, index=True)
    filename: Mapped[str] = mapped_column(String(500), default="")  # 存储相对路径 instrument_archives/xxx
    original_filename: Mapped[str] = mapped_column(String(500), default="")  # 原始文件名
    file_size: Mapped[int] = mapped_column(Integer, default=0)
    file_ext: Mapped[str] = mapped_column(String(20), default="")  # .docx / .pdf / .doc
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
