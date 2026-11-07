"""Unit tests for input validation and referential integrity."""

from datetime import datetime, time
import pytest

from src.input.validator import ValidationError, Validator
from src.models import (
    Brand,
    Channel,
    DeliveryZone,
    Kitchen,
    MenuItem,
    Order,
    OrderItem,
    Recipe,
    StationType,
)


def test_validate_kitchen_empty_id():
    k = Kitchen(kitchen_id="", name="Empty Hub", open_time=time(8, 0), close_time=time(22, 0))
    with pytest.raises(ValidationError, match="Kitchen ID cannot be empty"):
        Validator.validate_kitchen(k)


def test_validate_recipe_negative_prep():
    with pytest.raises(ValueError, match="prep_minutes must be > 0"):
        Recipe(recipe_id="REC-BAD", station_type=StationType.GRILL, prep_minutes=-5)


def test_validate_recipe_zero_batch():
    with pytest.raises(ValueError, match="max_batch_size must be > 0"):
        Recipe(recipe_id="REC-BAD", station_type=StationType.GRILL, prep_minutes=5, max_batch_size=0)


def test_validate_menu_item_unknown_brand():
    item = MenuItem(item_id="ITM-1", brand_id="B-UNKNOWN", name="Item", price=100.0, recipe_id="REC-1")
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    recipes = {"REC-1": Recipe("REC-1", StationType.GRILL, prep_minutes=5)}

    with pytest.raises(ValidationError, match="references unknown brand"):
        Validator.validate_menu_item(item, brands, recipes)


def test_validate_menu_item_unknown_recipe():
    item = MenuItem(item_id="ITM-1", brand_id="B-01", name="Item", price=100.0, recipe_id="REC-UNKNOWN")
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    recipes = {"REC-1": Recipe("REC-1", StationType.GRILL, prep_minutes=5)}

    with pytest.raises(ValidationError, match="references unknown recipe"):
        Validator.validate_menu_item(item, brands, recipes)


def test_validate_order_unknown_brand():
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    zones = {"ZONE-1": DeliveryZone("ZONE-1", 15, {"K-01"})}
    menu_items = {"ITM-1": MenuItem("ITM-1", "B-01", "Burger", 150.0, "REC-1")}

    order = Order(
        order_id="ORD-BAD",
        brand_id="B-UNKNOWN",
        items=[OrderItem("1", "ORD-BAD", "ITM-1", 150.0, "REC-1")],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    with pytest.raises(ValidationError, match="references unknown brand"):
        Validator.validate_order(order, brands, zones, menu_items)


def test_validate_order_unknown_zone():
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    zones = {"ZONE-1": DeliveryZone("ZONE-1", 15, {"K-01"})}
    menu_items = {"ITM-1": MenuItem("ITM-1", "B-01", "Burger", 150.0, "REC-1")}

    order = Order(
        order_id="ORD-BAD",
        brand_id="B-01",
        items=[OrderItem("1", "ORD-BAD", "ITM-1", 150.0, "REC-1")],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-UNKNOWN",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    with pytest.raises(ValidationError, match="references unknown delivery zone"):
        Validator.validate_order(order, brands, zones, menu_items)
