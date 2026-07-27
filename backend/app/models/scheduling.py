"""排班模块数据模型。

设计目标：生免组排班「先做一个框架，慢慢调整」。

三张业务表 + 一张配置表：
- SchedulingPost：岗位定义（门1岗、生化夜班……）；group 区分白班/夜班/特殊岗；
  preferred_people 为该岗的固定/优先人员（按优先级递减）；is_fever_day 标记发热白班（每月固定一人、每4天一班）。
- SchedulingPlan：排班计划（一个命名周期，含起止日期）；fever_day_person 为该计划发热白班的固定人员。
- SchedulingAssignment：每日每岗的具体分配（谁上、状态、是否早班/连班）。
  post_id 对「在岗」白班/夜班岗必填；对「休息/病假/开会/行政/质控/教学」等
  与岗位平行的非在岗状态可空（一人一天可有多条无岗位记录，如同时休息、开会）。
- SchedulingConfig：排班全局配置（单行 id=1）：排除人员、生成窗口天数等。

人员直接存 User.full_name 字符串，复用现有用户体系，不另建员工表。
"""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Date, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


# 岗位分组：day=工作日白班岗位，night=夜班岗位（生化夜班/发热夜班，科室提前录入，不自动生成），special=仅特定工作日出现的岗（如周三质谱）
POST_GROUP_DAY = "day"
POST_GROUP_NIGHT = "night"
POST_GROUP_SPECIAL = "special"

# 每日分配状态。
# 在岗=正常上班（自动生成 / 手动录入，必须绑定岗位）；其余均为「与岗位平行的非在岗状态」，
# 表示某人当天以该状态占用（不参与白班自动轮转、记录受保护不被覆盖），可无岗位（post_id 为空）。
# 状态类别（无岗位，按人聚合到月视图的「状态行」）：休息 / 病假 / 开会 / 行政 / 质控 / 教学。
ASSIGN_STATUS_ONDUTY = "在岗"
ASSIGN_STATUS_REST = "休息"
ASSIGN_STATUS_QC = "质控"
ASSIGN_STATUS_MEETING = "开会"
ASSIGN_STATUS_SICK = "病假"
ASSIGN_STATUS_ADMIN = "行政"
ASSIGN_STATUS_TEACH = "教学"
ASSIGN_STATUS_EARLY = "早班"
ASSIGN_STATUS_CONTINUOUS = "连班"

# 与岗位平行、无岗位的状态（月视图单独成行；对齐用户 Excel 含 教学/早班/连班 等）。
STATUS_CATEGORIES = [
    ASSIGN_STATUS_REST, ASSIGN_STATUS_SICK, ASSIGN_STATUS_MEETING,
    ASSIGN_STATUS_ADMIN, ASSIGN_STATUS_QC, ASSIGN_STATUS_TEACH,
    ASSIGN_STATUS_EARLY, ASSIGN_STATUS_CONTINUOUS,
]

ASSIGN_STATUS_ALL = [ASSIGN_STATUS_ONDUTY, *STATUS_CATEGORIES]

# 换班申请状态
SWAP_STATUS_PENDING = "待确认"
SWAP_STATUS_CONFIRMED = "已确认"
SWAP_STATUS_REJECTED = "已拒绝"
SWAP_STATUS_CANCELED = "已取消"
SWAP_STATUS_ALL = [SWAP_STATUS_PENDING, SWAP_STATUS_CONFIRMED, SWAP_STATUS_REJECTED, SWAP_STATUS_CANCELED]

# 休息申请状态（自服务，无需审批：确认即写入排班表，取消即移除）
REST_STATUS_ACTIVE = "生效中"
REST_STATUS_CANCELED = "已取消"
REST_STATUS_ALL = [REST_STATUS_ACTIVE, REST_STATUS_CANCELED]


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
    preferred_people: Mapped[list] = mapped_column(JSON, default=list)  # 该岗固定/优先人员（full_name 列表，按顺序轮转）
    is_fever_day: Mapped[bool] = mapped_column(Boolean, default=False)  # 发热白班：每月固定一人、每4个工作日一班
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
    fever_day_person: Mapped[str] = mapped_column(String(100), default="")  # 发热白班固定人员（full_name）；空=按普通白班轮转
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
    post_id: Mapped[int | None] = mapped_column(Integer, index=True, default=None, nullable=True)
    person: Mapped[str] = mapped_column(String(100), index=True, default="")  # User.full_name
    status: Mapped[str] = mapped_column(String(20), default=ASSIGN_STATUS_ONDUTY)  # 在岗/休息/病假/开会/行政/质控
    is_early: Mapped[bool] = mapped_column(Boolean, default=False)        # 早班
    is_continuous: Mapped[bool] = mapped_column(Boolean, default=False)  # 连班
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False)  # 早/连班已换班：生成逻辑需跳过/保护此行（该人已上过该早/连班）
    note: Mapped[str] = mapped_column(String(200), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingSwapRequest(Base):
    """换班申请。由 A（发起人）点击 B（接收人）的班次发起，B 在本人账号确认/拒绝。

    - 双向对调：from_assignment_id(A 的班) 与 to_assignment_id(B 的班) 均非空，
      确认后交换两条记录的 person（A 接 B 的班、B 接 A 的班）。
    - 单向顶班：to_assignment_id 为空，表示 B「顶」A 的班（B 上 A 的班，A 当天改由 B 顶，
      A 不另给出自己的班）。用于早/连班且 A 当月无班可换的场景。
    确认后，若交换涉及早/连班，相关 assignment 置 is_locked=True，使下一轮按顺序生成时
    跳过/保护已换班人（系统「记住」该人已上过该早/连班）。
    """

    __tablename__ = "scheduling_swap_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    from_person: Mapped[str] = mapped_column(String(100), index=True, default="")   # 发起人 full_name
    to_person: Mapped[str] = mapped_column(String(100), index=True, default="")     # 接收人 full_name
    from_assignment_id: Mapped[int] = mapped_column(Integer, default=0, index=True)  # A 的班次
    to_assignment_id: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True
    )  # B 的班次；顶班场景为空
    status: Mapped[str] = mapped_column(String(20), default=SWAP_STATUS_PENDING)  # 待确认/已确认/已拒绝/已取消
    note: Mapped[str] = mapped_column(String(200), default="")  # 发起人留言
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingRestRequest(Base):
    """休息申请（自服务，无需审批）。

    登录人填本人哪天需要休息，确认后后端直接在排班表写入一条
    status=休息、post_id=None 的 SchedulingAssignment，并记录本表
    （assignment_id 指向写入行），便于取消时精确删除。
    取消即软删本表（status=已取消）+ 删除对应 assignment 行。
    """

    __tablename__ = "scheduling_rest_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    person: Mapped[str] = mapped_column(String(100), index=True, default="")   # 申请人 full_name
    date: Mapped[str] = mapped_column(String(20), index=True, default="")      # YYYY-MM-DD
    status: Mapped[str] = mapped_column(String(20), default=REST_STATUS_ACTIVE)  # 生效中/已取消
    assignment_id: Mapped[int | None] = mapped_column(
        Integer, default=None, nullable=True, index=True
    )  # 写入的 SchedulingAssignment 行 id（取消时删除）
    note: Mapped[str] = mapped_column(String(200), default="")  # 申请人留言
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SchedulingConfig(Base):
    """排班全局配置（单行 id=1）。"""

    __tablename__ = "scheduling_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    excluded_people: Mapped[list] = mapped_column(JSON, default=list)  # 不参与任何排班的人员（full_name 列表）
    default_window_days: Mapped[int] = mapped_column(Integer, default=14)  # 常规排班生成窗口（1-2周）
    early_continuous_window_days: Mapped[int] = mapped_column(Integer, default=30)  # 早班/连班可提前排的天数
    # 不参与「早班/连班」的人员（full_name 列表）：这些人仍正常排白班，只是不排早班/连班、也不收早/连班提醒。
    early_continuous_excluded: Mapped[list] = mapped_column(JSON, default=list)
    notes: Mapped[str] = mapped_column(String(500), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
