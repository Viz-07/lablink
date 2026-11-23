from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, Field

from .enums import BookingStatus, Category, ProjectType, Role


class Record(BaseModel):
    id: str


class Department(Record):
    name: str
    code: str


class Window(BaseModel):
    open: str
    close: str


class Lab(Record):
    name: str
    department_id: str
    building: str
    room: str
    opening_hours: dict[int, list[Window]]
    supervisor_ids: list[str]
    accessibility_notes: str = "Step-free access via lift."
    contact_email: str = "labs@example.edu"


class Equipment(Record):
    name: str
    category: Category
    kind: Literal["equipment", "dev_kit", "workstation"]
    lab_id: str
    department_id: str
    description: str
    specs: dict[str, str]
    capability_tags: list[str]
    unit_ids: list[str]
    approval_mode: Literal["auto", "faculty"]
    required_training: str | None = None
    max_booking_minutes: int = 240
    weekly_limit_minutes_per_user: int = 600
    high_demand: bool = False
    status: Literal["active", "maintenance", "retired"] = "active"
    created_at: datetime
    updated_at: datetime


class User(Record):
    name: str
    role: Role = Role.STUDENT
    department_id: str
    year: int | None = None
    certifications: list[str] = Field(default_factory=list)
    no_show_count: int = 0
    blurb: str = ""


class Project(Record):
    owner_id: str
    member_ids: list[str] = Field(default_factory=list)
    title: str
    description: str
    type: ProjectType
    deadline: date | None
    supervisor_id: str | None = None
    created_at: datetime


class AccessRequest(Record):
    project_id: str
    requester_id: str
    equipment_ids: list[str]
    hours_requested: int
    needed_from: date
    needed_until: date
    justification: str
    status: Literal["pending", "approved", "declined", "withdrawn"] = "pending"
    reviewer_id: str | None = None
    reviewer_comment: str | None = None
    created_at: datetime
    decided_at: datetime | None = None


class AccessGrant(Record):
    access_request_id: str
    user_id: str
    project_id: str
    equipment_ids: list[str]
    minutes_quota: int
    minutes_used: int = 0
    valid_from: date
    valid_until: date


class Interval(BaseModel):
    start: datetime
    end: datetime


class Alternative(Interval):
    type: Literal["same_equipment_other_time", "equivalent_equipment"]
    equipment_id: str
    equipment_name: str
    lab_name: str
    unit_id: str
    score: float
    reason: str


class Factor(BaseModel):
    label: str
    value: float
    weight: float
    contribution: float


class PriorityBreakdown(BaseModel):
    score: float
    factors: dict[str, Factor]


class Booking(Interval, Record):
    equipment_id: str
    unit_id: str | None = None
    user_id: str
    project_id: str | None = None
    grant_id: str | None = None
    purpose: str
    status: BookingStatus
    priority_snapshot: PriorityBreakdown | None = None
    conflict_id: str | None = None
    alternatives: list[Alternative] = Field(default_factory=list)
    approved_by: str | None = None
    created_at: datetime
    updated_at: datetime
    checked_in_at: datetime | None = None
    replaced_by: str | None = None
    message: str | None = None


class AllocationRow(BaseModel):
    booking_id: str
    student: str
    project: str | None
    breakdown: PriorityBreakdown
    unit_id: str | None = None
    reason: str | None = None
    alternatives: list[Alternative] = Field(default_factory=list)


class Conflict(Record):
    equipment_id: str
    window_start: datetime
    window_end: datetime
    booking_ids: list[str]
    capacity: int
    status: Literal["open", "resolved", "dismissed"] = "open"
    recommendation: list[AllocationRow] | None = None
    ai_explanation: str | None = None
    explanation_source: Literal["ai", "fallback"] | None = None
    messages: dict[str, str] = Field(default_factory=dict)
    resolved_by: str | None = None
    resolved_at: datetime | None = None


class Notification(Record):
    user_id: str
    type: str
    title: str
    body: str
    link: str
    read: bool = False
    created_at: datetime


class AuditEntry(Record):
    actor_id: str
    action: str
    target_type: str
    target_id: str
    details: dict[str, str | int | float] = Field(default_factory=dict)
    at: datetime


class DemandEvent(Interval, Record):
    equipment_id: str
