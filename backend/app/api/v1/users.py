from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.crud_base import paginate, write_audit
from ...core.database import get_db
from ...core.security import get_current_user, hash_password, require_roles
from ...models.user import User
from ...schemas import UserCreate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


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
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.username == item.username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = User(
        username=item.username,
        full_name=item.full_name,
        role=item.role,
        department=item.department,
        is_active=item.is_active,
        password_hash=hash_password(item.password or "123456"),
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    write_audit(db, admin, "create", "users", u.id, item.model_dump())
    return u


@router.put("/{uid}", response_model=UserRead)
def update_user(
    uid: int,
    item: UserUpdate,
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
    write_audit(db, admin, "update", "users", uid, item.model_dump(exclude_unset=True))
    return u


@router.delete("/{uid}")
def delete_user(
    uid: int,
    db: Session = Depends(get_db),
    admin: User = Depends(require_roles("admin")),
):
    u = db.get(User, uid)
    if not u:
        raise HTTPException(status_code=404, detail="未找到用户")
    db.delete(u)
    db.commit()
    write_audit(db, admin, "delete", "users", uid, "")
    return {"ok": True}
