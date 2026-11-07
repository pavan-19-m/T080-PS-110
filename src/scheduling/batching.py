"""Batching engine grouping identical recipes into station slots (BR-02)."""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from src.models import OrderItem, Recipe, StationType


@dataclass
class ScheduledBatch:
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
        Handle the exact 3-minute boundary (<= 180 seconds).
        """
        if self.is_full:
            return False
        if self.recipe_id != recipe_id:
            return False
        delta_seconds = abs((order_time - self.first_order_time).total_seconds())
        return delta_seconds <= 180.0


class BatchingEngine:
    """Manages active batches within a scheduling session."""

    def __init__(self):
        self.active_batches: List[ScheduledBatch] = []
        self._batch_counter = 0

    def find_or_create_batch(
        self,
        item: OrderItem,
        recipe: Recipe,
        order_time: datetime
    ) -> ScheduledBatch:
        """Find an existing batch within 3 min window or create a new one."""
        # Only batch if max_batch_size > 1
        if recipe.max_batch_size > 1:
            for b in self.active_batches:
                if b.can_batch_with(recipe.recipe_id, order_time):
                    b.items.append(item)
                    item.batch_id = b.batch_id
                    return b

        # Create new batch
        self._batch_counter += 1
        new_batch = ScheduledBatch(
            batch_id=f"BATCH-{self._batch_counter:04d}",
            recipe_id=recipe.recipe_id,
            station_type=recipe.station_type,
            max_batch_size=recipe.max_batch_size,
            first_order_time=order_time,
            items=[item],
        )
        item.batch_id = new_batch.batch_id
        if recipe.max_batch_size > 1:
            self.active_batches.append(new_batch)
        return new_batch
