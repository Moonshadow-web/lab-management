import json
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
    search_fields: list[str] | None = None,
    filter_fields: list[str] | None = None,
    order_by: list | None = None,
    prefix: str = "",
    after_write: Callable | None = None,
    write_roles: tuple[str, ...] | None = None,
    delete_roles: tuple[str, ...] | None = None,
    json_fields: list[str] | None = None,
):
    """通用 CRUD 路由工厂：分页/搜索、get、create、update、delete，并统一写审计日志。

    权限模型：
    - 查（list/get）：所有登录用户可访问
    - 写（create/update）：需要 write_roles 中的任一角色；admin 自动通过
    - 删（delete）：需要 delete_roles 中的任一角色；admin 自动通过
      未设 delete_roles 时回退到 write_roles
    - write_roles=None 时不做角色限制（向后兼容，仅要求登录）

    json_fields：声明为 Text 但 API 层用 list/dict 表达的列名；create/update 时
    自动 json.dumps 序列化（ensure_ascii=False），读回时由 schema 反序列化。
    """
    _json_fields = set(json_fields or [])
    # 写权限依赖：有 write_roles 则校验角色，否则仅要求登录
    WriteDep = require_roles(*write_roles) if write_roles else get_current_user
    # 删除权限：独立配置；未设则沿用 write_roles
    DeleteRoles = delete_roles if delete_roles is not None else write_roles
    DeleteDep = require_roles(*DeleteRoles) if DeleteRoles else get_current_user
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

    @router.post("", status_code=201)
    def create(
        item: CreateSchema,
        request: Request,
        db: Session = Depends(get_db),
        user: User = Depends(WriteDep),
    ):
        data = item.model_dump()
        for f in _json_fields:
            if f in data and data[f] is not None and not isinstance(data[f], str):
                data[f] = json.dumps(data[f], ensure_ascii=False)
        obj = Model(**data)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        write_audit(db, user, "create", Model.__tablename__, obj.id, data, _ip(request))
        if after_write:
            after_write(db, "create", obj)
        _dbg = {"id": obj.id, "_debug_dump": item.model_dump(), "_debug_data": {k: (str(v)[:300] if not isinstance(v, (int, float, bool, str, type(None))) else v) for k, v in data.items()}}
        try:
            _rs = ReadSchema.model_validate(obj)
            _dbg["_dbg_readschema_plan"] = _rs.plan_items
            _dbg["_dbg_readschema_scores"] = _rs.scores_json
        except Exception as e:
            _dbg["_dbg_readschema_err"] = str(e)[:300]
        for fld in ("plan_items", "scores_json", "detail_json", "items_json", "sample_nos", "results_json", "sign_in_header", "subjects_json"):
            if hasattr(obj, fld):
                raw = getattr(obj, fld)
                try:
                    loaded = json.loads(raw)
                    _dbg["_dbg_" + fld] = {"repr": repr(raw)[:200], "load_ok": True, "loaded": str(loaded)[:200]}
                except Exception as e:
                    _dbg["_dbg_" + fld] = {"repr": repr(raw)[:200], "load_ok": False, "err": str(e)}
        return _dbg

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
            if k in _json_fields and v is not None and not isinstance(v, str):
                v = json.dumps(v, ensure_ascii=False)
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
        user: User = Depends(DeleteDep),
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
