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


# ---------------- InstrumentRepair（仪器维修记录，对应 BG-KS-CZ-909 仪器维修记录表） ----------------
class InstrumentRepairBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    instrument_id: int = 0
    fault_desc: str = ""          # 故障描述
    affected_items: str = ""      # 影响项目
    finder: str = ""              # 发现人
    found_at: str = ""            # 发现时间
    notify_repair_at: str = ""    # 通知维修时间
    handled_at: str = ""          # 处理时间
    cause_process: str = ""       # 故障原因及维修过程
    repairer: str = ""            # 维修人
    qc_verification: str = ""    # 排查后质控验证结果
    qc_detail: dict = {}          # 质控验证结构化数据（方式/室内质控行/样本比对行/校准验证/影响前比对）
    restored_at: str = ""        # 恢复使用时间
    signer: str = ""              # 签字
    signer_id: int | None = None
    created_by_id: int | None = None


class InstrumentRepairCreate(InstrumentRepairBase):
    pass


class InstrumentRepairUpdate(InstrumentRepairBase):
    pass


class InstrumentRepairRead(InstrumentRepairBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


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
    rule_column_present: bool = False  # 上传时是否识别到规则列（空单元格据此判在控）
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
    is_warning: bool = False
    rule_violated: str = ""
    operator: str = ""
    violate_reason: str = ""
    violate_deal: str = ""
    uploaded_rule: str = ""  # 上传表格规则列原始值（覆盖后端Westgard判定）


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
    received_at: str = ""
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


class EqaPlanReceive(BaseModel):
    """「收样登记」：录入质评样本送达签收日期。"""
    model_config = ConfigDict(from_attributes=True)
    received_at: str = ""


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


# ---------------- UncertaintyAssessment（测量不确定度评估，对应 BG-SM-CZ-072） ----------------
class UncertaintyAssessmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    project_name: str = ""
    project_code: str = ""
    instrument: str = ""
    reagent: str = ""
    eval_date: str = ""
    cycle_months: int = 12
    prepared_by: str = ""
    reviewed_by: str = ""
    l1_values: list[float] = []
    l2_values: list[float] = []
    l1_mean: float = 0
    l1_sd: float = 0
    l1_cv: float = 0
    l2_mean: float = 0
    l2_sd: float = 0
    l2_cv: float = 0
    bias_rms: float = 0
    ucal: float = 0
    pt_result: str = "合格"
    l1_u: float = 0
    l2_u: float = 0
    l1_passed: bool = False
    l2_passed: bool = False


class UncertaintyAssessmentCreate(UncertaintyAssessmentBase):
    pass


class UncertaintyAssessmentUpdate(UncertaintyAssessmentBase):
    pass


class UncertaintyAssessmentRead(UncertaintyAssessmentBase):
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


# ---------------- Scheduling ----------------
class SchedulingPostBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    group: str = "day"          # day / night / special
    required: bool = True
    only_weekday: int | None = None
    required_weekday: int | None = None
    order: int = 0
    preferred_people: list[str] = []   # 该岗固定/优先人员（按顺序轮转）
    is_fever_day: bool = False         # 发热白班：每月固定一人、每4个工作日一班
    notes: str = ""


class SchedulingPostCreate(SchedulingPostBase):
    pass


class SchedulingPostUpdate(SchedulingPostBase):
    pass


class SchedulingPostRead(SchedulingPostBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchedulingPlanBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    name: str = ""
    start_date: str = ""
    end_date: str = ""
    fever_day_person: str = ""    # 发热白班固定人员（full_name）；空=按普通白班轮转
    notes: str = ""


class SchedulingPlanCreate(SchedulingPlanBase):
    pass


class SchedulingPlanUpdate(SchedulingPlanBase):
    pass


class SchedulingPlanRead(SchedulingPlanBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchedulingAssignmentBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    plan_id: int = 0
    date: str = ""
    weekday: int = 0
    is_workday: bool = True
    post_id: int | None = None
    person: str = ""
    status: str = "在岗"        # 在岗 / 休息 / 病假 / 开会 / 行政 / 质控 / 教学 / 早班 / 连班
    is_early: bool = False
    is_continuous: bool = False
    note: str = ""


class SchedulingAssignmentCreate(SchedulingAssignmentBase):
    pass


class SchedulingAssignmentUpdate(SchedulingAssignmentBase):
    pass


class SchedulingAssignmentRead(SchedulingAssignmentBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MyScheduleItem(BaseModel):
    """「今日我的岗位」只读排班表单项（含岗位名/分组）。"""
    model_config = ConfigDict(from_attributes=True)
    id: int
    date: str = ""
    weekday: int = 0
    post_id: int | None = None
    post_name: str = ""
    group: str = ""
    person: str = ""
    status: str = ""
    is_early: bool = False
    is_continuous: bool = False
    is_locked: bool = False


class SchedulingSwapRequestBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    from_person: str = ""
    to_person: str = ""
    from_assignment_id: int = 0
    to_assignment_id: int | None = None
    status: str = "待确认"
    note: str = ""


class SchedulingSwapRequestCreate(BaseModel):
    """发起换班：A 点击 B 的班次后提交。"""
    from_assignment_id: int
    to_person: str
    to_assignment_id: int | None = None  # 双向对调时填 B 的班；顶班(单向)时留空
    note: str = ""


class SchedulingSwapRequestRead(SchedulingSwapRequestBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchedulingRestRequestBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    person: str = ""
    date: str = ""
    status: str = "生效中"   # 生效中/已取消
    assignment_id: int | None = None
    note: str = ""


class SchedulingRestRequestCreate(BaseModel):
    """发起休息申请：仅填本人需要休息的日期（person 由后端取当前用户）。"""
    date: str                              # YYYY-MM-DD
    note: str = ""


class SchedulingRestRequestRead(SchedulingRestRequestBase):
    id: int
    created_at: datetime | None = None
    updated_at: datetime | None = None


class SchedulingConfigBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    excluded_people: list[str] = []      # 不参与任何排班的人员
    default_window_days: int = 14        # 常规排班生成窗口
    early_continuous_window_days: int = 30  # 早班/连班可提前排的天数
    early_continuous_excluded: list[str] = []  # 不参与早班/连班的人员
    notes: str = ""


class SchedulingConfigRead(SchedulingConfigBase):
    id: int = 1
    updated_at: datetime | None = None


class SchedulingGenerateRequest(BaseModel):
    """自动生成排班请求。"""
    plan_id: int
    people: list[str] | None = None   # 生免组人员名单（full_name）；缺省用全部活跃用户
    start: str | None = None           # 覆盖计划起止日期（YYYY-MM-DD）
    end: str | None = None
    days: int | None = None            # 生成天数（从 start 起算）；设定后用 start+days-1 作为结束


class SchedulingCellRequest(BaseModel):
    """手动录入/修改单个单元格（按 plan_id+date+post_id upsert；post_id 为空表示无岗位的状态记录）。"""
    plan_id: int
    date: str
    post_id: int | None = None
    person: str = ""
    status: str = "在岗"
    is_early: bool = False
    is_continuous: bool = False
    note: str = ""


class SchedulingBatchItem(BaseModel):
    """批量录入中的单条：某人某天某状态（或某夜班岗）。"""
    person: str
    date: str
    post_id: int | None = None     # 夜班岗传岗位 id；状态类留空
    status: str = "在岗"
    is_early: bool = False
    is_continuous: bool = False
    note: str = ""


class SchedulingBatchRequest(BaseModel):
    """批量录入一批非白班约束（夜班、发热门诊、休息、病假……），按 items 逐条 upsert。

    prune + prune_keys 用于「矩阵整体保存」场景：把 prune_keys 列出的
    (date, status) 对，裁剪为本次提交的 persons 集合（删除未提交的人员），
    实现单元格「取消勾选即移除」。仅对无岗位状态记录（post_id 为空）生效。
    """
    plan_id: int
    items: list[SchedulingBatchItem] = []
    prune: bool = False
    prune_keys: list[list[str]] = []  # [[date, status], ...] 状态行裁剪
    prune_post_keys: list[list[str]] = []  # [[date, str(post_id)], ...] 岗位行(夜班/发热)裁剪


class SchedulingMergePlansRequest(BaseModel):
    """一次性数据归并：将 source_plan_ids 下的所有排班分配迁移到 target_plan_id。

    仅用于排班计划弱化后，把历史计划(如 2026-7 / 2026-8)的数据归并到默认
    「主班表」，使其在月视图直接可见。不动任何行数据，仅改写 plan_id；
    source 计划本身保留、不被删除。需管理员权限（一次性运维操作）。
    """
    source_plan_ids: list[int]
    target_plan_id: int


from .iso15189 import *  # 15189 内审专项 schema（文件评审 / 自查 / 科室内审）

