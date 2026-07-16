from ...core.crud_base import make_router
from ...models.nonconformity import Nonconformity
from ...schemas import NonconformityCreate, NonconformityRead, NonconformityUpdate

router = make_router(
    Nonconformity,
    NonconformityRead,
    NonconformityCreate,
    NonconformityUpdate,
    search_fields=["title", "description", "responsible", "corrective_action"],
    filter_fields=["nc_type", "source", "status"],
    prefix="/nonconformities",
    write_roles=("admin", "quality_manager", "qc_manager", "training_manager", "reagent_manager", "it_manager", "specialty_leader"),
)
