from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


REPORT_ARCHIVE_SOURCES = ["generated", "uploaded"]


class ReportArchive(Base):
    """性能验证报告归档（独立文件库，来源：上传 or 从新建验证生成）。

    - source_type：generated（由 verification_reports.generate 生成）/ uploaded（手动上传）
    - ref_report_id：外键关联 verification_reports.id（generated 时必填，uploaded 时为空）
    - file_path：归档文件相对路径（COS/本地，BLOB）
    - original_name：原始文件名
    """

    __tablename__ = "report_archives"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), index=True, default="")
    report_type: Mapped[str] = mapped_column(String(20), default="")        # qualitative/quantitative
    source_type: Mapped[str] = mapped_column(String(20), index=True, default="uploaded")  # generated/uploaded
    ref_report_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    ref_archive_kind: Mapped[str] = mapped_column(String(50), default="")   # verification_report/uncertainty
    original_name: Mapped[str] = mapped_column(String(255), default="")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
