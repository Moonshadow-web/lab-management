from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ...core.crud_base import write_audit
from ...core.database import get_db
from ...core.security import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)
from ...models.user import User
from ...schemas import ChangePassword, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# 登录失败锁定策略
MAX_FAILED_ATTEMPTS = 5
LOCK_DURATION_MINUTES = 15


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _is_locked(user: User) -> bool:
    return bool(user.locked_until and _now_utc() < user.locked_until.replace(tzinfo=timezone.utc))


def _lock_msg(user: User) -> str:
    remain = user.locked_until.replace(tzinfo=timezone.utc) - _now_utc()
    mins = max(1, int(remain.total_seconds() // 60))
    return f"账号已锁定，请 {mins} 分钟后重试"


@router.post("/login")
def login(
    form: OAuth2PasswordRequestForm = Depends(),
    request: Request = None,
    db: Session = Depends(get_db),
):
    ip = request.client.host if request and request.client else ""
    user = db.query(User).filter(User.username == form.username).first()

    # 账号不存在 → 统一报错（不暴露用户名是否存在），但记审计
    if not user:
        write_audit(db, None, "login_failed", "auth", 0, f"username={form.username}", ip)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户名或密码错误")

    # 锁定中 → 拒绝
    if _is_locked(user):
        write_audit(db, user, "login_blocked", "users", user.id, "account locked", ip)
        raise HTTPException(status_code=status.HTTP_423_LOCKED, detail=_lock_msg(user))

    # 账号停用 → 拒绝
    if not user.is_active:
        write_audit(db, user, "login_failed", "users", user.id, "account disabled", ip)
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已停用，请联系管理员")

    # 密码校验
    if not verify_password(form.password, user.password_hash):
        user.failed_login_attempts = (user.failed_login_attempts or 0) + 1
        if user.failed_login_attempts >= MAX_FAILED_ATTEMPTS:
            user.locked_until = _now_utc() + timedelta(minutes=LOCK_DURATION_MINUTES)
            write_audit(db, user, "login_locked", "users", user.id,
                        f"failed={user.failed_login_attempts}", ip)
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_423_LOCKED,
                detail=f"连续 {MAX_FAILED_ATTEMPTS} 次密码错误，账号已锁定 {LOCK_DURATION_MINUTES} 分钟",
            )
        write_audit(db, user, "login_failed", "users", user.id,
                    f"attempts={user.failed_login_attempts}", ip)
        db.commit()
        remaining = MAX_FAILED_ATTEMPTS - user.failed_login_attempts
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户名或密码错误（剩余 {remaining} 次尝试）",
        )

    # 登录成功 → 清零失败计数与锁定
    user.failed_login_attempts = 0
    user.locked_until = None
    db.commit()
    write_audit(db, user, "login", "users", user.id, "login success", ip)
    token = create_access_token(user.id)
    return {
        "access_token": token,
        "token_type": "bearer",
        "must_change_password": bool(user.must_change_password),
        "roles": user.roles or "",
    }


@router.post("/change-password")
def change_password(
    payload: ChangePassword,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """登录用户自主修改密码（首次强制改密或自愿修改）。"""
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码错误")
    if payload.old_password == payload.new_password:
        raise HTTPException(status_code=400, detail="新密码不能与原密码相同")
    pw = payload.new_password
    if len(pw) < 8 or not (any(c.isdigit() for c in pw) and any(c.isalpha() for c in pw)):
        raise HTTPException(status_code=400, detail="新密码至少 8 位，且需同时包含字母和数字")
    user.password_hash = hash_password(pw)
    user.must_change_password = False
    db.commit()
    write_audit(db, user, "update", "users", user.id, {"action": "change_password"})
    return {"ok": True}


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)):
    return user
