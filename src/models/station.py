"""Station models and StationType definitions."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import List, Optional


class StationType(str, Enum):
    """Culinary workstation types in physical cloud kitchens."""
    GRILL = "GRILL"
    FRYER = "FRYER"
    WOK = "WOK"
    COLD = "COLD"
    BAKERY = "BAKERY"

    @classmethod
    def from_str(cls, value: str) -> "StationType":
        if not value:
            raise ValueError("StationType cannot be empty")
        return cls(value.strip().upper())


@dataclass
class SlotBooking:
    """Represents a scheduled block of time on an individual station slot."""
    booking_id: str
    item_id: str
    order_id: str
    recipe_id: str
    start_time: datetime
    end_time: datetime
    batch_id: Optional[str] = None


@dataclass
class StationSlot:
    """Individual concurrency slot inside a workstation."""
    slot_id: int
    bookings: List[SlotBooking] = field(default_factory=list)

    def is_available(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if this slot is free during [start_time, end_time)."""
        for b in self.bookings:
            # Overlap condition: start < b.end and end > b.start
            if start_time < b.end_time and end_time > b.start_time:
                return False
        return True

    def find_earliest_start(self, min_start: datetime, duration_minutes: int) -> datetime:
        """Find earliest time >= min_start where duration_minutes is free."""
        duration = timedelta(minutes=duration_minutes)
        if not self.bookings:
            return min_start

        # Check at min_start
        candidate = min_start
        # Sort bookings by start time
        sorted_bookings = sorted(self.bookings, key=lambda b: b.start_time)
        for b in sorted_bookings:
            candidate_end = candidate + duration
            if candidate_end <= b.start_time:
                return candidate
            if candidate < b.end_time:
                candidate = max(candidate, b.end_time)
        return candidate

    def remaining_busy_minutes(self, at_time: datetime) -> float:
        """Return total minutes of booked work that are active or future relative to at_time."""
        total = 0.0
        for b in self.bookings:
            if b.end_time > at_time:
                effective_start = max(b.start_time, at_time)
                total += (b.end_time - effective_start).total_seconds() / 60.0
        return total


@dataclass
class Station:
    """A physical workstation inside a kitchen with a configured slot capacity."""
    station_type: StationType
    capacity: int
    slots: List[StationSlot] = field(default_factory=list)

    def __post_init__(self):
        if not self.slots and self.capacity > 0:
            self.slots = [StationSlot(slot_id=i + 1) for i in range(self.capacity)]

    def get_remaining_load(self, at_time: datetime) -> float:
        """Total remaining busy minutes across all slots at at_time."""
        return sum(slot.remaining_busy_minutes(at_time) for slot in self.slots)
