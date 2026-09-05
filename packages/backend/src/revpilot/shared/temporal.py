"""
RevPilot AI — Core Temporal Primitives
Enforces timezone-aware UTC datetime abstractions and bounded time windows.
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import re


@dataclass(frozen=True, slots=True, order=True)
class UtcDateTime:
    """
    Immutable value object guaranteeing UTC timezone.
    Rejects naive datetimes to prevent timezone bugs.
    """
    value: datetime

    def __post_init__(self) -> None:
        if not isinstance(self.value, datetime):
            raise TypeError(f"UtcDateTime value must be a datetime, got {type(self.value).__name__}")
        if self.value.tzinfo is None or self.value.tzinfo.utcoffset(self.value) is None:
            raise ValueError(f"UtcDateTime requires timezone-aware datetime, got naive datetime: {self.value}")
        if self.value.tzinfo != timezone.utc:
            # Normalize to UTC
            object.__setattr__(self, "value", self.value.astimezone(timezone.utc))

    @classmethod
    def now(cls) -> UtcDateTime:
        """Return current time in UTC."""
        return cls(datetime.now(timezone.utc))

    @classmethod
    def from_iso(cls, iso_str: str) -> UtcDateTime:
        """Parse ISO-8601 string and ensure UTC timezone."""
        if not isinstance(iso_str, str):
            raise TypeError(f"iso_str must be a str, got {type(iso_str).__name__}")
        # Standardize Z to +00:00 for fromisoformat compatibility in standard library
        cleaned = iso_str.strip()
        if cleaned.endswith("Z") or cleaned.endswith("z"):
            cleaned = cleaned[:-1] + "+00:00"
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            raise ValueError(f"ISO string must include timezone offset: {iso_str}")
        return cls(dt.astimezone(timezone.utc))

    @classmethod
    def from_datetime(cls, dt: datetime) -> UtcDateTime:
        """Construct from datetime, converting to UTC if aware."""
        return cls(dt)

    def as_datetime(self) -> datetime:
        """Return raw timezone-aware datetime object."""
        return self.value

    def isoformat(self) -> str:
        """Return canonical ISO-8601 string representation ending in Z."""
        return self.value.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    def __str__(self) -> str:
        return self.isoformat()

    def __repr__(self) -> str:
        return f"UtcDateTime({self.isoformat()!r})"


@dataclass(frozen=True, slots=True)
class TimeWindow:
    """
    Bounded time interval [start, end].
    Invariant: start <= end.
    """
    start: UtcDateTime
    end: UtcDateTime

    def __post_init__(self) -> None:
        if not isinstance(self.start, UtcDateTime):
            raise TypeError(f"start must be UtcDateTime, got {type(self.start).__name__}")
        if not isinstance(self.end, UtcDateTime):
            raise TypeError(f"end must be UtcDateTime, got {type(self.end).__name__}")
        if self.start.value > self.end.value:
            raise ValueError(
                f"Invalid TimeWindow: start ({self.start}) must precede or equal end ({self.end})"
            )

    def contains(self, dt: UtcDateTime) -> bool:
        """Return True if dt falls within [start, end] inclusive."""
        if not isinstance(dt, UtcDateTime):
            raise TypeError(f"dt must be UtcDateTime, got {type(dt).__name__}")
        return self.start.value <= dt.value <= self.end.value

    def duration_seconds(self) -> float:
        """Return total duration of the window in seconds."""
        return (self.end.value - self.start.value).total_seconds()
