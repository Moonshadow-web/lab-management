"""项目质量要求 CRUD：WS/T 403-2024 / 2025 北京互认 / 2026 NCCL EQA 三类标准。

GET 列表/单条：所有登录用户
POST/PUT/DELETE：需要 admin 角色
POST /seed：幂等灌库，灌过的 source 不会重复追加；admin 角色
GET /matrix：综合矩阵视图——以 test_items 为行，三个标准源为列，支持搜索与分页
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ...core.crud_base import make_router, paginate
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.quality_requirement import QualityRequirement, QUALITY_SOURCES
from ...models.test_item import TestItem
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


# ── 三个标准源的 source 常量，与 QUALITY_SOURCES 顺序一致 ──
_SOURCES = [s[0] for s in QUALITY_SOURCES]  # ["wst403-2024", "bj-hr-2025", "nccl-2026"]


def _qr_row_dict(row: QualityRequirement | None) -> dict:
    """把 QualityRequirement 行转为字典；NULL 时返回全空。"""
    if row is None:
        return {"id": None, "cv": "", "bias": "", "tea": "", "unit": "", "category": ""}
    return {
        "id": row.id,
        "category": row.category or "",
        "cv": row.cv or "",
        "bias": row.bias or "",
        "tea": row.tea or "",
        "unit": row.unit or "",
    }


@router.get("/_meta/matrix")
def matrix_view(
    q: str = Query("", description="搜索关键词（匹配项目名称/别名）"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """综合矩阵视图：以 test_items 为行，三个标准源（行标/北京/卫健委）为列。

    返回每行的项目基本信息 + 三个源各自的 CV/Bias/TEa/unit。
    前端可用此接口渲染「一个表格看全部标准」的综合比对页。
    """
    base = db.query(TestItem)

    if q.strip():
        kw = f"%{q.strip()}%"
        base = base.filter(
            or_(TestItem.name.like(kw), TestItem.code.like(kw), TestItem.aliases.like(kw))
        )

    total = base.count()
    items = base.order_by(TestItem.category, TestItem.id).offset((page - 1) * page_size).limit(page_size).all()

    # 批量查出每个 source 下按 item_name 索引的 quality_requirements
    qr_maps = {}
    for src in _SOURCES:
        rows = (
            db.query(QualityRequirement)
            .filter(QualityRequirement.source == src)
            .all()
        )
        qr_maps[src] = {r.item_name: r for r in rows}

    # 模糊匹配辅助：item_name 不完全一致时按包含关系兜底
    def _find_best(src: str, name: str) -> QualityRequirement | None:
        m = qr_maps[src].get(name)
        if m:
            return m
        # 尝试反向包含（标准名包含项目名 或 项目名包含标准名）
        for k, v in qr_maps[src].items():
            if name in k or k in name:
                return v
        return None

    rows_out = []
    for ti in items:
        rec = {
            "item_id": ti.id,
            "item_code": ti.code or "",
            "item_name": ti.name or "",
            "category": ti.category or "",
            "specimen": ti.specimen or "",
        }
        for src in _SOURCES:
            qr = _find_best(src, ti.name)
            rec[src] = _qr_row_dict(qr)
        rows_out.append(rec)

    return {"total": total, "page": page, "page_size": page_size, "items": rows_out}
