from ...core.crud_base import make_router
from ...models.training import TrainingRecord
from ...schemas import TrainingRecordCreate, TrainingRecordRead, TrainingRecordUpdate

router = make_router(
    TrainingRecord,
    TrainingRecordRead,
    TrainingRecordCreate,
    TrainingRecordUpdate,
    search_fields=["person", "title", "category", "organizer", "certificate_no"],
    filter_fields=["category", "status", "person"],
    prefix="/training-records",
    write_roles=("admin", "training_manager"),
)
