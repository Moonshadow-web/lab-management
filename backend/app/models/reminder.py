from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from ..core.database import Base


class NotifyRecipient(Base):
    """提醒接收人（独立于系统用户，可增删）。支持邮箱、手机号（短信预留）、微信(ServerChan/方糖)。"""

    __tablename__ = "notify_recipients"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100), default="")          # 姓名/称谓
    email: Mapped[str] = mapped_column(String(200), default="")         # 接收提醒的邮箱
    phone: Mapped[str] = mapped_column(String(30), default="")          # 手机号（短信预留）
    wx_uid: Mapped[str] = mapped_column(String(60), default="")         # 微信推送 ServerChan SendKey（复用此列，按人精准推送）
    channels: Mapped[str] = mapped_column(String(50), default="email")  # 渠道：email / sms / serverchan(兼容旧 wxpusher) / 逗号分隔
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)        # 是否启用
    rule_categories: Mapped[str] = mapped_column(String(200), default="")  # 订阅的提醒分类(CSV)；空=不接收
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReminderRule(Base):
    """提醒规则（可开关/调阈值的提醒类型）。

    ref_kind: eqa（室间质评上报）或 calibration（仪器校准到期）。
    lead_days: 提前提醒天数（进入该窗口即首次触发）。
    escalate_days_left: 升级再发里程碑，剩余天数到达这些值时再发（逗号分隔）。
    scope_kind/scope_values: eqa 按 group 过滤（生化,凝血 / 免疫 …），calibration 用 all。
    """

    __tablename__ = "reminder_rules"

    id: Mapped[int] = mapped_column(primary_key=True)
    category: Mapped[str] = mapped_column(String(40), index=True, default="")  # 唯一键：eqa_biochem_coag / eqa_immuno / calibration
    label: Mapped[str] = mapped_column(String(100), default="")       # 展示名
    ref_kind: Mapped[str] = mapped_column(String(20), default="eqa")  # eqa / calibration
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    lead_days: Mapped[int] = mapped_column(Integer, default=14)
    escalate_days_left: Mapped[str] = mapped_column(String(60), default="7")  # 如 "14,7"
    scope_kind: Mapped[str] = mapped_column(String(20), default="group")      # group / all
    scope_values: Mapped[str] = mapped_column(String(200), default="")        # csv：生化,凝血
    note: Mapped[str] = mapped_column(String(300), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class ReminderSendLog(Base):
    """提醒发送记录：用于升级去重与「未消除再发」控制。

    每个 (rule_id, ref_type, ref_id) 一行。sent_milestones 记录已发送的里程碑集合，
    避免同一里程碑重复发送；resolved 标记事项已处理（不再提醒）。
    """

    __tablename__ = "reminder_send_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    rule_id: Mapped[int] = mapped_column(Integer, index=True)
    ref_type: Mapped[str] = mapped_column(String(30), default="")   # eqa / calibration
    ref_id: Mapped[int] = mapped_column(Integer, index=True)
    sent_milestones: Mapped[str] = mapped_column(String(200), default="")  # csv 里程碑
    last_sent_at: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    send_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
