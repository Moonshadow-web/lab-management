from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


VERIFICATION_REPORT_TYPES = ["qualitative", "quantitative"]
# 定性：精密度 / 方法符合率 / 检出限 / 分析特异性（合适时） / 参考范围
QUALITATIVE_ITEMS = ["precision", "conformity", "lod", "specificity", "reference"]
# 定量：精密度 / 正确度 / 线性范围 / 可报告范围 / 参考区间 / 分析特异性（合适时）
QUANTITATIVE_ITEMS = ["precision", "trueness", "linearity", "reportable", "reference", "specificity"]


class VerificationReport(Base):
    """性能验证报告归档（模板驱动生成 xlsx，格式与 51-HBsAg/2.ALP 模板一致）。

    - report_type：qualitative（定性 BG-SM-CZ-040）/ quantitative（定量 BG-SM-CZ-039）
    - data：各验证项录入数据（JSON，结构由前端按验证项组织）
    - result_summary：各验证项结果文本 + 结论（前端/生成器计算）
    - report_file_path：生成的 xlsx 归档路径（COS/本地）
    """

    __tablename__ = "verification_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_type: Mapped[str] = mapped_column(String(20), index=True, default="qualitative")
    project_name: Mapped[str] = mapped_column(String(200), index=True, default="")
    project_method: Mapped[str] = mapped_column(String(300), default="")   # 项目方法
    unit: Mapped[str] = mapped_column(String(50), default="")               # 报告单位
    reagent: Mapped[str] = mapped_column(String(300), default="")
    reagent_lot: Mapped[str] = mapped_column(String(100), default="")
    calibrator: Mapped[str] = mapped_column(String(300), default="")
    calibrator_lot: Mapped[str] = mapped_column(String(100), default="")
    qc: Mapped[str] = mapped_column(String(300), default="")
    qc_lot: Mapped[str] = mapped_column(String(100), default="")
    instrument: Mapped[str] = mapped_column(String(300), default="")
    instrument_manufacturer: Mapped[str] = mapped_column(String(200), default="")
    instrument_model: Mapped[str] = mapped_column(String(100), default="")
    instrument_no: Mapped[str] = mapped_column(String(100), default="")
    tea: Mapped[str] = mapped_column(String(50), default="")                # 允许总误差 TEA（定量）
    linear_low: Mapped[str] = mapped_column(String(50), default="")        # 声称线性范围下限
    linear_high: Mapped[str] = mapped_column(String(50), default="")
    dilution: Mapped[str] = mapped_column(String(50), default="")          # 稀释倍数
    verify_items: Mapped[str] = mapped_column(Text, default="[]")           # 勾选验证项 JSON
    data: Mapped[str] = mapped_column(Text, default="{}")                   # 各验证项数据 JSON
    result_summary: Mapped[str] = mapped_column(Text, default="{}")         # 结果汇总 JSON
    conclusion: Mapped[str] = mapped_column(Text, default="")               # 总结论文本
    verify_date: Mapped[str] = mapped_column(String(100), default="")
    operator: Mapped[str] = mapped_column(String(100), default="")
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    report_file_path: Mapped[str] = mapped_column(String(500), default="")  # 生成的 xlsx 路径
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
