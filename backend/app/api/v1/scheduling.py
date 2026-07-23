"""排班模块 API：岗位/计划/分配的 CRUD + 自动生成 + 排班表矩阵 + 我的今日。

路由规划（均挂在 /api/v1 下）：
- /scheduling/posts        岗位定义 CRUD（make_router）
- /scheduling/plans        排班计划 CRUD（make_router）
- /scheduling/assignments  每日分配 CRUD（make_router）
- /scheduling/generate     自动生成排班（POST）
- /scheduling/grid         排班表矩阵（GET，按 岗×日）
- /scheduling/my-today     当前用户某日岗位（GET）

自定义端点单独挂在 router（prefix=/scheduling），不与 assignments 的 /{item_id} 冲突。
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ...core.crud_base import make_router
from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.scheduling import (
    SchedulingPost,
    SchedulingPlan,
    SchedulingAssignment,
    POST_GROUP_DAY,
    POST_GROUP_NIGHT,
    POST_GROUP_SPECIAL,
    ASSIGN_STATUS_ONDUTY,
)
from ...models.user import User
from ...schemas import (
    SchedulingPostCreate,
    SchedulingPostRead,
    SchedulingPostUpdate,
    SchedulingPlanCreate,
    SchedulingPlanRead,
    SchedulingPlanUpdate,
    SchedulingAssignmentCreate,
    SchedulingAssignmentRead,
    SchedulingAssignmentUpdate,
    SchedulingGenerateRequest,
)

WRITE_ROLES = ("admin", "specialty_leader")

posts_router = make_router(
    SchedulingPost, SchedulingPostRead, SchedulingPostCreate, SchedulingPostUpdate,
    search_fields=["name", "notes"],
    filter_fields=["group", "required"],
    order_by=[SchedulingPost.order, SchedulingPost.id],
    prefix="/scheduling/posts",
    write_roles=WRITE_ROLES,
)

plans_router = make_router(
    SchedulingPlan, SchedulingPlanRead, SchedulingPlanCreate, SchedulingPlanUpdate,
    search_fields=["name", "notes"],
    order_by=[SchedulingPlan.id.desc()],
    prefix="/scheduling/plans",
    write_roles=WRITE_ROLES,
)

assignments_router = make_router(
    SchedulingAssignment, SchedulingAssignmentRead, SchedulingAssignmentCreate, SchedulingAssignmentUpdate,
    search_fields=["person", "note"],
    filter_fields=["plan_id", "post_id", "status", "is_early", "is_continuous", "date"],
    order_by=[SchedulingAssignment.date, SchedulingAssignment.post_id],
    prefix="/scheduling/assignments",
    write_roles=WRITE_ROLES,
)

router = APIRouter(prefix="/scheduling", tags=["scheduling"])


def _daterange(start_str: str, end_str: str):
    s = datetime.strptime(start_str, "%Y-%m-%d").date()
    e = datetime.strptime(end_str, "%Y-%m-%d").date()
    cur = s
    while cur <= e:
        yield cur
        cur += timedelta(days=1)


def generate_assignments(db: Session, plan: SchedulingPlan, people: list[str], start: str, end: str) -> int:
    """按规则自动生成每日分配（框架版，后续可调）。

    规则：
    - 仅工作日（周一~周五）生成；周末/节假日框架先留空（另算）。
    - 白班岗（含周三质谱）按轮转池每天取不同人；夜班岗随后取。
    - 同人同日不重复占岗（轮转池切片保证）。
    - 每天白班人员中挑 早班/连班 各一名，尽量不是同一人，每人连续最多 2 天。
    - 门诊辅助岗/电泳岗 required=False 时若人员不足可空缺；电泳周四(required_weekday)优先排。
    """
    posts = db.query(SchedulingPost).order_by(SchedulingPost.order).all()
    if not posts:
        raise HTTPException(status_code=400, detail="请先在 /scheduling/posts 定义岗位")
    day_posts = [p for p in posts if p.group in (POST_GROUP_DAY, POST_GROUP_SPECIAL)]
    night_posts = [p for p in posts if p.group == POST_GROUP_NIGHT]
    pool = [p for p in people if p]
    if not pool:
        raise HTTPException(status_code=400, detail="没有可用人员")

    # 清空该计划在日期范围内的既有分配，重新生成
    db.query(SchedulingAssignment).filter(
        SchedulingAssignment.plan_id == plan.id,
        SchedulingAssignment.date >= start,
        SchedulingAssignment.date <= end,
    ).delete(synchronize_session=False)

    assignments: list[SchedulingAssignment] = []
    n = len(pool)
    idx = 0
    early_state = {"person": None, "streak": 0}
    cont_state = {"person": None, "streak": 0}

    for cur in _daterange(start, end):
        weekday = cur.weekday()  # 0=周一 .. 6=周日
        is_workday = weekday < 5
        if not is_workday:
            continue  # 周末另算（框架留空）
        date_str = cur.strftime("%Y-%m-%d")

        # 当天需要的白班岗（含周三才出现的特殊岗）
        needed = [p for p in day_posts if (p.only_weekday is None or p.only_weekday == weekday)]
        # required_weekday 岗位（如电泳周四必有）排在前面优先占用
        needed.sort(key=lambda p: 0 if (p.required_weekday is not None and p.required_weekday == weekday) else 1)

        day_pool = pool[idx:] + pool[:idx]
        pos = 0

        def take() -> str:
            nonlocal pos
            if pos < len(day_pool):
                v = day_pool[pos]
                pos += 1
                return v
            return ""

        day_assigned: list[tuple[str, SchedulingAssignment]] = []
        for p in needed:
            person = take()
            a = SchedulingAssignment(
                plan_id=plan.id, date=date_str, weekday=weekday, is_workday=True,
                post_id=p.id, person=person, status=ASSIGN_STATUS_ONDUTY,
            )
            day_assigned.append((person, a))
            assignments.append(a)
        for p in night_posts:
            a = SchedulingAssignment(
                plan_id=plan.id, date=date_str, weekday=weekday, is_workday=True,
                post_id=p.id, person=take(), status=ASSIGN_STATUS_ONDUTY,
            )
            assignments.append(a)

        # 早班 / 连班：在当天白班人员中挑，尽量不是同一人，每人连续最多 2 天
        day_people = [dp for dp in (x[0] for x in day_assigned) if dp]
        if day_people:
            if early_state["person"] in day_people and early_state["streak"] < 2:
                early_state["streak"] += 1
            else:
                cands = [x for x in day_people if x != cont_state["person"]]
                early_state["person"] = cands[0] if cands else day_people[0]
                early_state["streak"] = 1
            if cont_state["person"] in day_people and cont_state["streak"] < 2:
                cont_state["streak"] += 1
            else:
                cands = [x for x in day_people if x != early_state["person"]]
                cont_state["person"] = cands[0] if cands else day_people[0]
                cont_state["streak"] = 1
            for person, a in day_assigned:
                if person == early_state["person"]:
                    a.is_early = True
                if person == cont_state["person"]:
                    a.is_continuous = True

        idx = (idx + len(needed) + len(night_posts)) % n

    db.add_all(assignments)
    db.commit()
    return len(assignments)


@router.post("/generate")
def generate(req: SchedulingGenerateRequest, db: Session = Depends(get_db),
             user: User = Depends(require_roles(*WRITE_ROLES))):
    plan = db.get(SchedulingPlan, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="排班计划不存在")
    people = req.people
    if not people:
        people = [
            (u.full_name or u.username)
            for u in db.query(User).filter(User.is_active == True).all()  # noqa: E712
        ]
    start = req.start or plan.start_date
    end = req.end or plan.end_date
    if not start or not end:
        raise HTTPException(status_code=400, detail="计划缺少起止日期，且请求也未提供 start/end")
    count = generate_assignments(db, plan, people, start, end)
    return {"ok": True, "generated": count}


@router.get("/grid")
def grid(plan_id: int = Query(...), start: str | None = None, end: str | None = None,
         db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    plan = db.get(SchedulingPlan, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="排班计划不存在")
    s = start or plan.start_date
    e = end or plan.end_date
    if not s or not e:
        raise HTTPException(status_code=400, detail="缺少日期范围")
    posts = db.query(SchedulingPost).order_by(SchedulingPost.order).all()
    dates = [d.strftime("%Y-%m-%d") for d in _daterange(s, e)]
    rows = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.plan_id == plan_id,
                SchedulingAssignment.date >= s, SchedulingAssignment.date <= e)
        .all()
    )
    cells: dict[int, dict[str, dict]] = {}
    for a in rows:
        cells.setdefault(a.post_id, {})[a.date] = {
            "id": a.id, "person": a.person, "status": a.status,
            "is_early": a.is_early, "is_continuous": a.is_continuous, "note": a.note,
        }
    return {
        "plan_id": plan_id,
        "dates": dates,
        "posts": [{"id": p.id, "name": p.name, "group": p.group, "required": p.required} for p in posts],
        "cells": cells,
    }


@router.get("/my-today")
def my_today(date: str | None = None, db: Session = Depends(get_db),
             user: User = Depends(get_current_user)):
    me = user.full_name or user.username
    d = date or date.today().strftime("%Y-%m-%d")
    rows = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.person == me, SchedulingAssignment.date == d)
        .all()
    )
    out = []
    for a in rows:
        post = db.get(SchedulingPost, a.post_id)
        out.append({
            "date": a.date,
            "post_id": a.post_id,
            "post_name": post.name if post else "",
            "group": post.group if post else "",
            "status": a.status,
            "is_early": a.is_early,
            "is_continuous": a.is_continuous,
            "note": a.note,
            "plan_id": a.plan_id,
        })
    return out
