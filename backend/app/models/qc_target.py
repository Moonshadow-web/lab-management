from datetime import datetime

from sqlalchemy import DateTime, String, Float, Text, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# 质控品下拉预设（前端复用；后端不强制，允许手填）
QC_MATERIAL_PRESETS = [
    "生化多项质控品",
    "伯乐免疫多项",
    "昆涞免疫多项",
]


class QCTargetBatch(Base):
    """批号累积靶值 —— 主记录（一盒质控品 = 一条批号）。

    - mode='archive'：仅存档（生化多项质控品），上传 PDF 做存档、可预览，不录结果。
    - mode='entry'：上传存档 + 录入每次测定结果，按所选 method 累计靶值。
    - method='conventional'：常规法（≥10 可暂定、≥20 确立）。
    - method='immediate'：即刻法（≥3 次起按 SI 界值表判在控/警告/失控，累计到 20 次确立）。
    - 一个批号含多个项目（分析物），靶值按项目分别累计，结果见 qc_target_results.analyte。
    """

    __tablename__ = "qc_target_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    qc_material: Mapped[str] = mapped_column(String(200), index=True, default="")  # 质控品
    qc_material_id: Mapped[int | None] = mapped_column(ForeignKey("qc_materials.id"), nullable=True, index=True, default=None)  # 关联注册质控品
    lot_no: Mapped[str] = mapped_column(String(100), index=True, default="")  # 批号
    level: Mapped[int] = mapped_column(Integer, default=0)  # 水平 1/2/3，0=未指定
    instrument: Mapped[str] = mapped_column(String(100), index=True, default="")  # 仪器
    method: Mapped[str] = mapped_column(String(20), default="")  # conventional / immediate（archive 模式为空）
    mode: Mapped[str] = mapped_column(String(20), default="entry")  # archive / entry
    established: Mapped[bool] = mapped_column(default=False)  # 是否已确立（entry）/ 已存档（archive 建批即 True）
    targets_json: Mapped[str] = mapped_column(Text, default="")  # 确立后的 per-analyte 靶值 JSON
    archive_file: Mapped[str] = mapped_column(String(500), default="")  # 存档 PDF 相对路径
    archive_filename: Mapped[str] = mapped_column(String(500), default="")  # 存档 PDF 原始文件名
    note: Mapped[str] = mapped_column(Text, default="")  # 备注 / 靶值说明
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QCTargetResult(Base):
    """批号累积靶值 —— 每次测定明细（仅 entry 模式）。

    一个批号下，每个 analyte（项目）各自累计一条值序列；靶值按 analyte 分别算。
    is_out=True 表示即刻法判为「失控」被标记（按需求保留、不自动舍去，由人工决定删/留）。
    """

    __tablename__ = "qc_target_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    batch_id: Mapped[int] = mapped_column(ForeignKey("qc_target_batches.id"), index=True)
    analyte: Mapped[str] = mapped_column(String(200), index=True, default="")  # 项目/分析物
    value: Mapped[float] = mapped_column(Float, default=0.0)  # 测定值
    qc_date: Mapped[str] = mapped_column(String(30), default="")  # 测定日期
    seq: Mapped[int] = mapped_column(default=0)  # 该 (batch, analyte) 内序号
    si_upper: Mapped[float] = mapped_column(Float, default=0.0)  # 即刻法：本次 SI上限
    si_lower: Mapped[float] = mapped_column(Float, default=0.0)  # 即刻法：本次 SI下限
    status: Mapped[str] = mapped_column(String(20), default="累计中")  # 累计中/在控/警告/失控
    is_out: Mapped[bool] = mapped_column(default=False)  # 失控标记（保留，人工决定）
    operator: Mapped[str] = mapped_column(String(100), default="")
    remark: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
