from ...core.crud_base import make_router
from ...models.reagent import Reagent
from ...schemas import ReagentCreate, ReagentRead, ReagentUpdate

router = make_router(
    Reagent,
    ReagentRead,
    ReagentCreate,
    ReagentUpdate,
    search_fields=["name", "brand", "spec", "lot_no", "supplier", "operator"],
    filter_fields=["status", "brand"],
    prefix="/reagents",
    write_roles=("admin", "reagent_manager"),
)
