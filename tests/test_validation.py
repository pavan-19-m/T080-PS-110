"""Unit tests for input validation, referential integrity, and dependency graph validation."""

from datetime import datetime, time
from pathlib import Path
import pytest

from src.loaders.data_validator import ValidationError, DataValidator, Validator
from src.loaders.csv_loader import CsvLoader
from src.models import (
    Brand,
    Channel,
    DeliveryZone,
    Event,
    EventType,
    Kitchen,
    MenuItem,
    Order,
    OrderItem,
    Recipe,
    Station,
    StationType,
)


def test_validate_kitchen_empty_id():
    k = Kitchen(kitchen_id="", name="Empty Hub", open_time=time(8, 0), close_time=time(22, 0))
    with pytest.raises(ValidationError, match="Kitchen ID cannot be empty"):
        Validator.validate_kitchen(k)


def test_validate_station_zero_or_negative_capacity():
    st = Station(station_type=StationType.GRILL, capacity=0)
    with pytest.raises(ValidationError, match="capacity must be > 0"):
        Validator.validate_station(st)


def test_validate_recipe_negative_prep():
    with pytest.raises(ValueError, match="prep_minutes must be > 0"):
        Recipe(recipe_id="REC-BAD", station_type=StationType.GRILL, prep_minutes=-5)


def test_validate_recipe_zero_batch():
    with pytest.raises(ValueError, match="max_batch_size must be > 0"):
        Recipe(recipe_id="REC-BAD", station_type=StationType.GRILL, prep_minutes=5, max_batch_size=0)


def test_validate_recipe_circular_dependency():
    """Validates that circular recipe dependencies are detected and rejected."""
    recipes = {
        "REC-A": Recipe("REC-A", StationType.GRILL, 5, dependency_recipe_id="REC-B"),
        "REC-B": Recipe("REC-B", StationType.COLD, 3, dependency_recipe_id="REC-A"),
    }
    with pytest.raises(ValidationError, match="Circular recipe dependency detected"):
        DataValidator.validate_recipes_dependency_graph(recipes)


def test_validate_recipe_missing_dependency():
    """Validates that references to non-existent predecessor recipes are caught."""
    recipes = {
        "REC-A": Recipe("REC-A", StationType.GRILL, 5, dependency_recipe_id="REC-NONEXISTENT"),
    }
    with pytest.raises(ValidationError, match="references missing predecessor recipe"):
        DataValidator.validate_recipes_dependency_graph(recipes)


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


def test_validate_menu_item_negative_price():
    with pytest.raises(ValueError, match="price cannot be negative"):
        MenuItem(item_id="ITM-1", brand_id="B-01", name="Item", price=-50.0, recipe_id="REC-1")


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


def test_validate_order_empty_items():
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    zones = {"ZONE-1": DeliveryZone("ZONE-1", 15, {"K-01"})}
    menu_items = {"ITM-1": MenuItem("ITM-1", "B-01", "Burger", 150.0, "REC-1")}

    order = Order(
        order_id="ORD-EMPTY",
        brand_id="B-01",
        items=[],
        channel=Channel.OWN_APP,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
    )

    with pytest.raises(ValidationError, match="must have at least one item"):
        Validator.validate_order(order, brands, zones, menu_items)


def test_validate_event_empty_id():
    ev = Event(event_id="", event_type=EventType.STOCK_OUT, timestamp=datetime(2026, 11, 6, 12, 0, 0))
    with pytest.raises(ValidationError, match="Event ID cannot be empty"):
        Validator.validate_event(ev)


def test_csv_loader_item_quantity_parsing(tmp_path):
    """Verify that orders with 'ITEM:QTY' tokens are properly parsed into multiple items."""
    orders_csv = tmp_path / "orders.csv"
    orders_csv.write_text(
        "order_id,brand_id,items,channel,delivery_zone,order_time,channel_priority\n"
        "ORD-QTY,B-01,ITM-1:3;ITM-2:2,OWN_APP,ZONE-1,2026-11-06 12:00:00,false\n",
        encoding="utf-8"
    )
    brands = {"B-01": Brand("B-01", "BurgerCraze")}
    zones = {"ZONE-1": DeliveryZone("ZONE-1", 15, {"K-01"})}
    rec1 = Recipe("REC-1", StationType.GRILL, 5)
    rec2 = Recipe("REC-2", StationType.FRYER, 3)
    recipes = {"REC-1": rec1, "REC-2": rec2}
    itm1 = MenuItem("ITM-1", "B-01", "Burger", 100.0, "REC-1")
    itm2 = MenuItem("ITM-2", "B-01", "Fries", 50.0, "REC-2")
    brands["B-01"].add_menu_item(itm1)
    brands["B-01"].add_menu_item(itm2)
    menu_items = {"ITM-1": itm1, "ITM-2": itm2}

    loader = CsvLoader(tmp_path)
    loaded = loader.load_orders(brands, zones, menu_items, recipes, filename="orders.csv")

    assert len(loaded) == 1
    order = loaded[0]
    # 3 burgers + 2 fries = 5 total OrderItems
    assert len(order.items) == 5
    assert sum(1 for it in order.items if it.item_id == "ITM-1") == 3
    assert sum(1 for it in order.items if it.item_id == "ITM-2") == 2
    assert order.gross_food_value == 400.0  # (3 * 100) + (2 * 50)
