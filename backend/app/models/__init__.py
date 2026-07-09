# 注册所有模型，确保 Base.metadata 包含全部表
from .audit_log import AuditLog
from .document import Document, DocumentVersion
from .instrument import CalibrationRecord, Instrument
from .nonconformity import Nonconformity
from .notification import Notification
from .qc import QCRecord
from .reagent import Reagent
from .test_item import TestItem
from .training import TrainingRecord
from .user import User
from .verification import VerificationRecord

__all__ = [
    "User",
    "TestItem",
    "Document",
    "DocumentVersion",
    "Instrument",
    "CalibrationRecord",
    "Notification",
    "AuditLog",
    "QCRecord",
    "Reagent",
    "TrainingRecord",
    "VerificationRecord",
    "Nonconformity",
]
