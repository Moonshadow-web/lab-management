from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


TRAINING_CATEGORY = ["院内培训", "院外培训", "线上课程", "学术会议", "岗位培训"]
TRAINING_STATUS = ["已完成", "进行中", "未通过"]


class TrainingRecord(Base):
    """人员继续教育与培训记录。"""

    __tablename__ = "training_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    person: Mapped[str] = mapped_column(String(100), index=True, default="")  # 人员姓名
    title: Mapped[str] = mapped_column(String(300), index=True, default="")  # 培训主题
    category: Mapped[str] = mapped_column(String(50), default="")  # 类型
    train_date: Mapped[str] = mapped_column(String(30), default="")  # 培训日期
    hours: Mapped[str] = mapped_column(String(30), default="")  # 学时
    credits: Mapped[str] = mapped_column(String(30), default="")  # 学分
    organizer: Mapped[str] = mapped_column(String(200), default="")  # 组织方
    certificate_no: Mapped[str] = mapped_column(String(100), default="")  # 证书编号
    status: Mapped[str] = mapped_column(String(20), default="已完成")  # 已完成/进行中/未通过
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
