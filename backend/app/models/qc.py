from datetime import datetime

from sqlalchemy import DateTime, String, Float, Text, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


QC_STATUS = ["在控", "警告", "失控"]


class QCRecord(Base):
    """室内质控记录（IQC）。"""

    __tablename__ = "qc_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item: Mapped[str] = mapped_column(String(200), index=True, default="")  # 质控项目
    level: Mapped[str] = mapped_column(String(50), default="")  # 质控水平（水平1/水平2）
    lot_no: Mapped[str] = mapped_column(String(100), default="")  # 质控品批号
    instrument: Mapped[str] = mapped_column(String(100), index=True, default="")  # 仪器
    target_mean: Mapped[str] = mapped_column(String(50), default="")  # 靶值均值
    target_sd: Mapped[str] = mapped_column(String(50), default="")  # 靶值SD
    measured_value: Mapped[str] = mapped_column(String(50), default="")  # 测定值
    qc_date: Mapped[str] = mapped_column(String(30), default="")  # 质控日期
    status: Mapped[str] = mapped_column(String(20), default="在控")  # 在控/警告/失控
    rule_violated: Mapped[str] = mapped_column(String(100), default="")  # 违反的质控规则（1-2s/1-3s/2-2s…）
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作者
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QCMonthlySummary(Base):
    """室内质控月结：每个 (年, 月, 项目, 批号, 水平, 仪器) 一行。

    数值字段统一用 float；mean/sd/cv/n/out_of_control_count/in_control_rate
    由每日测值(Westgard)聚合得到，target_* 来自 LIS 导出或手填。
    """

    __tablename__ = "qc_monthly_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True, default=0)
    month: Mapped[int] = mapped_column(index=True, default=0)
    test_item: Mapped[str] = mapped_column(String(200), index=True, default="")  # 项目
    unit: Mapped[str] = mapped_column(String(50), default="")  # 单位
    lot_no: Mapped[str] = mapped_column(String(100), default="")  # 质控批号
    level: Mapped[str] = mapped_column(String(50), default="")  # 水平
    instrument: Mapped[str] = mapped_column(String(100), default="")  # 仪器名称（受控下拉填充）
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=True)  # 关联仪器表
    instrument_no: Mapped[str] = mapped_column(String(100), default="")  # 仪器编号（dept_no）
    target_mean: Mapped[float] = mapped_column(Float, default=0.0)  # 靶值
    target_sd: Mapped[float] = mapped_column(Float, default=0.0)  # 靶值SD
    target_cv: Mapped[float] = mapped_column(Float, default=0.0)  # 靶值CV%
    mean: Mapped[float] = mapped_column(Float, default=0.0)  # 检测均值
    sd: Mapped[float] = mapped_column(Float, default=0.0)  # 检测SD
    cv: Mapped[float] = mapped_column(Float, default=0.0)  # 检测CV%
    n: Mapped[int] = mapped_column(default=0)  # 检测数
    out_of_control_count: Mapped[int] = mapped_column(default=0)  # 失控数
    in_control_rate: Mapped[float] = mapped_column(Float, default=0.0)  # 在控率
    quality_goal: Mapped[str] = mapped_column(String(50), default="")  # 质量目标（允许不精密度）
    handling_note: Mapped[str] = mapped_column(Text, default="")  # 失控处理说明
    pdf_path: Mapped[str] = mapped_column(String(500), default="")  # 质控图PDF相对路径
    pdf_filename: Mapped[str] = mapped_column(String(500), default="")  # 质控图原始文件名
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class QCDailyValue(Base):
    """室内质控每日测值（月结的明细）。"""

    __tablename__ = "qc_daily_values"

    id: Mapped[int] = mapped_column(primary_key=True)
    summary_id: Mapped[int] = mapped_column(ForeignKey("qc_monthly_summaries.id"), index=True)
    qc_date: Mapped[str] = mapped_column(String(30), default="")  # 质控日期
    value: Mapped[float] = mapped_column(Float, default=0.0)  # 测定值
    is_out_of_control: Mapped[bool] = mapped_column(default=False)  # 是否失控
    rule_violated: Mapped[str] = mapped_column(String(50), default="")  # 触发规则


class QCMonthlyReport(Base):
    """室内质控月结『文字部分』：每个 (仪器, 年, 月) 一份。

    对应 CZ-012 的文字小结，覆盖：仪器运行情况、各项目漂移/趋势、各项目
    CV%设置达标、各项目计算CV%达标、各项目质控频次达标。上传时由系统按
    数据自动草拟，之后可由检验人编辑留痕。
    """

    __tablename__ = "qc_monthly_reports"

    id: Mapped[int] = mapped_column(primary_key=True)
    instrument_id: Mapped[int | None] = mapped_column(ForeignKey("instruments.id"), index=True, nullable=True)
    instrument: Mapped[str] = mapped_column(String(100), default="")  # 仪器名称（受控）
    instrument_no: Mapped[str] = mapped_column(String(100), default="")  # 仪器编号（dept_no）
    year: Mapped[int] = mapped_column(index=True, default=0)
    month: Mapped[int] = mapped_column(index=True, default=0)
    operation_status: Mapped[str] = mapped_column(Text, default="")  # 一、仪器运行情况
    drift_trend: Mapped[str] = mapped_column(Text, default="")  # 二、各项目是否出现漂移或趋势性改变
    cv_setting_ok: Mapped[str] = mapped_column(Text, default="")  # 三、各项目CV%设置是否达标
    cv_calc_ok: Mapped[str] = mapped_column(Text, default="")  # 四、各项目计算CV%是否达标
    freq_ok: Mapped[str] = mapped_column(Text, default="")  # 五、各项目质控频次是否达标
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
