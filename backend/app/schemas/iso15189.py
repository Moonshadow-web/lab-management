"""ISO15189 内审专项 Pydantic 序列化定义（三子功能：文件评审 / 自查 / 科室内审）。

字段与 backend/app/models/iso15189.py 严格对齐；JSON 字段（record_json / clause_ids）
由 CRUD 层以 json_fields 声明，自动序列化/反序列化。
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ===================== 一、文件评审 =====================
class ReviewCampaignBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str = ""
    year: str = ""
    campaign_type: str = "文件评审"
    due_date: str = ""
    status: str = "进行中"
    note: str = ""


class ReviewCampaignCreate(ReviewCampaignBase):
    created_by: str = ""


class ReviewCampaignUpdate(ReviewCampaignBase):
    pass


class ReviewCampaignRead(ReviewCampaignBase):
    id: int
    created_by: str = ""
    created_at: datetime | None = None


class ReviewAssignmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    campaign_id: int = 0
    document_id: int = 0
    reviewer: str = ""
    reviewer_id: Optional[int] = None
    status: str = "待评审"
    record_json: dict = {}
    revised_filename: str = ""
    document_new_version: str = ""
    note: str = ""


class ReviewAssignmentCreate(ReviewAssignmentBase):
    pass


class ReviewAssignmentUpdate(ReviewAssignmentBase):
    pass


class ReviewAssignmentRead(ReviewAssignmentBase):
    id: int
    revised_cloud_key: str = ""
    submitted_at: datetime | None = None
    admin_received_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ReviewRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    campaign_id: int = 0
    reviewer_id: Optional[int] = None
    reviewer: str = ""
    status: str = "待提交"
    record_json: dict = {}


class ReviewRecordCreate(ReviewRecordBase):
    pass


class ReviewRecordUpdate(ReviewRecordBase):
    pass


class ReviewRecordRead(ReviewRecordBase):
    id: int
    submitted_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ===================== 二、自查（条款内审） =====================
class AuditClauseBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    clause_no: str = ""
    chapter: str = ""
    title: str = ""
    content: str = ""
    check_point: str = ""
    application_requirement: str = ""


class AuditClauseCreate(AuditClauseBase):
    pass


class AuditClauseUpdate(AuditClauseBase):
    pass


class AuditClauseRead(AuditClauseBase):
    id: int


class SelfInspectionCampaignBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str = ""
    year: str = ""
    due_date: str = ""
    status: str = "进行中"
    note: str = ""


class SelfInspectionCampaignCreate(SelfInspectionCampaignBase):
    created_by: str = ""


class SelfInspectionCampaignUpdate(SelfInspectionCampaignBase):
    pass


class SelfInspectionCampaignRead(SelfInspectionCampaignBase):
    id: int
    created_by: str = ""
    created_at: datetime | None = None


class SelfInspectionAssignmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    campaign_id: int = 0
    assignee: str = ""
    assignee_id: Optional[int] = None
    clause_ids: list[int] = []
    clause_range: str = ""
    status: str = "待自查"
    note: str = ""


class SelfInspectionAssignmentCreate(SelfInspectionAssignmentBase):
    pass


class SelfInspectionAssignmentUpdate(SelfInspectionAssignmentBase):
    pass


class SelfInspectionAssignmentRead(SelfInspectionAssignmentBase):
    id: int
    created_at: datetime | None = None


class SelfInspectionRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    campaign_id: int = 0
    assignment_id: Optional[int] = None
    clause_id: int = 0
    assignee: str = ""
    check_content: str = ""
    result: str = ""
    finding: str = ""
    action: str = ""


class SelfInspectionRecordCreate(SelfInspectionRecordBase):
    pass


class SelfInspectionRecordUpdate(SelfInspectionRecordBase):
    pass


class SelfInspectionRecordRead(SelfInspectionRecordBase):
    id: int
    filled_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ===================== 三、科室内审（逐条款整改） =====================
class CorrectiveActionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    nonconformity_id: Optional[int] = None
    clause: str = ""
    title: str = ""
    source: str = ""
    description: str = ""
    root_cause: str = ""
    corrective_action: str = ""
    preventive_action: str = ""
    responsible: str = ""
    due_date: str = ""
    verify_result: str = ""
    status: str = "未整改"


class CorrectiveActionCreate(CorrectiveActionBase):
    pass


class CorrectiveActionUpdate(CorrectiveActionBase):
    pass


class CorrectiveActionRead(CorrectiveActionBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ===================== 四、认可能力范围 =====================
class AccreditedScopeBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    category_l1: str = ""
    category_l2: str = ""
    seq: str = ""
    item_name: str = ""
    sample_type: str = ""
    method_id: Optional[int] = None
    method_name: str = ""
    instrument_id: Optional[int] = None
    instrument_name: str = ""
    reagent_id: Optional[int] = None
    reagent_name: str = ""
    calibrator: str = ""
    description: str = ""
    remark: str = ""
    perf_correctness: str = ""
    perf_precision: str = ""
    perf_linearity: str = ""
    perf_reportable: str = ""
    perf_other: str = ""


class AccreditedScopeCreate(AccreditedScopeBase):
    pass


class AccreditedScopeUpdate(AccreditedScopeBase):
    pass


class AccreditedScopeRead(AccreditedScopeBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
