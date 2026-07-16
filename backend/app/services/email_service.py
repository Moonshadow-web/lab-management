"""邮件发送服务：基于标准库 smtplib，配置来自环境变量（见 core/config.py）。

设计原则：
- 凭证就绪（SMTP_HOST + SMTP_USER 均配置）即真正发信；
- 未配置时降级为本地日志（logger.warning 打印拟发送内容），不抛错、不阻塞主流程，
  便于本地开发与上云迁移阶段先把链路跑通，配好凭证即可真发。

典型配置（QQ 邮箱示例）：
  SMTP_HOST=smtp.qq.com
  SMTP_PORT=465            # 465 走 SSL；587 走 STARTTLS
  SMTP_USER=815268425@qq.com
  SMTP_PASS=<邮箱授权码>    # 注意是授权码，不是登录密码
  MAIL_FROM=815268425@qq.com
"""
import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

from ..core.config import MAIL_FROM, SMTP_HOST, SMTP_PASS, SMTP_PORT, SMTP_TLS, SMTP_USER, SYSTEM_NAME

logger = logging.getLogger("email_service")


def smtp_configured() -> bool:
    """是否已配置 SMTP（配置后才真正发信，否则走降级日志）。"""
    return bool(SMTP_HOST and SMTP_USER)


def _render_text(notifications: Iterable) -> str:
    lines = [f"【{SYSTEM_NAME}】待办提醒", ""]
    for n in notifications:
        due = f"（截止 {n.due_date}）" if getattr(n, "due_date", "") else ""
        lines.append(f"· [{n.level}] {n.title}{due}")
        if getattr(n, "message", ""):
            lines.append(f"    {n.message}")
    lines.append("")
    lines.append("（此邮件由系统自动发送，请勿直接回复）")
    return "\n".join(lines)


def _render_html(notifications: Iterable) -> str:
    rows = []
    for n in notifications:
        due = f"（截止 {n.due_date}）" if getattr(n, "due_date", "") else ""
        msg = getattr(n, "message", "") or ""
        rows.append(
            f"<tr>"
            f"<td style='padding:6px 10px;border:1px solid #eee'>{n.level}</td>"
            f"<td style='padding:6px 10px;border:1px solid #eee'>"
            f"<b>{n.title}</b>{due}<br/><span style='color:#555'>{msg}</span></td>"
            f"</tr>"
        )
    return (
        f"<h3 style='margin:0 0 12px'>【{SYSTEM_NAME}】待办提醒</h3>"
        f"<table border='0' cellpadding='0' cellspacing='0' "
        f"style='border-collapse:collapse;font-size:14px;width:100%'>"
        f"{''.join(rows)}</table>"
        "<p style='color:#999;font-size:12px;margin-top:12px'>此邮件由系统自动发送，请勿直接回复。</p>"
    )


def send_email(to_addrs, subject: str, text: str = None, html: str = None) -> dict:
    """发送一封邮件。to_addrs 可为字符串或列表。

    返回 {"sent": bool, "detail": str, "to": [...]}
    - 无收件人 → sent=False, detail="no_recipients"
    - 未配置 SMTP → sent=False, detail="smtp_not_configured_logged"（内容已记日志）
    - 发送成功 → sent=True, detail="ok"
    - 发送异常 → sent=False, detail="error:..."
    """
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    to_addrs = [a for a in (to_addrs or []) if a]
    if not to_addrs:
        return {"sent": False, "detail": "no_recipients"}

    if not smtp_configured():
        # 降级：记录到日志，不真正发送
        logger.warning(
            "[EMAIL-DEGRADED] to=%s subject=%s\n%s",
            ",".join(to_addrs), subject, text or html or "",
        )
        return {"sent": False, "detail": "smtp_not_configured_logged", "to": to_addrs}

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = MAIL_FROM
    msg["To"] = ", ".join(to_addrs)
    if html:
        msg.set_content(text or "请使用支持 HTML 的邮件客户端查看。")
        msg.add_alternative(html, subtype="html")
    else:
        msg.set_content(text or "")

    try:
        if SMTP_PORT == 465:
            with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        else:
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as s:
                if SMTP_TLS:
                    s.starttls()
                s.login(SMTP_USER, SMTP_PASS)
                s.send_message(msg)
        return {"sent": True, "detail": "ok", "to": to_addrs}
    except Exception as e:  # noqa: BLE001
        logger.error("[EMAIL-ERROR] to=%s error=%s", ",".join(to_addrs), e)
        return {"sent": False, "detail": f"error:{e}", "to": to_addrs}


def send_notifications_email(to_addrs, notifications: Iterable) -> dict:
    """给一组接收人发送「待办提醒汇总」邮件。

    to_addrs: 收件地址字符串或列表；notifications: Notification 对象列表。
    返回 {"sent": int, "logged": int, "recipients": int, "results": [...]}
    """
    if isinstance(to_addrs, str):
        to_addrs = [to_addrs]
    to_addrs = [a for a in (to_addrs or []) if a]
    if not to_addrs or not notifications:
        return {"sent": 0, "logged": 0, "recipients": len(to_addrs), "results": []}

    subject = f"【{SYSTEM_NAME}】实验室待办提醒（{len(list(notifications))} 条）"
    text = _render_text(notifications)
    html = _render_html(notifications)

    sent = 0
    logged = 0
    results = []
    for to in to_addrs:
        res = send_email(to, subject, text=text, html=html)
        if res.get("sent"):
            sent += 1
        else:
            logged += 1
        results.append({"to": to, **res})
    return {"sent": sent, "logged": logged, "recipients": len(to_addrs), "results": results}
