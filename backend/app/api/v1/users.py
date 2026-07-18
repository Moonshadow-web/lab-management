from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from ...core.crud_base import paginate, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, hash_password, require_roles
from ...models.user import User
from ...schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])

# 前端可用的角色选项（与 security.ROLE_LABELS 同步）
ROLE_OPTIONS = [
    {"code": "admin", "label": "管理员"},
    {"code": "director", "label": "主任"},
    {"code": "deputy_director", "label": "副主任"},
    {"code": "quality_manager", "label": "质量负责人"},
    {"code": "specialty_leader", "label": "专业组长"},
    {"code": "qc_manager", "label": "质控管理员"},
    {"code": "reagent_manager", "label": "试剂管理员"},
    {"code": "training_manager", "label": "继教管理员"},
    {"code": "biosafety_officer", "label": "生物安全员"},
    {"code": "it_manager", "label": "信息管理员"},
    {"code": "staff", "label": "职工"},
    {"code": "technical_support", "label": "技术支持"},
]


@router.get("/role-options")
def get_role_options(
    admin: User = Depends(require_roles("admin")),
):
    """返回可用的角色选项列表，供前端编辑时下拉/多选。"""
    return ROLE_OPTIONS


@router.get("/active")
def list_active_users(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """返回所有活跃用户的精简信息（id/full_name/username/roles），
    供前端「操作者/审核者」类下拉复用。鉴权：任意已登录用户。"""
    rows = (
        db.query(User)
        .filter(User.is_active == True)  # noqa: E712
        .order_by(User.full_name.asc(), User.username.asc())
        .all()
    )
    return [
        {
            "id": u.id,
            "username": u.username,
            "full_name": (u.full_name or "").strip() or u.username,
            "roles": u.roles or "",
        }
        for u in rows
    ]


@router.get("")
def list_users(
    page: int = 1,
    page_size: int = 50,
    q: str | None = None,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    query = db.query(User)
    if q:
        query = query.filter(User.username.ilike(f"%{q}%") | User.full_name.ilike(f"%{q}%"))
    return paginate(query, page, page_size)


@router.post("", response_model=UserRead, status_code=201)
def create_user(
    item: UserCreate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.username == item.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = User(
        username=item.username,
        full_name=item.full_name,
        role=item.role,
        roles=item.roles or "",
        department=item.department,
        is_active=item.is_active,
        must_change_password=True,
        password_hash=hash_password(item.password or "123456"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    write_audit(db, admin, "create", "users", u.id, item.model_dump(), request.client.host if request.client else None)
    return u


@router.put("/{uid}", response_model=UserRead)
def update_user(
    uid: int,
    item: UserUpdate,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(status_code=404, detail="未找到用户")
    for k, v in item.model_dump(exclude_unset=True).items():
        if k == "password":
            if v:
                u.password_hash = hash_password(v)
        else:
            setattr(u, k, v)
    db.commit()
    db.refresh(u)
    write_audit(db, admin, "update", "users", uid, item.model_dump(exclude_unset=True), request.client.host if request.client else None)
    return u


@router.post("/{uid}/reset-password")
def reset_password(
    uid: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    """管理员重置用户密码为初始密码 123456，并标记必须改密。"""
    u = db.get(User, uid)
    if not u:
        raise HTTPException(status_code=404, detail="未找到用户")
    u.password_hash = hash_password("123456")
    u.must_change_password = True
    u.failed_login_attempts = 0
    u.locked_until = None
    db.commit()
    write_audit(db, admin, "update", "users", uid, {"action": "reset_password"}, request.client.host if request.client else None)
    return {"ok": True, "message": "密码已重置为 123456，用户下次登录需修改"}


@router.delete("/{uid}")
def delete_user(
    uid: int,
    request: Request,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(status_code=404, detail="未找到用户")
    db.delete(u)
    db.commit()
    write_audit(db, admin, "delete", "users", uid, "", request.client.host if request.client else None)
    return {"ok": True}
