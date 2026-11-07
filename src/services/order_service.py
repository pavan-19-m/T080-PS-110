"""Order service coordinating end-to-end processing pipeline."""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

from src.accounting.accounting_engine import AccountingEngine, OrderFinancials
from src.models import (
    Brand,
    DeliveryZone,
    Kitchen,
    MenuItem,
    Order,
    OrderStatus,
    Recipe,
)
from src.routing.order_router import OrderRouter, RoutingEvaluation
from src.scheduling.order_sequencer import OrderSequencer
from src.scheduling.scheduler import ScheduleOutcome, StationScheduler


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
        scheduler: Optional[StationScheduler] = None
    ):
        self.kitchens = kitchens
        self.brands = brands
        self.menu_items = menu_items
        self.recipes = recipes
        self.zones = zones
        self.scheduler = scheduler or StationScheduler()
        self.router = router or OrderRouter(scheduler=self.scheduler)

    def process_all_orders(self, orders: List[Order]) -> List[ProcessedOrderRecord]:
        """Execute sequencing, routing, station scheduling, and financial calculation."""
        # 1. Order Sequencing with RUSH Priority Jumps (BR-03)
        sequenced = OrderSequencer.sequence_orders(orders)

        results: List[ProcessedOrderRecord] = []

        # 2. Sequential Execution for Each Order
        for order in sequenced:
            zone = self.zones.get(order.delivery_zone)
            if not zone:
                raise ValueError(f"Delivery zone {order.delivery_zone} not found for order {order.order_id}")

            # Routing evaluation (BR-01, BR-05, BR-06)
            routing_eval = self.router.route_order(
                order=order,
                all_kitchens=self.kitchens,
                zone=zone,
                recipes=self.recipes
            )

            schedule_outcome: Optional[ScheduleOutcome] = None
            if routing_eval.selected_kitchen_id:
                selected_kitchen = self.kitchens[routing_eval.selected_kitchen_id]
                # Commit the actual schedule bookings onto the selected kitchen
                schedule_outcome = self.scheduler.commit_order(
                    kitchen=selected_kitchen,
                    order=order,
                    recipes=self.recipes,
                    persist=True
                )
                order.status = OrderStatus.SCHEDULED

            # Accounting breakdown (BR-09)
            financials = AccountingEngine.calculate_order_financials(order)

            results.append(
                ProcessedOrderRecord(
                    order=order,
                    routing=routing_eval,
                    schedule=schedule_outcome,
                    financials=financials,
                )
            )

        return results
