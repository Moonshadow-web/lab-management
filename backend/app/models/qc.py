from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


QC_STATUS = ["在控", "警告", "失控"]


class QCRecord(Base):
    """室内质控记录（IQC）。"""

    __tablename__ = "qc_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item: Mapped[str] = mapped_column(String(200), index=True, default="")  # 质控项目
    level: Mapped[str] = mapped_column(String(50), default="")  # 质控水平（水平1/水平2）
    lot_no: Mapped[str] = mapped_column(String(100), default="")  # 质控品批号
    instrument: Mapped[str] = mapped_column(String(100), index=True, default="")  # 仪器
    target_mean: Mapped[str] = mapped_column(String(50), default="")  # 靶值均值
    target_sd: Mapped[str] = mapped_column(String(50), default="")  # 靶值SD
    measured_value: Mapped[str] = mapped_column(String(50), default="")  # 测定值
    qc_date: Mapped[str] = mapped_column(String(30), default="")  # 质控日期
    status: Mapped[str] = mapped_column(String(20), default="在控")  # 在控/警告/失控
    rule_violated: Mapped[str] = mapped_column(String(100), default="")  # 违反的质控规则（1-2s/1-3s/2-2s…）
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作者
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
