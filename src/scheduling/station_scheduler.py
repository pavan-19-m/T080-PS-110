"""Station scheduler simulating and committing station slot allocations (BR-02, BR-04)."""

import copy
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from src.models import (
    Kitchen,
    Order,
    OrderItem,
    Recipe,
    SlotBooking,
    Station,
    StationSlot,
    StationType,
)
from src.scheduling.batching import BatchingEngine, ScheduledBatch
from src.scheduling.dependency_manager import DependencyManager


@dataclass
class ScheduleOutcome:
    """Result of scheduling an order on a kitchen."""
    kitchen_id: str
    ready_time: datetime
    item_schedules: List[Tuple[str, datetime, datetime, int, Optional[str]]]
    # (order_item_id, start_time, end_time, slot_id, batch_id)


class StationScheduler:
    """Allocates kitchen station slots respecting capacity, duration, batching, and dependencies."""

    PACKAGING_MINUTES: int = 3

    def __init__(self, batching_engine: Optional[BatchingEngine] = None):
        self.batching_engine = batching_engine or BatchingEngine()

    def simulate_order(
        self,
        kitchen: Kitchen,
        order: Order,
        recipes: Dict[str, Recipe]
    ) -> ScheduleOutcome:
        """
        Simulate order execution on a shallow clone of the kitchen's stations
        to determine projected ready time without mutating real kitchen state.
        """
        cloned_kitchen = copy.deepcopy(kitchen)
        sim_batching = copy.deepcopy(self.batching_engine)
        sim_scheduler = StationScheduler(batching_engine=sim_batching)
        return sim_scheduler.commit_order(cloned_kitchen, order, recipes, persist=False)

    def commit_order(
        self,
        kitchen: Kitchen,
        order: Order,
        recipes: Dict[str, Recipe],
        persist: bool = True
    ) -> ScheduleOutcome:
        """
        Schedule all items in the order across required stations.
        If persist=True, slot bookings and order items are updated directly.
        """
        ordered_items = DependencyManager.sort_items_by_dependency(order.items, recipes)
        item_schedules: List[Tuple[str, datetime, datetime, int, Optional[str]]] = []
        max_item_finish = order.order_time

        item_finish_map: Dict[str, datetime] = {}

        for item in ordered_items:
            recipe = recipes[item.recipe_id]
            st_type = recipe.station_type

            if st_type not in kitchen.stations:
                raise ValueError(f"Kitchen {kitchen.kitchen_id} missing station {st_type}")

            station = kitchen.stations[st_type]
            if not station.slots:
                raise ValueError(f"Station {st_type} in {kitchen.kitchen_id} has zero slots")

            # Check predecessor dependencies in this order (BR-04)
            earliest_possible_start = order.order_time
            if recipe.has_dependency:
                dep_recipe_id = recipe.dependency_recipe_id
                for scheduled_item in ordered_items:
                    if (scheduled_item.recipe_id == dep_recipe_id 
                            and scheduled_item.order_item_id in item_finish_map):
                        dep_finish = item_finish_map[scheduled_item.order_item_id]
                        if dep_finish > earliest_possible_start:
                            earliest_possible_start = dep_finish

            # Evaluate batching (BR-02)
            batch: ScheduledBatch = self.batching_engine.find_or_create_batch(
                item, recipe, order.order_time
            )

            # If this batch already has an allocated slot and timing, piggyback on it
            if batch.start_time is not None and batch.end_time is not None and batch.slot_id is not None:
                start_time = batch.start_time
                end_time = batch.end_time
                best_slot_id = batch.slot_id
            else:
                # Find earliest slot across all station slots
                best_start = None
                best_slot = None

                for slot in station.slots:
                    slot_start = slot.find_earliest_start(
                        min_start=earliest_possible_start,
                        duration_minutes=recipe.prep_minutes
                    )
                    if best_start is None or slot_start < best_start:
                        best_start = slot_start
                        best_slot = slot

                start_time = best_start
                end_time = start_time + timedelta(minutes=recipe.prep_minutes)
                best_slot_id = best_slot.slot_id

                # Update batch details
                batch.start_time = start_time
                batch.end_time = end_time
                batch.slot_id = best_slot_id

                # Book the slot
                if persist:
                    booking = SlotBooking(
                        booking_id=f"BOOK-{order.order_id}-{item.order_item_id}",
                        item_id=item.item_id,
                        order_id=order.order_id,
                        recipe_id=recipe.recipe_id,
                        start_time=start_time,
                        end_time=end_time,
                        batch_id=batch.batch_id,
                    )
                    best_slot.bookings.append(booking)

            item_finish_map[item.order_item_id] = end_time
            if end_time > max_item_finish:
                max_item_finish = end_time

            if persist:
                item.prep_start_time = start_time
                item.prep_end_time = end_time
                item.slot_id = best_slot_id
                item.batch_id = batch.batch_id

            item_schedules.append((
                item.order_item_id,
                start_time,
                end_time,
                best_slot_id,
                batch.batch_id
            ))

        # BR-04: Ready time is max item completion time + 3 minutes packaging
        projected_ready = max_item_finish + timedelta(minutes=self.PACKAGING_MINUTES)

        if persist:
            order.projected_ready_time = projected_ready

        return ScheduleOutcome(
            kitchen_id=kitchen.kitchen_id,
            ready_time=projected_ready,
            item_schedules=item_schedules,
        )
