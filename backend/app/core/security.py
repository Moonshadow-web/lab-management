import uuid
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from .config import (
    ALGORITHM,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS,
    SECRET_KEY,
)
from .database import get_db
from ..models.user import User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return pwd_context.verify(password, hashed)
    except Exception:
        return False


def create_access_token(subject: int, expires_minutes: int | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode = {"sub": str(subject), "type": "access", "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def create_refresh_token(subject: int) -> tuple[str, str]:
    """签发 refresh token，返回 (token, jti)。

    jti 存入 refresh_tokens 表用于吊销；token 含 type=refresh 与 exp。
    """
    jti = uuid.uuid4().hex
    expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = {"sub": str(subject), "type": "refresh", "jti": jti, "exp": expire}
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM), jti


def decode_token(token: str, expected_type: str | None = None) -> dict:
    """解码并校验 JWT（签名 + 过期）。可选校验 type 声明。"""
    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    if expected_type and payload.get("type") != expected_type:
        raise JWTError("token type mismatch")
    return payload


def _token_from_request(request: Request, token: str | None) -> str | None:
    """优先 Authorization 头，其次 URL query token，最后 cookie access_token。"""
    if token:
        return token
    if request:
        t = request.query_params.get("token")
        if t:
            return t
        t = request.cookies.get("access_token")
        if t:
            return t
    return None


def get_current_user(
    request: Request,
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效或过期的凭证",
        headers={"WWW-Authenticate": "Bearer"},
    )
    t = _token_from_request(request, token)
    if not t:
        raise credentials_exception
    try:
        payload = jwt.decode(t, SECRET_KEY, algorithms=[ALGORITHM])
        uid = int(payload.get("sub"))
    except (JWTError, ValueError, TypeError):
        raise credentials_exception
    user = db.get(User, uid)
    if user is None or not user.is_active:
        raise credentials_exception
    return user


# 详细组织角色码 → 中文标签（用于展示与审计）。
# 一人可兼任多角色（如吕文娟=质控管理员+继教管理员），用逗号存于 users.roles。
ROLE_LABELS = {
    "admin": "管理员",
    "director": "主任",
    "deputy_director": "副主任",
    "quality_manager": "质量负责人",
    "specialty_leader": "专业组长",
    "qc_manager": "质控管理员",
    "reagent_manager": "试剂管理员",
    "training_manager": "继教管理员",
    "biosafety_officer": "生物安全员",
    "it_manager": "信息管理员",
    "staff": "职工",
    "technical_support": "技术支持",
}


def user_roles_list(user: User) -> list[str]:
    """返回用户拥有的全部角色码（粗粒度 role + 详细 roles 合并去重）。"""
    owned = set()
    if user.role:
        owned.add(user.role)
    if user.roles:
        owned.update(r for r in user.roles.split(",") if r)
    return sorted(owned)


def require_roles(*roles: str):
    """权限校验：用户只要拥有 roles 中的任意一个角色即通过。

    兼容旧的单一 role 字段与新的多角色 roles 字段——两者任一命中即可。
    admin 角色始终自动通过（超级管理员兜底）。
    """

    def dependency(current_user: User = Depends(get_current_user)):
        if not roles:
            return current_user
        owned = set(user_roles_list(current_user))
        if "admin" in owned:
            return current_user
        if not owned.intersection(set(roles)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
        return current_user

    return dependency
