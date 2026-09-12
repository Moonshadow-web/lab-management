# -*- coding: utf-8 -*-
"""专业组相关认证辅助（不改动 core/security.py，避免影响既有认证链路）。

- create_group_access_token：签发带 active_group 的 access token
- get_current_group：从请求令牌中取当前专业组（缺失/非法 → 默认生免组）
"""
from datetime import datetime, timedelta, timezone

from fastapi import Depends, Request
from jose import jwt

from .config import ACCESS_TOKEN_EXPIRE_MINUTES, ALGORITHM, SECRET_KEY
from .security import decode_token, get_current_user
from ..models.user import User

DEFAULT_GROUP_CODE = "sm"  # 生免组
ADMIN_ROLES = ("admin",)


def create_group_access_token(user_id: int, group_code: str, expires_minutes: int | None = None) -> str:
    """签发 access token 并在载荷中写入 active_group。"""
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "type": "access",
        "exp": expire,
        "active_group": (group_code or DEFAULT_GROUP_CODE).strip().lower(),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def _token_of(request: Request) -> str | None:
    """从请求中取令牌：Authorization 头优先，其次 query，最后 cookie。"""
    auth = request.headers.get("Authorization") if request else None
    if auth and auth.lower().startswith("bearer "):
        return auth[7:].strip()
    if request:
        t = request.query_params.get("token") or request.cookies.get("access_token")
        if t:
            return t
    return None


def get_current_group(request: Request, user: User = Depends(get_current_user)) -> str:
    """当前专业组：令牌中的 active_group → 用户所属组 → 生免组。

    老令牌（无 active_group）自然回落到用户所属组/生免组，行为与改造前一致。
    """
    t = _token_of(request)
    if t:
        try:
            payload = decode_token(t, "access")
            g = (payload.get("active_group") or "").strip().lower()
            if g:
                return g
        except Exception:  # noqa: BLE001
            pass
    return (getattr(user, "group_code", "") or DEFAULT_GROUP_CODE).strip().lower()


def is_admin(user: User) -> bool:
    roles = (getattr(user, "role", "") or "") + "," + (getattr(user, "roles", "") or "")
    return "admin" in [r.strip() for r in roles.split(",") if r.strip()]
