from fastapi import APIRouter

from ...core.crud_base import make_router
from ...models.test_item import TestItem
from ...schemas import TestItemCreate, TestItemRead, TestItemUpdate

router = make_router(
    TestItem,
    TestItemRead,
    TestItemCreate,
    TestItemUpdate,
    search_fields=["code", "name", "aliases", "category", "method", "instrument", "instrument_group"],
    filter_fields=["category", "specimen", "method"],
    prefix="/test-items",
)
