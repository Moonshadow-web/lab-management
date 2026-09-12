# -*- coding: utf-8 -*-
"""专业组字典（多专业组架构：生免/临检/微生物/分子/血库）。

- 表 lab_groups 由 main.py 的 create_all 自动创建，无需手工建表。
- 业务表通过 `group_code` 归属某个组；编号中含 KS 段的数据视为"科室共享"。
"""
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base

# (组编码, 组名称, 排序)
LAB_GROUPS: list[tuple[str, str, int]] = [
    ("sm", "生化免疫组", 10),
    ("lj", "临检组", 20),
    ("wsw", "微生物组", 30),
    ("fz", "分子组", 40),
    ("xk", "血库", 50),
]

GROUP_NAME_BY_CODE = {c: n for c, n, _ in LAB_GROUPS}
DEFAULT_GROUP_CODE = "sm"  # 生免组：存量数据与既有账号全部归属此组
SHARED_GROUP_MARK = "KS"  # 编号中含该段 = 科室共享（所有组可见）


class LabGroup(Base):
    """专业组字典。"""

    __tablename__ = "lab_groups"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(50), default="")
    sort_no: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    remark: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
