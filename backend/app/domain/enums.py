from enum import StrEnum


class Role(StrEnum):
    STUDENT = "student"
    FACULTY = "faculty"
    ADMIN = "lab_admin"


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    PENDING = "pending_approval"
    CONTESTED = "contested"
    DECLINED = "declined"
    REALLOCATED = "reallocated"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class ProjectType(StrEnum):
    CAPSTONE = "capstone"
    RESEARCH = "research"
    COURSE = "course_lab"
    COMPETITION = "competition"
    PERSONAL = "personal"


class Category(StrEnum):
    MEASUREMENT = "measurement"
    DEV_KIT = "dev_kit"
    WORKSTATION = "workstation"
    FABRICATION = "fabrication"
    BIO = "bio"
    MECHANICAL = "mechanical_testing"
    COMPUTING = "computing"
    ELECTRONICS = "electronics"
