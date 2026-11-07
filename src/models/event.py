"""Event model and event type enums for dynamic kitchen events."""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class EventType(str, Enum):
    """Event types processed by the kitchen engine."""
    ORDER = "ORDER"
    STOCK_OUT = "STOCK_OUT"
    STOCK_IN = "STOCK_IN"
    CANCEL = "CANCEL"
    HANDOFF = "HANDOFF"
    END_OF_DAY = "END_OF_DAY"

    @classmethod
    def from_str(cls, value: str) -> "EventType":
        if not value:
            raise ValueError("EventType cannot be empty")
        normalized = value.strip().upper().replace(" ", "_").replace("-", "_")
        return cls(normalized)


class CancellationSource(str, Enum):
    """Source requesting order cancellation."""
    CUSTOMER = "CUSTOMER"
    AGGREGATOR = "AGGREGATOR"
    AGGREGATOR_A = "AGGREGATOR_A"
    AGGREGATOR_B = "AGGREGATOR_B"
    KITCHEN = "KITCHEN"

    @classmethod
    def from_str(cls, value: str) -> "CancellationSource":
        if not value:
            return cls.CUSTOMER
        norm = value.strip().upper().replace(" ", "_").replace("-", "_")
        if "AGGREGATOR" in norm:
            return cls.AGGREGATOR
        if "KITCHEN" in norm:
            return cls.KITCHEN
        return cls.CUSTOMER


@dataclass
class Event:
    """Represents a discrete lifecycle or operational event."""
    event_id: str
    event_type: EventType
    timestamp: datetime
    order_id: Optional[str] = None
    kitchen_id: Optional[str] = None
    item_id: Optional[str] = None
    source: Optional[str] = None
    details: Optional[str] = None
