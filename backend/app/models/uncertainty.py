from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class UncertaintyAssessment(Base):
    """测量不确定度评估记录（对应 BG-SM-CZ-072 测量不确定度评定报告）。

    输入 L1/L2 两个水平的室内质控数据（各至少 5 个）→ 计算均值/SD/CV% →
    合成不确定度 Uc=√(uRw²+uBias²+uCal²)，扩展不确定度 U=k×Uc（k=2，P≈95.45%）。
    室间质评合格时 uBias=0（偏倚已含于精密度）；不合格时 uBias=RMS 偏倚。
    判定：U < 15% 为合格（满足目标不确定度要求）。
    """

    __tablename__ = "uncertainty_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_name: Mapped[str] = mapped_column(String(200), index=True, default="")   # 项目名称（如 ALT（丙氨酸氨基转移酶））
    project_code: Mapped[str] = mapped_column(String(100), default="")                # 项目编号（如 SM-SOP-101）
    instrument: Mapped[str] = mapped_column(String(200), default="")                  # 检测系统/仪器
    reagent: Mapped[str] = mapped_column(String(300), default="")                     # 试剂/校准品
    eval_date: Mapped[str] = mapped_column(String(30), default="")                    # 评定日期
    cycle_months: Mapped[int] = mapped_column(Integer, default=12)                    # 评定周期（月）
    prepared_by: Mapped[str] = mapped_column(String(100), default="")                 # 编制人
    reviewed_by: Mapped[str] = mapped_column(String(100), default="")                 # 审核人
    l1_values: Mapped[str] = mapped_column(Text, default="[]")                        # L1 水平质控数据（JSON 数组）
    l2_values: Mapped[str] = mapped_column(Text, default="[]")                        # L2 水平质控数据（JSON 数组）
    l1_mean: Mapped[float] = mapped_column(Float, default=0)
    l1_sd: Mapped[float] = mapped_column(Float, default=0)
    l1_cv: Mapped[float] = mapped_column(Float, default=0)                            # uRw
    l2_mean: Mapped[float] = mapped_column(Float, default=0)
    l2_sd: Mapped[float] = mapped_column(Float, default=0)
    l2_cv: Mapped[float] = mapped_column(Float, default=0)
    bias_rms: Mapped[float] = mapped_column(Float, default=0)                         # RMS 偏倚(%)
    ucal: Mapped[float] = mapped_column(Float, default=0)                             # 校准品不确定度 Ucal(%)
    pt_result: Mapped[str] = mapped_column(String(10), default="合格")                # 室间质评结果：合格/不合格
    l1_u: Mapped[float] = mapped_column(Float, default=0)                             # L1 扩展不确定度 U(%)
    l2_u: Mapped[float] = mapped_column(Float, default=0)
    l1_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    l2_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
