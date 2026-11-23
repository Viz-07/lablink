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
    id: str
    booking_id: str
    unit_id: str
    slot_start: datetime


class State(BaseModel):
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
    def read(self) -> State: ...

    def transact[T](self, operation: Callable[[State], T]) -> T: ...
