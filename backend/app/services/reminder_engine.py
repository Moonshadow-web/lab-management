"""提醒引擎：按可配置规则评估 EQA 上报 / 仪器校准到期，生成站内提醒并自动发邮件。

设计要点：
- 规则可开关、可改阈值（lead_days）与升级里程碑（escalate_days_left）。
- 发送按「剩余天数里程碑」：首次在 lead_days 触发；之后剩余天数降到 escalate_days_left
  中的某个值时再发（去重，避免每天刷屏）。事项逾期后若仍未消除，每 7 天再发一次。
- 站内提醒（notifications 表，ref_type=reminder_<category>）与邮件并行；邮件聚合后按接收人发送。
- as_of 参数用于测试：以指定日期评估，无需真实等待。
"""
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from ..core.config import SYSTEM_NAME
from ..models.eqa import EqaPlan
from ..models.instrument import CalibrationRecord, Instrument
from ..models.notification import Notification
from ..models.reminder import NotifyRecipient, ReminderRule, ReminderSendLog
from ..services.email_service import send_email

# 默认规则（种子，仅在库为空时写入）
DEFAULT_RULES = [
    {
        "category": "eqa_biochem_coag", "label": "生化+凝血质评提醒", "ref_kind": "eqa",
        "enabled": True, "lead_days": 14, "escalate_days_left": "7",
        "scope_kind": "group", "scope_values": "生化,凝血",
    },
    {
        "category": "eqa_immuno", "label": "免疫质评提醒", "ref_kind": "eqa",
        "enabled": True, "lead_days": 14, "escalate_days_left": "7",
        "scope_kind": "group", "scope_values": "免疫",
    },
    {
        "category": "calibration", "label": "设备校准到期提醒", "ref_kind": "calibration",
        "enabled": True, "lead_days": 30, "escalate_days_left": "14,7",
        "scope_kind": "all", "scope_values": "",
    },
]

DEFAULT_RECIPIENT = {
    "name": "金子正(测试)", "email": "815268425@qq.com", "phone": "13752760970",
    "channels": "email", "enabled": True, "note": "默认测试接收人",
    "rule_categories": "eqa_biochem_coag,eqa_immuno,calibration",
}


def _parse_date(s):
    if not s:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None


def ensure_reminder_defaults(db: Session):
    """种子默认规则与默认接收人（库为空时）。幂等。"""
    for d in DEFAULT_RULES:
        if not db.query(ReminderRule).filter(ReminderRule.category == d["category"]).first():
            db.add(ReminderRule(**d))
    if not db.query(NotifyRecipient).first():
        db.add(NotifyRecipient(**DEFAULT_RECIPIENT))
    db.commit()


def get_email_recipients(db: Session):
    return (
        db.query(NotifyRecipient)
        .filter(
            NotifyRecipient.enabled == True,  # noqa: E712
            NotifyRecipient.email != "",
            NotifyRecipient.channels.like("%email%"),
        )
        .all()
    )


def _milestones(rule: ReminderRule):
    ms = {rule.lead_days}
    for x in (rule.escalate_days_left or "").split(","):
        x = x.strip()
        if x.isdigit():
            ms.add(int(x))
    return sorted(ms, reverse=True)


def _fetch_items(db: Session, rule: ReminderRule, today: date):
    """返回本规则当前「在窗口内」的事项列表。"""
    out = []
    if rule.ref_kind == "eqa":
        q = db.query(EqaPlan).filter(EqaPlan.returned == False, EqaPlan.due_date != "")  # noqa: E712
        if rule.scope_kind == "group" and rule.scope_values:
            vals = [v.strip() for v in rule.scope_values.split(",") if v.strip()]
            if vals:
                q = q.filter(EqaPlan.group.in_(vals))
        for p in q.all():
            d = _parse_date(p.due_date)
            if not d:
                continue
            days_left = (d - today).days
            if days_left > rule.lead_days:
                continue
            label = f"{p.org} {p.program}" + (f" {p.round_no}" if p.round_no else "")
            if days_left < 0:
                msg = f"上报已逾期（应 {p.due_date} 前上报）"
            else:
                msg = f"将于 {p.due_date} 上报截止（剩 {days_left} 天）"
            out.append({
                "ref_id": p.id, "ref_type": "eqa", "days_left": days_left,
                "title": f"室间质评上报提醒：{label}", "message": msg, "due_date": p.due_date,
            })
    elif rule.ref_kind == "calibration":
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
            if days_left > rule.lead_days:
                continue
            model_txt = f"（{inst.model}）" if inst.model else ""
            if days_left < 0:
                msg = f"校准已逾期（应 {rec.next_due_date} 前完成）"
            else:
                msg = f"将于 {rec.next_due_date} 到期（剩 {days_left} 天）"
            out.append({
                "ref_id": inst.id, "ref_type": "calibration", "days_left": days_left,
                "title": f"{inst.name}{model_txt}校准提醒", "message": msg, "due_date": rec.next_due_date,
            })
    return out


def _render_text(items):
    lines = [f"【{SYSTEM_NAME}】待办提醒", ""]
    for it in items:
        due = f"（截止 {it['due_date']}）" if it.get("due_date") else ""
        lines.append(f"· {it['title']}{due}")
        if it.get("message"):
            lines.append(f"    {it['message']}")
    lines.append("")
    lines.append("（此邮件由系统自动发送，请勿直接回复）")
    return "\n".join(lines)


def _render_html(items):
    rows = []
    for it in items:
        due = f"（截止 {it.get('due_date','')}）" if it.get("due_date") else ""
        msg = it.get("message", "") or ""
        rows.append(
            f"<tr><td style='padding:6px 10px;border:1px solid #eee'>"
            f"<b>{it['title']}</b>{due}<br/><span style='color:#555'>{msg}</span></td></tr>"
        )
    return (
        f"<h3 style='margin:0 0 12px'>【{SYSTEM_NAME}】待办提醒</h3>"
        f"<table border='0' cellpadding='0' cellspacing='0' "
        f"style='border-collapse:collapse;font-size:14px;width:100%'>{''.join(rows)}</table>"
        "<p style='color:#999;font-size:12px;margin-top:12px'>此邮件由系统自动发送，请勿直接回复。</p>"
    )


def _sync_notifications(db: Session, notif_active, active_keys):
    """upsert 站内提醒（reminder_*），删除不再活跃的记录。

    同时清理与此引擎重叠的旧版通知类型（instrument_calibration / eqa_return），
    避免同一事项显示两条（一条来自旧 refresh_* 函数，一条来自 reminder_*）。
    """
    existing = {
        (n.ref_type, n.ref_id): n
        for n in db.query(Notification).filter(Notification.ref_type.like("reminder_%")).all()
    }
    for ref_type, ref_id, title, message, due_date, level, module in notif_active:
        n = existing.pop((ref_type, ref_id), None)
        if n:
            n.title, n.message, n.due_date, n.level, n.module = title, message, due_date, level, module
        else:
            db.add(Notification(
                module=module, ref_type=ref_type, ref_id=ref_id,
                title=title, message=message, due_date=due_date, level=level,
            ))
    for n in existing.values():
        db.delete(n)

    # 清理旧版通知类型：reminder_calibration → instrument_calibration
    cal_ref_ids = {k[1] for k in active_keys if k[0].startswith("reminder_calibration")}
    if cal_ref_ids:
        for n in db.query(Notification).filter(
            Notification.ref_type == "instrument_calibration",
            Notification.ref_id.in_(cal_ref_ids),
        ).all():
            db.delete(n)
    # reminder_eqA_* → eqa_return
    eqa_ref_ids = {k[1] for k in active_keys if k[0].startswith("reminder_eqA_")}
    if eqa_ref_ids:
        for n in db.query(Notification).filter(
            Notification.ref_type == "eqa_return",
            Notification.ref_id.in_(eqa_ref_ids),
        ).all():
            db.delete(n)


def run_reminders(db: Session, as_of: Optional[date] = None, dry_run: bool = False) -> dict:
    """评估所有启用规则，生成站内提醒并按接收人聚合发邮件。

    dry_run=True 时只返回计划发送的内容，不实际发信、不写发送记录。
    返回统计 dict；dry_run 时附带 planned 列表。
    """
    today = as_of or date.today()
    now = datetime.now()
    # 先从干净事务开始，避免复用连接池连接时读到陈旧快照（SQLite 多连接可见性），
    # 否则可能在「已发送」记录尚未可见时重复发信。
    try:
        db.rollback()
    except Exception:
        pass
    rules = db.query(ReminderRule).filter(ReminderRule.enabled == True).all()  # noqa: E712
    email_recipients = get_email_recipients(db)
    deliveries = {}            # email -> [item dict]
    notif_active = []          # (ref_type, ref_id, title, message, due_date, level, module)
    planned = []               # 用于 dry_run 展示
    stats = {"rules": len(rules), "items_sent": 0, "emails_sent": 0, "skipped_no_recipient": 0}
    active_keys = set()

    for rule in rules:
        ms = _milestones(rule)
        items = _fetch_items(db, rule, today)
        active_ref_ids = {it["ref_id"] for it in items}

        for it in items:
            ref_id = it["ref_id"]
            ref_type = it["ref_type"]
            days_left = it["days_left"]
            active_keys.add((f"reminder_{rule.category}", ref_id))

            level = "danger" if days_left < 0 else ("warning" if days_left <= rule.lead_days else "info")
            notif_active.append((
                f"reminder_{rule.category}", ref_id, it["title"], it["message"],
                it["due_date"], level, rule.label,
            ))

            log = db.query(ReminderSendLog).filter_by(
                rule_id=rule.id, ref_type=ref_type, ref_id=ref_id
            ).first()
            sent = set(
                int(x) for x in (log.sent_milestones or "").split(",") if x.strip().isdigit()
            ) if log else set()
            due_ms = [m for m in ms if m >= days_left]
            new_ms = [m for m in due_ms if m not in sent]
            overdue = days_left < 0
            should_send = bool(new_ms) or (
                overdue and log and log.last_sent_at and (now - log.last_sent_at).days >= 7
            )
            # 路由：仅发给订阅了该 rule.category 的接收人（rule_categories 为空 = 不接收任何）
            matched = [
                r for r in email_recipients
                if rule.category in {c.strip() for c in (r.rule_categories or "").split(",") if c.strip()}
            ]
            planned.append({
                "rule": rule.label, "title": it["title"], "message": it["message"],
                "days_left": days_left, "will_send": should_send,
                "milestones_reached": due_ms, "new_milestones": new_ms,
                "to": [r.email for r in matched],
            })
            if should_send and not dry_run:
                if not email_recipients:
                    stats["skipped_no_recipient"] += 1
                for rec in matched:
                    deliveries.setdefault(rec.email, []).append((rule, it))
                if not log:
                    log = ReminderSendLog(rule_id=rule.id, ref_type=ref_type, ref_id=ref_id)
                    db.add(log)
                stats["items_sent"] += 1

        # 标记已解决（事项离开窗口/已上报/已校准）：清除发送里程碑，下一周期重新提醒
        for log in db.query(ReminderSendLog).filter_by(rule_id=rule.id).all():
            if log.ref_id not in active_ref_ids and not log.resolved:
                log.resolved = True
                log.sent_milestones = ""

    if not dry_run:
        _sync_notifications(db, notif_active, active_keys)
        # 实际发送（按接收人聚合）；仅真实发送成功才更新发送里程碑
        for email, items in deliveries.items():
            subject = f"【{SYSTEM_NAME}】实验室待办提醒（{len(items)} 条）"
            res = send_email(
                email, subject,
                text=_render_text([it for _, it in items]),
                html=_render_html([it for _, it in items]),
            )
            if res.get("sent"):
                stats["emails_sent"] += 1
                for rule, it in items:
                    lg = db.query(ReminderSendLog).filter_by(
                        rule_id=rule.id, ref_type=it["ref_type"], ref_id=it["ref_id"]
                    ).first()
                    if not lg:
                        lg = ReminderSendLog(rule_id=rule.id, ref_type=it["ref_type"], ref_id=it["ref_id"])
                        db.add(lg)
                    due_ms = [m for m in _milestones(rule) if m >= it["days_left"]]
                    prev = set(int(x) for x in (lg.sent_milestones or "").split(",") if x.strip().isdigit())
                    lg.sent_milestones = ",".join(str(m) for m in sorted(prev | set(due_ms)))
                    lg.last_sent_at = now
                    lg.send_count = (lg.send_count or 0) + 1
                    lg.resolved = False
        db.commit()

    if dry_run:
        stats["planned"] = planned
    return stats
