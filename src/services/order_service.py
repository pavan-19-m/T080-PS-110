"""Order service coordinating end-to-end processing pipeline following BR-12 precedence."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.accounting.accounting_engine import AccountingEngine, OrderFinancials
from src.models import (
    Brand,
    DeliveryZone,
    Event,
    Kitchen,
    MenuItem,
    Order,
    OrderStatus,
    Recipe,
)
from src.routing.order_router import OrderRouter, RoutingEvaluation
from src.scheduling.order_sequencer import OrderSequencer
from src.scheduling.station_scheduler import ScheduleOutcome, StationScheduler
from src.services.cancellation_service import CancellationService
from src.services.event_service import EventService
from src.services.substitution_service import SubstitutionService


@dataclass
class ProcessedOrderRecord:
    """Full execution outcome for an order including routing, scheduling, and accounting."""
    order: Order
    routing: RoutingEvaluation
    schedule: Optional[ScheduleOutcome]
    financials: OrderFinancials


class OrderService:
    """End-to-end orchestrator for the cloud kitchen engine."""

    def __init__(
        self,
        kitchens: Dict[str, Kitchen],
        brands: Dict[str, Brand],
        menu_items: Dict[str, MenuItem],
        recipes: Dict[str, Recipe],
        zones: Dict[str, DeliveryZone],
        router: Optional[OrderRouter] = None,
        scheduler: Optional[StationScheduler] = None,
        substitutions: Optional[Dict[Tuple[str, str], str]] = None,
    ):
        self.kitchens = kitchens
        self.brands = brands
        self.menu_items = menu_items
        self.recipes = recipes
        self.zones = zones
        self.scheduler = scheduler or StationScheduler()
        self.router = router or OrderRouter(scheduler=self.scheduler)
        self.substitution_service = SubstitutionService(
            substitutions=substitutions or {},
            menu_items=menu_items,
        )
        self.order_lookup: Dict[str, Order] = {}
        self.event_service = EventService(
            kitchens=self.kitchens,
            orders=self.order_lookup,
        )

    def process_all_orders(
        self,
        orders: List[Order],
        events: Optional[List[Event]] = None
    ) -> List[ProcessedOrderRecord]:
        """
        Execute pipeline according to BR-12 execution precedence:
        1. Eligibility
        2. Throttling
        3. Routing based on projected ready time
        4. Order sequencing (RUSH jumps)
        5. Batching
        6. Dependency scheduling
        7. Promised-time calculation
        (Substitution happens before scheduling).
        """
        # Register in lookup for event handling
        for o in orders:
            self.order_lookup[o.order_id] = o

        # Process any pre-routing stock-out events if provided
        if events:
            pre_events = [e for e in events if e.event_type.value in ("STOCK_OUT", "STOCK_IN")]
            self.event_service.process_all_events(pre_events)

        # 4. Order Sequencing with RUSH Priority Jumps (BR-03)
        sequenced = OrderSequencer.sequence_orders(orders)

        results: List[ProcessedOrderRecord] = []

        # Process each order through the pipeline
        for order in sequenced:
            zone = self.zones.get(order.delivery_zone)
            if not zone:
                raise ValueError(f"Delivery zone {order.delivery_zone} not found for order {order.order_id}")

            # 1, 2, 3: Routing evaluation (Eligibility, Throttling, Projected ready time)
            routing_eval = self.router.route_order(
                order=order,
                all_kitchens=self.kitchens,
                zone=zone,
                recipes=self.recipes
            )

            schedule_outcome: Optional[ScheduleOutcome] = None
            if routing_eval.selected_kitchen_id:
                selected_kitchen = self.kitchens[routing_eval.selected_kitchen_id]

                # BR-07: Substitution occurs before scheduling
                can_proceed = self.substitution_service.apply_substitutions_for_kitchen(
                    order=order,
                    kitchen=selected_kitchen,
                    recipes=self.recipes,
                )

                if can_proceed:
                    # 5 & 6: Commit scheduling with batching (BR-02) and dependencies (BR-04)
                    schedule_outcome = self.scheduler.commit_order(
                        kitchen=selected_kitchen,
                        order=order,
                        recipes=self.recipes,
                        persist=True
                    )
                    order.status = OrderStatus.SCHEDULED
                    # 7: Re-evaluate promised delivery time
                    order.promised_time = self.router.calculate_promised_time(
                        order.projected_ready_time, zone.delivery_minutes
                    )
                    routing_eval.projected_ready_time = order.projected_ready_time
                    routing_eval.promised_time = order.promised_time

            # Accounting breakdown (BR-09, BR-10)
            financials = AccountingEngine.calculate_order_financials(order)

            results.append(
                ProcessedOrderRecord(
                    order=order,
                    routing=routing_eval,
                    schedule=schedule_outcome,
                    financials=financials,
                )
            )

        # Process post-scheduling lifecycle events (cancellations, hand-offs)
        if events:
            post_events = [e for e in events if e.event_type.value in ("CANCEL", "HANDOFF", "END_OF_DAY")]
            self.event_service.process_all_events(post_events)
            # Refresh order financials after cancellations and hand-offs
            for r in results:
                r.financials = AccountingEngine.calculate_order_financials(r.order)

        return results
