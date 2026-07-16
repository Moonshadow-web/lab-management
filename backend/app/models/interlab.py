"""室间比对（无室间质评项目 · 外部参比实验室比对）模块数据模型。

核心概念（与「仪器间比对」区分）：
- 室间比对用于**无室间质评**(has_eqa=0) 且**有外部参比实验室**(has_interlab=1) 的项目，
  每半年一次（上半年/下半年），按所属仪器分类。
- InterlabPlan（比对计划）：年 + 半年 + 我室仪器 + 参比实验室 + 比对日期/操作者/审核者/结论。
- InterlabItem（比对结果）：每行 = 一个项目，录入我室检测值与参比实验室检测值；
  偏倚% = (我室 - 参比)/参比 × 100（relative）或 我室 - 参比（absolute），
  是否合格由服务层按允许偏倚(TE%)判定。

报告严格保留「室间比对结果记录及分析报告表」版式，可生成 docx / 预览 / 下载 / 上传存档。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class InterlabPlan(Base):
    __tablename__ = "interlab_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 年份
    half: Mapped[int] = mapped_column(Integer, default=1)  # 半年：1=上半年，2=下半年
    instrument_id: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 我室仪器 id
    reference_lab: Mapped[str] = mapped_column(String(200), default="")  # 参比实验室名称
    compared_at: Mapped[str] = mapped_column(String(30), default="")  # 比对日期
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作者
    reviewer: Mapped[str] = mapped_column(String(100), default="")  # 审核者
    summary: Mapped[str] = mapped_column(Text, default="")  # 结果分析
    conclusion: Mapped[str] = mapped_column(String(50), default="")  # 可接受 / 不可接受 / 空
    handle_plan: Mapped[str] = mapped_column(Text, default="")  # 处理方案（如不合格）
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft / done
    report_path: Mapped[str] = mapped_column(String(500), default="")  # 报告相对路径
    report_filename: Mapped[str] = mapped_column(String(300), default="")  # 报告原始文件名
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterlabItem(Base):
    """室间比对结果：每行 = 项目（我室值 vs 参比实验室值）。"""

    __tablename__ = "interlab_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("interlab_plans.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(100), default="")  # 项目名
    unit: Mapped[str] = mapped_column(String(30), default="")  # 单位
    our_value: Mapped[str] = mapped_column(String(50), default="")  # 我室检测值
    ref_value: Mapped[str] = mapped_column(String(50), default="")  # 参比实验室检测值
    te: Mapped[str] = mapped_column(String(20), default="0")  # 允许偏倚，数字字符串
    mode: Mapped[str] = mapped_column(String(20), default="relative")  # relative(相对%) / absolute(绝对)
    kind: Mapped[str] = mapped_column(String(20), default="定量")  # 定性 / 定量（决定套用 BG-SM-CZ-018 / 019 模板）
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
