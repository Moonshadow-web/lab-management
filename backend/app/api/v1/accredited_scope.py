"""认可能力范围子模块 API：CRUD + 批量导入（供 xlsx 种子导入脚本调用）。

权限模型沿用 15189 内审专项其他子模块（文件评审/自查/科室内审）：
- 查（list/get）：所有登录用户
- 写（create/update/delete）：WRITE_ROLES 中任一角色或 admin
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, write_audit
from ...core.database import get_db
from ...core.security import require_roles
from ...models.iso15189 import AccreditedScope
from ...models.user import User
from ...schemas import (
    AccreditedScopeCreate,
    AccreditedScopeRead,
    AccreditedScopeUpdate,
)

WRITE_ROLES = (
    "admin", "quality_manager", "qc_manager", "training_manager",
    "reagent_manager", "it_manager", "specialty_leader", "leader",
)

scope_router = APIRouter(tags=["accredited-scope"])

crud_router = make_router(
    AccreditedScope, AccreditedScopeRead, AccreditedScopeCreate, AccreditedScopeUpdate,
    search_fields=["item_name", "sample_type", "method_name", "instrument_name", "reagent_name", "calibrator"],
    filter_fields=["category_l1", "category_l2", "method_id", "instrument_id", "reagent_id"],
    prefix="/accredited-scope",
    write_roles=WRITE_ROLES,
)
scope_router.include_router(crud_router)


@scope_router.post("/accredited-scope/batch")
def batch_import(
    items: list[AccreditedScopeCreate],
    replace: bool = False,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles(*WRITE_ROLES)),
):
    """批量导入认可能力范围（xlsx 种子脚本调用）。

    - replace=True 时先清空现有全部行再插入（用于重新全量导入）。
    - 一次事务内写入，返回新建条数。
    """
    if replace:
        db.query(AccreditedScope).delete()
    created = []
    for it in items:
        obj = AccreditedScope(**it.model_dump())
        db.add(obj)
        db.flush()
        created.append(obj.id)
    db.commit()
    write_audit(db, user, "create", "accredited_scopes", 0, {"count": len(created), "replace": replace})
    return {"ok": True, "created": len(created)}
