from datetime import datetime
from typing import Callable

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from functools import reduce

from sqlalchemy import or_, case
from sqlalchemy.orm import Session

from .database import get_db
from .security import get_current_user, require_roles
from ..models.audit_log import AuditLog
from ..models.user import User


def write_audit(db: Session, user: User | None, action: str, table: str, record_id, detail, ip: str | None = None):
    db.add(
        AuditLog(
            user_id=user.id if user else 0,
            action=action,
            table_name=table,
            record_id=record_id or 0,
            detail=str(detail)[:2000],
            ip=ip,
        )
    )
    db.commit()


def paginate(query, page: int, page_size: int):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    pages = (total + page_size - 1) // page_size if page_size else 0
    return {"items": items, "total": total, "page": page, "pages": pages, "page_size": page_size}


def make_router(
    Model,
    ReadSchema: type[BaseModel],
    CreateSchema: type[BaseModel],
    UpdateSchema: type[BaseModel],
    search_fields: list[str],
    filter_fields: list[str] | None = None,
    order_by: list | None = None,
    prefix: str = "",
    after_write: Callable | None = None,
    write_roles: tuple[str, ...] | None = None,
):
    """通用 CRUD 路由工厂：分页/搜索、get、create、update、delete，并统一写审计日志。

    权限模型：
    - 查（list/get）：所有登录用户可访问
    - 改（create/update/delete）：需要 write_roles 中的任一角色；admin 自动通过
    - write_roles=None 时不做角色限制（向后兼容，仅要求登录）
    """
    # 写权限依赖：有 write_roles 则校验角色，否则仅要求登录
    WriteDep = require_roles(*write_roles) if write_roles else get_current_user
    router = APIRouter(prefix=prefix, tags=[Model.__name__])

    @router.get("")
    def list_items(
        request: Request,
        page: int = 1,
        page_size: int = 20,
        q: str | None = None,
        db: Session = Depends(get_db),
        user: User = Depends(get_current_user),
    ):
        params = dict(request.query_params)
        query = db.query(Model)
        if q and search_fields:
            conds = [getattr(Model, f).ilike(f"%{q}%") for f in search_fields if hasattr(Model, f)]
            if conds:
                query = query.filter(or_(*conds))
                # 相关性排序：精确匹配(3) > 前缀匹配(2) > 模糊包含(1)
                # 避免缩写搜索（如 PA）被英文名里恰好含该子串的项目淹没
                weights = []
                for f in search_fields:
                    if not hasattr(Model, f):
                        continue
                    col = getattr(Model, f)
                    weights.append(
                        case(
                            (col.ilike(q), 3),
                            (col.ilike(f"{q}%"), 2),
                            (col.ilike(f"%{q}%"), 1),
                            else_=0,
                        )
                    )
                relevance = reduce(lambda a, b: a + b, weights) if len(weights) > 1 else weights[0]
                query = query.order_by(relevance.desc(), Model.id.desc())
        for f in filter_fields or []:
            val = params.get(f)
            if val is not None and hasattr(Model, f):
                query = query.filter(getattr(Model, f) == val)
        if not (q and search_fields):
            if order_by:
                query = query.order_by(*order_by)
            else:
                query = query.order_by(Model.id.desc())
        return paginate(query, page, page_size)

    @router.get("/{item_id}", response_model=ReadSchema)
    def get_item(item_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="未找到记录")
        return obj

    @router.post("", response_model=ReadSchema, status_code=201)
    def create(
        item: CreateSchema,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
    ):
        data = item.model_dump()
        obj = Model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        write_audit(db, user, "create", Model.__tablename__, obj.id, data, _ip(request))
        if after_write:
            after_write(db, "create", obj)
        return obj

    @router.put("/{item_id}", response_model=ReadSchema)
    def update(
        item_id: int,
        item: UpdateSchema,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
    ):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="未找到记录")
        changes = item.model_dump(exclude_unset=True)
        for k, v in changes.items():
            setattr(obj, k, v)
        if hasattr(obj, "updated_at"):
            obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        write_audit(db, user, "update", Model.__tablename__, item_id, changes, _ip(request))
        if after_write:
            after_write(db, "update", obj)
        return obj

    @router.delete("/{item_id}")
    def delete(
        item_id: int,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
    ):
        obj = db.get(Model, item_id)
        if not obj:
            raise HTTPException(status_code=404, detail="未找到记录")
        db.delete(obj)
        db.commit()
        write_audit(db, user, "delete", Model.__tablename__, item_id, "", _ip(request))
        if after_write:
            after_write(db, "delete", obj)
        return {"ok": True}

    return router


def _ip(request: Request) -> str | None:
    return request.client.host if request and request.client else None
