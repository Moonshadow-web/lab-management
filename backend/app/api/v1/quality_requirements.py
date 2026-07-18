"""项目质量要求 CRUD：WS/T 403-2024 / 2025 北京互认 / 2026 NCCL EQA 三类标准。

GET 列表/单条：所有登录用户
POST/PUT/DELETE：需要 admin 角色
POST /seed：幂等灌库，灌过的 source 不会重复追加；admin 角色
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ...core.crud_base import make_router, paginate
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.quality_requirement import QualityRequirement, QUALITY_SOURCES
from ...models.user import User
from ...schemas import QualityRequirementCreate, QualityRequirementRead, QualityRequirementUpdate
from ...services.quality_requirements_seed import all_seed

router = make_router(
    QualityRequirement,
    QualityRequirementRead,
    QualityRequirementCreate,
    QualityRequirementUpdate,
    search_fields=["item_name", "item_code", "category", "cv", "bias", "tea", "remark"],
    filter_fields=["source", "category"],
    prefix="/quality-requirements",
    write_roles=("admin",),
    order_by=["source", "category", "id"],
)


@router.get("/_meta/sources")
def list_sources(_: User = Depends(get_current_user)):
    """返回所有可用标准源（描述 + 计数），供前端 tab 切换。

    用 _meta 前缀避开 make_router 自动生成的 /{item_id} 路由（int_parsing 冲突）。
    """
    return {"items": [{"id": sid, "name": name} for sid, name in QUALITY_SOURCES]}


@router.post("/_meta/seed", dependencies=[Depends(require_roles("admin"))])
def seed_defaults(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """幂等灌库：已存在的 (source, item_name) 不会重复追加；缺则新增。"""
    seed_rows = all_seed()
    existing = {(r.source, r.item_name): r for r in db.query(QualityRequirement).all()}
    added = updated = skipped = 0
    for row in seed_rows:
        key = (row["source"], row["item_name"])
        if key in existing:
            # 已存在则不更新，避免覆盖人工修改；只统计
            skipped += 1
            continue
        db.add(QualityRequirement(**row))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped, "total_seed": len(seed_rows), "by": user.username}
