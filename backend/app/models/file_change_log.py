from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class FileChangeLog(Base):
    """文件更改日志：记录文档的新增 / 修改 / 作废操作，供「文件更改申请单」查看与导出。"""

    __tablename__ = "file_change_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)  # 关联文档（作废后可能已删除）
    file_name: Mapped[str] = mapped_column(String(200), default="")  # 更改的文件名称（标题）
    file_code: Mapped[str] = mapped_column(String(100), default="")  # 文件编码（doc_number）
    change_type: Mapped[str] = mapped_column(String(20), default="")  # 新增 / 修改 / 作废
    operator: Mapped[str] = mapped_column(String(100), default="")  # 申请人 / 操作人
    change_date: Mapped[date] = mapped_column(Date, default=date.today, index=True)  # 更改日期
    handled: Mapped[bool] = mapped_column(Boolean, default=False, index=True)  # 是否已处理
    handled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 处理时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
