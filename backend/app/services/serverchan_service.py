"""方糖 ServerChan 推送（个人微信，免企业资质）。

机制：用户登录 sctapi.ftqq.com 用微信扫码关注「方糖」公众号，复制自己的 SendKey，
     存到接收人记录 NotifyRecipient.wx_uid 字段（此处复用该列，语义=ServerChan SendKey）。
提醒引擎按人推送：POST https://sctapi.ftqq.com/send/{sendkey}.send
表单字段：title(必填,≤100字) / desp(选填, 支持 Markdown, ≤30000字)
返回 JSON：成功 code==0；失败返回非 0（如 40001 错误的Key）。
"""
import json
import logging
import urllib.parse
import urllib.request

from ..core.config import SYSTEM_NAME

logger = logging.getLogger("serverchan")

API_SEND = "https://sctapi.ftqq.com/send/{key}.send"


def send_serverchan(title, desp="", sendkey=""):
    """向指定 SendKey 推送一条微信消息。

    返回 dict：成功 {"sent": True, "raw": ...}；失败 {"sent": False, "error": str}。
    sendkey 为空时直接返回未配置，不发起请求。
    """
    if not sendkey:
        return {"sent": False, "error": "缺少 ServerChan SendKey（请在接收人处填写 wx_uid）"}
    url = API_SEND.format(key=sendkey)
    data = urllib.parse.urlencode({"title": title, "desp": desp or ""}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        detail = ""
        try:
            detail = e.read().decode("utf-8", "replace")
        except Exception:
            pass
        logger.error("[SERVERCHAN-HTTPERROR] status=%s body=%s", e.code, detail[:300])
        return {"sent": False, "error": f"HTTP {e.code}: {detail[:200]}"}
    except Exception as e:  # noqa: BLE001
        logger.error("[SERVERCHAN-ERROR] key=%s error=%s", (sendkey or "")[:8], e)
        return {"sent": False, "error": repr(e)}
    try:
        j = json.loads(body)
    except Exception:
        return {"sent": False, "error": f"非预期响应: {body[:200]}"}
    if j.get("code") == 0:
        return {"sent": True, "raw": j}
    return {"sent": False, "error": j.get("message") or j.get("info") or str(j)}


def is_configured():
    """ServerChan 无需全局配置（SendKey 存于接收人），这里恒为 True 表示通道可用。"""
    return True
