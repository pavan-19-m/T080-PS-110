"""Dependency manager enforcing cooking predecessor constraints (BR-04)."""

from datetime import datetime
from typing import Dict, List, Optional

from src.models import OrderItem, Recipe


class DependencyManager:
    """Calculates prerequisite completion times for dependent recipes."""

    @staticmethod
    def get_earliest_start_for_item(
        item: OrderItem,
        recipes: Dict[str, Recipe],
        order_items: List[OrderItem],
        base_time: datetime
    ) -> datetime:
        """
        BR-04: Dependent items can start only after predecessor items finish.
        Returns the maximum completion time of any required predecessor items, or base_time.
        """
        recipe = recipes.get(item.recipe_id)
        if not recipe or not recipe.has_dependency:
            return base_time

        dep_recipe_id = recipe.dependency_recipe_id
        earliest_start = base_time

        # Find any predecessor items in this order with recipe_id == dep_recipe_id
        for other in order_items:
            if other.order_item_id != item.order_item_id and other.recipe_id == dep_recipe_id:
                if other.prep_end_time is not None:
                    if other.prep_end_time > earliest_start:
                        earliest_start = other.prep_end_time
                else:
                    # Predecessor not scheduled yet; will depend on order of scheduling
                    pass

        return earliest_start

    @staticmethod
    def sort_items_by_dependency(
        items: List[OrderItem],
        recipes: Dict[str, Recipe]
    ) -> List[OrderItem]:
        """Sort items topologically so independent items precede dependent items."""
        # Simple topological sort: items with no dependency come first
        independent = []
        dependent = []
        for it in items:
            rec = recipes.get(it.recipe_id)
            if rec and rec.has_dependency:
                dependent.append(it)
            else:
                independent.append(it)
        return independent + dependent
