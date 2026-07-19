"""项目质量要求 CRUD：WS/T 403-2024 / 2025 北京互认 / 2026 NCCL EQA 三类标准。

GET 列表/单条：所有登录用户
POST/PUT/DELETE：需要 admin 角色
POST /seed：幂等灌库，灌过的 source 不会重复追加；admin 角色
GET /matrix：综合矩阵视图——以 test_items 为行，三个标准源为列，支持搜索与分页
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
import re

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

# ── 项目库名 → 标准源中可能的同义叫法（打通综合比对匹配）──
# 例：项目库「二氧化碳」在临床生化里即标准源的「碳酸氢根 / HCO3 / 二氧化碳结合力」
_SYNONYMS = {
    "二氧化碳": ["碳酸氢根", "HCO3", "Bicarbonate", "总二氧化碳", "二氧化碳结合力", "CO2"],
}


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
    排序规则：被至少一个标准源提及的项目在前，三个源均未提及的沉底；
    同组内按 category、id 升序。
    前端可用此接口渲染「一个表格看全部标准」的综合比对页。
    """
    base = db.query(TestItem)

    if q.strip():
        kw = f"%{q.strip()}%"
        base = base.filter(
            or_(TestItem.name.like(kw), TestItem.code.like(kw), TestItem.aliases.like(kw))
        )

    # 批量查出每个 source 下按 item_name 索引的 quality_requirements
    qr_maps = {}
    for src in _SOURCES:
        rows = (
            db.query(QualityRequirement)
            .filter(QualityRequirement.source == src)
            .all()
        )
        qr_maps[src] = {r.item_name: r for r in rows}

    # 预计算归一化映射：去空格/连字符/括号/全角后统一小写，打通名字差异
    def _norm(s: str) -> str:
        return re.sub(r"[\s\-‐—()（）\[\]【】　]", "", s).lower()

    qr_norm_maps = {}
    for src in _SOURCES:
        qr_norm_maps[src] = {_norm(k): v for k, v in qr_maps[src].items()}

    # 模糊匹配辅助：item_name 不完全一致时按包含关系兜底；并应用同义词和归一化匹配
    def _find_best(src: str, name: str) -> QualityRequirement | None:
        candidates = [name] + _SYNONYMS.get(name, [])
        # 1) 候选精确匹配
        for cand in candidates:
            m = qr_maps[src].get(cand)
            if m:
                return m
        # 2) 候选与标准名互相包含
        for cand in candidates:
            for k, v in qr_maps[src].items():
                if cand in k or k in cand:
                    return v
        # 3) 归一化精确匹配（补体C3 ↔ 补体 C3；C肽 ↔ C-肽；免疫球蛋白G ↔ 免疫球蛋白 G 等）
        n_name = _norm(name)
        hit = qr_norm_maps[src].get(n_name)
        if hit:
            return hit
        # 4) 归一化同义词精确匹配
        for cand in candidates:
            n_cand = _norm(cand)
            hit = qr_norm_maps[src].get(n_cand)
            if hit:
                return hit
        # 5) 归一化包含匹配
        for cand in candidates:
            n_cand = _norm(cand)
            for nk, v in qr_norm_maps[src].items():
                if n_cand in nk or nk in n_cand:
                    return v
        return None

    # 先取全部符合搜索条件的项目（数量不大，应用层排序后再分页）
    all_items = base.order_by(TestItem.category, TestItem.id).all()
    total = len(all_items)

    # 统计每个项目被多少源提及（有任一要求字段非空才计入）
    def _mentioned_count(name: str) -> int:
        cnt = 0
        for src in _SOURCES:
            qr = _find_best(src, name)
            if qr is not None and (qr.cv or qr.bias or qr.tea or qr.unit):
                cnt += 1
        return cnt

    annotated = [( _mentioned_count(ti.name), ti) for ti in all_items]
    # 排序：被提及源数降序（均未提及=0 沉底），其次按 category、id 升序
    annotated.sort(key=lambda x: (-x[0], x[1].category, x[1].id))

    page_items = annotated[(page - 1) * page_size: (page - 1) * page_size + page_size]

    rows_out = []
    for mc, ti in page_items:
        rec = {
            "item_id": ti.id,
            "item_code": ti.code or "",
            "item_name": ti.name or "",
            "category": ti.category or "",
            "specimen": ti.specimen or "",
            "mentioned_count": mc,
        }
        for src in _SOURCES:
            qr = _find_best(src, ti.name)
            rec[src] = _qr_row_dict(qr)
        rows_out.append(rec)

    return {"total": total, "page": page, "page_size": page_size, "items": rows_out}
