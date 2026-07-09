# 注册所有模型，确保 Base.metadata 包含全部表
from .audit_log import AuditLog
from .document import Document, DocumentVersion
from .instrument import CalibrationRecord, Instrument
from .notification import Notification
from .test_item import TestItem
from .user import User

__all__ = [
    "User",
    "TestItem",
    "Document",
    "DocumentVersion",
    "Instrument",
    "CalibrationRecord",
    "Notification",
    "AuditLog",
]
