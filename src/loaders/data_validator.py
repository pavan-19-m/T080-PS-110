"""Data validation utilities for domain entities, referential integrity, and dependency graphs."""

from datetime import datetime
from typing import Dict, List, Set, Optional

from src.models import (
    Brand,
    DeliveryZone,
    Event,
    EventType,
    Kitchen,
    MenuItem,
    Order,
    Recipe,
    Station,
    StationType,
)


class ValidationError(Exception):
    """Raised when data validation fails."""
    pass


class DataValidator:
    """Validates CSV data rows, schemas, referential integrity, and dependency graphs."""

    @staticmethod
    def validate_kitchen(kitchen: Kitchen) -> None:
        if not kitchen.kitchen_id:
            raise ValidationError("Kitchen ID cannot be empty")
        if not kitchen.name:
            raise ValidationError(f"Kitchen {kitchen.kitchen_id} must have a name")
        if kitchen.open_time is None or kitchen.close_time is None:
            raise ValidationError(f"Kitchen {kitchen.kitchen_id} must have valid open and close times")

    @staticmethod
    def validate_station(station: Station) -> None:
        if station.capacity <= 0:
            raise ValidationError(f"Station {station.station_type} capacity must be > 0 (found {station.capacity})")

    @staticmethod
    def validate_recipe(recipe: Recipe) -> None:
        if not recipe.recipe_id:
            raise ValidationError("Recipe ID cannot be empty")
        if recipe.prep_minutes <= 0:
            raise ValidationError(f"Recipe {recipe.recipe_id} prep_minutes must be > 0 (found {recipe.prep_minutes})")
        if recipe.max_batch_size <= 0:
            raise ValidationError(f"Recipe {recipe.recipe_id} max_batch_size must be > 0 (found {recipe.max_batch_size})")

    @staticmethod
    def validate_recipes_dependency_graph(recipes: Dict[str, Recipe]) -> None:
        """
        Validates referential integrity and detects circular dependencies among recipes.
        Raises ValidationError if a prerequisite recipe is missing or a cycle is detected.
        """
        for r_id, rec in recipes.items():
            if rec.has_dependency:
                dep_id = rec.dependency_recipe_id
                if dep_id not in recipes:
                    raise ValidationError(
                        f"Recipe {r_id} references missing predecessor recipe {dep_id}"
                    )
                # Check for cycle via depth-first search
                visited = {r_id}
                curr = dep_id
                while curr:
                    if curr in visited:
                        raise ValidationError(
                            f"Circular recipe dependency detected involving recipe {curr}"
                        )
                    visited.add(curr)
                    next_rec = recipes.get(curr)
                    curr = next_rec.dependency_recipe_id if next_rec and next_rec.has_dependency else None

    @staticmethod
    def validate_menu_item(item: MenuItem, brands: Dict[str, Brand], recipes: Dict[str, Recipe]) -> None:
        if not item.item_id:
            raise ValidationError("Item ID cannot be empty")
        if item.price < 0:
            raise ValidationError(f"Item {item.item_id} price cannot be negative (found {item.price})")
        if item.brand_id not in brands:
            raise ValidationError(f"Item {item.item_id} references unknown brand {item.brand_id}")
        if item.recipe_id not in recipes:
            raise ValidationError(f"Item {item.item_id} references unknown recipe {item.recipe_id}")

    @staticmethod
    def validate_order(
        order: Order,
        brands: Dict[str, Brand],
        zones: Dict[str, DeliveryZone],
        menu_items: Dict[str, MenuItem]
    ) -> None:
        if not order.order_id:
            raise ValidationError("Order ID cannot be empty")
        if order.brand_id not in brands:
            raise ValidationError(f"Order {order.order_id} references unknown brand {order.brand_id}")
        if order.delivery_zone not in zones:
            raise ValidationError(f"Order {order.order_id} references unknown delivery zone {order.delivery_zone}")
        if not order.items:
            raise ValidationError(f"Order {order.order_id} must have at least one item")

        brand = brands[order.brand_id]
        for it in order.items:
            if it.item_id not in menu_items:
                raise ValidationError(f"Order {order.order_id} contains unknown item {it.item_id}")
            if not brand.has_menu_item(it.item_id):
                raise ValidationError(f"Item {it.item_id} does not belong to brand {order.brand_id}")

    @staticmethod
    def validate_event(event: Event) -> None:
        if not event.event_id:
            raise ValidationError("Event ID cannot be empty")
        if not event.timestamp:
            raise ValidationError("Event must have a valid timestamp")


# Alias for backward compatibility
Validator = DataValidator
