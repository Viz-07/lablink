from .enums import BookingStatus, ProjectType

SLOT_MINUTES = 30
PRIORITY_WEIGHTS = {"deadline": 0.35, "fairness": 0.25, "project": 0.20, "approval": 0.10, "waiting": 0.10}
PROJECT_WEIGHTS = {
    ProjectType.CAPSTONE: 1.0,
    ProjectType.RESEARCH: 0.9,
    ProjectType.COMPETITION: 0.85,
    ProjectType.COURSE: 0.8,
    ProjectType.PERSONAL: 0.4,
}
QUEUE = frozenset({BookingStatus.PENDING, BookingStatus.CONTESTED})
ACTIVE = QUEUE | {BookingStatus.CONFIRMED}
OCCUPIED = frozenset({BookingStatus.CONFIRMED, BookingStatus.COMPLETED, BookingStatus.NO_SHOW})
CERTIFICATIONS = ("laser-safety", "rf-safety", "bsl1-biosafety", "machine-shop-basic", "high-voltage")
