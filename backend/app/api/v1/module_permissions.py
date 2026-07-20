"""模块写权限配置 API。

- GET /api/v1/module-permissions/structure 返回所有模块 + 各自允许的角色 + 模块/角色字典
- GET /api/v1/module-permissions 返回所有 (module_key, role_code) 配对
- PUT /api/v1/module-permissions/{module_key} body={"roles":[...]} 全量替换该模块的角色
- POST /api/v1/module-permissions/reset 把全部配置重置为出厂默认

所有写操作：admin 角色。
GET：所有登录用户。
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ...core.crud_base import write_audit
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models import ModulePermission
from ...models.module_permission import (
    DEFAULT_MODULE_PERMISSIONS, ALL_MODULES, ALL_ROLES,
)
from ...models.user import User

router = APIRouter(prefix="/module-permissions", tags=["module-permissions"])


class StructureResponse(BaseModel):
    modules: list[dict]  # [{key, label, roles: [code]}]
    roles: list[dict]    # [{code, label}]


@router.get("/structure", response_model=StructureResponse)
def get_structure(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """返回模块→角色结构（用于前端权限配置页 + 用户管理矩阵 tab）。

    不存在的模块在表里查不到时，回退到出厂默认。
    """
    # 收集表中所有配对
    pairs = db.query(ModulePermission).all()
    by_mod: dict[str, list[str]] = {}
    for p in pairs:
        by_mod.setdefault(p.module_key, []).append(p.role_code)
    # 合并默认：对每一个模块键，取「DB 已配置角色」与「出厂默认角色」的**并集**。
    # 目的：
    #   1. 新分级键（如 comparison-create / interlab-create）即使 DB 无记录也始终返回默认角色，
    #      避免前端 canWrite 命中「缺键→默认允许」分支，导致 staff/member 被误判可写。
    #   2. 视图级键（comparison/interlab/qc-monthly/qc-target）的默认含 member/staff，
    #      取并集后不会被 DB 里的部分配置意外收窄，保证职工始终可查看。
    #   注：并集只会「放宽」不会「收窄」——管理员无法把角色限制到默认之下，以安全兜底为准。
    modules_out = []
    for key, label in ALL_MODULES:
        db_roles = by_mod.get(key) or []
        default_roles = DEFAULT_MODULE_PERMISSIONS.get(key, ["admin"])
        union, seen = [], set()
        for r in db_roles + default_roles:
            if r not in seen:
                seen.add(r)
                union.append(r)
        modules_out.append({"key": key, "label": label, "roles": union})
    return StructureResponse(modules=modules_out, roles=[{"code": c, "label": l} for c, l in ALL_ROLES])


class RolesPayload(BaseModel):
    roles: list[str]


@router.put("/{module_key}", dependencies=[Depends(require_roles("admin"))])
def set_module_roles(
    module_key: str,
    payload: RolesPayload,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
    request = None,  # 留位，方便 write_audit
):
    """替换指定模块的角色白名单。

    校验：module_key 必须是已知模块；roles 必须是已知角色码。
    旧行先删后插，事务性由 SQLAlchemy Session 保证。
    """
    # 校验 module
    known_keys = {k for k, _ in ALL_MODULES}
    if module_key not in known_keys:
        raise HTTPException(status_code=400, detail=f"未知模块: {module_key}")
    # 校验 roles
    known_codes = {c for c, _ in ALL_ROLES}
    bad = [r for r in payload.roles if r not in known_codes]
    if bad:
        raise HTTPException(status_code=400, detail=f"未知角色: {bad}")
    # 不允许把 admin 从白名单移除（admin 仍是通杀，但保留显式记录便于审计）
    if "admin" not in payload.roles:
        payload.roles = ["admin", *payload.roles]

    # 删旧
    db.query(ModulePermission).filter(ModulePermission.module_key == module_key).delete()
    # 插新
    for r in payload.roles:
        db.add(ModulePermission(module_key=module_key, role_code=r, updated_by=user.username))
    db.commit()
    write_audit(db, user, "update", "module_permissions", module_key,
                f"roles={payload.roles}", getattr(request, "client", None).host if request else None)
    return {"ok": True, "module_key": module_key, "roles": payload.roles}


@router.post("/reset", dependencies=[Depends(require_roles("admin"))])
def reset_to_default(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """把所有模块重置为出厂默认（硬编码值）。**慎用**：会清空所有自定义改动。"""
    db.query(ModulePermission).delete()
    for mod_key, roles in DEFAULT_MODULE_PERMISSIONS.items():
        for r in roles:
            db.add(ModulePermission(module_key=mod_key, role_code=r, updated_by=user.username))
    db.commit()
    write_audit(db, user, "reset", "module_permissions", 0, "reset to default", None)
    return {"ok": True, "modules": len(DEFAULT_MODULE_PERMISSIONS)}
