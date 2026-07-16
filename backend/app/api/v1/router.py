from fastapi import APIRouter

from . import (
    auth,
    audit_logs,
    change_log,
    documents,
    eqa,
    eqa_associations,
    instruments,
    instrument_families,
    nonconformity,
    notifications,
    qc,
    reminders,
    comparison,
    interlab,

    qc_summaries,
    reagents,
    test_items,
    training,
    users,
    verification,
)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(audit_logs.router)
api_router.include_router(test_items.router)
api_router.include_router(change_log.router)
api_router.include_router(documents.router)
api_router.include_router(instruments.router)
api_router.include_router(instrument_families.router)
api_router.include_router(qc.router)
api_router.include_router(qc_summaries.router)
api_router.include_router(eqa.router)
api_router.include_router(eqa_associations.router)
api_router.include_router(reagents.router)
api_router.include_router(training.router)
api_router.include_router(verification.router)
api_router.include_router(nonconformity.router)
api_router.include_router(notifications.router)
api_router.include_router(reminders.router)
api_router.include_router(comparison.router)
api_router.include_router(interlab.router)

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
