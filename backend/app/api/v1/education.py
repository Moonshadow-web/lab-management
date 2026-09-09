"""人员能力管理接口：六大子功能 + 授权表 + 通用附件（rename from 人员继教管理，2026-09-01）。

权限：写（增删改）需 admin 或 training_manager；读对所有登录用户开放。模块 key 沿用 'training'。
"""
import json
import os
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.security import get_current_user, require_roles
from ...models.education import (
    PersonnelMaster, PersonnelEducation, PersonnelWorkExp, PersonnelCert, PersonnelReward, PersonnelEduExp,
    NewEmployeeTrain, NewEmployeeCertAuth,
    CompetencyAssessment, PersonnelComparison,
    TrainingPlan, TrainingSession,
    InternshipMentor, InternshipScore,
    AuthSheet,
    PreJobAuth, ExamBank, PostInstrumentMap,
    EducationAttachment,
)
from ...models.user import User
from ...core.crud_base import make_router
from ...core.cos_storage import cos_storage
from ...services.attachment_compress import optimize_image_bytes
from ...schemas.education import (
    PersonnelMasterCreate, PersonnelMasterUpdate, PersonnelMasterRead,
    PersonnelEducationCreate, PersonnelEducationUpdate, PersonnelEducationRead,
    PersonnelWorkExpCreate, PersonnelWorkExpUpdate, PersonnelWorkExpRead,
    PersonnelCertCreate, PersonnelCertUpdate, PersonnelCertRead,
    PersonnelRewardCreate, PersonnelRewardUpdate, PersonnelRewardRead,
    PersonnelEduExpCreate, PersonnelEduExpUpdate, PersonnelEduExpRead,
    NewEmployeeTrainCreate, NewEmployeeTrainUpdate, NewEmployeeTrainRead,
    NewEmployeeCertAuthCreate, NewEmployeeCertAuthUpdate, NewEmployeeCertAuthRead,
    CompetencyAssessmentCreate, CompetencyAssessmentUpdate, CompetencyAssessmentRead,
    PersonnelComparisonCreate, PersonnelComparisonUpdate, PersonnelComparisonRead,
    TrainingPlanCreate, TrainingPlanUpdate, TrainingPlanRead,
    TrainingSessionCreate, TrainingSessionUpdate, TrainingSessionRead,
    InternshipMentorCreate, InternshipMentorUpdate, InternshipMentorRead,
    InternshipScoreCreate, InternshipScoreUpdate, InternshipScoreRead,
    AuthSheetCreate, AuthSheetUpdate, AuthSheetRead,
    PreJobAuthCreate, PreJobAuthUpdate, PreJobAuthRead,
    ExamBankCreate, ExamBankUpdate, ExamBankRead,
    PostInstrumentMapCreate, PostInstrumentMapUpdate, PostInstrumentMapRead,
    EducationAttachmentRead,
)

WRITE = require_roles("admin", "training_manager")

router = APIRouter(prefix="/education", tags=["education"])

# A. 人员档案主表 + 5 张子表
personnel_router = make_router(
    PersonnelMaster, PersonnelMasterRead, PersonnelMasterCreate, PersonnelMasterUpdate,
    search_fields=["name", "title", "position", "group_duty"],
    filter_fields=["gender", "title", "political_status"],
    order_by=[PersonnelMaster.name],
    prefix="/personnel", write_roles=("admin", "training_manager"),
)
edu_router = make_router(
    PersonnelEducation, PersonnelEducationRead, PersonnelEducationCreate, PersonnelEducationUpdate,
    filter_fields=["person_id"], prefix="/personnel-education", write_roles=("admin", "training_manager"),
)
work_router = make_router(
    PersonnelWorkExp, PersonnelWorkExpRead, PersonnelWorkExpCreate, PersonnelWorkExpUpdate,
    filter_fields=["person_id"], prefix="/personnel-work-exp", write_roles=("admin", "training_manager"),
)
cert_router = make_router(
    PersonnelCert, PersonnelCertRead, PersonnelCertCreate, PersonnelCertUpdate,
    filter_fields=["person_id"], prefix="/personnel-certs", write_roles=("admin", "training_manager"),
)
reward_router = make_router(
    PersonnelReward, PersonnelRewardRead, PersonnelRewardCreate, PersonnelRewardUpdate,
    filter_fields=["person_id", "reward_type"], prefix="/personnel-rewards", write_roles=("admin", "training_manager"),
)
edu_exp_router = make_router(
    PersonnelEduExp, PersonnelEduExpRead, PersonnelEduExpCreate, PersonnelEduExpUpdate,
    filter_fields=["person_id"], prefix="/personnel-edu-exp", write_roles=("admin", "training_manager"),
)

# B. 新员工培训 + 独立上岗认证
new_emp_router = make_router(
    NewEmployeeTrain, NewEmployeeTrainRead, NewEmployeeTrainCreate, NewEmployeeTrainUpdate,
    search_fields=["name", "employee_category", "train_major"],
    filter_fields=["employee_category", "status", "person_id"],
    order_by=[NewEmployeeTrain.id.desc()],
    prefix="/new-employee-trains", write_roles=("admin", "training_manager"),
    json_fields=["plan_items", "detail_json"],
)
cert_auth_router = make_router(
    NewEmployeeCertAuth, NewEmployeeCertAuthRead, NewEmployeeCertAuthCreate, NewEmployeeCertAuthUpdate,
    search_fields=["applicant", "apply_content"], filter_fields=["status", "person_id"],
    order_by=[NewEmployeeCertAuth.id.desc()],
    prefix="/cert-auths", write_roles=("admin", "training_manager"),
)

# G. 授权表（人员能力评估的输出：5 要素 + 状态机）
auth_sheet_router = make_router(
    AuthSheet, AuthSheetRead, AuthSheetCreate, AuthSheetUpdate,
    search_fields=["name", "project", "instrument", "authorizer", "source_assessment_text"],
    filter_fields=["status", "auth_scope", "department", "person_id", "authorizer"],
    json_fields=["posts_json", "instruments_json", "scopes_json"],
    order_by=[AuthSheet.id.desc()],
    prefix="/auth-sheets", write_roles=("admin", "training_manager"),
)

# C. 能力评估 + 人员比对
competency_router = make_router(
    CompetencyAssessment, CompetencyAssessmentRead, CompetencyAssessmentCreate, CompetencyAssessmentUpdate,
    search_fields=["name", "post", "department"], filter_fields=["year", "department", "person_id"],
    order_by=[CompetencyAssessment.id.desc()],
    prefix="/competency-assessments", write_roles=("admin", "training_manager"),
    json_fields=["scores_json", "evidence_json"],
)
comparison_router = make_router(
    PersonnelComparison, PersonnelComparisonRead, PersonnelComparisonCreate, PersonnelComparisonUpdate,
    search_fields=["project", "method", "reagent"], filter_fields=["year", "specialty_group", "department"],
    order_by=[PersonnelComparison.id.desc()],
    prefix="/personnel-comparisons", write_roles=("admin", "training_manager"),
    json_fields=["sample_nos", "results_json"],
)

# D/E/F. 培训计划 / 培训记录 / 实习带教
plan_router = make_router(
    TrainingPlan, TrainingPlanRead, TrainingPlanCreate, TrainingPlanUpdate,
    filter_fields=["year"], order_by=[TrainingPlan.year.desc()],
    prefix="/training-plans", write_roles=("admin", "training_manager"),
    json_fields=["items_json"],
)
session_router = make_router(
    TrainingSession, TrainingSessionRead, TrainingSessionCreate, TrainingSessionUpdate,
    search_fields=["name", "teacher", "tag"], filter_fields=["tag", "plan_id"],
    order_by=[TrainingSession.id.desc()],
    prefix="/training-sessions", write_roles=("admin", "training_manager"),
    json_fields=["sign_in_header"],
)
mentor_router = make_router(
    InternshipMentor, InternshipMentorRead, InternshipMentorCreate, InternshipMentorUpdate,
    search_fields=["intern_name", "sop_ref"], filter_fields=["intern_type"],
    order_by=[InternshipMentor.id.desc()],
    prefix="/internship-mentors", write_roles=("admin", "training_manager"),
    json_fields=["items_json"],
)
score_router = make_router(
    InternshipScore, InternshipScoreRead, InternshipScoreCreate, InternshipScoreUpdate,
    search_fields=["intern_name"], filter_fields=["intern_type"],
    order_by=[InternshipScore.id.desc()],
    prefix="/internship-scores", write_roles=("admin", "training_manager"),
    json_fields=["subjects_json"],
)
# H. 岗前培训考核及授权表
prejob_router = make_router(
    PreJobAuth, PreJobAuthRead, PreJobAuthCreate, PreJobAuthUpdate,
    search_fields=["name"], filter_fields=["conclusion", "status"],
    order_by=[PreJobAuth.id.desc()],
    prefix="/pre-job-auths", write_roles=("admin", "training_manager"),
    json_fields=["positions_json", "instruments_json", "permissions_json", "items_json", "exam_json"],
)
# I. 岗位考核题库
exambank_router = make_router(
    ExamBank, ExamBankRead, ExamBankCreate, ExamBankUpdate,
    search_fields=["post"], order_by=[ExamBank.id.asc()],
    prefix="/exam-banks", write_roles=("admin", "training_manager"),
    json_fields=["methods_json", "qa_json", "practical_json", "theory_json"],
)


@prejob_router.post("/{pid}/generate-auths")
def generate_prejob_auths(pid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    """P3：考核意见=同意上岗 时，为该人员生成「一人一条」的授权记录。"""
    p = db.get(PreJobAuth, pid)
    if not p:
        raise HTTPException(404, "记录不存在")
    if p.conclusion not in ("通过", "同意上岗"):
        raise HTTPException(400, "考核意见须为「同意上岗」才能生成授权")
    if p.batch_id:
        raise HTTPException(400, f"已生成过授权（批次 {p.batch_id}），请到「授权表」查看")

    def _as_list(v):
        if isinstance(v, list):
            return v
        try:
            return json.loads(v or "[]")
        except Exception:
            return []

    positions = _as_list(p.positions_json)
    instruments = _as_list(p.instruments_json)
    scopes = [x for x in _as_list(p.permissions_json) if x in ("操作", "复核", "报告")] or ["操作"]
    person = db.query(PersonnelMaster).filter_by(name=p.name).first()

    # 有效期：授权日期起 1 年
    auth_date = p.auth_date or datetime.now().strftime("%Y-%m-%d")
    valid_until = ""
    try:
        d = datetime.strptime(auth_date, "%Y-%m-%d")
        valid_until = "%04d-%02d-%02d" % (d.year + 1, d.month, d.day)
    except Exception:
        valid_until = ""

    db.add(AuthSheet(
        person_id=person.id if person else None,
        name=p.name,
        department="生化免疫组",
        post="、".join(positions),
        instrument="、".join([i.get("name", "") for i in instruments]),
        auth_scope="、".join(scopes),
        posts_json=json.dumps(positions, ensure_ascii=False),
        instruments_json=json.dumps(instruments, ensure_ascii=False),
        scopes_json=json.dumps(scopes, ensure_ascii=False),
        status="有效",
        valid_from=auth_date,
        valid_until=valid_until,
        auth_date=auth_date,
        authorizer="金子铮",
        authorizer_qualification="免疫组组长/主治医师/本领域6年",
        source_assessment_id=p.id,
        source_assessment_text=f"岗前培训授权-单{p.id}",
        has_assessment_pass=True,
        remark=f"岗前培训考核及授权表 id={p.id} 自动生成（一人一条）",
        created_by=user.username,
    ))
    p.batch_id = f"PJ{p.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.commit()
    return {"ok": True, "created": 1, "batch_id": p.batch_id}

# =========================================================================
# K. 免登录公开答题（扫码即答：填姓名 → 找到自己的岗前考核单 → 提交自动判分回写）
# =========================================================================
@router.get("/public/pre-job-auths")
def public_prejob_by_name(name: str = "", db: Session = Depends(get_db)):
    """按姓名查找待考的岗前培训考核单（免登录）。"""
    q = (name or "").strip()
    if not q:
        return {"items": []}
    rows = (
        db.query(PreJobAuth)
        .filter(PreJobAuth.name == q)
        .order_by(PreJobAuth.id.desc())
        .limit(20)
        .all()
    )
    return {
        "items": [
            {
                "id": r.id,
                "name": r.name,
                "apply_date": r.apply_date,
                "positions_json": json.loads(r.positions_json or "[]"),
                "conclusion": r.conclusion,
            }
            for r in rows
        ]
    }


@router.get("/public/exam-paper/{pid}")
def public_exam_paper(pid: int, db: Session = Depends(get_db)):
    """取理论试卷（不含答案，免登录）。"""
    p = db.get(PreJobAuth, pid)
    if not p:
        raise HTTPException(404, "考核单不存在")
    positions = json.loads(p.positions_json or "[]")

    def strip(lst):
        return [{"q": t.get("q", ""), "options": t.get("options", [])} for t in (lst or [])]

    papers = []
    for post in positions:
        b = db.query(ExamBank).filter(ExamBank.post == post).first()
        T = json.loads((b.theory_json if b else None) or "{}")
        papers.append({
            "post": post,
            "single": strip(T.get("single")),
            "multi": strip(T.get("multi")),
            "judge": strip(T.get("judge")),
        })
    return {"id": p.id, "name": p.name, "positions": positions, "papers": papers}


@router.post("/public/exam-submit/{pid}")
def public_exam_submit(pid: int, payload: dict, db: Session = Depends(get_db)):
    """提交理论答卷：校验姓名 → 服务端判分 → 回写 exam_json（免登录）。"""
    p = db.get(PreJobAuth, pid)
    if not p:
        raise HTTPException(404, "考核单不存在")
    name = (payload.get("name") or "").strip()
    if not name or name != (p.name or "").strip():
        raise HTTPException(400, "姓名与考核单不一致，请确认")
    positions = json.loads(p.positions_json or "[]")
    answers = payload.get("answers") or {}
    try:
        exam = json.loads(p.exam_json or "{}") if isinstance(p.exam_json, str) else (p.exam_json or {})
    except Exception:
        exam = {}

    total = 0
    full = 0
    detail = {}
    for post in positions:
        b = db.query(ExamBank).filter(ExamBank.post == post).first()
        T = json.loads((b.theory_json if b else None) or "{}")
        a = answers.get(post) or {}
        s = 0
        for i, t in enumerate(T.get("single") or []):
            if a.get("s%d" % i) == str(t.get("answer", "")).strip()[:1]:
                s += 2
        for i, t in enumerate(T.get("multi") or []):
            got = "".join(sorted(a.get("m%d" % i) or []))
            if got and got == "".join(sorted(str(t.get("answer", "")))):
                s += 4
        for i, t in enumerate(T.get("judge") or []):
            if a.get("j%d" % i) == str(t.get("answer", "")):
                s += 2
        f = len(T.get("single") or []) * 2 + len(T.get("multi") or []) * 4 + len(T.get("judge") or []) * 2
        detail[post] = {"score": s, "full": f}
        total += s
        full += f
        d = exam.get(post) or {}
        if not d.get("trainContent"):
            d["trainContent"] = "岗位职责、项目SOP、仪器SOP"
        if not d.get("mastery"):
            d["mastery"] = "基本了解"
        if not d.get("qaResult"):
            d["qaResult"] = "合格"
        d["theoryAnswers"] = a
        exam[post] = d
    p.exam_json = json.dumps(exam, ensure_ascii=False)
    db.commit()
    return {"ok": True, "score": total, "full": full, "detail": detail}

router.include_router(postmap_router)
