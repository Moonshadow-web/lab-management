from ...core.crud_base import make_router
from ...models.qc import QCRecord
from ...schemas import QCRecordCreate, QCRecordRead, QCRecordUpdate

router = make_router(
    QCRecord,
    QCRecordRead,
    QCRecordCreate,
    QCRecordUpdate,
    search_fields=["test_item", "level", "lot_no", "instrument", "operator", "rule_violated"],
    filter_fields=["status", "instrument", "level"],
    prefix="/qc-records",
)
