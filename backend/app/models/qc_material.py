from datetime import datetime

from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class QcMaterial(Base):
    """质控品主数据：一种质控品（如「伯乐免疫多项」），含其包含的测定项目清单。

    同一质控品的不同批号共享这一项目清单——建批时选质控品，录入结果时
    的分析物下拉即由本表 items_json 预填，避免每个批号重复手填项目。
    """

    __tablename__ = "qc_materials"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, default="")  # 质控品名称
    items_json: Mapped[str] = mapped_column(Text, default="")  # JSON 数组：分析物/项目名称
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
