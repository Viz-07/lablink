from ..domain.models import AccessGrant, Equipment, Interval, User
from ..domain.timeslots import campus_date, minutes
from ..repositories.base import State


def valid_grant(
    state: State,
    user: User,
    item: Equipment,
    project_id: str | None,
    interval: Interval,
) -> AccessGrant | None:
    """Find a grant that covers the user, project, equipment, and interval."""
    return next(
        (
            g
            for g in sorted(state.access_grants.values(), key=lambda g: (g.valid_until, g.id))
            if g.user_id == user.id
            and g.project_id == project_id
            and item.id in g.equipment_ids
            and g.valid_from <= campus_date(interval.start) <= campus_date(interval.end) <= g.valid_until
            and g.minutes_quota - g.minutes_used >= minutes(interval)
        ),
        None,
    )
