from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class SpecimenComparabilityRecord(Base):
    """样本类型可比性验证（如血清 vs 血浆-肝素锂）。

    判定依据 CNAS-CL02:2023 7.3.7.4：允许偏倚取 1/2 TEa，达标比例 ≥80%。

    - pairs：[{"no":1,"a":血清值,"b":血浆值}, ...]
    - result_summary：统计与判定结果 JSON
    """

    __tablename__ = "specimen_comparability_records"

    group_code: Mapped[str] = mapped_column(String(20), server_default="sm", default="sm", index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    verify_type: Mapped[str] = mapped_column(String(50), default="serum_vs_plasma", index=True)
    project_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    project_method: Mapped[str] = mapped_column(String(300), default="")
    unit: Mapped[str] = mapped_column(String(50), default="")

    # 标本与采集/处理条件（评审最常追问，必须留痕）
    specimen_a: Mapped[str] = mapped_column(String(100), default="血清")
    specimen_b: Mapped[str] = mapped_column(String(100), default="血浆-肝素锂")
    tube_a: Mapped[str] = mapped_column(String(200), default="")
    tube_b: Mapped[str] = mapped_column(String(200), default="")
    centrifuge: Mapped[str] = mapped_column(String(200), default="")
    storage: Mapped[str] = mapped_column(String(200), default="")
    instrument: Mapped[str] = mapped_column(String(200), default="")

    sample_count: Mapped[int] = mapped_column(Integer, default=20)
    sample_source: Mapped[str] = mapped_column(String(300), default="同一患者同次采集的配对标本")
    tea: Mapped[str] = mapped_column(String(50), default="")
    ref_range_low: Mapped[str] = mapped_column(String(50), default="")
    ref_range_high: Mapped[str] = mapped_column(String(50), default="")

    verify_date: Mapped[str] = mapped_column(String(100), default="")
    pairs: Mapped[str] = mapped_column(Text, default="[]")
    result_summary: Mapped[str] = mapped_column(Text, default="{}")
    conclusion: Mapped[str] = mapped_column(Text, default="")
    operator: Mapped[str] = mapped_column(String(100), default="")
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    report_file_path: Mapped[str] = mapped_column(String(500), default="")
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
