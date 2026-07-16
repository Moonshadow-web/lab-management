from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class TestItem(Base):
    __tablename__ = "test_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), index=True, default="")
    name: Mapped[str] = mapped_column(String(200), index=True, default="")
    aliases: Mapped[str] = mapped_column(String(200), default="")  # 别名，逗号分隔
    category: Mapped[str] = mapped_column(String(50), index=True, default="")  # 分类
    specimen: Mapped[str] = mapped_column(String(50), default="")  # 标本类型
    method: Mapped[str] = mapped_column(String(100), default="")  # 检测方法
    unit: Mapped[str] = mapped_column(String(30), default="")
    reference: Mapped[str] = mapped_column(Text, default="")  # 参考范围
    fee: Mapped[str] = mapped_column(String(30), default="")  # 收费（占位待补）
    instrument: Mapped[str] = mapped_column(String(100), default="")
    instrument_group: Mapped[str] = mapped_column(String(100), default="")
    linear_range: Mapped[str] = mapped_column(String(100), default="")
    dilution_fold: Mapped[str] = mapped_column(String(30), default="")
    reportable_range: Mapped[str] = mapped_column(String(100), default="")
    diluent: Mapped[str] = mapped_column(String(100), default="")
    calibrator: Mapped[str] = mapped_column(String(100), default="")
    traceability: Mapped[str] = mapped_column(String(200), default="")
    brand: Mapped[str] = mapped_column(String(50), default="")  # 品牌标识（显式存储，优先于从校准品推导）
    last_update: Mapped[str] = mapped_column(String(50), default="")
    interference_hemolysis: Mapped[str] = mapped_column(String(100), default="")
    interference_bilirubin: Mapped[str] = mapped_column(String(100), default="")
    interference_lipemia: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    # 室间质评 / 室间比对标记：默认均有（1）；无室间质评=0；无室间比对（既无 EQA 也无外部参比）=0
    has_eqa: Mapped[int] = mapped_column(Integer, default=1)
    has_interlab: Mapped[int] = mapped_column(Integer, default=1)
