"""Order routing engine implementing BR-01, BR-05, and BR-06."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple

from src.models import (
    DeliveryZone,
    Kitchen,
    Order,
    OrderStatus,
    Recipe,
    StationType,
)
from src.scheduling.scheduler import ScheduleOutcome, StationScheduler


@dataclass
class RoutingEvaluation:
    """Detailed evaluation result of routing an order."""
    selected_kitchen_id: Optional[str]
    routing_reason: str
    projected_ready_time: Optional[datetime]
    promised_time: Optional[datetime]
    late_risk: bool = False
    throttled_routing: bool = False


class OrderRouter:
    """Evaluates kitchen eligibility, ready times, throttling, and routing selection."""

    LATE_RISK_THRESHOLD_MINUTES: int = 45
    REROUTE_SAVING_THRESHOLD_MINUTES: int = 10
    THROTTLE_TRIGGER_MINUTES: int = 60
    THROTTLE_CLEAR_MINUTES: int = 40
    DELIVERY_BUFFER_MINUTES: int = 5

    def __init__(self, scheduler: Optional[StationScheduler] = None):
        self.scheduler = scheduler or StationScheduler()

    @staticmethod
    def calculate_promised_time(ready_time: datetime, delivery_minutes: int) -> datetime:
        """
        BR-05: Promised time = ready time + delivery-zone delivery minutes + 5-minute buffer,
        rounded UP to the next 5-minute boundary.
        """
        raw = ready_time + timedelta(minutes=delivery_minutes + OrderRouter.DELIVERY_BUFFER_MINUTES)
        minute = raw.minute
        second = raw.second
        micro = raw.microsecond

        # Check if already exact 5-minute boundary
        if minute % 5 == 0 and second == 0 and micro == 0:
            return raw

        add_minutes = 5 - (minute % 5)
        rounded = raw.replace(second=0, microsecond=0) + timedelta(minutes=add_minutes)
        return rounded

    def find_eligible_kitchens(
        self,
        order: Order,
        all_kitchens: Dict[str, Kitchen],
        zone: DeliveryZone,
        recipes: Dict[str, Recipe]
    ) -> List[Kitchen]:
        """
        BR-01: A kitchen is eligible only if:
        1. It serves the brand.
        2. It is listed in the delivery zone's kitchen list.
        3. It is operating at the order time.
        4. It has every required station.
        """
        required_stations: Set[StationType] = set()
        for it in order.items:
            rec = recipes.get(it.recipe_id)
            if rec:
                required_stations.add(rec.station_type)

        eligible: List[Kitchen] = []
        for k_id, kitchen in all_kitchens.items():
            # Check delivery zone inclusion
            if not zone.serves_kitchen(k_id):
                continue
            # Check brand partnership
            if not kitchen.supports_brand(order.brand_id):
                continue
            # Check operating hours
            if not kitchen.is_operating_at(order.order_time):
                continue
            # Check required stations
            if not kitchen.has_all_stations(required_stations):
                continue

            # Check BR-06 Throttling: Throttled kitchen accepts ONLY if it is sole eligible kitchen
            # We first collect all physically eligible kitchens, then filter throttled kitchens if non-throttled exist
            eligible.append(kitchen)

        return eligible

    def filter_throttling(
        self,
        eligible: List[Kitchen],
        at_time: datetime
    ) -> List[Kitchen]:
        """
        BR-06: A throttled kitchen accepts only orders for which it is the sole eligible kitchen.
        If non-throttled eligible kitchens exist, throttled kitchens are excluded.
        Also clears throttling if load falls below 40 minutes.
        """
        # First check clearance of throttling
        for k in eligible:
            if k.is_throttled:
                curr_load = k.get_current_load(at_time)
                if curr_load < self.THROTTLE_CLEAR_MINUTES:
                    k.is_throttled = False

        non_throttled = [k for k in eligible if not k.is_throttled]
        if non_throttled:
            return non_throttled

        # If only throttled kitchens exist, they may accept because it's sole eligible pool
        return eligible

    def route_order(
        self,
        order: Order,
        all_kitchens: Dict[str, Kitchen],
        zone: DeliveryZone,
        recipes: Dict[str, Recipe]
    ) -> RoutingEvaluation:
        """
        Full routing execution according to BR-01, BR-05, and BR-06.
        """
        raw_eligible = self.find_eligible_kitchens(order, all_kitchens, zone, recipes)
        if not raw_eligible:
            return RoutingEvaluation(
                selected_kitchen_id=None,
                routing_reason="No eligible kitchen found meeting brand, zone, operating hours, and station criteria",
                projected_ready_time=None,
                promised_time=None,
            )

        # Apply BR-06 throttling filtering
        filtered_eligible = self.filter_throttling(raw_eligible, order.order_time)

        # Simulate ready time and load for each eligible candidate
        candidates: List[Tuple[Kitchen, ScheduleOutcome, float]] = []
        for kitchen in filtered_eligible:
            sim_outcome = self.scheduler.simulate_order(kitchen, order, recipes)
            load = kitchen.get_current_load(order.order_time)
            candidates.append((kitchen, sim_outcome, load))

        # BR-01: Lowest projected ready time, then lowest current load, then lowest kitchen ID
        candidates.sort(key=lambda c: (c[1].ready_time, c[2], c[0].kitchen_id))

        best_kitchen, best_outcome, _ = candidates[0]
        selected_kitchen = best_kitchen
        final_ready_time = best_outcome.ready_time
        routing_reason = (
            f"Selected by lowest projected ready time ({best_outcome.ready_time.strftime('%H:%M:%S')}), "
            f"load tie-break, ID {best_kitchen.kitchen_id}"
        )
        late_risk = False
        throttled_routing = best_kitchen.is_throttled

        # BR-05: Late Risk & Reroute Evaluation
        time_to_ready_minutes = (final_ready_time - order.order_time).total_seconds() / 60.0
        if time_to_ready_minutes > self.LATE_RISK_THRESHOLD_MINUTES:
            # Check alternative kitchens
            alternative_found = False
            for alt_kitchen, alt_outcome, _ in candidates[1:]:
                saving = (final_ready_time - alt_outcome.ready_time).total_seconds() / 60.0
                if saving >= self.REROUTE_SAVING_THRESHOLD_MINUTES:
                    selected_kitchen = alt_kitchen
                    final_ready_time = alt_outcome.ready_time
                    routing_reason = (
                        f"Rerouted to {alt_kitchen.kitchen_id} to reduce ready time by {saving:.1f}m (>=10m threshold)"
                    )
                    alternative_found = True
                    throttled_routing = alt_kitchen.is_throttled
                    break

            if not alternative_found:
                late_risk = True
                routing_reason += f" [Accepted with LATE_RISK: prep time {time_to_ready_minutes:.1f}m > 45m]"

        # BR-06: Throttling Trigger Check on Selected Kitchen
        new_ready_delay = (final_ready_time - order.order_time).total_seconds() / 60.0
        if new_ready_delay > self.THROTTLE_TRIGGER_MINUTES:
            selected_kitchen.is_throttled = True

        # Calculate promised time
        promised_time = self.calculate_promised_time(final_ready_time, zone.delivery_minutes)

        # Update order entity
        order.assigned_kitchen_id = selected_kitchen.kitchen_id
        order.routing_reason = routing_reason
        order.projected_ready_time = final_ready_time
        order.promised_time = promised_time
        order.late_risk = late_risk
        order.throttled_routing = throttled_routing
        order.status = OrderStatus.ROUTED

        return RoutingEvaluation(
            selected_kitchen_id=selected_kitchen.kitchen_id,
            routing_reason=routing_reason,
            projected_ready_time=final_ready_time,
            promised_time=promised_time,
            late_risk=late_risk,
            throttled_routing=throttled_routing,
        )
