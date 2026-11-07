"""Order domain model with lifecycle statuses, channel economics, and RUSH evaluation."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional

from src.models.order_item import OrderItem


class Channel(str, Enum):
    """Ordering channel types and their fee parameters (BR-09)."""
    AGGREGATOR_A = "AGGREGATOR_A"
    AGGREGATOR_B = "AGGREGATOR_B"
    OWN_APP = "OWN_APP"

    @classmethod
    def from_str(cls, value: str) -> "Channel":
        if not value:
            raise ValueError("Channel cannot be empty")
        clean = value.strip().upper().replace(" ", "_").replace("-", "_")
        if clean in ("AGGREGATOR_A", "AGGREGATORA"):
            return cls.AGGREGATOR_A
        if clean in ("AGGREGATOR_B", "AGGREGATORB"):
            return cls.AGGREGATOR_B
        if clean in ("OWN_APP", "OWNAPP", "APP"):
            return cls.OWN_APP
        raise ValueError(f"Unknown channel: {value}")

    @property
    def commission_rate(self) -> float:
        """Commission rate as decimal fraction (BR-09)."""
        if self == Channel.AGGREGATOR_A:
            return 0.22
        if self == Channel.AGGREGATOR_B:
            return 0.18
        return 0.00

    @property
    def fixed_fee(self) -> float:
        """Fixed transaction fee in Rupees (BR-09)."""
        if self == Channel.OWN_APP:
            return 15.0
        return 0.0


class OrderStatus(str, Enum):
    """Order lifecycle status."""
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    ROUTED = "ROUTED"
    SCHEDULED = "SCHEDULED"
    PREPARING = "PREPARING"
    READY = "READY"
    DISPATCHED = "DISPATCHED"
    HANDED_OFF = "HANDED_OFF"
    DELIVERED = "DELIVERED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    LATE_RISK = "LATE_RISK"


@dataclass
class Order:
    """Customer order with items, routing outcome, scheduling timestamps, and priority metrics."""
    order_id: str
    brand_id: str
    items: List[OrderItem]
    channel: Channel
    delivery_zone: str
    order_time: datetime
    channel_priority: bool = False
    assigned_kitchen_id: Optional[str] = None
    routing_reason: Optional[str] = None
    projected_ready_time: Optional[datetime] = None
    promised_time: Optional[datetime] = None
    actual_handoff_time: Optional[datetime] = None
    late_risk: bool = False
    throttled_routing: bool = False
    rush_jumps_made: int = 0
    delayed_jumps_count: int = 0
    status: OrderStatus = OrderStatus.RECEIVED
    cancellation_time: Optional[datetime] = None
    cancellation_source: Optional[str] = None
    cancellation_charge: float = 0.0
    late_penalty: float = 0.0
    penalty_cost_centre: str = "BRAND"
    substitutions_applied: List[str] = field(default_factory=list)

    @property
    def gross_food_value(self) -> float:
        """Sum of prices across all active items."""
        return sum(item.price for item in self.items)

    @property
    def food_value(self) -> float:
        return self.gross_food_value

    @property
    def is_rush(self) -> bool:
        """BR-03: RUSH applies when channel priority flag is set or order value > ₹1,500."""
        return self.channel_priority or self.gross_food_value > 1500.0

    @property
    def item_count(self) -> int:
        return len(self.items)

    def earliest_item_start_time(self) -> Optional[datetime]:
        """Find the earliest preparation start time among all scheduled items."""
        starts = [it.prep_start_time for it in self.items if it.prep_start_time is not None]
        return min(starts) if starts else None

    def has_prep_started_at(self, at_time: datetime) -> bool:
        """
        Check if food preparation has begun at or before at_time.
        BR-08 / Edge case 6: The exact instant prep starts counts as started.
        """
        earliest = self.earliest_item_start_time()
        if earliest is None:
            return False
        return earliest <= at_time
