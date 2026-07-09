from fastapi import APIRouter

from . import auth, documents, instruments, notifications, test_items, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(test_items.router)
api_router.include_router(documents.router)
api_router.include_router(instruments.router)
api_router.include_router(notifications.router)
