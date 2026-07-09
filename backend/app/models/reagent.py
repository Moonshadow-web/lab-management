from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


REAGENT_STATUS = ["在库", "预警", "过期", "停用"]


class Reagent(Base):
    """试剂出入库与库存管理。"""

    __tablename__ = "reagents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, default="")  # 试剂名称
    brand: Mapped[str] = mapped_column(String(100), default="")  # 品牌/生产厂家
    spec: Mapped[str] = mapped_column(String(100), default="")  # 规格
    lot_no: Mapped[str] = mapped_column(String(100), index=True, default="")  # 批号
    quantity: Mapped[str] = mapped_column(String(50), default="")  # 库存数量
    unit: Mapped[str] = mapped_column(String(30), default="")  # 单位（盒/支/瓶）
    production_date: Mapped[str] = mapped_column(String(30), default="")  # 生产日期
    expiry_date: Mapped[str] = mapped_column(String(30), default="")  # 有效期至
    in_date: Mapped[str] = mapped_column(String(30), default="")  # 入库日期
    supplier: Mapped[str] = mapped_column(String(200), default="")  # 供应商
    storage_condition: Mapped[str] = mapped_column(String(100), default="")  # 储存条件
    status: Mapped[str] = mapped_column(String(20), default="在库")  # 在库/预警/过期/停用
    operator: Mapped[str] = mapped_column(String(100), default="")  # 经手人
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
