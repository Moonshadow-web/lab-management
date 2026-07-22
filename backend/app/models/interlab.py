"""室间比对（无室间质评项目 · 外部参比实验室比对）模块数据模型。

核心概念（与「仪器间比对」区分）：
- 室间比对用于**无室间质评**(has_eqa=0) 且**有外部参比实验室**(has_interlab=1) 的项目，
  每半年一次（上半年/下半年），按所属仪器分类。
- InterlabPlan（比对计划）：年 + 半年 + 我室仪器 + 参比实验室 + 比对日期/操作者/审核者/结论。
- InterlabItem（比对项目）：一个计划下的一个项目，含单位/TE/定性定量等元数据。
- InterlabLevel（水平结果）：每个项目 5 个水平（1~5），含我室值 X、比较系统1/2 的 Y1/Y2/均值Y。

报告严格保留「室间比对结果记录及分析报告表」版式，可生成 docx / 预览 / 下载 / 上传存档。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, LargeBinary, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class InterlabPlan(Base):
    __tablename__ = "interlab_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 年份
    half: Mapped[int] = mapped_column(Integer, default=1)  # 半年：1=上半年，2=下半年
    instrument_id: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 我室仪器 id
    reference_lab: Mapped[str] = mapped_column(String(200), default="")  # 参比实验室名称（可比较系统）
    compared_instrument2: Mapped[str] = mapped_column(String(200), default="")  # 本实验室比较系统2（第二平台）仪器名称
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
    """室间比对项目：元数据（项目名/单位/允许总误差/定性定量），实际结果在 InterlabLevel。"""

    __tablename__ = "interlab_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("interlab_plans.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(100), default="")  # 项目名
    unit: Mapped[str] = mapped_column(String(30), default="")  # 单位
    te: Mapped[str] = mapped_column(String(20), default="0")  # 允许总误差，数字字符串
    mode: Mapped[str] = mapped_column(String(20), default="relative")  # relative(相对%) / absolute(绝对)
    kind: Mapped[str] = mapped_column(String(20), default="定量")  # 定性 / 定量
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterlabLevel(Base):
    """室间比对每个项目的 5 个水平结果。

    每行 = 一个项目的一个水平（1~5），支持两个比较系统（模板预留）。
    """

    __tablename__ = "interlab_levels"

    id: Mapped[int] = mapped_column(primary_key=True)
    item_id: Mapped[int] = mapped_column(ForeignKey("interlab_items.id", ondelete="CASCADE"), index=True)
    level_num: Mapped[int] = mapped_column(Integer, default=1)  # 1–5
    # 我室均值 X
    our_value: Mapped[str] = mapped_column(String(50), default="")
    # 比较系统1
    ref1_y1: Mapped[str] = mapped_column(String(50), default="")
    ref1_y2: Mapped[str] = mapped_column(String(50), default="")
    ref1_mean: Mapped[str] = mapped_column(String(50), default="")
    # 比较系统2
    ref2_y1: Mapped[str] = mapped_column(String(50), default="")
    ref2_y2: Mapped[str] = mapped_column(String(50), default="")
    ref2_mean: Mapped[str] = mapped_column(String(50), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class InterlabAttachment(Base):
    """室间比对原始报告附件：手工上传的扫描件/图片/PDF/Word 等，沉淀在计划下便于审核/复盘预览。

    与仪器间比对的 ComparisonAttachment 同源设计，但独立建表（plan_id 关联 interlab_plans），
    避免跨表外键约束。报告本身的 docx 不归这里。
    """

    __tablename__ = "interlab_attachments"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("interlab_plans.id", ondelete="CASCADE"), index=True)
    file_type: Mapped[str] = mapped_column(String(20), default="other")  # image / pdf / doc / other
    original_name: Mapped[str] = mapped_column(String(300), default="")  # 用户上传时的文件名
    stored_name: Mapped[str] = mapped_column(String(300), default="")  # 实际存储文件名（避免冲突）
    rel_path: Mapped[str] = mapped_column(String(500), default="")  # 相对 DATA_DIR 的路径（兼容旧记录，新记录留空）
    data: Mapped[bytes | None] = mapped_column(LargeBinary(16 * 1024 * 1024), nullable=True)  # 文件字节（持久化于 MySQL LONGBLOB，避免容器重建丢文件）
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    uploaded_by: Mapped[str] = mapped_column(String(100), default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
