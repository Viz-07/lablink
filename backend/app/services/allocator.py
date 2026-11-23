from dataclasses import dataclass
from datetime import datetime

from ..domain.models import Interval, PriorityBreakdown
from ..domain.timeslots import overlaps


@dataclass(frozen=True)
class RequestInput:
    """Represent a booking's rank and feasibility inputs for allocation."""

    id: str
    user_id: str
    interval: Interval
    created_at: datetime
    priority: PriorityBreakdown
    reason: str | None = None


@dataclass(frozen=True)
class Placement:
    """Pair an allocation request with a unit or a rejection reason."""

    request: RequestInput
    unit_id: str | None
    reason: str | None


def allocate(
    requests: list[RequestInput],
    units: list[str],
    locked: dict[str, list[Interval]],
) -> list[Placement]:
    """Rank requests and assign the first feasible unit in stable order."""
    occupied = {unit: list(locked.get(unit, [])) for unit in units}
    allocated: dict[str, list[Interval]] = {}
    output = []
    for request in sorted(requests, key=lambda r: (-r.priority.score, r.created_at, r.id)):
        reason = request.reason
        if any(overlaps(request.interval, other) for other in allocated.get(request.user_id, [])):
            reason = reason or "USER_OVERLAP"
        unit = (
            None
            if reason
            else next(
                (
                    u
                    for u in sorted(occupied)
                    if not any(overlaps(request.interval, interval) for interval in occupied[u])
                ),
                None,
            )
        )
        if unit:
            occupied[unit].append(request.interval)
            allocated.setdefault(request.user_id, []).append(request.interval)
        output.append(Placement(request, unit, reason or (None if unit else "CAPACITY")))
    return output
