from fastapi import APIRouter

from . import (
    auth,
    audit_logs,
    change_log,
    dashboard,
    documents,
    eqa,
    eqa_associations,
    education,
    instruments,
    instrument_families,
    nonconformity,
    notifications,
    qc,
    reminders,
    comparison,
    interlab,
    qc_target,
    qc_material,
    quality_requirements,
    module_permissions,
    scheduling,

    qc_summaries,
    reagent_management,
    reagents,
    test_items,
    training,
    users,
    verification,
    uncertainty,
    verification_reports,
    report_archives,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(dashboard.router)
api_router.include_router(test_items.router)
api_router.include_router(change_log.router)
api_router.include_router(documents.router)
api_router.include_router(instruments.router)
api_router.include_router(instruments.public_router)
api_router.include_router(instrument_families.router)
api_router.include_router(qc.router)
api_router.include_router(qc_summaries.router)
api_router.include_router(eqa.router)
api_router.include_router(eqa_associations.router)
api_router.include_router(reagents.router)
api_router.include_router(reagent_management.router)
api_router.include_router(training.router)
api_router.include_router(verification.router)
api_router.include_router(nonconformity.router)
api_router.include_router(notifications.router)
api_router.include_router(reminders.router)
api_router.include_router(comparison.router)
api_router.include_router(interlab.router)
api_router.include_router(qc_target.router)
api_router.include_router(qc_material.router)
api_router.include_router(quality_requirements.router)
api_router.include_router(module_permissions.router)
api_router.include_router(scheduling.posts_router)
api_router.include_router(scheduling.plans_router)
api_router.include_router(scheduling.assignments_router)
api_router.include_router(scheduling.router)
api_router.include_router(education.router)
api_router.include_router(education.attach_router)
api_router.include_router(uncertainty.custom_router)  # 必须先于 router，否则 /{item_id} 抢匹配
api_router.include_router(uncertainty.router)
api_router.include_router(verification_reports.router)
api_router.include_router(verification_reports.project_archive_router)
api_router.include_router(report_archives.router)

# CNAS / WS-T 医学实验室认可规范文件（列表 / 预览 / 下载）
from . import cnas_standards
api_router.include_router(cnas_standards.router)

# 15189 内审专项（文件评审 / 自查 / 科室内审 / 认可能力范围）
from . import review, self_inspection, corrective_action, accredited_scope
api_router.include_router(review.review_router)
api_router.include_router(self_inspection.si_router)
api_router.include_router(corrective_action.corrective_router)
api_router.include_router(accredited_scope.scope_router)

# 将 test-items 的静态路由 /stats、/export 移到参数路由 /{item_id} 之前，
# 避免具体路径被通用参数路由吞掉（如 GET /test-items/stats 误命中 /{item_id}）。
_static_test_item = [
    r for r in api_router.routes
    if getattr(r, "path", None) in ("/api/v1/test-items/stats", "/api/v1/test-items/export")
]
_other_routes = [
    r for r in api_router.routes
    if getattr(r, "path", None) not in ("/api/v1/test-items/stats", "/api/v1/test-items/export")
]
api_router.routes = _static_test_item + _other_routes

# 同理：instruments 的静态路由 /family-map 移到参数路由 /{instrument_id} 之前
_static_instrument = [
    r for r in api_router.routes
    if getattr(r, "path", None) == "/api/v1/instruments/family-map"
]
_other_instr_routes = [
    r for r in api_router.routes
    if getattr(r, "path", None) != "/api/v1/instruments/family-map"
]
api_router.routes = _static_instrument + _other_instr_routes
