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
    PreJobAuth, ExamBank,
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
    """P3：结论=通过 时，按考核仪器逐台自动生成授权记录（AuthSheet，监督期「有条件」状态）。"""
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
    scopes = [s for s in _as_list(p.permissions_json) if s in ("操作", "复核", "报告")] or ["操作"]
    items = _as_list(p.items_json)
    item_map = {i.get("code"): (i.get("items") or "") for i in items}
    person = db.query(PersonnelMaster).filter_by(name=p.name).first()
    today = datetime.now().strftime("%Y-%m-%d")
    created = 0
    for inst in instruments:
        code = inst.get("code", "")
        for scope in scopes:
            db.add(AuthSheet(
                person_id=person.id if person else None,
                name=p.name,
                post="、".join(positions),
                instrument=f"{inst.get('name', '')}（{code.replace('MHZYY-JYK-', '')}）",
                project=item_map.get(code, ""),
                auth_scope=scope,
                status="有条件",
                status_reason="岗前培训考核通过，监督期内",
                source_assessment_id=p.id,
                source_assessment_text=f"岗前培训授权-单{p.id}",
                auth_date=p.auth_date or today,
                valid_from=p.auth_date or today,
                has_assessment_pass=True,
                remark=f"岗前培训考核及授权表 id={p.id} 自动生成",
                created_by=user.username,
            ))
            created += 1
    p.batch_id = f"PJ{p.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    db.commit()
    return {"ok": True, "created": created, "batch_id": p.batch_id}

router.include_router(personnel_router)
router.include_router(edu_router)
router.include_router(work_router)
router.include_router(cert_router)
router.include_router(reward_router)
router.include_router(edu_exp_router)
router.include_router(new_emp_router)
router.include_router(cert_auth_router)
router.include_router(auth_sheet_router)
router.include_router(competency_router)
router.include_router(comparison_router)
router.include_router(plan_router)
router.include_router(session_router)
router.include_router(mentor_router)
router.include_router(score_router)
router.include_router(prejob_router)
router.include_router(exambank_router)


# =========================================================================
# 附件：照片 / 签到扫描件 / 课件 / 通知 / 考题 / 效果评价 等
# （独立挂载到顶层 api_router，避免被 /education 前缀二次包裹）
# =========================================================================
attach_router = APIRouter(prefix="/education-attachments", tags=["education-attachments"])

_IMAGE_EXTS = {"jpg", "jpeg", "png", "gif", "webp", "bmp"}
_PDF_EXTS = {"pdf"}
_DOC_EXTS = {"doc", "docx", "xls", "xlsx", "csv", "ppt", "pptx"}


def _classify_ext(ext: str) -> str:
    e = (ext or "").lstrip(".").lower()
    if e in _IMAGE_EXTS:
        return "image"
    if e in _PDF_EXTS:
        return "pdf"
    if e in _DOC_EXTS:
        return "doc"
    return "other"


def _ser_attachment(a: EducationAttachment) -> dict:
    return {
        "id": a.id, "owner_type": a.owner_type, "owner_id": a.owner_id, "kind": a.kind,
        "file_type": a.file_type, "original_name": a.original_name, "size_bytes": a.size_bytes,
        "uploaded_by": a.uploaded_by,
        "uploaded_at": a.uploaded_at.isoformat() if a.uploaded_at else None,
    }


@attach_router.get("/file/{aid}")
def get_attachment(aid: int, inline: bool = True, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    from urllib.parse import quote
    a = db.get(EducationAttachment, aid)
    if not a:
        raise HTTPException(404, "附件不存在")

    def _cd():
        # RFC 5987 编码中文文件名，避免响应头含非 ASCII 字符导致 500
        disp = "inline" if inline else "attachment"
        return f"{disp}; filename*=UTF-8''{quote(a.original_name)}"

    if a.cloud_key and cos_storage.ready:
        if not inline:
            cos_url = cos_storage.url(a.cloud_key, a.original_name)
            if cos_url:
                return RedirectResponse(url=cos_url, status_code=302)
        content = cos_storage.get_bytes(a.cloud_key)
        if content:
            return Response(content, media_type=_media_for(a), headers={"Content-Disposition": _cd()})
    if not a.data:
        raise HTTPException(404, "文件已丢失")
    return Response(a.data, media_type=_media_for(a), headers={"Content-Disposition": _cd()})


@attach_router.get("/{owner_type}/{owner_id}")
def list_attachments(
    owner_type: str, owner_id: int, kind: str | None = None,
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    q = db.query(EducationAttachment).filter_by(owner_type=owner_type, owner_id=owner_id)
    if kind:
        q = q.filter_by(kind=kind)
    items = q.order_by(EducationAttachment.id.desc()).all()
    return {"items": [_ser_attachment(a) for a in items], "total": len(items)}


@attach_router.post("/{owner_type}/{owner_id}", status_code=201)
async def upload_attachments(
    owner_type: str, owner_id: int, kind: str = "other",
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db), user: User = Depends(WRITE),
):
    out = []
    parsed_meta = {"exam_person_count": None, "exam_pass_rate": None, "eval_satisfy_rate": None}
    for f in files:
        if not f or not f.filename:
            continue
        ext = os.path.splitext(f.filename)[1] or ""
        safe = f"{owner_type}_{owner_id}_{datetime.now().strftime('%Y%m%d%H%M%S%f')}_{len(out)}{ext}"
        content = await f.read()
        ft = _classify_ext(ext)
        if ft == "image":
            content = optimize_image_bytes(content, ext)
        cloud_key = None
        if cos_storage.ready:
            try:
                cloud_key = cos_storage.save("education_attachments", f.filename or safe, content)
            except Exception:
                pass
        a = EducationAttachment(
            owner_type=owner_type, owner_id=owner_id, kind=kind,
            file_type=ft, original_name=f.filename, stored_name=safe, rel_path="",
            cloud_key=cloud_key, data=content if not cloud_key else None,
            size_bytes=len(content), uploaded_by=user.username,
        )
        db.add(a)
        out.append(a)
        # 考题 / 效果评价：从上传文档文本自动解析人数/合格率/满意率
        if owner_type == "training_session" and kind in ("exam", "effect_eval"):
            try:
                text = _extract_doc_text(content, ext)
                if kind == "exam":
                    cnt, rate = _parse_exam(text)
                    if cnt is not None:
                        parsed_meta["exam_person_count"] = cnt
                    if rate is not None:
                        parsed_meta["exam_pass_rate"] = rate
                elif kind == "effect_eval":
                    rate = _parse_satisfy(text)
                    if rate is not None:
                        parsed_meta["eval_satisfy_rate"] = rate
            except Exception:
                pass
    try:
        db.commit()
    except Exception as e:  # noqa: BLE001
        db.rollback()
        msg = str(e)
        if "max_allowed_packet" in msg or "packet bigger" in msg:
            raise HTTPException(413, "文件过大：超过数据库单包大小限制(max_allowed_packet)。请压缩后再上传。")
        raise
    # 回写培训记录解析元数据
    if owner_type == "training_session" and any(v is not None for v in parsed_meta.values()):
        try:
            sess = db.get(TrainingSession, owner_id)
            if sess:
                for k, v in parsed_meta.items():
                    if v is not None:
                        setattr(sess, k, v)
                db.commit()
        except Exception:
            db.rollback()
    for a in out:
        db.refresh(a)
    return {"items": [_ser_attachment(a) for a in out], "total": len(out)}


def _extract_doc_text(content: bytes, ext: str) -> str:
    """从 docx/pdf 中提取纯文本，用于考题/效果评价自动解析。无第三方依赖时降级。"""
    ext = (ext or "").lstrip(".").lower()
    # docx = zip 的 xml
    if ext in ("docx", "dotx"):
        try:
            import zipfile
            import io
            import re
            z = zipfile.ZipFile(io.BytesIO(content))
            xml = z.read("word/document.xml").decode("utf-8", errors="ignore")
            xml = re.sub(r"</w:p>", "\n", xml)
            xml = re.sub(r"<[^>]+>", "", xml)
            return xml
        except Exception:
            return ""
    # pdf：仅当项目装有 PyMuPDF 时可用
    if ext == "pdf":
        try:
            import fitz  # PyMuPDF
            doc = fitz.open(stream=content, filetype="pdf")
            return "\n".join(page.get_text() for page in doc)
        except Exception:
            return ""
    return ""


def _num(s: str) -> float | None:
    s = (s or "").replace("%", "").strip()
    try:
        return float(s)
    except Exception:
        return None


_CN_DIGITS = "零一二三四五六七八九十百"
def _parse_exam(text: str):
    """从考题文档文本解析 (考核人数, 合格率%)。示例：应考 17 人，合格 17 人，合格率 100%。"""
    if not text:
        return None, None
    import re
    cnt = None
    for pat in (r"实考[^\d]{0,6}(\d+)\s*人", r"应考[^\d]{0,6}(\d+)\s*人"):
        m = re.search(pat, text)
        if m:
            cnt = int(m.group(1))
            break
    if cnt is None:
        m = re.search(r"合格率\s*([\d.]+)\s*%", text)
        if m:
            rate = _num(m.group(1))
            return None, rate
    rate = None
    m = re.search(r"合格率\s*([\d.]+)\s*%", text)
    if m:
        rate = _num(m.group(1))
    return cnt, rate


def _parse_satisfy(text: str) -> float | None:
    """从效果评价文档文本解析满意率(%)。示例：「满意」17 人（占 100%）。"""
    if not text:
        return None
    import re
    m = re.search(r"满意[^0-9占]{0,12}(\d+)\s*人[^0-9占]{0,6}占\s*([\d.]+)\s*%", text)
    if m:
        return _num(m.group(2))
    m = re.search(r"满意度\s*([\d.]+)\s*%", text)
    if m:
        return _num(m.group(1))
    return None




@attach_router.delete("/file/{aid}")
def delete_attachment(aid: int, db: Session = Depends(get_db), user: User = Depends(WRITE)):
    a = db.get(EducationAttachment, aid)
    if not a:
        raise HTTPException(404, "附件不存在")
    db.delete(a)
    db.commit()
    return {"ok": True}


def _media_for(a: EducationAttachment) -> str:
    if a.file_type == "image":
        ext = os.path.splitext(a.stored_name)[1].lstrip(".").lower() or "jpeg"
        return f"image/{ext}" if ext != "jpg" else "image/jpeg"
    if a.file_type == "pdf":
        return "application/pdf"
    return "application/octet-stream"
