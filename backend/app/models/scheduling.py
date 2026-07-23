"""排班模块数据模型。

设计目标：生免组排班「先做一个框架，慢慢调整」。三张表：
- SchedulingPost：岗位定义（门1岗、生化夜班……）；group 区分白班/夜班/周三特殊岗。
- SchedulingPlan：排班计划（一个命名周期，含起止日期）。
- SchedulingAssignment：每日每岗的具体分配（谁上、状态、是否早班/连班）。

人员直接存 User.full_name 字符串，复用现有用户体系，不另建员工表。
"""
from datetime import datetime

from sqlalchemy import Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# 岗位分组：day=工作日白班岗位，night=夜班岗位（生化夜班/发热夜班），special=仅特定工作日出现的岗（如周三质谱）
POST_GROUP_DAY = "day"
POST_GROUP_NIGHT = "night"
POST_GROUP_SPECIAL = "special"

# 每日分配状态：在岗（默认）/质控/开会/病假。
# 注：「休息」不生成分配记录（该人当天不出现在任何岗即视为休息），框架后续可扩展请假表。
ASSIGN_STATUS_ONDUTY = "在岗"
ASSIGN_STATUS_QC = "质控"
ASSIGN_STATUS_MEETING = "开会"
ASSIGN_STATUS_SICK = "病假"


class SchedulingPost(Base):
    """岗位定义。每个岗位各一人；门诊辅助岗/电泳岗可空缺（required=False）。"""

    __tablename__ = "scheduling_posts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, index=True)  # 岗位名，如「门1岗」
    group: Mapped[str] = mapped_column(String(20), default=POST_GROUP_DAY, index=True)  # day/night/special
    required: Mapped[bool] = mapped_column(Boolean, default=True)  # 该岗每天是否必填（False=可空缺）
    only_weekday: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)  # 仅该星期几出现（0=周一），如质谱=2(周三)
    required_weekday: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)  # 该星期几必填（如电泳=3(周四)必有）
    order: Mapped[int] = mapped_column(Integer, default=0, index=True)  # 展示顺序
    notes: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingPlan(Base):
    """排班计划（一个命名周期，如「2026年8月排班」）。岗位集由 SchedulingPost 表动态决定。"""

    __tablename__ = "scheduling_plans"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), index=True)
    start_date: Mapped[str] = mapped_column(String(20), default="")  # YYYY-MM-DD
    end_date: Mapped[str] = mapped_column(String(20), default="")    # YYYY-MM-DD
    notes: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingAssignment(Base):
    """每日每岗的具体分配。一行 = (plan, date, post) 谁上。"""

    __tablename__ = "scheduling_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    date: Mapped[str] = mapped_column(String(20), index=True, default="")  # YYYY-MM-DD
    weekday: Mapped[int] = mapped_column(Integer, default=0)  # 0=周一 .. 6=周日
    is_workday: Mapped[bool] = mapped_column(Boolean, default=True)
    post_id: Mapped[int] = mapped_column(Integer, index=True, default=0)
    person: Mapped[str] = mapped_column(String(100), index=True, default="")  # User.full_name
    status: Mapped[str] = mapped_column(String(20), default=ASSIGN_STATUS_ONDUTY)  # 在岗/质控/开会/病假
    is_early: Mapped[bool] = mapped_column(Boolean, default=False)        # 早班
    is_continuous: Mapped[bool] = mapped_column(Boolean, default=False)  # 连班
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
