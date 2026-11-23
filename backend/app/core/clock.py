from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Provide the time source used by scheduling and request handling."""

    def now(self) -> datetime:
        """Return the current instant as a timezone-aware datetime."""
        ...


class SystemClock:
    """Provide the current time from the system clock."""

    def now(self) -> datetime:
        """Return the current system time in UTC."""
        return datetime.now(UTC)


@dataclass(frozen=True)
class FixedClock:
    """Provide a stable time for deterministic tests."""

    value: datetime

    def now(self) -> datetime:
        """Return the configured test instant."""
        return self.value
