"""Substitution service implementing BR-07 stock-outs and substitutions."""

from typing import Dict, List, Optional, Tuple
from src.models import Brand, Kitchen, MenuItem, Order, OrderItem, OrderStatus, Recipe


class SubstitutionService:
    """Handles item stock-out verification, brand substitutions, repricing and cancellations."""

    PRICE_TOLERANCE_RUPEES: float = 20.0

    def __init__(
        self,
        substitutions: Optional[Dict[Tuple[str, str], str]] = None,
        menu_items: Optional[Dict[str, MenuItem]] = None,
    ):
        # substitutions key: (brand_id, original_item_id) -> substitute_item_id
        self.substitutions = substitutions or {}
        self.menu_items = menu_items or {}

    def apply_substitutions_for_kitchen(
        self,
        order: Order,
        kitchen: Kitchen,
        recipes: Dict[str, Recipe]
    ) -> bool:
        """
        BR-07:
        - If an item is unavailable (kitchen.stock_out), check the brand's substitution table.
        - Allow a substitute if its price is within ₹20 of the original item (<= 20.0).
        - Exactly ₹20 difference is allowed (Edge Case 5).
        - If no acceptable substitute exists, remove the unavailable item and reprice.
        - If no items remain, cancel the order.

        Returns True if order still has items and can proceed, False if cancelled.
        """
        if not kitchen.stock_out:
            return True

        retained_items: List[OrderItem] = []
        for line in order.items:
            if line.item_id not in kitchen.stock_out:
                retained_items.append(line)
                continue

            # Item is stocked out at this kitchen
            sub_key = (order.brand_id, line.item_id)
            sub_item_id = self.substitutions.get(sub_key)
            sub_menu_item = self.menu_items.get(sub_item_id) if sub_item_id else None

            # Check if substitute exists and price difference is within ₹20
            # BR-07: within ₹20 of the original item; exactly ₹20 difference allowed
            if sub_menu_item and abs(sub_menu_item.price - line.price) <= self.PRICE_TOLERANCE_RUPEES:
                # Apply substitution
                sub_item = OrderItem(
                    order_item_id=line.order_item_id,
                    order_id=line.order_id,
                    item_id=sub_menu_item.item_id,
                    price=sub_menu_item.price,
                    recipe_id=sub_menu_item.recipe_id,
                    brand_id=sub_menu_item.brand_id,
                )
                retained_items.append(sub_item)
                order.substitutions_applied.append(f"{line.item_id}->{sub_menu_item.item_id}")
            else:
                # No acceptable substitute -> item removed
                order.substitutions_applied.append(f"REMOVED:{line.item_id}")

        order.items = retained_items

        if not order.items:
            order.status = OrderStatus.CANCELLED
            order.routing_reason = "Order cancelled: All items stocked out and no valid substitutes available (BR-07)"
            return False

        return True
