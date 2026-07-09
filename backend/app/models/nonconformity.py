from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


NC_TYPE = ["体系性", "技术性", "管理性"]
NC_SOURCE = ["内审", "外审", "日常监督", "客户投诉", "能力验证", "管理评审"]
NC_STATUS = ["待处理", "整改中", "已关闭", "已验证"]


class Nonconformity(Base):
    """ISO15189 不符合项与纠正措施（CAPA）。"""

    __tablename__ = "nonconformities"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(300), index=True, default="")  # 标题
    nc_type: Mapped[str] = mapped_column(String(50), index=True, default="")  # 类型
    source: Mapped[str] = mapped_column(String(50), index=True, default="")  # 来源
    description: Mapped[str] = mapped_column(String(1000), default="")  # 问题描述
    root_cause: Mapped[str] = mapped_column(String(1000), default="")  # 原因分析
    corrective_action: Mapped[str] = mapped_column(String(1000), default="")  # 纠正措施
    responsible: Mapped[str] = mapped_column(String(100), default="")  # 责任人
    found_date: Mapped[str] = mapped_column(String(30), default="")  # 发现日期
    due_date: Mapped[str] = mapped_column(String(30), default="")  # 要求完成日期
    close_date: Mapped[str] = mapped_column(String(30), default="")  # 关闭日期
    status: Mapped[str] = mapped_column(String(20), default="待处理")  # 待处理/整改中/已关闭/已验证
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
