"""Event service processing stock-outs, cancellations, and hand-off lifecycle events."""

from datetime import datetime
from typing import Dict, List, Optional, Tuple

from src.accounting.penalty_calculator import PenaltyCalculator
from src.models import (
    Event,
    EventType,
    Kitchen,
    Order,
    OrderStatus,
)
from src.services.cancellation_service import CancellationService


class EventService:
    """Processes discrete operational events modifying kitchen state or order lifecycles."""

    def __init__(
        self,
        kitchens: Dict[str, Kitchen],
        orders: Dict[str, Order],
    ):
        self.kitchens = kitchens
        self.orders = orders
        self.event_log: List[str] = []

    def handle_event(self, event: Event) -> str:
        """Process an individual event and update kitchen or order domain models."""
        msg = ""
        if event.event_type == EventType.STOCK_OUT:
            if event.kitchen_id and event.kitchen_id in self.kitchens and event.item_id:
                self.kitchens[event.kitchen_id].stock_out.add(event.item_id)
                msg = f"STOCK_OUT: Kitchen {event.kitchen_id} marked item {event.item_id} out of stock"

        elif event.event_type == EventType.STOCK_IN:
            if event.kitchen_id and event.kitchen_id in self.kitchens and event.item_id:
                self.kitchens[event.kitchen_id].stock_out.discard(event.item_id)
                msg = f"STOCK_IN: Kitchen {event.kitchen_id} restored stock for item {event.item_id}"

        elif event.event_type == EventType.CANCEL:
            if event.order_id and event.order_id in self.orders:
                order = self.orders[event.order_id]
                source = event.source or "CUSTOMER"
                _, charge, detail = CancellationService.cancel_order(
                    order=order,
                    cancellation_time=event.timestamp,
                    source=source,
                )
                msg = f"CANCEL: Order {order.order_id} cancelled by {source} (Charge: Rs. {charge:.2f}) - {detail}"
            else:
                msg = f"CANCEL: Order {event.order_id} not found"

        elif event.event_type == EventType.HANDOFF:
            if event.order_id and event.order_id in self.orders:
                order = self.orders[event.order_id]
                order.status = OrderStatus.HANDED_OFF
                order.actual_handoff_time = event.timestamp
                penalty = PenaltyCalculator.apply_penalty_to_order(order, event.timestamp)
                msg = (
                    f"HANDOFF: Order {order.order_id} handed off at {event.timestamp.strftime('%H:%M:%S')} "
                    f"(Penalty: Rs. {penalty:.2f}, Cost Centre: {order.penalty_cost_centre})"
                )
            else:
                msg = f"HANDOFF: Order {event.order_id} not found"

        elif event.event_type == EventType.END_OF_DAY:
            msg = f"END_OF_DAY: Day cycle closed at {event.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"

        else:
            msg = f"UNKNOWN: Event {event.event_type} ignored"

        self.event_log.append(f"[{event.timestamp.strftime('%H:%M:%S')}] {msg}")
        return msg

    def process_all_events(self, events: List[Event]) -> List[str]:
        """Process chronological event stream."""
        sorted_events = sorted(events, key=lambda e: e.timestamp)
        results: List[str] = []
        for ev in sorted_events:
            results.append(self.handle_event(ev))
        return results
