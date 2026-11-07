"""Batch domain model for grouped cooking operations (BR-02)."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
from src.models.order_item import OrderItem
from src.models.station import StationType


@dataclass
class Batch:
    """Represents a scheduled batch of items sharing a recipe and station slot."""
    batch_id: str
    recipe_id: str
    station_type: StationType
    max_batch_size: int
    first_order_time: datetime
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    slot_id: Optional[int] = None
    items: List[OrderItem] = field(default_factory=list)

    @property
    def current_size(self) -> int:
        return len(self.items)

    @property
    def is_full(self) -> bool:
        return len(self.items) >= self.max_batch_size

    def can_batch_with(self, recipe_id: str, order_time: datetime) -> bool:
        """
        BR-02: Identical recipes on the same station placed within 3 minutes
        may batch into one slot, up to the recipe batch size.
        Exact 3-minute boundary (<= 180 seconds) is treated as within window.
        """
        if self.is_full:
            return False
        if self.recipe_id != recipe_id:
            return False
        delta_seconds = abs((order_time - self.first_order_time).total_seconds())
        return delta_seconds <= 180.0
