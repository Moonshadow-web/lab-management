"""提醒服务：根据各模块到期/预警规则，统一生成 notifications 记录，供首页提醒中心聚合展示。"""
from datetime import date, datetime

from sqlalchemy.orm import Session

from ..models.instrument import CalibrationRecord, Instrument
from ..models.eqa import EqaPlan
from ..models.notification import Notification
from ..models.user import User


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        try:
            return datetime.strptime(s, "%Y-%m").date()
        except Exception:
            return None


# 仪器设备校准提前提醒天数：在到期前 30 天内（含已逾期）触发预警
WARN_DAYS = 30

# 室间质评（EQA）上报提前提醒天数：在上报截止前 14 天内（含已逾期）触发预警
EQA_WARN_DAYS = 14


def compute_calibration_alerts(db: Session):
    """计算每个在用仪器的最近一次校准记录的预警状态。

    返回 list[dict]，字段：instrument_id, name, dept_no, next_due_date,
    days_left, level(danger/warning/info), has_report。
    """
    today = date.today()
    alerts = []
    for inst in db.query(Instrument).filter(Instrument.status == "在用").all():
        rec = (
            db.query(CalibrationRecord)
            .filter(CalibrationRecord.instrument_id == inst.id)
            .order_by(CalibrationRecord.id.desc())
            .first()
        )
        if not rec or not rec.next_due_date:
            continue
        d = _parse_date(rec.next_due_date)
        if not d:
            continue
        days_left = (d - today).days
        if days_left < 0:
            level = "danger"
        elif days_left <= WARN_DAYS:
            level = "warning"
        else:
            level = "info"
        alerts.append(
            {
                "instrument_id": inst.id,
                "name": inst.name,
                "dept_no": inst.dept_no,
                "next_due_date": rec.next_due_date,
                "days_left": days_left,
                "level": level,
                "has_report": bool(rec.report_file_path),
            }
        )
    return alerts


def refresh_calibration_notifications(db: Session):
    """清除旧的校准提醒并重新生成（基于在用仪器的最近一条校准记录的 next_due_date）。"""
    db.query(Notification).filter(Notification.ref_type == "instrument_calibration").delete(
        synchronize_session=False
    )
    today = datetime.now().date()
    for inst in db.query(Instrument).filter(Instrument.status == "在用").all():
        rec = (
            db.query(CalibrationRecord)
            .filter(CalibrationRecord.instrument_id == inst.id)
            .order_by(CalibrationRecord.id.desc())
            .first()
        )
        if not rec or not rec.next_due_date:
            continue
        d = _parse_date(rec.next_due_date)
        if not d:
            continue
        days_left = (d - today).days
        # 未逾期且距下次校准超过提醒阈值（默认 30 天）的不提醒，跳过
        if days_left > WARN_DAYS:
            continue
        if days_left < 0:
            level, msg = "danger", f"校准已逾期（应 {rec.next_due_date} 前完成）"
        elif days_left <= WARN_DAYS:
            level, msg = "warning", f"将于 {rec.next_due_date} 到期（剩 {days_left} 天）"
        else:
            level, msg = "info", f"下次校准日期 {rec.next_due_date}"
        model_txt = f"（{inst.model}）" if inst.model else ""
        db.add(
            Notification(
                module="仪器设备档案",
                ref_type="instrument_calibration",
                ref_id=inst.id,
                title=f"{inst.name}{model_txt}校准提醒",
                message=msg,
                due_date=rec.next_due_date,
                level=level,
            )
        )
    db.commit()


# ---------------------------------------------------------------------------
# 室间质评（EQA）上报提醒：基于未上报计划的上报截止日期
# ---------------------------------------------------------------------------
def compute_eqa_alerts(db: Session):
    """计算每个未上报室间质评计划的预警状态（基于上报截止日期）。

    返回 list[dict]，字段：plan_id, org, program, round_no, due_date,
    days_left, level(danger/warning/info)。
    """
    today = date.today()
    alerts = []
    for plan in db.query(EqaPlan).filter(EqaPlan.returned == False).all():  # noqa: E712
        if not plan.due_date:
            continue
        d = _parse_date(plan.due_date)
        if not d:
            continue
        days_left = (d - today).days
        # 未逾期且距回报截止超过提醒阈值（EQA 14 天）的不作为提醒项
        if days_left > EQA_WARN_DAYS:
            continue
        level = "danger" if days_left < 0 else "warning"
        alerts.append(
            {
                "plan_id": plan.id,
                "org": plan.org,
                "program": plan.program,
                "round_no": plan.round_no,
                "due_date": plan.due_date,
                "days_left": days_left,
                "level": level,
            }
        )
    return alerts


def get_email_recipients(db: Session):
    """返回应接收提醒邮件的用户：配置了邮箱、开启邮件通知、且角色为管理员/组长。"""
    return (
        db.query(User)
        .filter(
            User.email != "",
            User.notify_email == True,  # noqa: E712
            User.role.in_(["admin", "leader"]),
        )
        .all()
    )


def refresh_eqa_notifications(db: Session):
    """清除旧 EQA 提醒并重新生成（基于未上报计划的上报截止日期提前 EQA_WARN_DAYS 预警）。"""
    db.query(Notification).filter(Notification.ref_type == "eqa_return").delete(
        synchronize_session=False
    )
    today = datetime.now().date()
    for plan in db.query(EqaPlan).filter(EqaPlan.returned == False).all():  # noqa: E712
        if not plan.due_date:
            continue
        d = _parse_date(plan.due_date)
        if not d:
            continue
        days_left = (d - today).days
        if days_left > EQA_WARN_DAYS:
            continue  # 未逾期且距上报截止超过提醒阈值（EQA 14 天）的不提醒
        if days_left < 0:
            level, msg = "danger", f"上报已逾期（应 {plan.due_date} 前上报）"
        else:
            level, msg = "warning", f"将于 {plan.due_date} 上报截止（剩 {days_left} 天）"
        label = f"{plan.org} {plan.program}" + (f" {plan.round_no}" if plan.round_no else "")
        db.add(
            Notification(
                module="室间质评",
                ref_type="eqa_return",
                ref_id=plan.id,
                title=f"室间质评上报提醒：{label}",
                message=msg,
                due_date=plan.due_date,
                level=level,
            )
        )
    db.commit()
