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
    SchedulingSwapRequest,
    POST_GROUP_DAY,
    POST_GROUP_NIGHT,
    POST_GROUP_SPECIAL,
    ASSIGN_STATUS_ONDUTY,
    ASSIGN_STATUS_ALL,
    STATUS_CATEGORIES,
    ASSIGN_STATUS_EARLY,
    ASSIGN_STATUS_CONTINUOUS,
    SWAP_STATUS_PENDING,
    SWAP_STATUS_CONFIRMED,
    SWAP_STATUS_REJECTED,
    SWAP_STATUS_CANCELED,
)
from ...models.user import User
from ...models.notification import Notification
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
    SchedulingBatchRequest,
    MyScheduleItem,
    SchedulingSwapRequestCreate,
    SchedulingSwapRequestRead,
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
    """为某岗挑一人：按固定岗优先人「优先级递减」排，除非该人当天不在岗（休息/病假/开会/行政/质控）
    或已被排了别的岗，否则优先排他；都不可用才回退到通用池（轮换分散）。

    与用户约定一致：preferred_people[0] 优先级最高，[1] 次之……不是轮转均摊。
    """
    for cand in (post.preferred_people or []):
        if (cand and cand not in excluded and cand not in occupied
                and cand not in assigned_today):
            return cand
    # 固定优先人均不在岗：回退通用池（轮换，避免总压同一个人）
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
    - 早班/连班作为独立无岗位状态行生成：每人连上 2 天早班 → 退下连上 2 天连班，流水线轮转；
      当天早班与连班必为不同人；自动排除当天休息/病假/开会/行政/质控/夜班/发热的人。
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
    post_by_id = {p.id: p for p in posts}
    occupied: dict[str, set] = {}
    protected_cells: set = set()
    existing_on_duty: dict[tuple, SchedulingAssignment] = {}
    for a in existing:
        post = post_by_id.get(a.post_id) if a.post_id else None
        is_night = post is not None and post.group == POST_GROUP_NIGHT
        # 非在岗状态、或夜班岗的在岗记录，都视为当天被占用（不能排白班），且受保护不被覆盖。
        if a.status != ASSIGN_STATUS_ONDUTY or is_night:
            occupied.setdefault(a.date, set()).add(a.person)
            protected_cells.add((a.date, a.post_id))
        else:
            existing_on_duty[(a.date, a.post_id)] = a

    # 已通过换班完成早/连班义务的人（is_locked 记录）：下一轮生成时不再为他们排早/连班，
    # 实现「系统记住换过班的人已经上过该班了」。锁定行本身受保护、不被下方删除/覆盖。
    served_people: set = {
        a.person for a in existing
        if a.is_locked and a.person
        and a.status in (ASSIGN_STATUS_EARLY, ASSIGN_STATUS_CONTINUOUS)
    }

    assignments: list[SchedulingAssignment] = []
    post_cursor: dict[int, int] = {p.id: 0 for p in posts}
    fever_day_idx = 0
    fever_busy_by_date: dict[str, str] = {}  # 发热白班当天该人需排除出早班/连班

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
                        fever_busy_by_date[date_str] = person
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

    # 早班 / 连班：作为独立的无岗位状态行生成（对齐用户 Excel 版式）。
    # 流水线规则：每人连上 2 天早班 → 退下连上 2 天连班；下一人在其 早班 期间顶上。
    # 故 early_seq[i]=roster[(i//2)%n]，连班=早班序列整体后移 2 天（当天早班与连班必不同人）。
    # 自动排除当天休息/病假/开会/行政/质控/夜班/发热的人。
    if people_pool and len(people_pool) >= 2:
        roster = list(people_pool)
        workdays = [cur for cur in _daterange(start, end) if cur.weekday() < 5]
        early_seq = [roster[(i // 2) % len(roster)] for i in range(len(workdays))]
        cont_seq = [roster[((i - 2) // 2) % len(roster)] for i in range(len(workdays))]
        early_assigns: list[SchedulingAssignment] = []
        for i, cur in enumerate(workdays):
            date_str = cur.strftime("%Y-%m-%d")
            busy = occupied.get(date_str, set())
            if date_str in fever_busy_by_date:  # 发热白班当天该人排除出早班/连班
                busy = busy | {fever_busy_by_date[date_str]}
            e = early_seq[i]
            c = cont_seq[i]
            # 早班人当天不在岗、或已通过换班完成早/连班义务，则顺延到下一位
            if e in busy or e in served_people:
                for k in range(1, len(roster)):
                    cand = roster[(i // 2 + k) % len(roster)]
                    if cand not in busy and cand not in served_people:
                        e = cand
                        break
            # 连班人当天不在岗、已换班完成义务，或和早班撞同一个人，则顺延到下一位（保证不同人）
            if c in busy or c in served_people or c == e:
                for k in range(1, len(roster)):
                    cand = roster[((i - 2) // 2 + k) % len(roster)]
                    if cand not in busy and cand not in served_people and cand != e:
                        c = cand
                        break
            if e and e not in busy and e not in served_people:
                early_assigns.append(SchedulingAssignment(
                    plan_id=plan.id, date=date_str, weekday=cur.weekday(), is_workday=True,
                    post_id=None, person=e, status=ASSIGN_STATUS_EARLY))
            if c and c not in busy and c not in served_people and c != e:
                early_assigns.append(SchedulingAssignment(
                    plan_id=plan.id, date=date_str, weekday=cur.weekday(), is_workday=True,
                    post_id=None, person=c, status=ASSIGN_STATUS_CONTINUOUS))

    # 先删范围内「在岗」自动记录，以及旧的早班/连班状态行（保留手动录入的休息/病假/质控等），再写入新生成
    db.query(SchedulingAssignment).filter(
        SchedulingAssignment.plan_id == plan.id,
        SchedulingAssignment.date >= start,
        SchedulingAssignment.date <= end,
        SchedulingAssignment.status == ASSIGN_STATUS_ONDUTY,
    ).delete(synchronize_session=False)
    db.query(SchedulingAssignment).filter(
        SchedulingAssignment.plan_id == plan.id,
        SchedulingAssignment.date >= start,
        SchedulingAssignment.date <= end,
        SchedulingAssignment.status.in_([ASSIGN_STATUS_EARLY, ASSIGN_STATUS_CONTINUOUS]),
        SchedulingAssignment.is_locked == False,  # 换班锁定的行受保护，保留不被覆盖
    ).delete(synchronize_session=False)
    db.add_all(assignments)
    if people_pool and len(people_pool) >= 2:
        db.add_all(early_assigns)
    db.commit()
    return len(assignments) + (len(early_assigns) if (people_pool and len(people_pool) >= 2) else 0)


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


def _sync_early_continuous_rows(db: Session, plan_id: int, date_str: str, person: str,
                                is_early: bool, is_continuous: bool):
    """岗位行保存早班/连班标记后，同步创建或删除对应的无岗位状态行。

    这样月视图里「早班」「连班」独立状态行会自动显示岗位行已标记人员，实现联动。
    """
    if not person:
        return
    for flag, status in ((is_early, ASSIGN_STATUS_EARLY), (is_continuous, ASSIGN_STATUS_CONTINUOUS)):
        q = db.query(SchedulingAssignment).filter(
            SchedulingAssignment.plan_id == plan_id,
            SchedulingAssignment.date == date_str,
            SchedulingAssignment.post_id.is_(None),
            SchedulingAssignment.person == person,
            SchedulingAssignment.status == status,
        )
        if flag:
            if not q.first():
                d = datetime.strptime(date_str, "%Y-%m-%d").date()
                db.add(SchedulingAssignment(
                    plan_id=plan_id, date=date_str, weekday=d.weekday(), is_workday=d.weekday() < 5,
                    post_id=None, person=person, status=status,
                    is_early=False, is_continuous=False, note="",
                ))
        else:
            q.delete(synchronize_session=False)


@router.post("/cell")
def set_cell(req: SchedulingCellRequest, db: Session = Depends(get_db),
             user: User = Depends(require_roles(*WRITE_ROLES))):
    """手动录入/修改单个单元格（upsert）。
    - 在岗：必须指定岗位(post_id)，按 (plan_id,date,post_id) 唯一。
    - 休息/病假/开会/行政/质控/教学：post_id 可空，按 (plan_id,date,person,post_id IS NULL) 唯一（一人一天一条无岗位记录）。
    用于夜班、发热门诊、休息等提前录入。
    """
    if req.status not in ASSIGN_STATUS_ALL:
        raise HTTPException(status_code=400, detail=f"无效状态：{req.status}")
    if not req.person:
        raise HTTPException(status_code=400, detail="请指定人员")
    if req.status == ASSIGN_STATUS_ONDUTY and req.post_id is None:
        raise HTTPException(status_code=400, detail="在岗状态需指定岗位")
    d = datetime.strptime(req.date, "%Y-%m-%d").date()
    q = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.plan_id == req.plan_id,
                SchedulingAssignment.date == req.date)
    )
    if req.post_id is not None:
        q = q.filter(SchedulingAssignment.post_id == req.post_id)
    else:
        q = q.filter(SchedulingAssignment.post_id.is_(None), SchedulingAssignment.person == req.person)
    exist = q.first()
    if exist:
        exist.post_id = req.post_id
        exist.person = req.person
        exist.status = req.status
        exist.is_early = req.is_early
        exist.is_continuous = req.is_continuous
        exist.note = req.note
        exist.weekday = d.weekday()
        exist.is_workday = d.weekday() < 5
    else:
        exist = SchedulingAssignment(
            plan_id=req.plan_id, date=req.date, weekday=d.weekday(), is_workday=d.weekday() < 5,
            post_id=req.post_id, person=req.person, status=req.status,
            is_early=req.is_early, is_continuous=req.is_continuous, note=req.note,
        )
        db.add(exist)
    # 岗位行保存早班/连班标记时，同步维护对应无岗位状态行，实现月视图联动
    if req.post_id is not None and req.status == ASSIGN_STATUS_ONDUTY:
        _sync_early_continuous_rows(db, req.plan_id, req.date, req.person, req.is_early, req.is_continuous)
    db.commit()
    db.refresh(exist)
    return exist


@router.post("/batch")
def batch_set(req: SchedulingBatchRequest, db: Session = Depends(get_db),
              user: User = Depends(require_roles(*WRITE_ROLES))):
    """批量录入一批非白班约束（夜班、发热门诊、休息、病假……）。按 items 逐条 upsert，返回写入条数。

    prune=True 时：
    - prune_keys（[date, status]）把无岗位状态记录裁剪为提交人员集合（取消勾选即移除）。
    - prune_post_keys（[date, str(post_id)]）把绑定岗位的录入（夜班/发热白班）裁剪为提交人员集合。
    两者配合实现「矩阵整体保存」：单元格取消勾选即移除对应记录。
    """
    plan = db.get(SchedulingPlan, req.plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="排班计划不存在")

    upserted = 0
    # 提交人员按 (date, status) / (date, post_id) 归组，供 prune 比对
    submitted: dict[tuple, set] = {}
    submitted_posts: dict[tuple, set] = {}
    for it in req.items:
        if it.status not in ASSIGN_STATUS_ALL or not it.person:
            continue
        if it.status == ASSIGN_STATUS_ONDUTY and it.post_id is None:
            continue
        d = datetime.strptime(it.date, "%Y-%m-%d").date()
        q = (
            db.query(SchedulingAssignment)
            .filter(SchedulingAssignment.plan_id == req.plan_id,
                    SchedulingAssignment.date == it.date)
        )
        if it.post_id is not None:
            q = q.filter(SchedulingAssignment.post_id == it.post_id)
        else:
            q = q.filter(SchedulingAssignment.post_id.is_(None), SchedulingAssignment.person == it.person)
        exist = q.first()
        if exist:
            exist.status = it.status
            exist.is_early = it.is_early
            exist.is_continuous = it.is_continuous
            exist.note = it.note
            exist.weekday = d.weekday()
            exist.is_workday = d.weekday() < 5
            if it.post_id is not None:
                exist.post_id = it.post_id
        else:
            db.add(SchedulingAssignment(
                plan_id=req.plan_id, date=it.date, weekday=d.weekday(), is_workday=d.weekday() < 5,
                post_id=it.post_id, person=it.person, status=it.status,
                is_early=it.is_early, is_continuous=it.is_continuous, note=it.note))
        upserted += 1
        if it.post_id is None:
            submitted.setdefault((it.date, it.status), set()).add(it.person)
        else:
            submitted_posts.setdefault((it.date, it.post_id), set()).add(it.person)
    # prune：把 prune_keys 中列出的 (date, status) 裁剪为提交人员集合
    if req.prune:
        for key in req.prune_keys:
            if len(key) != 2:
                continue
            date_s, status_s = key[0], key[1]
            if status_s not in STATUS_CATEGORIES:
                continue
            keep = submitted.get((date_s, status_s), set())
            q = (
                db.query(SchedulingAssignment)
                .filter(SchedulingAssignment.plan_id == req.plan_id,
                        SchedulingAssignment.date == date_s,
                        SchedulingAssignment.status == status_s,
                        SchedulingAssignment.post_id.is_(None))
            )
            if keep:
                q = q.filter(SchedulingAssignment.person.notin_(keep))
            q.delete(synchronize_session=False)
    # prune：岗位行(夜班/发热白班) 裁剪为提交人员集合
    if req.prune:
        for key in req.prune_post_keys:
            if len(key) != 2:
                continue
            date_s, pid_s = key[0], key[1]
            try:
                pid = int(pid_s)
            except (ValueError, TypeError):
                continue
            keep = submitted_posts.get((date_s, pid), set())
            q = (
                db.query(SchedulingAssignment)
                .filter(SchedulingAssignment.plan_id == req.plan_id,
                        SchedulingAssignment.date == date_s,
                        SchedulingAssignment.post_id == pid,
                        SchedulingAssignment.status == ASSIGN_STATUS_ONDUTY)
            )
            if keep:
                q = q.filter(SchedulingAssignment.person.notin_(keep))
            q.delete(synchronize_session=False)
    db.commit()
    return {"ok": True, "upserted": upserted}


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
    # 展示顺序：白班 → 特殊岗 → 夜班
    posts.sort(key=lambda p: (
        0 if p.group == POST_GROUP_DAY else (1 if p.group == POST_GROUP_SPECIAL else 2),
        p.order or 0,
    ))
    dates = [d.strftime("%Y-%m-%d") for d in _daterange(s, e)]
    rows = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.plan_id == plan_id,
                SchedulingAssignment.date >= s, SchedulingAssignment.date <= e)
        .all()
    )
    post_id_set = {p.id for p in posts}
    post_cells: dict[str, dict] = {}
    status_cells: dict[str, dict] = {}
    for a in rows:
        if a.post_id and a.post_id in post_id_set:
            post_cells.setdefault(f"post:{a.post_id}", {})[a.date] = {
                "id": a.id, "person": a.person, "status": a.status,
                "is_early": a.is_early, "is_continuous": a.is_continuous, "note": a.note,
            }
        elif a.status in STATUS_CATEGORIES:
            cell = status_cells.setdefault(f"status:{a.status}", {}).setdefault(a.date, {"persons": []})
            cell["persons"].append({"id": a.id, "person": a.person, "note": a.note})
    # 岗位行标记了早班/连班的人，自动投影到对应状态行显示，实现月视图联动
    for cell_map in post_cells.values():
        for date_str, cell in cell_map.items():
            person = cell.get("person")
            if not person:
                continue
            for flag, status in ((cell.get("is_early"), ASSIGN_STATUS_EARLY),
                                 (cell.get("is_continuous"), ASSIGN_STATUS_CONTINUOUS)):
                if flag:
                    sc = status_cells.setdefault(f"status:{status}", {}).setdefault(date_str, {"persons": []})
                    if not any(p["person"] == person for p in sc["persons"]):
                        sc["persons"].append({"id": cell.get("id"), "person": person, "note": cell.get("note") or ""})
    row_defs = [{"kind": "post", "id": p.id, "name": p.name, "group": p.group,
                 "required": p.required, "is_fever_day": p.is_fever_day} for p in posts]
    row_defs += [{"kind": "status", "key": s, "name": s} for s in STATUS_CATEGORIES]
    return {
        "plan_id": plan_id,
        "dates": dates,
        "posts": [{"id": p.id, "name": p.name, "group": p.group, "required": p.required,
                   "is_fever_day": p.is_fever_day} for p in posts],
        "status_rows": [{"key": s, "label": s} for s in STATUS_CATEGORIES],
        "rows": row_defs,
        "cells": {**post_cells, **status_cells},
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


def _user_by_name(db: Session, name: str) -> Optional[User]:
    """按 full_name 或 username 解析系统用户。"""
    if not name:
        return None
    return (
        db.query(User)
        .filter((User.full_name == name) | (User.username == name))
        .first()
    )


def _resolve_range(range: str, today: date) -> tuple[str, str]:
    """根据 range 计算起止日期：week=本周(周一~周日)，fortnight=本周~下周日(两周)，month=本月。"""
    if range == "month":
        start = today.replace(day=1)
        nxt = start.replace(month=start.month + 1) if start.month < 12 else start.replace(year=start.year + 1, month=1)
        end = nxt - timedelta(days=1)
    elif range == "fortnight":
        monday = today - timedelta(days=today.weekday())
        start, end = monday, monday + timedelta(days=13)
    else:  # week
        monday = today - timedelta(days=today.weekday())
        start, end = monday, monday + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


@router.get("/my-schedule", response_model=list[MyScheduleItem])
def my_schedule(range: str = Query("week"),
                db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """当前用户在本周/近两周/本月的只读排班（含岗位名/分组）。用于工作台「今日我的岗位」扩展排班表。"""
    if range not in ("week", "fortnight", "month"):
        raise HTTPException(status_code=400, detail="range 仅支持 week/fortnight/month")
    me = user.full_name or user.username
    today = date.today()
    s, e = _resolve_range(range, today)
    rows = (
        db.query(SchedulingAssignment)
        .filter(SchedulingAssignment.person == me,
                SchedulingAssignment.date >= s, SchedulingAssignment.date <= e)
        .order_by(SchedulingAssignment.date, SchedulingAssignment.post_id)
        .all()
    )
    out = []
    for a in rows:
        post = db.get(SchedulingPost, a.post_id) if a.post_id else None
        out.append(MyScheduleItem(
            id=a.id, date=a.date, weekday=a.weekday, post_id=a.post_id,
            post_name=post.name if post else "",
            group=post.group if post else "",
            person=a.person, status=a.status,
            is_early=a.is_early, is_continuous=a.is_continuous,
            is_locked=a.is_locked,
        ))
    return out


@router.post("/swap/request", response_model=SchedulingSwapRequestRead)
def request_swap(req: SchedulingSwapRequestCreate, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """发起换班：发起人(A)点击 B 的班次后提交。

    - to_assignment_id 给定 = 双向对调（A 选自己一个班与 B 的班互换）。
    - to_assignment_id 为空 = 单向顶班（B 顶 A 的早/连班，A 当天被顶替）。
    仅 A 本人可发起（from_assignment_id 必须是 A 的班次）；向接收人 B 推送私密站内通知。
    """
    me = user.full_name or user.username
    fa = db.get(SchedulingAssignment, req.from_assignment_id)
    if not fa:
        raise HTTPException(status_code=404, detail="发起班次不存在")
    if fa.person != me:
        raise HTTPException(status_code=403, detail="只能用自己的班次发起换班")
    to_user = _user_by_name(db, req.to_person)
    if not to_user:
        raise HTTPException(status_code=404, detail=f"接收人「{req.to_person}」不是系统用户")
    if req.to_person == me:
        raise HTTPException(status_code=400, detail="不能与自己换班")
    if req.to_assignment_id:
        ta = db.get(SchedulingAssignment, req.to_assignment_id)
        if not ta:
            raise HTTPException(status_code=404, detail="目标班次不存在")
        if ta.is_locked:
            raise HTTPException(status_code=400, detail="该班次已换班锁定，不能再换")
    is_top = req.to_assignment_id is None
    swap = SchedulingSwapRequest(
        from_person=me, to_person=req.to_person,
        from_assignment_id=req.from_assignment_id,
        to_assignment_id=req.to_assignment_id,
        status=SWAP_STATUS_PENDING, note=req.note,
    )
    db.add(swap)
    db.flush()
    db.add(Notification(
        module="排班", ref_type="scheduling_swap", ref_id=swap.id,
        title=f"换班申请：{me} 请求与您换班",
        message=f"{me} 希望与您{'对调班次' if not is_top else '顶班'}。备注：{req.note or '无'}",
        due_date=fa.date, level="info", recipient_user_id=to_user.id,
    ))
    db.commit()
    db.refresh(swap)
    return swap


@router.get("/swap/list", response_model=list[SchedulingSwapRequestRead])
def list_swaps(role: str = Query("all"),
               db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """换班列表。role=pending_in(待我接收) / pending_out(我发起) / all(全部相关)。"""
    if role not in ("pending_in", "pending_out", "all"):
        raise HTTPException(status_code=400, detail="role 仅支持 pending_in/pending_out/all")
    me = user.full_name or user.username
    q = db.query(SchedulingSwapRequest)
    if role == "pending_in":
        q = q.filter(SchedulingSwapRequest.to_person == me,
                     SchedulingSwapRequest.status == SWAP_STATUS_PENDING)
    elif role == "pending_out":
        q = q.filter(SchedulingSwapRequest.from_person == me)
    else:
        q = q.filter((SchedulingSwapRequest.from_person == me)
                     | (SchedulingSwapRequest.to_person == me))
    return q.order_by(SchedulingSwapRequest.created_at.desc()).all()


def _swap_finalize(db: Session, swap: SchedulingSwapRequest, me: str) -> SchedulingSwapRequest:
    """执行换班：双向对调交换 person，单向顶班改 from 班次 person 为接收人；涉及早/连班则锁定。"""
    fa = db.get(SchedulingAssignment, swap.from_assignment_id)
    if not fa:
        raise HTTPException(status_code=404, detail="发起班次已不存在")
    if swap.to_assignment_id:
        ta = db.get(SchedulingAssignment, swap.to_assignment_id)
        if not ta:
            raise HTTPException(status_code=404, detail="目标班次已不存在")
        fa.person, ta.person = ta.person, fa.person
        if fa.is_early or fa.is_continuous or ta.is_early or ta.is_continuous:
            fa.is_locked = True
            ta.is_locked = True
        db.add(fa)
        db.add(ta)
    else:
        fa.person = swap.to_person
        if fa.is_early or fa.is_continuous:
            fa.is_locked = True
        db.add(fa)
    swap.status = SWAP_STATUS_CONFIRMED
    swap.updated_at = datetime.now()
    from_user = _user_by_name(db, swap.from_person)
    if from_user:
        db.add(Notification(
            module="排班", ref_type="scheduling_swap", ref_id=swap.id,
            title=f"换班已确认：{me} 接受了您的换班",
            message=f"{me} 已确认与您的换班（{'顶班' if not swap.to_assignment_id else '双向对调'}）。",
            due_date=fa.date, level="info", recipient_user_id=from_user.id,
        ))
    db.commit()
    db.refresh(swap)
    return swap


@router.post("/swap/{swap_id}/confirm", response_model=SchedulingSwapRequestRead)
def confirm_swap(swap_id: int, db: Session = Depends(get_db),
                 user: User = Depends(get_current_user)):
    """接收人(B)确认换班 → 执行对调/顶班并锁定早/连班，通知发起人。"""
    me = user.full_name or user.username
    swap = db.get(SchedulingSwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="换班申请不存在")
    if swap.to_person != me:
        raise HTTPException(status_code=403, detail="只有接收人可以确认换班")
    if swap.status != SWAP_STATUS_PENDING:
        raise HTTPException(status_code=400, detail=f"该申请已{swap.status}，无法确认")
    return _swap_finalize(db, swap, me)


@router.post("/swap/{swap_id}/reject", response_model=SchedulingSwapRequestRead)
def reject_swap(swap_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """接收人(B)拒绝换班。"""
    me = user.full_name or user.username
    swap = db.get(SchedulingSwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="换班申请不存在")
    if swap.to_person != me:
        raise HTTPException(status_code=403, detail="只有接收人可以拒绝换班")
    if swap.status != SWAP_STATUS_PENDING:
        raise HTTPException(status_code=400, detail=f"该申请已{swap.status}，无法拒绝")
    swap.status = SWAP_STATUS_REJECTED
    swap.updated_at = datetime.now()
    from_user = _user_by_name(db, swap.from_person)
    if from_user:
        db.add(Notification(
            module="排班", ref_type="scheduling_swap", ref_id=swap.id,
            title=f"换班被拒绝：{me} 拒绝了您的换班",
            message=f"{me} 拒绝了您的换班申请。",
            level="warning", recipient_user_id=from_user.id,
        ))
    db.commit()
    db.refresh(swap)
    return swap


@router.post("/swap/{swap_id}/cancel", response_model=SchedulingSwapRequestRead)
def cancel_swap(swap_id: int, db: Session = Depends(get_db),
                user: User = Depends(get_current_user)):
    """发起人(A)取消换班。"""
    me = user.full_name or user.username
    swap = db.get(SchedulingSwapRequest, swap_id)
    if not swap:
        raise HTTPException(status_code=404, detail="换班申请不存在")
    if swap.from_person != me:
        raise HTTPException(status_code=403, detail="只有发起人可以取消换班")
    if swap.status != SWAP_STATUS_PENDING:
        raise HTTPException(status_code=400, detail=f"该申请已{swap.status}，无法取消")
    swap.status = SWAP_STATUS_CANCELED
    swap.updated_at = datetime.now()
    db.commit()
    db.refresh(swap)
    return swap
