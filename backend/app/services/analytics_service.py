from collections import defaultdict
from datetime import datetime, timedelta
from typing import TypedDict

from ..ai.schemas import Insight
from ..domain.constants import OCCUPIED
from ..domain.enums import BookingStatus, Role
from ..domain.models import Booking, DemandEvent, Interval, User
from ..domain.timeslots import IST, at_local, campus_date, minutes, opening, overlaps
from ..repositories.base import State
from .permissions import supervises


class EquipmentUsage(TypedDict):
    id: str
    name: str
    utilisation_pct: float
    demand_ratio: float
    bookings: int
    no_show_pct: float
    available_minutes: int


class DepartmentUsage(TypedDict):
    id: str
    name: str
    bookings: int
    hours: float


def percent(value: float, total: float) -> float:
    """Express a ratio as a percentage."""
    return round(100 * value / total, 1) if total else 0.0


def duration(booking: Interval, window: Interval) -> int:
    """Measure the overlap between a booking and a reporting window."""
    return minutes(Interval(start=max(window.start, booking.start), end=min(window.end, booking.end)))


def overview(
    state: State, actor: User, now: datetime, days: int, department: str | None = None, lab: str | None = None
) -> dict:
    """Aggregate booking, demand, and utilisation statistics for a reporting range."""
    first = campus_date(now) - timedelta(days=days - 1)
    window = Interval(start=at_local(first), end=now)
    visible = [
        item
        for item in state.equipment.values()
        if supervises(actor, state, item)
        and (not department or item.department_id == department)
        and (not lab or item.lab_id == lab)
        and item.status != "retired"
    ]
    visible_ids = {item.id for item in visible}
    bookings_by_equipment: defaultdict[str, list[Booking]] = defaultdict(list)
    for booking in state.bookings.values():
        if booking.equipment_id in visible_ids and overlaps(booking, window):
            bookings_by_equipment[booking.equipment_id].append(booking)
    rejected_by_equipment: defaultdict[str, list[DemandEvent]] = defaultdict(list)
    for event in state.demand_events.values():
        if event.equipment_id in visible_ids and overlaps(event, window):
            rejected_by_equipment[event.equipment_id].append(event)

    by_equipment: list[EquipmentUsage] = []
    by_department: dict[str, DepartmentUsage] = {}
    heat = [[0 for _ in range(12)] for _ in range(7)]
    booked: list[Booking] = []
    supply, used, contested = 0, 0, 0
    for item in visible:
        history = bookings_by_equipment[item.id]
        occupied = [b for b in history if b.status in OCCUPIED]
        waitlisted = [
            b
            for b in history
            if b.status in {BookingStatus.CONTESTED, BookingStatus.DECLINED, BookingStatus.REALLOCATED}
        ]
        rejected = rejected_by_equipment[item.id]
        capacity = sum(
            duration(interval, window)
            for day in range(days)
            for interval in opening(state.labs[item.lab_id], first + timedelta(days=day))
            if overlaps(interval, window)
        ) * len(item.unit_ids)
        busy = sum(duration(b, window) for b in occupied)
        demand = busy + sum(duration(b, window) for b in [*waitlisted, *rejected])
        by_equipment.append(
            {
                "id": item.id,
                "name": item.name,
                "utilisation_pct": percent(busy, capacity),
                "demand_ratio": round(demand / capacity, 2) if capacity else 0,
                "bookings": len(occupied),
                "no_show_pct": no_show(occupied),
                "available_minutes": capacity,
            }
        )
        dep = state.departments[item.department_id]
        totals = by_department.setdefault(dep.id, {"id": dep.id, "name": dep.name, "bookings": 0, "hours": 0})
        totals["bookings"] += len(occupied)
        totals["hours"] += busy / 60
        supply += capacity
        used += busy
        contested += sum(b.status in {BookingStatus.CONTESTED, BookingStatus.REALLOCATED} for b in waitlisted)
        booked.extend(occupied)
        for booking in occupied:
            time = booking.start.astimezone(IST)
            if 8 <= time.hour < 20:
                heat[time.weekday()][time.hour - 8] += 1
    return {
        "kpis": {
            "utilisation_pct": percent(used, supply),
            "bookings": len(booked),
            "no_show_pct": no_show(booked),
            "unique_students": len({b.user_id for b in booked if state.users[b.user_id].role == Role.STUDENT}),
            "contested": contested,
            "avg_lead_time_h": round(
                sum((b.start - b.created_at).total_seconds() / 3600 for b in booked) / max(1, len(booked)), 1
            ),
        },
        "by_equipment": sorted(by_equipment, key=lambda row: (-row["utilisation_pct"], row["name"])),
        "by_department": list(by_department.values()),
        "heatmap": {"days": 7, "hours": list(range(8, 20)), "cells": heat},
    }


def no_show(bookings: list[Booking]) -> float:
    """Calculate the percentage of completed or missed bookings marked as no-shows."""
    finished = [b for b in bookings if b.status in {BookingStatus.COMPLETED, BookingStatus.NO_SHOW}]
    return percent(sum(b.status == BookingStatus.NO_SHOW for b in finished), len(finished))


def local_insights(data: dict) -> list[Insight]:
    """Derive utilisation insights deterministically from the aggregate data."""
    equipment = data["by_equipment"]
    ideas = []
    for row in sorted(equipment, key=lambda r: -r["demand_ratio"]):
        if row["demand_ratio"] > 1.2:
            ideas.append(
                Insight(
                    title="Demand exceeds capacity",
                    detail=f"{row['name']} has a demand ratio of {row['demand_ratio']:.2f}.",
                    action="Review staffing and opening hours.",
                    equipment_ids=[row["id"]],
                    severity="warning",
                )
            )
        if row["bookings"] >= 3 and row["no_show_pct"] > 20:
            ideas.append(
                Insight(
                    title="High no-show rate",
                    detail=f"{row['name']} recorded a {row['no_show_pct']:g}% no-show rate.",
                    action="Remind users to release unused bookings.",
                    equipment_ids=[row["id"]],
                    severity="warning",
                )
            )
    underused = sorted(
        (r for r in equipment if r["available_minutes"] and r["utilisation_pct"] < 15),
        key=lambda r: r["utilisation_pct"],
    )
    if underused:
        row = underused[0]
        ideas.append(
            Insight(
                title="Capacity available",
                detail=f"{row['name']} used {row['utilisation_pct']:g}% of available time.",
                action="Highlight suitable equipment in the catalogue.",
                equipment_ids=[row["id"]],
                severity="opportunity",
            )
        )
    if data["kpis"]["bookings"]:
        counts = [sum(values) for values in zip(*data["heatmap"]["cells"], strict=True)]
        peak = max(range(len(counts) - 1), key=lambda i: counts[i] + counts[i + 1])
        share = percent(counts[peak] + counts[peak + 1], data["kpis"]["bookings"])
        if share > 40:
            hour = data["heatmap"]["hours"][peak]
            ideas.append(
                Insight(
                    title="Bookings cluster at peak hours",
                    detail=f"{share:g}% of bookings start from {hour}:00 to {hour + 2}:00 IST.",
                    action="Encourage users to book earlier in the day.",
                    equipment_ids=[],
                    severity="info",
                )
            )
    return ideas[:5]
