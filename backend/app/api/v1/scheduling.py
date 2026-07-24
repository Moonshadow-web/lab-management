"""排班模块 API：岗位/计划/分配的 CRUD + 自动生成 + 排班表矩阵 + 我的今日 + 配置 + 单格录入。

路由规划（均挂在 /api/v1 下）：
- /scheduling/posts        岗位定义 CRUD（make_router）
- /scheduling/plans        排班计划 CRUD（make_router）
- /scheduling/assignments  每日分配 CRUD（make_router）
- /scheduling/config       排班全局配置（GET/PUT，单行）
- /scheduling/generate     自动生成排班（POST）
- /scheduling/cell         手动录入/修改单个单元格（POST，upsert）
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
    SchedulingConfig,
    POST_GROUP_DAY,
    POST_GROUP_NIGHT,
    POST_GROUP_SPECIAL,
    ASSIGN_STATUS_ONDUTY,
    ASSIGN_STATUS_ALL,
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
    SchedulingConfigRead,
    SchedulingGenerateRequest,
    SchedulingCellRequest,
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


def _load_config(db: Session) -> SchedulingConfig:
    cfg = db.get(SchedulingConfig, 1)
    if not cfg:
        cfg = SchedulingConfig(id=1)
        db.add(cfg)
        db.commit()
        db.refresh(cfg)
    return cfg


def _pick_person(post: SchedulingPost, people: list, excluded: set, occupied: set,
                 assigned_today: set, post_cursor: dict) -> str:
    """为某岗挑一人：优先 preferred_people（轮转），不足则回退到通用池（轮转）。

    排除：被排除人员、当天占用（休息/病假/开会/行政/质控）、当天已排其他岗。
    """
    pref = [x for x in (post.preferred_people or [])
            if x and x not in excluded and x not in occupied and x not in assigned_today]
    if pref:
        c = post_cursor.get(post.id, 0) % len(pref)
        post_cursor[post.id] = c + 1
        return pref[c]
    pool = [x for x in people
            if x and x not in excluded and x not in occupied and x not in assigned_today]
    if not pool:
        return ""
    c = post_cursor.get(post.id, 0) % len(pool)
    post_cursor[post.id] = c + 1
    return pool[c]


def generate_assignments(db: Session, plan: SchedulingPlan, people: list[str],
                         start: str, end: str, config: SchedulingConfig) -> int:
    """按规则自动生成每日分配。

    规则（生免组，框架版）：
    - 仅工作日（周一~周五）生成；周末/节假日另算（留空，手动录入）。
    - 夜班岗（生化夜班/发热夜班，group=night）由科室提前录入，不自动生成。
    - 白班岗按 preferred_people 顺序轮转；无优先人员时回退通用池。同人同日不重复占岗。
    - 发热白班（is_fever_day）：若计划设了 fever_day_person，则该人每 4 个工作日上一班（当月固定一人），
      且其仍参与普通白班轮转；未设则该岗按普通白班轮转。
    - 既有「非在岗」记录（休息/病假/开会/行政/质控）受保护、不被覆盖，且占用该人当天名额。
    - 每天白班人员中挑早班/连班各一名，尽量不同人，每人连续最多 2 天。
    """
    posts = db.query(SchedulingPost).order_by(SchedulingPost.order).all()
    if not posts:
        raise HTTPException(status_code=400, detail="请先在 /scheduling/posts 定义岗位")
    day_posts = [p for p in posts if p.group in (POST_GROUP_DAY, POST_GROUP_SPECIAL)]
    excluded = set(config.excluded_people or [])
    people_pool = [p for p in people if p and p not in excluded]
    if not people_pool:
        raise HTTPException(status_code=400, detail="没有可用人员（可能被排除名单清空）")

    existing = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.plan_id == plan.id,
                SchedulingAssignment.date >= start, SchedulingAssignment.date <= end)
        .all()
    )
    occupied: dict[str, set] = {}
    protected_cells: set = set()
    existing_on_duty: dict[tuple, SchedulingAssignment] = {}
    for a in existing:
        if a.status != ASSIGN_STATUS_ONDUTY:
            occupied.setdefault(a.date, set()).add(a.person)
            protected_cells.add((a.date, a.post_id))
        else:
            existing_on_duty[(a.date, a.post_id)] = a

    assignments: list[SchedulingAssignment] = []
    post_cursor: dict[int, int] = {p.id: 0 for p in posts}
    early_state = {"person": None, "streak": 0}
    cont_state = {"person": None, "streak": 0}
    fever_day_idx = 0

    for cur in _daterange(start, end):
        weekday = cur.weekday()
        is_workday = weekday < 5
        if not is_workday:
            continue
        date_str = cur.strftime("%Y-%m-%d")
        day_people: list[str] = []
        assigned_today: set = set()

        # 发热白班（固定人，每4个工作日一班）
        if plan.fever_day_person and plan.fever_day_person not in excluded:
            fp = next((p for p in day_posts if p.is_fever_day), None)
            if fp and (date_str, fp.id) not in protected_cells:
                if fever_day_idx % 4 == 0:
                    person = plan.fever_day_person
                    if person not in occupied.get(date_str, set()) and person not in assigned_today:
                        assignments.append(SchedulingAssignment(
                            plan_id=plan.id, date=date_str, weekday=weekday, is_workday=True,
                            post_id=fp.id, person=person, status=ASSIGN_STATUS_ONDUTY))
                        assigned_today.add(person)
                        day_people.append(person)
                fever_day_idx += 1

        # 普通白班岗（含周三质谱、周四电泳等）
        needed = [p for p in day_posts
                  if (p.only_weekday is None or p.only_weekday == weekday) and not p.is_fever_day]
        needed.sort(key=lambda p: 0 if (p.required_weekday is not None and p.required_weekday == weekday) else 1)
        for p in needed:
            if (date_str, p.id) in protected_cells:
                exist = existing_on_duty.get((date_str, p.id))
                if exist:
                    assigned_today.add(exist.person)
                    day_people.append(exist.person)
                continue
            person = _pick_person(p, people_pool, excluded, occupied.get(date_str, set()),
                                  assigned_today, post_cursor)
            if not person:
                continue
            assignments.append(SchedulingAssignment(
                plan_id=plan.id, date=date_str, weekday=weekday, is_workday=True,
                post_id=p.id, person=person, status=ASSIGN_STATUS_ONDUTY))
            assigned_today.add(person)
            day_people.append(person)

        # 早班 / 连班：在当天白班人员中挑，尽量不是同一人，每人连续最多 2 天
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
            for a in assignments:
                if a.date == date_str and a.person == early_state["person"]:
                    a.is_early = True
                if a.date == date_str and a.person == cont_state["person"]:
                    a.is_continuous = True

    # 先删范围内所有「在岗」自动记录（保留非在岗的手动记录），再写入新生成
    db.query(SchedulingAssignment).filter(
        SchedulingAssignment.plan_id == plan.id,
        SchedulingAssignment.date >= start,
        SchedulingAssignment.date <= end,
        SchedulingAssignment.status == ASSIGN_STATUS_ONDUTY,
    ).delete(synchronize_session=False)
    db.add_all(assignments)
    db.commit()
    return len(assignments)


@router.post("/generate")
def generate(req: SchedulingGenerateRequest, db: Session = Depends(get_db),
             user: User = Depends(require_roles(*WRITE_ROLES))):
    plan = db.get(SchedulingPlan, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="排班计划不存在")
    config = _load_config(db)
    people = req.people
    if not people:
        people = [
            (u.full_name or u.username)
            for u in db.query(User).filter(User.is_active == True).all()  # noqa: E712
        ]
    start = req.start or plan.start_date
    if not start:
        raise HTTPException(status_code=400, detail="缺少开始日期（计划未设起止且请求未提供）")
    if req.days:
        end = (datetime.strptime(start, "%Y-%m-%d").date() + timedelta(days=req.days - 1)).strftime("%Y-%m-%d")
    else:
        end = req.end or plan.end_date
    if not end:
        raise HTTPException(status_code=400, detail="缺少结束日期（计划未设起止且请求未提供）")
    count = generate_assignments(db, plan, people, start, end, config)
    return {"ok": True, "generated": count}


@router.get("/config", response_model=SchedulingConfigRead)
def get_config(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return _load_config(db)


@router.put("/config", response_model=SchedulingConfigRead)
def put_config(payload: SchedulingConfigRead, db: Session = Depends(get_db),
               user: User = Depends(require_roles(*WRITE_ROLES))):
    cfg = _load_config(db)
    cfg.excluded_people = payload.excluded_people or []
    cfg.default_window_days = payload.default_window_days or 14
    cfg.early_continuous_window_days = payload.early_continuous_window_days or 30
    cfg.notes = payload.notes or ""
    db.commit()
    db.refresh(cfg)
    return cfg


@router.post("/cell")
def set_cell(req: SchedulingCellRequest, db: Session = Depends(get_db),
             user: User = Depends(require_roles(*WRITE_ROLES))):
    """手动录入/修改单个单元格（按 plan_id+date+post_id upsert）。用于夜班、休息/病假/开会/行政/质控等提前录入。"""
    if req.status not in ASSIGN_STATUS_ALL:
        raise HTTPException(status_code=400, detail=f"无效状态：{req.status}")
    if not req.person and req.status == ASSIGN_STATUS_ONDUTY:
        raise HTTPException(status_code=400, detail="在岗状态需指定人员")
    d = datetime.strptime(req.date, "%Y-%m-%d").date()
    exist = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.plan_id == req.plan_id,
                SchedulingAssignment.date == req.date,
                SchedulingAssignment.post_id == req.post_id)
        .first()
    )
    if exist:
        exist.person = req.person
        exist.status = req.status
        exist.is_early = req.is_early
        exist.is_continuous = req.is_continuous
        exist.note = req.note
        exist.weekday = d.weekday()
        exist.is_workday = d.weekday() < 5
        db.commit()
        db.refresh(exist)
        return exist
    a = SchedulingAssignment(
        plan_id=req.plan_id, date=req.date, weekday=d.weekday(), is_workday=d.weekday() < 5,
        post_id=req.post_id, person=req.person, status=req.status,
        is_early=req.is_early, is_continuous=req.is_continuous, note=req.note,
    )
    db.add(a)
    db.commit()
    db.refresh(a)
    return a


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
        "posts": [{"id": p.id, "name": p.name, "group": p.group, "required": p.required,
                   "is_fever_day": p.is_fever_day} for p in posts],
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
