# 注册所有模型，确保 Base.metadata 包含全部表
from .audit_log import AuditLog
from .document import Document, DocumentVersion
from .document_instrument import DocumentInstrument
from .file_change_log import FileChangeLog
from .instrument import CalibrationRecord, Instrument
from .instrument_archive import InstrumentArchive
from .instrument_family import InstrumentFamily, InstrumentFamilyMember
from .nonconformity import Nonconformity
from .notification import Notification
from .qc import QCRecord, QCMonthlySummary, QCDailyValue, QCMonthlyReport
from .eqa import EqaPlan, EqaSummary
from .reagent import Reagent
from .test_item import TestItem
from .training import TrainingRecord
from .user import User
from .verification import VerificationRecord
from .comparison import ComparisonGroup, ComparisonPlan, ComparisonResult, ComparisonQualResult, ComparisonAttachment
from .interlab import InterlabPlan, InterlabItem, InterlabLevel
from .qc_target import QCTargetBatch, QCTargetResult
from .qc_material import QcMaterial

__all__ = [
    "User",
    "TestItem",
    "Document",
    "DocumentVersion",
    "DocumentInstrument",
    "Instrument",
    "InstrumentArchive",
    "InstrumentFamily",
    "InstrumentFamilyMember",
    "CalibrationRecord",
    "Notification",
    "AuditLog",
    "FileChangeLog",
    "QCRecord",
    "QCMonthlySummary",
    "QCMonthlyReport",
    "QCDailyValue",
    "EqaPlan",
    "EqaSummary",
    "Reagent",
    "TrainingRecord",
    "VerificationRecord",
    "Nonconformity",
    "ComparisonGroup",
    "ComparisonPlan",
    "ComparisonResult",
    "ComparisonQualResult",
    "ComparisonAttachment",
    "InterlabPlan",
    "InterlabItem",
    "InterlabLevel",
    "QCTargetBatch",
    "QCTargetResult",
    "QcMaterial",
]
