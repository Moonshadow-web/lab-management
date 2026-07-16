from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class EqaPlan(Base):
    """室间质评（EQA）年度计划条目：每个 (年, 机构, 专业组, 轮次) 一行。

    一条记录代表某一年度某机构某专业组的一次质评活动，工作流分两步：
      1) 上报：在「上报截止日期」前于卫健委/临检中心网页完成上报 → 此处
         标记「已上报」(returned)；
      2) 结果回报：等待官方下发结果后，在本处填入「成绩/得分」与「是否合格」
         (result/score/qualified)，并可「导入报告」(report_file) 留存入档。
    用于年度计划管理、上报到期提醒与半年/年度总结统计。
    """

    __tablename__ = "eqa_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True, default=0)          # 年度（如 2026）
    org: Mapped[str] = mapped_column(String(200), index=True, default="")   # 组织机构（北京市临检中心/卫健委/CAP…）
    program: Mapped[str] = mapped_column(String(200), index=True, default="")  # 项目组（常规化学A/肝纤/药物监测…）
    group: Mapped[str] = mapped_column(String(50), index=True, default="")     # 专业组（生化/免疫/凝血/其他，可手动改）
    item: Mapped[str] = mapped_column(String(200), default="")        # 细项（具体检测项目，可空）
    round_no: Mapped[str] = mapped_column(String(50), default="")     # 轮次（第1次 / 2026-1）
    sample_date: Mapped[str] = mapped_column(String(30), default="")  # 样本检测日期 YYYY-MM-DD
    due_date: Mapped[str] = mapped_column(String(30), index=True, default="")  # 上报截止日期 YYYY-MM-DD（提醒依据）
    returned: Mapped[bool] = mapped_column(Boolean, default=False)    # 是否已上报（在官方网页完成上报后标记）
    result: Mapped[str] = mapped_column(String(200), default="")      # 结果回报文本（合格/不合格/PT及格…）
    qualified: Mapped[bool] = mapped_column(Boolean, default=False)   # 结果是否合格/通过（用于合格率统计）
    score: Mapped[str] = mapped_column(String(50), default="")        # 成绩/得分（结果回报后填入）
    note: Mapped[str] = mapped_column(String(500), default="")        # 备注
    report_file: Mapped[str] = mapped_column(String(500), default="") # 导入的质评报告 PDF 相对路径（卫健委/北京市）
    result_data: Mapped[str] = mapped_column(Text, default="")         # 逐项「录入结果」矩阵 JSON（样本×项目 + 打印元信息）
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EqaSummary(Base):
    """室间质评半年/年度总结：每个 (年, 半年, 分类) 一份（文字总结 + 生成的 Word 报告）。

    分类拆分为两份独立报告，由两人分别负责、各自签字：
      - 「生化+凝血」组
      - 「免疫」组
    （「其他」类别不进任何总结报告。）
    """

    __tablename__ = "eqa_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    year: Mapped[int] = mapped_column(index=True, default=0)          # 年度
    half: Mapped[int] = mapped_column(index=True, default=1)          # 1=上半年（1-6月），2=下半年（7-12月），0=全年
    department: Mapped[str] = mapped_column(String(50), index=True, default="")  # 质评部门（org）：卫健委 / 北京市
    category: Mapped[str] = mapped_column(String(20), index=True, default="生化+凝血")  # 分类：生化+凝血 / 免疫
    summary_text: Mapped[str] = mapped_column(Text, default="")       # 文字总结（合格项目分析/叙述）
    docx_path: Mapped[str] = mapped_column(String(500), default="")   # 生成的总结 Word 相对路径
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)  # 报告生成时间
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
