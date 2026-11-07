"""Delivery zone model specifying transit time and eligible kitchen coverage."""

from dataclasses import dataclass, field
from typing import Set


@dataclass(frozen=True)
class DeliveryZone:
    """Geographic sector with delivery duration and list of eligible kitchens."""
    zone_id: str
    delivery_minutes: int
    eligible_kitchen_ids: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.delivery_minutes < 0:
            raise ValueError(f"delivery_minutes cannot be negative: {self.delivery_minutes}")

    def serves_kitchen(self, kitchen_id: str) -> bool:
        return kitchen_id.strip().upper() in {k.strip().upper() for k in self.eligible_kitchen_ids}
