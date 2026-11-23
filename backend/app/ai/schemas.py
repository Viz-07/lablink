from typing import Literal

from pydantic import BaseModel, Field


class Hit(BaseModel):
    equipment_id: str
    reason: str = Field(max_length=200)
    match: int = Field(ge=0, le=100)


class SearchResult(BaseModel):
    interpreted_need: str = Field(max_length=200)
    hits: list[Hit] = Field(max_length=8)


class DraftResult(BaseModel):
    justification: str = Field(min_length=30, max_length=1800)
    estimated_hours: int = Field(ge=1, le=60)
    checklist: list[str] = Field(max_length=5)
    suggested_equipment: list[Hit] = Field(max_length=5)


class Summary(BaseModel):
    summary: str = Field(max_length=400)
    recommendation: Literal["approve", "approve_with_changes", "review_carefully"]


class PersonalMessage(BaseModel):
    booking_id: str
    text: str = Field(max_length=300)


class Explanation(BaseModel):
    summary: str = Field(max_length=600)
    messages: list[PersonalMessage] = Field(max_length=30)


class Insight(BaseModel):
    title: str = Field(max_length=60)
    detail: str = Field(max_length=240)
    action: str = Field(max_length=120)
    equipment_ids: list[str] = Field(max_length=8)
    severity: Literal["info", "warning", "opportunity"]


class InsightResult(BaseModel):
    insights: list[Insight] = Field(max_length=5)
