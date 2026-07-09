from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


VERIFY_TYPE = ["精密度", "正确度", "线性范围", "可报告范围", "携带污染", "参考区间", "检出限"]
VERIFY_CONCLUSION = ["通过", "不通过", "待复核"]


class VerificationRecord(Base):
    """检验项目性能验证记录。"""

    __tablename__ = "verification_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    test_item: Mapped[str] = mapped_column(String(200), index=True, default="")  # 验证项目
    verify_type: Mapped[str] = mapped_column(String(50), index=True, default="")  # 验证类型
    instrument: Mapped[str] = mapped_column(String(100), default="")  # 仪器
    verify_date: Mapped[str] = mapped_column(String(30), default="")  # 验证日期
    criteria: Mapped[str] = mapped_column(String(300), default="")  # 判定标准
    result: Mapped[str] = mapped_column(String(500), default="")  # 验证结果
    conclusion: Mapped[str] = mapped_column(String(20), default="通过")  # 通过/不通过/待复核
    report_file_path: Mapped[str] = mapped_column(String(500), default="")  # 报告文件路径
    operator: Mapped[str] = mapped_column(String(100), default="")  # 操作者
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
