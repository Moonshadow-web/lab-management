"""ISO15189 内审专项数据模型（三子功能：文件评审 / 自查 / 科室内审）。

- 文件评审：ReviewCampaign（评审活动）+ ReviewAssignment（分配项）
- 自查（条款内审）：AuditClause（条款字典）+ SelfInspectionCampaign
  + SelfInspectionAssignment + SelfInspectionRecord
- 科室内审：复用 nonconformity.Nonconformity；新增 CorrectiveAction（逐条款整改）

新建表由 main.py 的 `Base.metadata.create_all` + `_ensure_missing_columns` 自动创建，
只需在本文件定义模型并在 models/__init__.py 注册即可。
"""
from datetime import datetime

from sqlalchemy import (
    Boolean, DateTime, ForeignKey, Integer, String, Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# ===================== 一、文件评审 =====================
REVIEW_ASSIGNMENT_STATUS = ["待评审", "已提交", "管理员已接收", "已完成"]
REVIEW_RECORD_STATUS = ["待提交", "已填写", "已提交"]
# 文件评审范围：仅这三类 SOP 参与评审（不含 项目说明书 / 记录表格）
REVIEW_DOC_CATEGORIES = ["通用SOP", "项目SOP", "仪器SOP"]


class ReviewCampaign(Base):
    """文件评审活动（一次评审任务）。"""
    __tablename__ = "review_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[str] = mapped_column(String(20), default="")
    # 活动类型：文件评审 / 体系文件评审（可合并为同一流程）
    campaign_type: Mapped[str] = mapped_column(String(30), default="文件评审")
    due_date: Mapped[str] = mapped_column(String(30), default="")  # 截止日期
    status: Mapped[str] = mapped_column(String(20), default="进行中")  # 进行中/已结束
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")  # 发起人
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReviewAssignment(Base):
    """文件评审分配项：把某个在用文档分配给某位审核人。"""
    __tablename__ = "review_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("review_campaigns.id"), index=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id"), index=True)
    reviewer: Mapped[str] = mapped_column(String(100), default="")  # 被分配人 full_name
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(20), default="待评审", index=True
    )  # 待评审/已提交/管理员已接收/已完成
    # A-027 文件评审记录表内容（JSON 字符串），含：
    #   review_files(评审文件列表), problems(文件中主要存在问题),
    #   recorder(记录人), approver(审批人), record_date(记录日期), approve_date(批准日期)
    record_json: Mapped[str] = mapped_column(Text, default="")
    # 审核人上传的修订后文件（云存储键 / 本地键）
    revised_cloud_key: Mapped[str] = mapped_column(String(500), default="")
    revised_filename: Mapped[str] = mapped_column(String(300), default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    admin_received_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # 管理员接收后，为该文档生成的新版本号（来自 documents 的 new-version）
    document_new_version: Mapped[str] = mapped_column(String(20), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


class ReviewRecord(Base):
    """文件评审记录（A-027）：每人每活动一份，覆盖其被分配的全部文件。

    record_json 结构：
      review_group(专业组), review_date(评审时间, 如 2026-08),
      review_members(评审组成员，全部被分配人，逗号分隔),
      recorder(记录人=本人), approver(审批人, 默认 金子铮),
      record_date, approve_date,
      problems(主要存在问题),
      files([{document_id, title, doc_number, version, comment(评审意见), conclusion(评审结论)}])
    """
    __tablename__ = "review_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(ForeignKey("review_campaigns.id"), index=True)
    reviewer_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    reviewer: Mapped[str] = mapped_column(String(100), default="")  # 记录人 full_name
    status: Mapped[str] = mapped_column(String(20), default="待提交", index=True)
    record_json: Mapped[str] = mapped_column(Text, default="")
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ===================== 二、自查（条款内审） =====================
SELF_INSPECTION_STATUS = ["待自查", "自查中", "已提交"]
SELF_INSPECTION_RESULT = ["符合", "不符合", "观察项", "不适用"]


class AuditClause(Base):
    """CNAS-AL02-07 附表3 自查表条款字典（种子导入，供分配/填写时选择）。"""
    __tablename__ = "audit_clauses"

    id: Mapped[int] = mapped_column(primary_key=True)
    clause_no: Mapped[str] = mapped_column(String(30), index=True, default="")  # 6.4.1
    chapter: Mapped[str] = mapped_column(String(80), default="")  # 第六章 资源要求
    title: Mapped[str] = mapped_column(String(300), default="")  # 条款标题
    content: Mapped[str] = mapped_column(Text, default="")  # 条款内容（原文）
    check_point: Mapped[str] = mapped_column(Text, default="")  # 核查要点（可选）


class SelfInspectionCampaign(Base):
    """自查活动（一次条款内审任务）。"""
    __tablename__ = "self_inspection_campaigns"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="")
    year: Mapped[str] = mapped_column(String(20), default="")
    due_date: Mapped[str] = mapped_column(String(30), default="")
    status: Mapped[str] = mapped_column(String(20), default="进行中")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(100), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelfInspectionAssignment(Base):
    """自查分配：把若干条款分配给某位员工。"""
    __tablename__ = "self_inspection_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("self_inspection_campaigns.id"), index=True
    )
    assignee: Mapped[str] = mapped_column(String(100), default="")  # 员工 full_name
    assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    # 分配的条款 id 列表（JSON 数组），或按章节范围分配
    clause_ids: Mapped[str] = mapped_column(Text, default="[]")  # JSON 数组 of audit_clauses.id
    clause_range: Mapped[str] = mapped_column(String(200), default="")  # 展示用，如 "第六章 资源要求"
    status: Mapped[str] = mapped_column(String(20), default="待自查", index=True)
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class SelfInspectionRecord(Base):
    """自查记录：员工按分配条款逐条填写的检查结果。"""
    __tablename__ = "self_inspection_records"

    id: Mapped[int] = mapped_column(primary_key=True)
    campaign_id: Mapped[int] = mapped_column(
        ForeignKey("self_inspection_campaigns.id"), index=True
    )
    assignment_id: Mapped[int | None] = mapped_column(
        ForeignKey("self_inspection_assignments.id"), index=True, nullable=True
    )
    clause_id: Mapped[int] = mapped_column(ForeignKey("audit_clauses.id"), index=True)
    assignee: Mapped[str] = mapped_column(String(100), default="")
    check_content: Mapped[str] = mapped_column(Text, default="")  # 核查内容
    result: Mapped[str] = mapped_column(String(20), default="")  # 符合/不符合/观察项/不适用
    finding: Mapped[str] = mapped_column(Text, default="")  # 问题描述 / 不符合描述
    action: Mapped[str] = mapped_column(Text, default="")  # 建议采取措施
    filled_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )


# ===================== 三、科室内审（不符合项 + 逐条款整改） =====================
CORRECTIVE_STATUS = ["未整改", "整改中", "待验证", "已关闭"]


class CorrectiveAction(Base):
    """逐条款整改报告（关联不符合项，按条款号组织）。"""
    __tablename__ = "corrective_actions"

    id: Mapped[int] = mapped_column(primary_key=True)
    nonconformity_id: Mapped[int | None] = mapped_column(
        ForeignKey("nonconformities.id"), index=True, nullable=True
    )
    clause: Mapped[str] = mapped_column(String(30), default="")  # 条款号 6.4.5
    title: Mapped[str] = mapped_column(String(300), default="")
    source: Mapped[str] = mapped_column(String(50), default="")  # 内审/外审/日常监督...
    description: Mapped[str] = mapped_column(Text, default="")  # 不符合描述
    root_cause: Mapped[str] = mapped_column(Text, default="")  # 原因分析
    corrective_action: Mapped[str] = mapped_column(Text, default="")  # 纠正措施
    preventive_action: Mapped[str] = mapped_column(Text, default="")  # 预防措施
    responsible: Mapped[str] = mapped_column(String(100), default="")  # 责任人
    due_date: Mapped[str] = mapped_column(String(30), default="")  # 要求完成日期
    verify_result: Mapped[str] = mapped_column(Text, default="")  # 整改验证
    status: Mapped[str] = mapped_column(String(20), default="未整改", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow
    )
