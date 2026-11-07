"""Cancellation service implementing BR-08 lifecycle rules."""

from datetime import datetime
from typing import Optional, Tuple
from src.models import CancellationSource, Order, OrderStatus


class CancellationService:
    """Manages order cancellations, timing evaluation, and customer/aggregator charges (BR-08)."""

    @classmethod
    def cancel_order(
        cls,
        order: Order,
        cancellation_time: datetime,
        source: str = "CUSTOMER"
    ) -> Tuple[bool, float, str]:
        """
        BR-08:
        - Before any item starts preparation: cancellation is free.
        - After preparation starts: charge the customer for started items.
        - Aggregator cancellation after preparation starts charges the channel 100% of started-item value.
        - Edge Case 6: Cancellation at the exact instant the first item starts preparation
          is treated as after preparation starts (earliest_start <= cancellation_time).

        Returns: (success, charge_amount, message)
        """
        order.cancellation_time = cancellation_time
        order.cancellation_source = source
        order.status = OrderStatus.CANCELLED

        # Determine which items have started
        started_items = [
            it for it in order.items
            if it.prep_start_time is not None and it.prep_start_time <= cancellation_time
        ]

        if not started_items:
            # Cancelled before any preparation started: Free
            order.cancellation_charge = 0.0
            message = "Cancelled before preparation started (Free cancellation)"
            order.routing_reason = (order.routing_reason or "") + f" [{message}]"
            return True, 0.0, message

        # Preparation has started: calculate started item value
        started_value = sum(it.price for it in started_items)
        order.cancellation_charge = started_value

        norm_source = source.upper()
        if "AGGREGATOR" in norm_source:
            message = f"Cancelled after prep start by aggregator: Channel charged 100% of started items (Rs. {started_value:.2f})"
        else:
            message = f"Cancelled after prep start: Customer charged for started items (Rs. {started_value:.2f})"

        order.routing_reason = (order.routing_reason or "") + f" [{message}]"
        return True, started_value, message
