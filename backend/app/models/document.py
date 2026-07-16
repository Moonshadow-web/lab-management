from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# 文件分类枚举（5 类）
DOC_CATEGORIES = ["通用SOP", "项目SOP", "仪器SOP", "记录表格", "项目说明书"]
DOC_STATUS = ["草稿", "生效", "作废"]


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), index=True, default="")
    category: Mapped[str] = mapped_column(String(50), index=True, default="通用SOP")  # 5 类
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    file_path: Mapped[str] = mapped_column(String(500), default="")  # 相对路径
    original_filename: Mapped[str] = mapped_column(String(300), default="")
    uploader: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="生效")  # 草稿/生效/作废
    description: Mapped[str] = mapped_column(Text, default="")
    # 文件头元数据（从 .docx 表头表格自动解析，便于展示与版本追溯）
    doc_number: Mapped[str] = mapped_column(String(100), default="", index=True)  # 文件编号
    doc_version: Mapped[str] = mapped_column(String(50), default="")  # 文件版本号
    revision: Mapped[str] = mapped_column(String(20), default="")  # 修订号
    author: Mapped[str] = mapped_column(String(100), default="")  # 编写者/编制人
    reviewer: Mapped[str] = mapped_column(String(100), default="")  # 审核者
    approver: Mapped[str] = mapped_column(String(100), default="")  # 批准者
    issued_date: Mapped[str] = mapped_column(String(50), default="")  # 发布/编制日期
    audit_date: Mapped[str] = mapped_column(String(50), default="")  # 审核日期
    approve_date: Mapped[str] = mapped_column(String(50), default="")  # 批准日期
    effective_date: Mapped[str] = mapped_column(String(50), default="")  # 实施/生效日期
    meta_raw: Mapped[str] = mapped_column(Text, default="")  # 原始头表（审计用）
    parent_id: Mapped[int] = mapped_column(Integer, nullable=True)  # 版本链
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class DocumentVersion(Base):
    __tablename__ = "document_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(Integer, index=True)
    version: Mapped[str] = mapped_column(String(20), default="1.0")
    file_path: Mapped[str] = mapped_column(String(500), default="")
    uploader: Mapped[str] = mapped_column(String(100), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    # 该版本时的文件头元数据快照
    doc_number: Mapped[str] = mapped_column(String(100), default="")
    doc_version: Mapped[str] = mapped_column(String(50), default="")
    revision: Mapped[str] = mapped_column(String(20), default="")
    author: Mapped[str] = mapped_column(String(100), default="")
    reviewer: Mapped[str] = mapped_column(String(100), default="")
    approver: Mapped[str] = mapped_column(String(100), default="")
    meta_raw: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
