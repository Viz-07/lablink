from fastapi import APIRouter

from ...core.errors import find
from ...services.analytics_service import local_insights, overview
from ...services.catalog_service import summary
from ...services.project_service import project_for
from ..deps import Reviewer, SignedIn
from ..schemas import Draft, Insights, Search

router = APIRouter(prefix="/ai", tags=["AI"])


@router.post("/search")
def search(s: SignedIn, payload: Search) -> dict:
    """Return natural-language equipment search results."""
    items = list(s.state.equipment.values())
    result, source = s.ctx.ai.search(payload.query, items)
    hits = [
        {
            **hit.model_dump(),
            "equipment": summary(s.state, s.user, s.state.equipment[hit.equipment_id], s.now),
        }
        for hit in result.hits
    ]
    return {"source": source, "interpreted": result.interpreted_need, "results": hits}


@router.post("/draft-access-request")
def draft(s: SignedIn, payload: Draft) -> dict:
    """Draft an access request for a project the caller belongs to."""
    project = project_for(s.state, s.user, payload.project_id)
    items = list(s.state.equipment.values())
    chosen = [find(s.state.equipment, key, "Equipment") for key in dict.fromkeys(payload.equipment_ids)]
    result, source = s.ctx.ai.draft(project, items, chosen, payload.notes)
    training = sorted(
        {
            s.state.equipment[hit.equipment_id].required_training
            for hit in result.suggested_equipment
            if s.state.equipment[hit.equipment_id].required_training
        }
    )
    return {**result.model_dump(), "source": source, "training_needed": training}


@router.post("/insights")
def insights(s: Reviewer, payload: Insights) -> dict:
    """Summarize utilisation data in the reviewer's scope."""
    data = overview(s.state, s.user, s.now, payload.range_days)
    result, source = s.ctx.ai.insights(local_insights(data))
    return {**result.model_dump(), "source": source}
