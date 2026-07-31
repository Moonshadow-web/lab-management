"""科室内审（逐条款整改）子模块 API：关联不符合项，按条款号组织纠正/预防措施与验证。"""
from ...core.crud_base import make_router
from ...models.iso15189 import CorrectiveAction
from ...schemas import (
    CorrectiveActionCreate,
    CorrectiveActionRead,
    CorrectiveActionUpdate,
)

WRITE_ROLES = (
    "admin", "quality_manager", "qc_manager", "training_manager",
    "reagent_manager", "it_manager", "specialty_leader",
)

corrective_router = make_router(
    CorrectiveAction, CorrectiveActionRead,
    CorrectiveActionCreate, CorrectiveActionUpdate,
    search_fields=["clause", "title", "description", "responsible", "root_cause"],
    filter_fields=["nonconformity_id", "status", "source"],
    prefix="/corrective-actions",
    write_roles=WRITE_ROLES,
)
