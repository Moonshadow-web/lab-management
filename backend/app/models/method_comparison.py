from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class MethodComparisonRecord(Base):
    """方法学比对记录（EP9-A3 方案，新方法 vs 现行方法）。

    - pairs：样本对原始数据 JSON，形如 [{"no":1,"a":1.42,"b":1.72}, ...]
      a = 参照方法（现行）/ b = 待评方法（新方法）
    - result_summary：统计结果 JSON（偏移、回归、一致性、结论）
    - report_file_path：生成的单项目 docx 报告归档路径
    - batch_name：同一次比对（同批次）用于汇总报告聚合
    """

    __tablename__ = "method_comparison_records"

    group_code: Mapped[str] = mapped_column(String(20), server_default="sm", default="sm", index=True)
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_name: Mapped[str] = mapped_column(String(200), default="", index=True)     # 汇总批次
    compare_type: Mapped[str] = mapped_column(String(20), server_default="quantitative",
                                              default="quantitative", index=True)    # quantitative / qualitative
    project_name: Mapped[str] = mapped_column(String(200), default="", index=True)
    project_method: Mapped[str] = mapped_column(String(300), default="")
    unit: Mapped[str] = mapped_column(String(50), default="")

    # 参照方法（现行）
    ref_instrument: Mapped[str] = mapped_column(String(200), default="")
    ref_manufacturer: Mapped[str] = mapped_column(String(200), default="")
    ref_reagent: Mapped[str] = mapped_column(String(300), default="")
    ref_reagent_lot: Mapped[str] = mapped_column(String(100), default="")
    ref_calibrator: Mapped[str] = mapped_column(String(300), default="")
    ref_calibrator_lot: Mapped[str] = mapped_column(String(100), default="")

    # 待评方法（新）
    test_instrument: Mapped[str] = mapped_column(String(200), default="")
    test_manufacturer: Mapped[str] = mapped_column(String(200), default="")
    test_reagent: Mapped[str] = mapped_column(String(300), default="")
    test_reagent_lot: Mapped[str] = mapped_column(String(100), default="")
    test_calibrator: Mapped[str] = mapped_column(String(300), default="")
    test_calibrator_lot: Mapped[str] = mapped_column(String(100), default="")

    sample_count: Mapped[int] = mapped_column(Integer, default=40)                   # 计划样本数（20/40 可选）
    sample_source: Mapped[str] = mapped_column(String(300), default="临床检测剩余血清样本")
    tea: Mapped[str] = mapped_column(String(50), default="")                        # 允许总误差 %
    scheme: Mapped[str] = mapped_column(String(50), default="EP9-A3")
    ref_range_low: Mapped[str] = mapped_column(String(50), default="")
    ref_range_high: Mapped[str] = mapped_column(String(50), default="")
    test_range_low: Mapped[str] = mapped_column(String(50), default="")
    test_range_high: Mapped[str] = mapped_column(String(50), default="")

    compare_date: Mapped[str] = mapped_column(String(100), default="")
    pairs: Mapped[str] = mapped_column(Text, default="[]")                          # 样本对 JSON
    result_summary: Mapped[str] = mapped_column(Text, default="{}")                 # 统计结果 JSON
    conclusion: Mapped[str] = mapped_column(Text, default="")
    operator: Mapped[str] = mapped_column(String(100), default="")
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    report_file_path: Mapped[str] = mapped_column(String(500), default="")
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
