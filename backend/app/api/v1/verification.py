from ...core.crud_base import make_router
from ...models.verification import VerificationRecord
from ...schemas import VerificationRecordCreate, VerificationRecordRead, VerificationRecordUpdate

router = make_router(
    VerificationRecord,
    VerificationRecordRead,
    VerificationRecordCreate,
    VerificationRecordUpdate,
    search_fields=["test_item", "verify_type", "instrument", "operator", "criteria"],
    filter_fields=["verify_type", "conclusion", "instrument"],
    prefix="/verification-records",
)
