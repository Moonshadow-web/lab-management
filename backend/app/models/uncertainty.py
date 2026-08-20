from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class UncertaintyAssessment(Base):
    """测量不确定度评估记录（对应 BG-SM-CZ-072 测量不确定度评定报告）。

    支持两种模式（mode）：
    - "single"：单个测量系统，录入 L1/L2 两个水平的均值/SD/测试数（≥6个月 IQC）
    - "multi"：多个测量系统，录入每个系统的 L1/L2 数据，按"测量系统内平均不精密度
      方差 + 多个系统均值方差"合并算 u_pooled
    """

    __tablename__ = "uncertainty_assessments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # ── 项目基本信息 ──
    project_name: Mapped[str] = mapped_column(String(200), index=True, default="")
    sample_type: Mapped[str] = mapped_column(String(20), default="血清")  # 标本类型：血清/血浆/尿液/其他
    analyte: Mapped[str] = mapped_column(String(200), default="")  # 被测量 = 项目 + 浓度/活性
    reagent: Mapped[str] = mapped_column(String(300), default="")
    eval_date: Mapped[str] = mapped_column(String(30), default="")
    cycle_months: Mapped[int] = mapped_column(Integer, default=12)  # 评定周期（月，IQC数据采集周期）
    prepared_by: Mapped[str] = mapped_column(String(100), default="")
    reviewed_by: Mapped[str] = mapped_column(String(100), default="")
    # ── 模式 ──
    mode: Mapped[str] = mapped_column(String(10), default="single")  # single / multi
    # ── 校准品不确定度（厂家提供相对标准不确定度）──
    ucal: Mapped[float] = mapped_column(Float, default=0)
    ucal_source: Mapped[str] = mapped_column(String(20), default="厂家")  # 厂家/有证标准物质
    # ── 单个系统：L1/L2 的均值/SD/测试数 ──
    l1_mean: Mapped[float] = mapped_column(Float, default=0)
    l1_sd: Mapped[float] = mapped_column(Float, default=0)
    l1_n: Mapped[int] = mapped_column(Integer, default=0)
    l2_mean: Mapped[float] = mapped_column(Float, default=0)
    l2_sd: Mapped[float] = mapped_column(Float, default=0)
    l2_n: Mapped[int] = mapped_column(Integer, default=0)
    # ── 多个系统：JSON 数组（兼容老的 l1_values/l2_values）──
    # 结构：[{ name, l1_mean, l1_sd, l1_n, l2_mean, l2_sd, l2_n }, ...]
    multi_systems: Mapped[str] = mapped_column(Text, default="[]")
    # ── 不精密度合并后的合成标准不确定度 u_Rw(%)（相对值，单一模式）──
    #     或 u_pooled(%)（多模式）
    u_rw: Mapped[float] = mapped_column(Float, default=0)
    # ── 合成不确定度（u_c=√(u_Rw²+uCal²)）和扩展不确定度 U=2×u_c ──
    u_c: Mapped[float] = mapped_column(Float, default=0)
    u_extended: Mapped[float] = mapped_column(Float, default=0)  # U(k=2, P≈95.45%)
    # ── 质量目标查找结果（项目质量要求表）──
    # target_bias_source 优先级：wst403-2024（行标） > bj-hr-2025（北京市） > nccl-2026（1/2 EQA TE）
    target_bias: Mapped[float] = mapped_column(Float, default=0)
    target_bias_text: Mapped[str] = mapped_column(String(200), default="")
    target_bias_source: Mapped[str] = mapped_column(String(40), default="")
    # ── 判定 ──
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    # ── 患者结果报告（可选）──
    patient_value: Mapped[float] = mapped_column(Float, default=0)
    patient_unit: Mapped[str] = mapped_column(String(40), default="")
    patient_extended_value: Mapped[float] = mapped_column(Float, default=0)
    # ── 旧字段保留（兼容老数据 + 旧报告）──
    l1_values: Mapped[str] = mapped_column(Text, default="[]")
    l2_values: Mapped[str] = mapped_column(Text, default="[]")
    l1_cv: Mapped[float] = mapped_column(Float, default=0)
    l2_cv: Mapped[float] = mapped_column(Float, default=0)
    l1_u: Mapped[float] = mapped_column(Float, default=0)
    l2_u: Mapped[float] = mapped_column(Float, default=0)
    l1_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    l2_passed: Mapped[bool] = mapped_column(Boolean, default=False)
    bias_rms: Mapped[float] = mapped_column(Float, default=0)
    pt_result: Mapped[str] = mapped_column(String(10), default="合格")
    # ── 室间质评偏倚数据（5 水平：靶值 + 测量值）──
    # 结构：[{ target, measured }, ...]，EQA 不合格时用于算 RMS 偏倚
    bias_levels: Mapped[str] = mapped_column(Text, default="[]")
    # ── 报告文件路径 ──
    report_file_path: Mapped[str] = mapped_column(String(500), default="")
    # ── 元数据 ──
    created_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
