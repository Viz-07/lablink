from typing import Annotated

from fastapi import APIRouter, Query

from ...services.analytics_service import overview
from ..deps import Reviewer
from ..schemas import Id

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/overview")
def analytics(
    s: Reviewer,
    range_days: Annotated[int, Query(ge=7, le=30)] = 7,
    department_id: Id | None = None,
    lab_id: Id | None = None,
) -> dict:
    """Return equipment and campus utilisation metrics for the selected range."""
    from ...core.errors import require

    require(range_days in {7, 14, 30}, "INVALID_RANGE", "Choose a 7, 14 or 30 day range.")
    return overview(s.state, s.user, s.now, range_days, department_id, lab_id)
