import unicodedata
from datetime import date
from typing import Annotated, Literal

from pydantic import AfterValidator, AwareDatetime, BaseModel, ConfigDict, Field, StringConstraints, model_validator

from ..domain.enums import Category, ProjectType
from ..domain.models import Interval
from ..domain.timeslots import aligned, minutes

Id = Annotated[str, StringConstraints(pattern=r"^[a-z0-9_-]{3,64}$")]
RangeDays = Literal[7, 14, 30]
Certification = Literal["laser-safety", "rf-safety", "bsl1-biosafety", "machine-shop-basic", "high-voltage"]


def clean_text(text: str) -> str:
    return "".join(char for char in text if unicodedata.category(char)[0] != "C" or char in "\n\t").strip()


def bounded(low: int, high: int):
    def validate(text: str) -> str:
        text = clean_text(text)
        if not low <= len(text) <= high:
            raise ValueError(f"Use between {low} and {high} characters.")
        return text

    return AfterValidator(validate)


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class DemoLogin(Input):
    persona_id: Id


class BookingCreate(Input):
    equipment_id: Id
    start: AwareDatetime
    end: AwareDatetime
    purpose: Annotated[str, bounded(5, 300)]
    project_id: Id | None = None

    @model_validator(mode="after")
    def valid_interval(self) -> "BookingCreate":
        if not (
            aligned(self.start) and aligned(self.end) and 30 <= minutes(Interval(start=self.start, end=self.end)) <= 480
        ):
            raise ValueError("Select an aligned interval of 30 minutes to 8 hours.")
        return self


class Selection(Input):
    index: int = Field(ge=0, le=2)


class Reason(Input):
    reason: Annotated[str, bounded(5, 500)]


class Cancel(Input):
    reason: Annotated[str, bounded(0, 500)] = ""


class ProjectCreate(Input):
    title: Annotated[str, bounded(3, 120)]
    description: Annotated[str, bounded(20, 2000)]
    type: ProjectType
    deadline: date | None = None
    supervisor_id: Id | None = None
    member_ids: list[Id] = Field(default_factory=list, max_length=8)


class ProjectUpdate(Input):
    title: Annotated[str, bounded(3, 120)] | None = None
    description: Annotated[str, bounded(20, 2000)] | None = None
    type: ProjectType | None = None
    deadline: date | None = None
    supervisor_id: Id | None = None
    member_ids: list[Id] | None = Field(default=None, max_length=8)


class AccessCreate(Input):
    project_id: Id
    equipment_ids: list[Id] = Field(min_length=1, max_length=5)
    hours_requested: int = Field(ge=1, le=60)
    needed_from: date
    needed_until: date
    justification: Annotated[str, bounded(30, 2000)]


class Decision(Input):
    comment: Annotated[str, bounded(0, 500)] = ""
    hours_approved: int | None = Field(default=None, ge=1, le=60)


class Override(Input):
    promote: Id
    demote: Id
    reason: Annotated[str, bounded(10, 500)]


class Apply(Input):
    overrides: list[Override] = Field(default_factory=list, max_length=10)


class Search(Input):
    query: Annotated[str, bounded(3, 300)]


class Draft(Input):
    project_id: Id
    equipment_ids: list[Id] = Field(default_factory=list, max_length=5)
    notes: Annotated[str, bounded(0, 500)] = ""


class Insights(Input):
    range_days: RangeDays = 7


class ReadNotifications(Input):
    ids: list[Id] | Literal["all"] = Field(max_length=100)


class EquipmentCreate(Input):
    name: Annotated[str, bounded(3, 120)]
    lab_id: Id
    category: Category
    kind: Literal["equipment", "dev_kit", "workstation"] = "equipment"
    description: Annotated[str, bounded(10, 500)]
    specs: dict[Annotated[str, bounded(1, 30)], Annotated[str, bounded(1, 90)]] = Field(max_length=10)
    capability_tags: list[Annotated[str, bounded(1, 40)]] = Field(max_length=20)
    approval_mode: Literal["auto", "faculty"] = "auto"
    required_training: Certification | None = None
    max_booking_minutes: int = Field(default=240, ge=30, le=480, multiple_of=30)
    weekly_limit_minutes_per_user: int = Field(default=600, ge=30, le=2400, multiple_of=30)
    units: int = Field(default=1, ge=1, le=30)
    status: Literal["active", "maintenance", "retired"] = "active"


class EquipmentUpdate(Input):
    name: Annotated[str, bounded(3, 120)] | None = None
    lab_id: Id | None = None
    category: Category | None = None
    kind: Literal["equipment", "dev_kit", "workstation"] | None = None
    description: Annotated[str, bounded(10, 500)] | None = None
    specs: dict[Annotated[str, bounded(1, 30)], Annotated[str, bounded(1, 90)]] | None = Field(
        default=None, max_length=10
    )
    capability_tags: list[Annotated[str, bounded(1, 40)]] | None = Field(default=None, max_length=20)
    approval_mode: Literal["auto", "faculty"] | None = None
    required_training: Certification | None = None
    max_booking_minutes: int | None = Field(default=None, ge=30, le=480, multiple_of=30)
    weekly_limit_minutes_per_user: int | None = Field(default=None, ge=30, le=2400, multiple_of=30)
    units: int | None = Field(default=None, ge=1, le=30)
    status: Literal["active", "maintenance", "retired"] | None = None


class CertificationChange(Input):
    add: list[Certification] = Field(default_factory=list, max_length=5)
    remove: list[Certification] = Field(default_factory=list, max_length=5)
