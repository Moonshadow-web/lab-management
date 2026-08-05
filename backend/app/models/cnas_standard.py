from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class CnasStandard(Base):
    """CNAS / 卫生行业（WS/T）医学实验室认可规范文件。

    文件字节优先存 COS（cloud_key），COS 不可用时回退 MySQL LONGBLOB（data），
    与 documents 模块一致，避免大 PDF 撑爆 DB 内存。
    """

    __tablename__ = "cnas_standards"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(100), default="", index=True)  # 代号，如 CNAS-CL02-2023 / WS-T415-2024
    name: Mapped[str] = mapped_column(String(300), default="")               # 名称，如 医学实验室质量和能力认可准则
    category: Mapped[str] = mapped_column(String(50), default="其他")        # CNAS / WS/T / 其他
    original_filename: Mapped[str] = mapped_column(String(300), default="")  # 原始文件名
    cloud_key: Mapped[str | None] = mapped_column(String(500), nullable=True, default=None)
    data: Mapped[bytes | None] = mapped_column(LargeBinary(32 * 1024 * 1024), nullable=True)  # COS 失败兜底
    file_size: Mapped[int] = mapped_column(BigInteger, default=0)            # 字节数
    sort_order: Mapped[int] = mapped_column(Integer, default=999)            # 展示顺序（取文件名前导序号）
    uploader: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
