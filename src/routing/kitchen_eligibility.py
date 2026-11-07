"""Kitchen eligibility checker enforcing BR-01 requirements."""

from datetime import datetime
from typing import Dict, List, Set

from src.models import DeliveryZone, Kitchen, Order, Recipe, StationType


class KitchenEligibilityChecker:
    """Evaluates whether physical cloud kitchens meet all BR-01 eligibility criteria."""

    @staticmethod
    def get_required_stations(order: Order, recipes: Dict[str, Recipe]) -> Set[StationType]:
        """Extract all culinary workstation types required by an order's items."""
        required: Set[StationType] = set()
        for it in order.items:
            rec = recipes.get(it.recipe_id)
            if rec:
                required.add(rec.station_type)
        return required

    @classmethod
    def is_eligible(
        cls,
        kitchen: Kitchen,
        order: Order,
        zone: DeliveryZone,
        recipes: Dict[str, Recipe]
    ) -> bool:
        """
        BR-01: A kitchen is eligible only if:
        1. It serves the requested brand.
        2. It is listed in the delivery zone's eligible kitchen list.
        3. It is open at the order timestamp.
        4. It has all required stations with positive capacity.
        """
        # 1. Delivery zone inclusion
        if not zone.serves_kitchen(kitchen.kitchen_id):
            return False

        # 2. Brand partnership
        if not kitchen.supports_brand(order.brand_id):
            return False

        # 3. Operating hours check
        if not kitchen.is_operating_at(order.order_time):
            return False

        # 4. Station capability check
        required_stations = cls.get_required_stations(order, recipes)
        if not kitchen.has_all_stations(required_stations):
            return False

        return True

    @classmethod
    def find_eligible_kitchens(
        cls,
        order: Order,
        all_kitchens: Dict[str, Kitchen],
        zone: DeliveryZone,
        recipes: Dict[str, Recipe]
    ) -> List[Kitchen]:
        """Return list of all kitchens meeting the BR-01 criteria."""
        return [
            k for k in all_kitchens.values()
            if cls.is_eligible(k, order, zone, recipes)
        ]
