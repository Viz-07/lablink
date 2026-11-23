from datetime import datetime
from secrets import token_hex

from ..domain.models import AuditEntry, Notification
from ..repositories.base import State


def new_id(prefix: str) -> str:
    return f"{prefix}_{token_hex(9)}"


def notify(state: State, now: datetime, user: str, event: str, title: str, body: str, link: str) -> None:
    entry = Notification(id=new_id("nt"), user_id=user, type=event, title=title, body=body, link=link, created_at=now)
    state.notifications[entry.id] = entry


def audit(
    state: State,
    now: datetime,
    actor: str,
    action: str,
    target: str,
    details: dict[str, str | int | float] | None = None,
) -> None:
    entry = AuditEntry(
        id=new_id("au"),
        actor_id=actor,
        action=action,
        target_type=action.split(".")[0],
        target_id=target,
        at=now,
        details=details or {},
    )
    state.audit_log[entry.id] = entry
