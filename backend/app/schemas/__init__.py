"""各模型的 Pydantic 序列化定义。Create/Update 共用 Base（字段带默认值，Update 用 exclude_unset 取增量）；Read 额外含 id 与时间戳。"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


# ---------------- User ----------------
class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    username: str = ""
    full_name: str = ""
    role: str = "member"
    department: str = ""
    is_active: bool = True


class UserCreate(UserBase):
    password: str = ""


class UserUpdate(UserBase):
    password: str | None = None


class UserRead(UserBase):
    id: int
    created_at: datetime | None = None


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
    report_file_path: str = ""
    operator: str = ""


class CalibrationRecordCreate(CalibrationRecordBase):
    pass


class CalibrationRecordUpdate(CalibrationRecordBase):
    pass


class CalibrationRecordRead(CalibrationRecordBase):
    id: int
    created_at: datetime | None = None


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
