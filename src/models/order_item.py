"""OrderItem model representing an ordered item in an order."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class OrderItem:
    """An individual line item within an order undergoing preparation."""
    order_item_id: str
    order_id: str
    item_id: str
    price: float
    recipe_id: str
    brand_id: Optional[str] = None
    prep_start_time: Optional[datetime] = None
    prep_end_time: Optional[datetime] = None
    slot_id: Optional[int] = None
    batch_id: Optional[str] = None

    @property
    def is_scheduled(self) -> bool:
        return self.prep_start_time is not None and self.prep_end_time is not None
