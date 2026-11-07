"""Unit tests for all core domain models and entity behaviors."""

from datetime import datetime, time
import pytest

from src.models import (
    Batch,
    Brand,
    CancellationSource,
    Channel,
    CostCentre,
    DeliveryZone,
    Event,
    EventType,
    FinancialRecord,
    Kitchen,
    KitchenStatus,
    MenuItem,
    Order,
    OrderItem,
    OrderStatus,
    Recipe,
    SlotBooking,
    Station,
    StationSchedule,
    StationSlot,
    StationType,
)


def test_station_and_slots():
    """Verify Station initialization, slot creation, and load calculation."""
    station = Station(station_type=StationType.GRILL, capacity=2)
    assert station.capacity == 2
    assert len(station.slots) == 2
    assert station.get_remaining_load(datetime(2026, 11, 6, 12, 0, 0)) == 0.0

    # Add booking
    booking = SlotBooking(
        booking_id="B-1",
        item_id="ITM-PATTY",
        order_id="ORD-1",
        recipe_id="REC-PATTY",
        start_time=datetime(2026, 11, 6, 12, 0, 0),
        end_time=datetime(2026, 11, 6, 12, 8, 0),
        slot_id=1,
    )
    station.slots[0].bookings.append(booking)
    load = station.get_remaining_load(datetime(2026, 11, 6, 12, 0, 0))
    assert load == 8.0
    # At halfway point
    assert station.get_remaining_load(datetime(2026, 11, 6, 12, 4, 0)) == 4.0


def test_kitchen_operating_hours_and_status():
    """Verify Kitchen operating hours, overnight shifts, throttling and stockouts."""
    kitchen = Kitchen(
        kitchen_id="K-01",
        name="Central Kitchen",
        open_time=time(8, 0),
        close_time=time(23, 0),
        supported_brands={"B-01"},
        delivery_zones={"ZONE-1"},
    )
    assert kitchen.supports_brand("B-01")
    assert not kitchen.supports_brand("B-99")
    assert kitchen.serves_delivery_zone("ZONE-1")
    assert kitchen.is_operating_at(datetime(2026, 11, 6, 12, 0, 0))
    assert not kitchen.is_operating_at(datetime(2026, 11, 6, 6, 0, 0))

    # Throttling
    kitchen.mark_throttled()
    assert kitchen.is_throttled
    assert kitchen.status == KitchenStatus.THROTTLED
    kitchen.clear_throttled()
    assert not kitchen.is_throttled
    assert kitchen.status == KitchenStatus.OPERATIONAL

    # Stock-out
    kitchen.stock_out.add("ITM-FRIES")
    assert "ITM-FRIES" in kitchen.stock_out


def test_recipe_and_menu_item():
    """Verify Recipe and MenuItem attributes and dependency checks."""
    recipe_patty = Recipe("REC-PATTY", StationType.GRILL, 8, 4)
    recipe_burger = Recipe("REC-BURGER", StationType.COLD, 3, 2, dependency_recipe_id="REC-PATTY")

    assert not recipe_patty.has_dependency
    assert recipe_burger.has_dependency
    assert recipe_burger.dependency_recipe_id == "REC-PATTY"

    item = MenuItem("ITM-BURGER", "B-01", "Burger", 220.0, "REC-BURGER")
    assert item.price == 220.0
    assert item.recipe_id == "REC-BURGER"


def test_order_and_rush_logic():
    """Verify Order gross food value, RUSH thresholds and status."""
    item1 = OrderItem("1", "ORD-1", "ITM-1", 800.0, "REC-1")
    item2 = OrderItem("2", "ORD-1", "ITM-2", 800.0, "REC-2")
    order = Order(
        order_id="ORD-1",
        brand_id="B-01",
        items=[item1, item2],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
        channel_priority=False,
    )
    assert order.gross_food_value == 1600.0
    assert order.is_rush  # > 1500 triggers RUSH

    # Test small order without priority
    small_order = Order(
        order_id="ORD-2",
        brand_id="B-01",
        items=[item1],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
        channel_priority=False,
    )
    assert not small_order.is_rush

    # Small order with priority flag
    priority_order = Order(
        order_id="ORD-3",
        brand_id="B-01",
        items=[item1],
        channel=Channel.AGGREGATOR_A,
        delivery_zone="ZONE-1",
        order_time=datetime(2026, 11, 6, 12, 0, 0),
        channel_priority=True,
    )
    assert priority_order.is_rush


def test_batch_model():
    """Verify Batch window and capacity limits."""
    batch = Batch(
        batch_id="BATCH-1",
        recipe_id="REC-FRIES",
        station_type=StationType.FRYER,
        max_batch_size=3,
        first_order_time=datetime(2026, 11, 6, 12, 0, 0),
    )
    assert not batch.is_full
    assert batch.can_batch_with("REC-FRIES", datetime(2026, 11, 6, 12, 2, 0))
    # Different recipe
    assert not batch.can_batch_with("REC-WINGS", datetime(2026, 11, 6, 12, 1, 0))
    # Exceeding 3 minutes
    assert not batch.can_batch_with("REC-FRIES", datetime(2026, 11, 6, 12, 3, 1))


def test_station_schedule_model():
    """Verify StationSchedule container."""
    sched = StationSchedule(kitchen_id="K-1", station_type=StationType.WOK, capacity=2)
    assert len(sched.slots) == 2
    assert sched.total_bookings == 0


def test_event_model():
    """Verify Event and EventType parsing."""
    ev = Event(
        event_id="EV-1",
        event_type=EventType.from_str("STOCK_OUT"),
        timestamp=datetime(2026, 11, 6, 12, 0, 0),
        kitchen_id="K-01",
        item_id="ITM-NOODLES",
    )
    assert ev.event_type == EventType.STOCK_OUT
    assert ev.item_id == "ITM-NOODLES"
