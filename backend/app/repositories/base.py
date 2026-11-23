from collections.abc import Callable
from datetime import datetime
from typing import Protocol

from pydantic import BaseModel, Field

from ..domain.models import (
    AccessGrant,
    AccessRequest,
    AuditEntry,
    Booking,
    Conflict,
    DemandEvent,
    Department,
    Equipment,
    Lab,
    Notification,
    Project,
    User,
)


class SlotLock(BaseModel):
    """Associate one equipment unit and half-hour slot with a booking."""

    id: str
    booking_id: str
    unit_id: str
    slot_start: datetime


class State(BaseModel):
    """Represent a snapshot of LabLink's stored collections."""

    departments: dict[str, Department] = Field(default_factory=dict)
    labs: dict[str, Lab] = Field(default_factory=dict)
    equipment: dict[str, Equipment] = Field(default_factory=dict)
    users: dict[str, User] = Field(default_factory=dict)
    projects: dict[str, Project] = Field(default_factory=dict)
    access_requests: dict[str, AccessRequest] = Field(default_factory=dict)
    access_grants: dict[str, AccessGrant] = Field(default_factory=dict)
    bookings: dict[str, Booking] = Field(default_factory=dict)
    conflicts: dict[str, Conflict] = Field(default_factory=dict)
    notifications: dict[str, Notification] = Field(default_factory=dict)
    audit_log: dict[str, AuditEntry] = Field(default_factory=dict)
    slot_locks: dict[str, SlotLock] = Field(default_factory=dict)
    demand_events: dict[str, DemandEvent] = Field(default_factory=dict)


COLLECTIONS = tuple(State.model_fields)


class Repository(Protocol):
    """Define the snapshot reads and atomic mutations used by services."""

    def read(self) -> State:
        """Return a consistent snapshot of the stored state."""
        ...

    def transact[T](self, operation: Callable[[State], T]) -> T:
        """Apply an operation atomically and return its result."""
        ...
