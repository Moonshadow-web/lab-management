"""微信推送（WxPusher）：按人精准推送提醒到用户微信。

设计要点：
- appToken 来自环境变量 WXPUSHER_APP_TOKEN；WXPUSHER_ENABLED 控制是否真正发送。
- 未配置 / 未启用 → 降级为本地日志（与邮件同策略），便于上云前验证流程不中断。
- 发送：POST /api/send/message
- 取关用户 UID：GET /api/fun/wxuser/v2（按 extra 解析，extra=接收人id，命中记录的 target 字段）
- 生成带参数的关注二维码：POST /api/fun/create/qrcode（extra=接收人id）
官方文档：https://wxpusher.zjiecode.com/docs/
"""
import json
import logging
import urllib.request

from ..core.config import SYSTEM_NAME, WXPUSHER_APP_TOKEN, WXPUSHER_ENABLED

logger = logging.getLogger("wxpusher")

API_BASE = "https://wxpusher.zjiecode.com/api"


def is_configured() -> bool:
    return bool(WXPUSHER_ENABLED and WXPUSHER_APP_TOKEN)


def send_wxpusher(content, uids, summary=None, url="", content_type=2):
    """向指定 uids 发送微信消息。content 支持 HTML(content_type=2)。
    返回 dict：{sent: bool, detail: str}。
    """
    if not is_configured():
        logger.warning("[WXPUSHER-DEGRADED] 未配置(enabled=%s) uids=%s\n%s",
                       WXPUSHER_ENABLED, uids, content)
        return {"sent": False, "detail": "wxpusher_not_configured_logged"}
    if not uids:
        return {"sent": False, "detail": "no_uids"}
    if isinstance(uids, str):
        uids = [uids]
    payload = {
        "appToken": WXPUSHER_APP_TOKEN,
        "content": content,
        "contentType": content_type,
        "uids": uids,
    }
    if summary:
        payload["summary"] = summary[:100]
    if url:
        payload["url"] = url
    try:
        req = urllib.request.Request(
            f"{API_BASE}/send/message",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") != 1000:
            logger.error("[WXPUSHER-FAIL] code=%s msg=%s", data.get("code"), data.get("msg"))
            return {"sent": False, "detail": data.get("msg", "api_error")}
        # 逐 uid 检查，记录失败（如 uid 不存在/未关注）
        for item in (data.get("data", []) or []):
            if item.get("code") != 1000:
                logger.warning("[WXPUSHER-PARTIAL] uid=%s status=%s",
                               item.get("uid"), item.get("status"))
        return {"sent": True, "detail": data.get("msg", "ok")}
    except Exception as e:  # noqa: BLE001
        logger.error("[WXPUSHER-ERROR] uids=%s error=%s", uids, e)
        return {"sent": False, "detail": str(e)}


def resolve_uid_by_extra(extra, max_pages=5):
    """按 extra（=接收人id）在关注用户列表中匹配，返回 uid 或 None。
    V2 列表记录含 target 字段，参数二维码的 extra 会体现在 target 上。
    """
    if not is_configured():
        return None
    extra = str(extra)
    for page in range(1, max_pages + 1):
        try:
            url = f"{API_BASE}/fun/wxuser/v2?appToken={WXPUSHER_APP_TOKEN}&page={page}&pageSize=100"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") != 1000:
                break
            payload = data.get("data", {}) or {}
            records = payload.get("records", []) or []
            if not records:
                break
            for u in records:
                if str(u.get("target", "")) == extra:
                    return u.get("uid")
            if page * 100 >= (payload.get("total", 0) or 0):
                break
        except Exception as e:  # noqa: BLE001
            logger.error("[WXPUSHER-ERROR] resolve_uid extra=%s error=%s", extra, e)
            break
    return None


def create_follow_qrcode(extra, valid_time=1800):
    """生成带 extra 的关注二维码，返回二维码图片/地址或 None。"""
    if not is_configured():
        return None
    try:
        url = f"{API_BASE}/fun/create/qrcode"
        body = json.dumps(
            {"appToken": WXPUSHER_APP_TOKEN, "extra": str(extra), "validTime": valid_time}
        ).encode("utf-8")
        req = urllib.request.Request(
            url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        if data.get("code") == 1000:
            return data.get("data")
    except Exception as e:  # noqa: BLE001
        logger.error("[WXPUSHER-ERROR] create_qrcode extra=%s error=%s", extra, e)
    return None
