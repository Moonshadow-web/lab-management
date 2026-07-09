"""提醒服务：根据各模块到期/预警规则，统一生成 notifications 记录，供首页提醒中心聚合展示。"""
from datetime import datetime

from sqlalchemy.orm import Session

from ..models.instrument import CalibrationRecord, Instrument
from ..models.notification import Notification


def _parse_date(s: str):
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except Exception:
        return None


def refresh_calibration_notifications(db: Session):
    """清除旧的校准提醒并重新生成（基于在用仪器的最近一条校准记录的 next_due_date）。"""
    db.query(Notification).filter(Notification.ref_type == "instrument_calibration").delete(
        synchronize_session=False
    )
    today = datetime.now().date()
    warn_days = 30
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
            level, msg = "danger", f"校准已逾期（应 {rec.next_due_date} 前完成）"
        elif days_left <= warn_days:
            level, msg = "warning", f"将于 {rec.next_due_date} 到期（剩 {days_left} 天）"
        else:
            level, msg = "info", f"下次校准日期 {rec.next_due_date}"
        db.add(
            Notification(
                module="仪器设备档案",
                ref_type="instrument_calibration",
                ref_id=inst.id,
                title=f"{inst.name} 校准提醒",
                message=msg,
                due_date=rec.next_due_date,
                level=level,
            )
        )
    db.commit()
