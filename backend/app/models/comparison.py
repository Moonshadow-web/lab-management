"""仪器间比对（室间质评）模块数据模型。

核心概念：
- ComparisonGroup（比对分组）：按仪器类型分组，每组含 1 台参照仪器 + 2 台及以上比对仪器，
  绑定一个 SOP 表格编号（BG-SM-CZ-025 生化 / 024 DXI800 / 026 凝血 / 027 早孕 /
  071 血气 / 021 定性），并预置参与比对的项目清单、各项允许偏倚(TE%)、偏倚计算方式
  （相对% 或 绝对）与水平数（多数 5 个，血气 2 个）。
- ComparisonPlan（比对计划）：分组下按"年 + 半年"建立一次比对（频率半年一次），
  记录比对日期、操作者、审核者、结果分析与结论。
- ComparisonResult（定量结果）：每行 = 某项目 × 某水平，录入参照仪器检测值与各比对仪器
  检测值；偏倚%与是否允许(Y/N)由服务层计算。
- ComparisonQualResult（定性结果）：每行 = 某项目，各仪器 5 例样本的阴/阳性结果，
  符合率由服务层计算。

报告严格保留原表格编号（BG-SM-CZ-0xx），版式参照对应 SOP 表单。
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class ComparisonGroup(Base):
    __tablename__ = "comparison_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True, default="")  # 分组名，如"生化分析仪"
    category: Mapped[str] = mapped_column(String(20), default="定量")  # 定量 / 定性
    form_code: Mapped[str] = mapped_column(String(40), default="")  # 表格编号，如 BG-SM-CZ-025
    form_title: Mapped[str] = mapped_column(String(200), default="")  # 表单标题，如"定量室内比对结果记录分析表（生化分析仪）"
    instrument_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组：组内全部仪器 id（含参照仪器）
    reference_instrument_id: Mapped[int] = mapped_column(Integer, default=0)  # 参照仪器 id
    levels: Mapped[int] = mapped_column(Integer, default=5)  # 水平数（血气为 2）
    items: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组：[{name, te, mode}], te=允许TE(数字字符串), mode=relative/absolute
    sample_desc: Mapped[str] = mapped_column(String(300), default="")  # 样本描述，如"5个不同浓度水平的室间质评样本"
    note: Mapped[str] = mapped_column(String(300), default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComparisonPlan(Base):
    __tablename__ = "comparison_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    group_id: Mapped[int] = mapped_column(ForeignKey("comparison_groups.id", ondelete="CASCADE"), index=True)
    year: Mapped[int] = mapped_column(Integer, index=True, default=0)  # 年份
    half: Mapped[int] = mapped_column(Integer, default=1)  # 半年：1=上半年，2=下半年（频率半年一次）
    form_code: Mapped[str] = mapped_column(String(40), default="")
    form_title: Mapped[str] = mapped_column(String(200), default="")
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


class ComparisonResult(Base):
    """定量比对结果：每行 = 项目 × 水平。"""

    __tablename__ = "comparison_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("comparison_plans.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(100), default="")  # 项目名
    level: Mapped[int] = mapped_column(Integer, default=1)  # 水平序号 1..N
    reference_value: Mapped[str] = mapped_column(String(50), default="")  # 参照仪器检测值
    values_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON：{仪器id(字符串): 检测值(字符串)}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ComparisonQualResult(Base):
    """定性比对结果：每行 = 项目。各仪器 5 例样本阴/阳性。"""

    __tablename__ = "comparison_qual_results"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("comparison_plans.id", ondelete="CASCADE"), index=True)
    item: Mapped[str] = mapped_column(String(100), default="")  # 项目名
    results_json: Mapped[str] = mapped_column(Text, default="{}")  # JSON：{仪器id(字符串): [样本1..5 的 P/N]}
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
