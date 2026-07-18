"""各模型的 Pydantic 序列化定义。Create/Update 共用 Base（字段带默认值，Update 用 exclude_unset 取增量）；Read 额外含 id 与时间戳。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, computed_field, field_validator


# ---------------- User ----------------
class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str = ""
    full_name: str = ""
    role: str = "member"
    roles: str = ""  # 详细组织角色,逗号分隔
    must_change_password: bool = True
    department: str = ""
    email: str = ""
    notify_email: bool = True
    is_active: bool = True

    @field_validator("notify_email", mode="before")
    @classmethod
    def _notify_email_none_to_true(cls, v):
        # 历史数据 notify_email 可能为 NULL，读回/回传时归一为 True，
        # 避免编辑保存时因 null 触发 422、以及详情接口序列化 None 触发 500。
        return True if v is None else v


class UserCreate(UserBase):
    password: str = ""


class UserUpdate(UserBase):
    password: str | None = None


class UserRead(UserBase):
    id: int
    created_at: datetime | None = None


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


# ---------------- TestItem ----------------
class TestItemBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str = ""
    name: str = ""
    aliases: str = ""
    category: str = ""
    specimen: str = ""
    method: str = ""
    unit: str = ""
    reference: str = ""
    fee: str = ""
    instrument: str = ""
    instrument_group: str = ""
    linear_range: str = ""
    dilution_fold: str = ""
    reportable_range: str = ""
    diluent: str = ""
    calibrator: str = ""
    traceability: str = ""
    brand: str = ""
    last_update: str = ""
    interference_hemolysis: str = ""
    interference_bilirubin: str = ""
    interference_lipemia: str = ""


class TestItemCreate(TestItemBase):
    pass


class TestItemUpdate(TestItemBase):
    pass


class TestItemRead(TestItemBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @computed_field
    @property
    def brand_label(self) -> str:
        """品牌标识：优先用显式存储的 brand 字段，否则从校准品(calibrator)文本推导。"""
        from ..core.brand import extract_brand

        stored = (self.brand or "").strip()
        return stored or extract_brand(self.calibrator)


# ---------------- Document ----------------
class DocumentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str = ""
    category: str = "通用SOP"
    version: str = "1.0"
    file_path: str = ""
    original_filename: str = ""
    uploader: str = ""
    status: str = "生效"
    description: str = ""
    # 文件头元数据（从 .docx 自动解析）
    doc_number: str = ""
    doc_version: str = ""
    revision: str = ""
    author: str = ""
    reviewer: str = ""
    approver: str = ""
    issued_date: str = ""
    audit_date: str = ""
    approve_date: str = ""
    effective_date: str = ""
    meta_raw: str = ""
    parent_id: int | None = None


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(DocumentBase):
    pass


class DocumentRead(DocumentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DocumentVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    document_id: int
    version: str = ""
    file_path: str = ""
    uploader: str = ""
    note: str = ""
    doc_number: str = ""
    doc_version: str = ""
    author: str = ""
    reviewer: str = ""
    approver: str = ""
    meta_raw: str = ""
    created_at: datetime | None = None


# ---------------- Instrument ----------------
class InstrumentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    dept_no: str = ""
    model: str = ""
    manufacturer: str = ""
    category: str = ""
    location: str = ""
    status: str = "在用"
    serial_no: str = ""
    purchase_date: str = ""
    start_date: str = ""
    owner: str = ""
    daily_manager: str = ""
    supplier: str = ""
    contact: str = ""
    qc_instrument: bool = False

    @field_validator("qc_instrument", mode="before")
    @classmethod
    def _qc_instrument_none_to_false(cls, v):
        # 历史数据 qc_instrument 可能为 NULL，读回/回传时归一为 False，
        # 避免编辑保存时因 null 触发 422、以及详情接口序列化 None 触发 500。
        return False if v is None else v


class InstrumentCreate(InstrumentBase):
    pass


class InstrumentUpdate(InstrumentBase):
    pass


class InstrumentRead(InstrumentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CalibrationRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    instrument_id: int = 0
    calibration_date: str = ""
    next_due_date: str = ""
    result: str = ""
    agency: str = ""
    cycle_months: str = ""
    operator: str = ""
    report_file_path: str = ""
    report_filename: str = ""


class CalibrationRecordCreate(CalibrationRecordBase):
    pass


class CalibrationRecordUpdate(CalibrationRecordBase):
    pass


class CalibrationRecordRead(CalibrationRecordBase):
    id: int
    created_at: datetime | None = None


# ---------------- InstrumentFamily（项目"使用仪器"总型号 ↔ 仪器档案关联） ----------------
class InstrumentFamilyBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    description: str = ""


class InstrumentFamilyCreate(InstrumentFamilyBase):
    pass


class InstrumentFamilyUpdate(InstrumentFamilyBase):
    pass


class InstrumentFamilyMemberOut(BaseModel):
    """关联的具体仪器（含建档状态），用于前端渲染芯片/管理页。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str = ""
    model: str = ""
    dept_no: str = ""
    status: str = ""
    has_archive: bool = False


class InstrumentFamilyRead(InstrumentFamilyBase):
    id: int
    instrument_ids: list[int] = []
    member_count: int = 0
    used_count: int = 0  # 有多少项目(test_items)的"使用仪器"指向该总型号
    members: list[InstrumentFamilyMemberOut] = []
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- QCRecord ----------------
class QCRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    test_item: str = ""
    level: str = ""
    lot_no: str = ""
    instrument: str = ""
    target_mean: str = ""
    target_sd: str = ""
    measured_value: str = ""
    qc_date: str = ""
    status: str = "在控"
    rule_violated: str = ""
    operator: str = ""
    remark: str = ""


class QCRecordCreate(QCRecordBase):
    pass


class QCRecordUpdate(QCRecordBase):
    pass


class QCRecordRead(QCRecordBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- QCMonthlySummary ----------------
class QCMonthlySummaryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    year: int = 0
    month: int = 0
    test_item: str = ""
    unit: str = ""
    lot_no: str = ""
    level: str = ""
    instrument: str = ""
    instrument_id: int | None = None
    operator: str = ""
    instrument_no: str = ""
    target_mean: float = 0.0
    target_sd: float = 0.0
    target_cv: float = 0.0
    mean: float = 0.0
    sd: float = 0.0
    cv: float = 0.0
    n: int = 0
    out_of_control_count: int = 0
    in_control_rate: float = 0.0
    quality_goal: str = ""
    handling_note: str = ""
    pdf_path: str = ""
    pdf_filename: str = ""


class QCMonthlySummaryCreate(QCMonthlySummaryBase):
    pass


class QCMonthlySummaryUpdate(QCMonthlySummaryBase):
    pass


class QCMonthlySummaryRead(QCMonthlySummaryBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class QCDailyValueRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    summary_id: int
    qc_date: str = ""
    value: float = 0.0
    is_out_of_control: bool = False
    rule_violated: str = ""
    operator: str = ""
    violate_reason: str = ""
    violate_deal: str = ""


# ---------------- QCMonthlyReport（月结文字部分） ----------------
class QCMonthlyReportBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    instrument_id: int | None = None
    instrument: str = ""
    instrument_no: str = ""
    year: int = 0
    month: int = 0
    operation_status: str = ""   # 一、仪器运行情况
    drift_trend: str = ""        # 二、各项目是否出现漂移或趋势性改变
    cv_setting_ok: str = ""      # 三、各项目CV%设置是否达标
    cv_calc_ok: str = ""         # 四、各项目计算CV%是否达标
    freq_ok: str = ""            # 五、各项目质控频次是否达标


class QCMonthlyReportCreate(QCMonthlyReportBase):
    pass


class QCMonthlyReportUpdate(QCMonthlyReportBase):
    pass


class QCMonthlyReportRead(QCMonthlyReportBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- Reagent ----------------
class ReagentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    brand: str = ""
    spec: str = ""
    lot_no: str = ""
    quantity: str = ""
    unit: str = ""
    production_date: str = ""
    expiry_date: str = ""
    in_date: str = ""
    supplier: str = ""
    storage_condition: str = ""
    status: str = "在库"
    operator: str = ""
    remark: str = ""


class ReagentCreate(ReagentBase):
    pass


class ReagentUpdate(ReagentBase):
    pass


class ReagentRead(ReagentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- TrainingRecord ----------------
class TrainingRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person: str = ""
    title: str = ""
    category: str = ""
    train_date: str = ""
    hours: str = ""
    credits: str = ""
    organizer: str = ""
    certificate_no: str = ""
    status: str = "已完成"
    remark: str = ""


class TrainingRecordCreate(TrainingRecordBase):
    pass


class TrainingRecordUpdate(TrainingRecordBase):
    pass


class TrainingRecordRead(TrainingRecordBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- VerificationRecord ----------------
class VerificationRecordBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    test_item: str = ""
    verify_type: str = ""
    instrument: str = ""
    verify_date: str = ""
    criteria: str = ""
    result: str = ""
    conclusion: str = "通过"
    report_file_path: str = ""
    operator: str = ""
    remark: str = ""


class VerificationRecordCreate(VerificationRecordBase):
    pass


class VerificationRecordUpdate(VerificationRecordBase):
    pass


class VerificationRecordRead(VerificationRecordBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- Nonconformity ----------------
class NonconformityBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    title: str = ""
    nc_type: str = ""
    source: str = ""
    description: str = ""
    root_cause: str = ""
    corrective_action: str = ""
    responsible: str = ""
    found_date: str = ""
    due_date: str = ""
    close_date: str = ""
    status: str = "待处理"


class NonconformityCreate(NonconformityBase):
    pass


class NonconformityUpdate(NonconformityBase):
    pass


class NonconformityRead(NonconformityBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- Notification ----------------
class NotificationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    module: str = ""
    ref_type: str = ""
    ref_id: int = 0
    title: str = ""
    message: str = ""
    due_date: str = ""
    level: str = "info"
    is_read: bool = False


class NotificationRead(NotificationBase):
    id: int
    created_at: datetime | None = None


# ---------------- EQA（室间质评） ----------------
class EqaPlanBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    year: int = 0
    org: str = ""
    program: str = ""
    group: str = ""
    item: str = ""
    round_no: str = ""
    sample_date: str = ""
    due_date: str = ""
    returned: bool = False
    result: str = ""
    qualified: bool = False
    score: str = ""
    note: str = ""
    report_file: str = ""


class EqaPlanCreate(EqaPlanBase):
    pass


class EqaPlanUpdate(EqaPlanBase):
    pass


class EqaPlanRead(EqaPlanBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class EqaSummaryBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    year: int = 0
    half: int = 1          # 1=上半年，2=下半年，0=全年
    department: str = ""   # 质评部门（org）：卫健委 / 北京市
    category: str = "生化+凝血"   # 分类：生化+凝血 / 免疫
    summary_text: str = ""
    docx_path: str = ""
    generated_at: datetime | None = None


class EqaSummaryCreate(EqaSummaryBase):
    pass


class EqaSummaryUpdate(EqaSummaryBase):
    pass


class EqaSummaryRead(EqaSummaryBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


# ---------------- QualityRequirement ----------------
class QualityRequirementBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    source: str = "wst403-2024"
    category: str = ""
    item_code: str = ""
    item_name: str = ""
    cv: str = ""
    bias: str = ""
    tea: str = ""
    unit: str = ""
    remark: str = ""
    updated_by: str = ""


class QualityRequirementCreate(QualityRequirementBase):
    pass


class QualityRequirementUpdate(QualityRequirementBase):
    pass


class QualityRequirementRead(QualityRequirementBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None
