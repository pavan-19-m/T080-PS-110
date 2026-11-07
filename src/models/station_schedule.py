"""Station schedule domain model representing workstation timeline allocations."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import List, Optional
from src.models.station import StationType


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
    slot_id: int = 1

    @property
    def duration_minutes(self) -> float:
        return (self.end_time - self.start_time).total_seconds() / 60.0


@dataclass
class StationSlot:
    """Individual concurrency slot inside a workstation."""
    slot_id: int
    bookings: List[SlotBooking] = field(default_factory=list)

    def is_available(self, start_time: datetime, end_time: datetime) -> bool:
        """Check if this slot is free during [start_time, end_time)."""
        for b in self.bookings:
            if start_time < b.end_time and end_time > b.start_time:
                return False
        return True

    def find_earliest_start(self, min_start: datetime, duration_minutes: int) -> datetime:
        """Find earliest time >= min_start where duration_minutes is free."""
        duration = timedelta(minutes=duration_minutes)
        if not self.bookings:
            return min_start

        candidate = min_start
        sorted_bookings = sorted(self.bookings, key=lambda b: b.start_time)
        for b in sorted_bookings:
            if candidate + duration <= b.start_time:
                return candidate
            if candidate < b.end_time:
                candidate = b.end_time
        return candidate


@dataclass
class StationSchedule:
    """Overall schedule and timeline for a kitchen station across all slots."""
    kitchen_id: str
    station_type: StationType
    capacity: int
    slots: List[StationSlot] = field(default_factory=list)

    def __post_init__(self):
        if not self.slots and self.capacity > 0:
            self.slots = [StationSlot(slot_id=i + 1) for i in range(self.capacity)]

    @property
    def total_bookings(self) -> int:
        return sum(len(slot.bookings) for slot in self.slots)

    def get_all_bookings(self) -> List[SlotBooking]:
        all_b: List[SlotBooking] = []
        for slot in self.slots:
            all_b.extend(slot.bookings)
        return sorted(all_b, key=lambda b: b.start_time)
