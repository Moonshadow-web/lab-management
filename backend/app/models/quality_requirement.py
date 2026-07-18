"""项目质量要求库：WS/T 403-2024、北京互认 2025、NCCL 2026 EQA 三类标准。

字段 cv/bias/tea 均以文本存储，因这三类标准里经常出现「正常:6.5% / 异常:10%」、
「0.32 mmol/L (≤4) 或 8% (>4)」等多形态描述；如需数值化比对，应在前端/服务层
按空格/分号/括号分段解析，不要直接 float()。

source 取值：
  - "wst403-2024"   WS/T 403—2024（推荐性国家标准）
  - "bj-hr-2025"    2025 年北京市临床检验结果互认项目（材料3，V6）
  - "nccl-2026"     2026 年国家卫健委临床检验中心 EQA 计划（0805 版）
"""
from datetime import datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


QUALITY_SOURCES = [
    ("wst403-2024", "WS/T 403—2024 临床化学检验常用项目分析质量标准"),
    ("bj-hr-2025", "2025 年北京市临床检验结果互认项目（材料3，V6）"),
    ("nccl-2026", "2026 年国家卫健委临床检验中心 EQA 计划（0805 版）"),
]


class QualityRequirement(Base):
    """单个 (来源, 项目) 的允许不精密度/偏倚/总误差要求。"""

    __tablename__ = "quality_requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(40), index=True)  # wst403-2024/bj-hr-2025/nccl-2026
    category: Mapped[str] = mapped_column(String(120), default="", index=True)  # 来源内部分类/计划号
    item_code: Mapped[str] = mapped_column(String(80), default="", index=True)  # 系统/标准项目代码
    item_name: Mapped[str] = mapped_column(String(200), default="", index=True)  # 中文名
    cv: Mapped[str] = mapped_column(String(200), default="")  # 允许不精密度（CV 或 SD）
    bias: Mapped[str] = mapped_column(String(200), default="")  # 允许偏倚
    tea: Mapped[str] = mapped_column(String(200), default="")  # 允许总误差 / EQA 可接受范围
    unit: Mapped[str] = mapped_column(String(40), default="")  # 推荐单位（北京互认列）
    remark: Mapped[str] = mapped_column(String(500), default="")  # 备注
    updated_by: Mapped[str] = mapped_column(String(60), default="")  # 最后修改人
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        Index("ix_qr_source_code", "source", "item_code"),
        Index("ix_qr_source_name", "source", "item_name"),
    )
