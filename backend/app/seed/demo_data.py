from datetime import datetime, timedelta
from random import Random

from ..domain.constants import CERTIFICATIONS
from ..domain.enums import BookingStatus, ProjectType, Role
from ..domain.models import AccessGrant, AccessRequest, Booking, Conflict, Project, User
from ..domain.timeslots import at_local, campus_date, opening
from ..repositories.base import COLLECTIONS, State
from ..services.events import notify
from .catalogue import seed_catalogue

PERSONAS = {
    "u-aarav": ("Aarav Shetty", Role.STUDENT, "ece", 4, ["rf-safety"], "Reserve RF equipment for an antenna capstone."),
    "u-meera": (
        "Dr. Meera Kulkarni",
        Role.FACULTY,
        "ece",
        None,
        list(CERTIFICATIONS),
        "Review requests and resolve a spectrum analyser conflict.",
    ),
    "u-ravi": (
        "Ravi Kumar",
        Role.ADMIN,
        "central",
        None,
        list(CERTIFICATIONS),
        "Track utilisation and manage the campus catalogue.",
    ),
    "u-diya": ("Diya Nair", Role.STUDENT, "cse", 3, [], "Request GPU time and a Jetson kit."),
    "u-kabir": (
        "Kabir Rao",
        Role.STUDENT,
        "me",
        2,
        ["machine-shop-basic", "rf-safety"],
        "Prototype a lightweight frame and check training requirements.",
    ),
    "u-sneha": ("Sneha Pai", Role.STUDENT, "mnc", 4, ["rf-safety"], "Review booking outcomes and accept alternatives."),
    "u-arjun": (
        "Prof. Arjun Hegde",
        Role.FACULTY,
        "cse",
        None,
        list(CERTIFICATIONS),
        "Review GPU and embedded systems requests.",
    ),
}


def seed(state: State, now: datetime, *, reset: bool = False) -> None:
    """Populate a reproducible demo with fresh dates and two open conflicts."""
    if state.users and not reset:
        return
    if reset:
        for name in COLLECTIONS:
            getattr(state, name).clear()
    seed_catalogue(state, now)
    for key, (name, role, department, year, certifications, blurb) in PERSONAS.items():
        state.users[key] = User(
            id=key,
            name=name,
            role=role,
            department_id=department,
            year=year,
            certifications=certifications,
            blurb=blurb,
        )
        notify(state, now, key, "welcome", "Welcome to LabLink", blurb, "/discover")
    for index in range(12):
        key = f"u-demo-{index}"
        state.users[key] = User(
            id=key,
            name=f"{['Isha', 'Neil', 'Mira', 'Aditya'][index % 4]} {['Shah', 'Rao', 'Joshi'][index // 4]}",
            department_id="cse",
        )
    seed_projects(state, now)
    seed_history(state, now)
    demo_conflict(state, now, "spectrum", "eq-spectrum-keysight", ["aarav", "sneha", "kabir"])
    demo_conflict(state, now, "gpu", "eq-gpu-a6000", ["diya", "demo-0", "demo-1"])


def seed_projects(state: State, now: datetime) -> None:
    today = campus_date(now)
    projects = [
        (
            "aarav",
            "Phased antenna array for 2.4 GHz ISM band",
            "Measure RF response and characterise antenna performance for the campus capstone demonstration.",
            ProjectType.CAPSTONE,
            6,
            "u-meera",
        ),
        (
            "sneha",
            "ML-based RF signal classification",
            "Collect and label measurements for a research project on RF signal classification.",
            ProjectType.RESEARCH,
            20,
            "u-meera",
        ),
        (
            "diya",
            "Real-time sign-language recognition on edge devices",
            "Train and evaluate a vision model and benchmark inference on a Jetson developer kit.",
            ProjectType.COMPETITION,
            10,
            "u-arjun",
        ),
        (
            "kabir",
            "Lightweight drone frame",
            "Compare printed samples and evaluate mechanical properties of a lightweight prototype.",
            ProjectType.PERSONAL,
            None,
            None,
        ),
    ]
    for owner, title, description, kind, days, supervisor in projects:
        project_id = f"pr-{owner}"
        state.projects[project_id] = Project(
            id=project_id,
            owner_id=f"u-{owner}",
            title=title,
            description=description,
            type=kind,
            supervisor_id=supervisor,
            deadline=today + timedelta(days=days) if days else None,
            created_at=now - timedelta(days=3),
        )
    requests = [
        (
            "aarav",
            ["eq-spectrum-keysight", "eq-rf-generator"],
            10,
            6,
            "I need to compare the two antenna revisions at 2.4 GHz before our capstone demonstration.",
            "approved",
        ),
        ("sneha", ["eq-spectrum-keysight"], 8, 12, "I need the equipment to take measurements.", "pending"),
        (
            "diya",
            ["eq-jetson", "eq-gpu-4090"],
            16,
            9,
            "I need to train and benchmark a sign-language recognition model in time for the campus competition.",
            "pending",
        ),
    ]
    for owner, items, hours, days, notes, status in requests:
        request = AccessRequest(
            id=f"ar-{owner}",
            project_id=f"pr-{owner}",
            requester_id=f"u-{owner}",
            equipment_ids=items,
            hours_requested=hours,
            needed_from=today,
            needed_until=today + timedelta(days=days),
            justification=notes,
            created_at=now - timedelta(hours=4),
        )
        if status == "approved":
            request.status, request.reviewer_id, request.decided_at = "approved", "u-meera", now
            state.access_grants["ag-aarav"] = AccessGrant(
                id="ag-aarav",
                access_request_id=request.id,
                user_id=request.requester_id,
                project_id=request.project_id,
                equipment_ids=items,
                minutes_quota=600,
                minutes_used=120,
                valid_from=today,
                valid_until=request.needed_until,
            )
        state.access_requests[request.id] = request


def seed_history(state: State, now: datetime) -> None:
    # Seeded PRNG keeps the demo history reproducible; it is never used for security.
    rng = Random(42)  # noqa: S311  # nosec B311
    keys = [key for key in state.equipment if key not in {"eq-spectrum-keysight", "eq-spectrum-rs"}]
    slots_used = set()
    for n in range(150):
        key = rng.choice(keys + ["eq-prusa", "eq-gpu-4090"] * 12)
        item = state.equipment[key]
        day = campus_date(now) - timedelta(days=rng.randint(1, 30))
        windows = opening(state.labs[item.lab_id], day)
        while not windows:
            day -= timedelta(days=1)
            windows = opening(state.labs[item.lab_id], day)
        unit = rng.choice(item.unit_ids)
        start = min(at_local(day, f"{rng.randint(13, 16):02}:00"), windows[0].end - timedelta(hours=1))
        if (unit, start) in slots_used:
            continue
        slots_used.add((unit, start))
        status = rng.choices([BookingStatus.COMPLETED, BookingStatus.NO_SHOW, BookingStatus.CANCELLED], [85, 6, 9])[0]
        key_id = f"bk-history-{n}"
        state.bookings[key_id] = Booking(
            id=key_id,
            equipment_id=key,
            unit_id=unit,
            user_id=f"u-demo-{rng.randrange(12)}",
            start=start,
            end=start + timedelta(hours=1),
            purpose="Scheduled lab work",
            status=status,
            created_at=start - timedelta(days=2),
            updated_at=start,
        )
    for who, length in [("aarav", 2), ("kabir", 5)]:
        start = at_local(campus_date(now) - timedelta(days=3), "10:00")
        key = f"bk-use-{who}"
        state.bookings[key] = Booking(
            id=key,
            equipment_id="eq-rf-generator" if who == "aarav" else "eq-prusa",
            user_id=f"u-{who}",
            start=start,
            end=start + timedelta(hours=length),
            status=BookingStatus.COMPLETED,
            purpose="Earlier project session",
            created_at=start - timedelta(days=1),
            updated_at=start,
        )


def demo_conflict(state: State, now: datetime, key: str, equipment_id: str, people: list[str]) -> None:
    day = campus_date(now) + timedelta(days=1)
    item = state.equipment[equipment_id]
    while not opening(state.labs[item.lab_id], day):
        day += timedelta(days=1)
    start, end = at_local(day, "10:00"), at_local(day, "12:00")
    conflict_id = f"cf-demo-{key}"
    ids = []
    for n, name in enumerate(people):
        booking_id = f"bk-demo-{key}-{n}"
        state.bookings[booking_id] = Booking(
            id=booking_id,
            user_id=f"u-{name}",
            equipment_id=equipment_id,
            project_id=f"pr-{name}" if f"pr-{name}" in state.projects else None,
            start=start,
            end=end,
            purpose="Reserved time for project measurements",
            status=BookingStatus.PENDING if n == 0 else BookingStatus.CONTESTED,
            conflict_id=conflict_id,
            created_at=now - timedelta(hours=[20, 30, 2][n]),
            updated_at=now,
        )
        ids.append(booking_id)
    state.conflicts[conflict_id] = Conflict(
        id=conflict_id,
        equipment_id=equipment_id,
        window_start=start,
        window_end=end,
        booking_ids=ids,
        capacity=1,
    )
