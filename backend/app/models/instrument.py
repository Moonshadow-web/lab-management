from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


INSTRUMENT_STATUS = ["在用", "备用", "维修", "停用"]


class Instrument(Base):
    __tablename__ = "instruments"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True, default="")
    dept_no: Mapped[str] = mapped_column(String(50), default="")  # 科室编号
    model: Mapped[str] = mapped_column(String(100), default="")  # 规格型号
    manufacturer: Mapped[str] = mapped_column(String(100), default="")  # 生产厂家
    category: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(100), default="")  # 存放位置
    status: Mapped[str] = mapped_column(String(20), default="在用")  # 在用/备用/维修/停用
    serial_no: Mapped[str] = mapped_column(String(100), default="")  # 出厂编号
    purchase_date: Mapped[str] = mapped_column(String(30), default="")  # 购入日期
    start_date: Mapped[str] = mapped_column(String(30), default="")  # 启用日期
    owner: Mapped[str] = mapped_column(String(100), default="")  # 设备负责人
    daily_manager: Mapped[str] = mapped_column(String(100), default="")  # 日常管理人
    supplier: Mapped[str] = mapped_column(String(200), default="")  # 供货商名称
    contact: Mapped[str] = mapped_column(String(200), default="")  # 联系人及电话
    qc_instrument: Mapped[bool] = mapped_column(Boolean, default=False)  # 是否室内质控受控仪器（月结下拉限定）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalibrationRecord(Base):
    __tablename__ = "calibration_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int] = mapped_column(Integer, index=True)
    calibration_date: Mapped[str] = mapped_column(String(30), default="")  # 校准日期
    next_due_date: Mapped[str] = mapped_column(String(30), default="")  # 下次到期
    result: Mapped[str] = mapped_column(String(200), default="")  # 校准结果
    agency: Mapped[str] = mapped_column(String(200), default="")  # 检定/校准机构
    cycle_months: Mapped[str] = mapped_column(String(10), default="")  # 检定周期(月)
    operator: Mapped[str] = mapped_column(String(100), default="")  # 校准人
    report_file_path: Mapped[str] = mapped_column(String(500), default="")  # 报告文件路径
    report_filename: Mapped[str] = mapped_column(String(300), default="")  # 报告原始文件名
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
