"""人员继教管理模块 Pydantic 定义。

约定（与代码库一致）：
- Create/Update 共用 Base（字段带默认值，Update 用 exclude_unset 取增量）。
- Read 额外含 id 与时间戳。
- JSON 列在 API 层用 list[dict] / dict 表达，落库时由 API 序列化为 Text。
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# =========================================================================
# A. 人员档案
# =========================================================================
class PersonnelMasterBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    gender: str = ""
    birth_date: str = ""
    education: str = ""
    title: str = ""
    position: str = ""
    political_status: str = ""
    group_duty: str = ""
    work_start: str = ""
    hospital_join: str = ""
    group_join: str = ""
    id_card: str = ""
    phone: str = ""
    photo_attachment_id: int | None = None
    remark: str = ""


class PersonnelMasterCreate(PersonnelMasterBase):
    pass


class PersonnelMasterUpdate(PersonnelMasterBase):
    pass


class PersonnelMasterRead(PersonnelMasterBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PersonnelChildBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PersonnelEducationBase(PersonnelChildBase):
    person_id: int = 0
    school: str = ""
    major: str = ""
    degree: str = ""
    start_date: str = ""
    end_date: str = ""
    remark: str = ""


class PersonnelEducationCreate(PersonnelEducationBase):
    pass


class PersonnelEducationUpdate(PersonnelEducationBase):
    pass


class PersonnelEducationRead(PersonnelEducationBase):
    id: int


class PersonnelWorkExpBase(PersonnelChildBase):
    person_id: int = 0
    org: str = ""
    post: str = ""
    start_date: str = ""
    end_date: str = ""
    remark: str = ""


class PersonnelWorkExpCreate(PersonnelWorkExpBase):
    pass


class PersonnelWorkExpUpdate(PersonnelWorkExpBase):
    pass


class PersonnelWorkExpRead(PersonnelWorkExpBase):
    id: int


class PersonnelCertBase(PersonnelChildBase):
    person_id: int = 0
    cert_name: str = ""
    cert_no: str = ""
    issue_org: str = ""
    issue_date: str = ""
    valid_until: str = ""
    remark: str = ""


class PersonnelCertCreate(PersonnelCertBase):
    pass


class PersonnelCertUpdate(PersonnelCertBase):
    pass


class PersonnelCertRead(PersonnelCertBase):
    id: int


class PersonnelRewardBase(PersonnelChildBase):
    person_id: int = 0
    reward_type: str = "奖励"
    title: str = ""
    date: str = ""
    org: str = ""
    remark: str = ""


class PersonnelRewardCreate(PersonnelRewardBase):
    pass


class PersonnelRewardUpdate(PersonnelRewardBase):
    pass


class PersonnelRewardRead(PersonnelRewardBase):
    id: int


class PersonnelEduExpBase(PersonnelChildBase):
    person_id: int = 0
    name: str = ""
    organizer: str = ""
    train_date: str = ""
    hours: str = ""
    credits: str = ""
    cert_no: str = ""
    remark: str = ""


class PersonnelEduExpCreate(PersonnelEduExpBase):
    pass


class PersonnelEduExpUpdate(PersonnelEduExpBase):
    pass


class PersonnelEduExpRead(PersonnelEduExpBase):
    id: int


# =========================================================================
# B. 新员工培训 + 独立上岗认证
# =========================================================================
class NewEmployeeTrainBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_id: int | None = None
    name: str = ""
    employee_category: str = "新职工"
    train_major: str = "生免室"
    group_join_date: str = ""
    train_duration: str = ""
    ability_bio_result: str = ""
    ability_bio_responsible: str = ""
    ability_immuno_result: str = ""
    ability_immuno_responsible: str = ""
    theory_operation_oral_result: str = ""
    exam_result: str = ""
    exam_responsible: str = ""
    exam_time: str = ""
    plan_items: list[dict] = []
    detail_json: dict = {}
    status: str = "进行中"
    remark: str = ""

    @field_validator("plan_items", mode="before")
    @classmethod
    def _plan_items(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []
        return v

    @field_validator("detail_json", mode="before")
    @classmethod
    def _detail_json(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return {}
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class NewEmployeeTrainCreate(NewEmployeeTrainBase):
    pass


class NewEmployeeTrainUpdate(NewEmployeeTrainBase):
    pass


class NewEmployeeTrainRead(NewEmployeeTrainBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class NewEmployeeCertAuthBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_id: int | None = None
    applicant: str = ""
    apply_date: str = ""
    apply_content: str = ""
    theory_eval: str = ""
    operation_eval: str = ""
    group_leader_opinion: str = ""
    director_opinion: str = ""
    status: str = "待审核"
    remark: str = ""


class NewEmployeeCertAuthCreate(NewEmployeeCertAuthBase):
    pass


class NewEmployeeCertAuthUpdate(NewEmployeeCertAuthBase):
    pass


class NewEmployeeCertAuthRead(NewEmployeeCertAuthBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =========================================================================
# C. 能力评估 + 人员比对
# =========================================================================
class CompetencyAssessmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person_id: int | None = None
    name: str = ""
    department: str = "生化免疫组"
    post: str = ""
    year: int = 0
    scores_json: dict = {}
    total: int = 0
    conclusion: str = ""
    assessor: str = ""
    authorizer: str = ""
    assess_date: str = ""
    remark: str = ""

    @field_validator("scores_json", mode="before")
    @classmethod
    def _scores_json(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return {}
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class CompetencyAssessmentCreate(CompetencyAssessmentBase):
    pass


class CompetencyAssessmentUpdate(CompetencyAssessmentBase):
    pass


class CompetencyAssessmentRead(CompetencyAssessmentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class PersonnelComparisonBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    department: str = "检验科"
    specialty_group: str = "生免组"
    year: int = 0
    project: str = ""
    method: str = ""
    reagent: str = ""
    reagent_batch: str = ""
    reagent_expire: str = ""
    test_date: str = ""
    sample_nos: list[str] = []
    results_json: list[dict] = []
    concordance: str = ""
    summary: str = ""
    operator: str = ""
    reviewer: str = ""
    remark: str = ""

    @field_validator("sample_nos", "results_json", mode="before")
    @classmethod
    def _lists(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class PersonnelComparisonCreate(PersonnelComparisonBase):
    pass


class PersonnelComparisonUpdate(PersonnelComparisonBase):
    pass


class PersonnelComparisonRead(PersonnelComparisonBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =========================================================================
# D/E/F. 培训计划 / 培训记录 / 实习带教
# =========================================================================
class TrainingPlanBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    year: int = 0
    title: str = ""
    items_json: list[dict] = []
    remark: str = ""

    @field_validator("items_json", mode="before")
    @classmethod
    def _items_json(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class TrainingPlanCreate(TrainingPlanBase):
    pass


class TrainingPlanUpdate(TrainingPlanBase):
    pass


class TrainingPlanRead(TrainingPlanBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class TrainingSessionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    plan_id: int | None = None
    name: str = ""
    teacher: str = ""
    target: str = ""
    train_time: str = ""
    location: str = ""
    content: str = ""
    effect_eval: str = ""
    tag: str = "组内培训"
    sign_in_attachment_id: int | None = None
    sign_in_header: dict = {}

    @field_validator("sign_in_header", mode="before")
    @classmethod
    def _sign_in_header(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return {}
            try:
                return json.loads(v)
            except Exception:
                return {}
        return v


class TrainingSessionCreate(TrainingSessionBase):
    pass


class TrainingSessionUpdate(TrainingSessionBase):
    pass


class TrainingSessionRead(TrainingSessionBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InternshipMentorBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    intern_name: str = ""
    intern_type: str = "实习"
    sop_ref: str = "SM-SOP-025"
    items_json: list[dict] = []
    remark: str = ""

    @field_validator("items_json", mode="before")
    @classmethod
    def _items_json(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class InternshipMentorCreate(InternshipMentorBase):
    pass


class InternshipMentorUpdate(InternshipMentorBase):
    pass


class InternshipMentorRead(InternshipMentorBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class InternshipScoreBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    intern_name: str = ""
    intern_type: str = "实习"
    date: str = ""
    subjects_json: list[dict] = []
    overall_comment: str = ""
    group_leader: str = ""
    sign_date: str = ""
    remark: str = ""

    @field_validator("subjects_json", mode="before")
    @classmethod
    def _subjects_json(cls, v):
        if isinstance(v, str):
            v = v.strip()
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []
        return v


class InternshipScoreCreate(InternshipScoreBase):
    pass


class InternshipScoreUpdate(InternshipScoreBase):
    pass


class InternshipScoreRead(InternshipScoreBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# =========================================================================
# 附件
# =========================================================================
class EducationAttachmentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    owner_type: str = ""
    owner_id: int = 0
    kind: str = "other"
    file_type: str = "other"
    original_name: str = ""
    size_bytes: int = 0
    uploaded_by: str = ""
    uploaded_at: datetime | None = None
